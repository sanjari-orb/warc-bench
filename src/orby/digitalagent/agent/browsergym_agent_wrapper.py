import os
from typing import Type, Any
from PIL import Image
import numpy as np

from browsergym.core.action.highlevel import HighLevelActionSet
from orby.digitalagent.agent.agent import Agent
from browsergym.utils.obs import flatten_axtree_to_str
from orby.digitalagent.utils import dom_utils
from orby.digitalagent.utils import action_utils
from orby.digitalagent.utils.action_utils import reground_bid_to_coord_action


class BrowserGymAgentWrapper:
    """A wrapper class that parses BrowserGym observations for the underlying agent and inform the configuration of BrowserGym env for evaluating the agent."""

    def __init__(
        self,
        agent_cls: Type[Agent],
        action_subsets: list[str] = ["bid", "coord"],
        use_orbot_dom: bool = False,
        orbot_dom_options: dict[
            str, Any
        ] = {},  # kwargs used in calling dom_utils.html_to_string
        use_normalized_coords: bool = False,
        coordinate_multiplier: float = 1,
        allow_multiple_actions: bool = False,
        max_html_tokens: int = -1,
        bid_to_coordinate_conversion: bool = False,
        mac_screenshot_size_reduction: bool = False,
        **kwargs,
    ):
        self.action_subsets = action_subsets
        self.use_orbot_dom = use_orbot_dom
        self.orbot_dom_options = orbot_dom_options
        self.use_normalized_coords = use_normalized_coords
        self.coordinate_multiplier = coordinate_multiplier
        self.allow_multiple_actions = allow_multiple_actions
        self.bid_to_coordinate_conversion = bid_to_coordinate_conversion
        self.trace = []
        self.max_html_tokens = max_html_tokens
        self.mac_screenshot_size_reduction = mac_screenshot_size_reduction

        if max_html_tokens > 0:
            # TODO: Make tokenizer configurable
            from transformers import AutoProcessor

            self.tokenizer = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-7B-Instruct")

        self.action_set = HighLevelActionSet(
            subsets=action_subsets,  # allow the agent to also use x,y coordinates
            strict=False,  # less strict on the parsing of the actions
            multiaction=self.allow_multiple_actions,  # disable to agent to take multiple actions at once
            demo_mode="off",  # disable visual effects
        )

        action_headers = self.action_set.describe(
            with_long_description=True, with_examples=True
        )
        self.agent = agent_cls(actions=action_headers, **kwargs)

    @property
    def llm_trace(self):
        return self.agent.llm_trace

    def _extract_obs(self, obs: dict):
        if self.use_orbot_dom and "orby_root_element" in obs and obs["orby_root_element"] is not None:
            html = dom_utils.html_to_string(
                obs["orby_root_element"], **self.orbot_dom_options
            )
        elif "orby_root_element" in obs and obs["orby_root_element"] is None and obs["axtree_object"] is None:
            html = None
        else:
            html = None
             
        if self.max_html_tokens > 0:

            def count_tokens(text: str) -> int:
                return len(self.tokenizer(text=text)["input_ids"][0])

            if count_tokens(html) > self.max_html_tokens:
                html = dom_utils.compress_dom(
                    obs["orby_root_element"],
                    self.orbot_dom_options,
                    count_tokens,
                    self.max_html_tokens,
                )

        screenshot = obs["screenshot"]
        if self.mac_screenshot_size_reduction:
            # Reduce screenshot size by 2x using PIL
            screenshot_pil = Image.fromarray(screenshot)
            screenshot_pil = screenshot_pil.resize(
                (screenshot_pil.width // 2, screenshot_pil.height // 2),
                Image.Resampling.LANCZOS,
            )
            screenshot = np.array(screenshot_pil)

        return html, screenshot

    def reset(self, obs: dict):
        goal = obs["goal"]
        goal_image_urls = [
            obj["image_url"]["url"].replace("__HOMEPAGE__", os.environ["VWA_HOMEPAGE"])
            for obj in obs["goal_object"]
            if obj["type"] == "image"
        ]
        html, screenshot = self._extract_obs(obs)
        self.agent.reset(goal, html, screenshot, goal_image_urls=goal_image_urls)
        self.trace = []

    def act(self, obs: dict) -> tuple[str, dict]:
        """Returns the next action and metadata (for recording purposes)."""
        if self.trace:
            self.trace[-1] = (self.trace[-1][0], obs["last_action_error"])
            html, screenshot = self._extract_obs(obs)
            print('Debug: screenshot size: ', screenshot.shape)
            self.agent.update(
                html,
                screenshot,
                self.trace,
            )
        action, metadata = self.agent.act()
        action = action_utils.clean_action(action)
        # BrowserGym cannot handle an action that spans multiple lines.
        # We need to escape the newlines in the action.
        if action.startswith("send_msg_to_user") or action.startswith(
            "report_infeasible"
        ):
            action = action.replace("\n", "\\n")

        if self.bid_to_coordinate_conversion:
            # Try to re-ground the bid action to a coordinate action
            # If the conversion is available
            screenshot_pil = Image.fromarray(obs["screenshot"])
            viewport_width, viewport_height = screenshot_pil.size
            action = reground_bid_to_coord_action(
                action, obs["orby_root_element"], viewport_width, viewport_height
            )

        self.trace.append((action, ""))
        return action, metadata


def wrap_agent_cls(
    agent_cls: Type[Agent],
    action_subsets: list[str] = ["bid", "coord", "chat", "infeas"],
    use_orbot_dom: bool = False,
    use_normalized_coords: bool = False,
    allow_multiple_actions: bool = False,
    **kwargs,
):
    def builder(**builder_kwargs):
        kwargs.update(builder_kwargs)
        return BrowserGymAgentWrapper(
            agent_cls,
            action_subsets=action_subsets,
            use_orbot_dom=use_orbot_dom,
            use_normalized_coords=use_normalized_coords,
            allow_multiple_actions=allow_multiple_actions,
            **kwargs,
        )

    return builder
