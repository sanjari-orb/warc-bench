from copy import deepcopy

from orby.digitalagent.agent import Agent
from orby.digitalagent.model import FoundationModel
from orby.digitalagent.agent.utils import prompt_to_messages, remove_thinking
from orby.digitalagent.utils.image_utils import download_image_as_numpy_array
from orby.digitalagent.prompts.prompts_20241007 import _trace_string
from orby.digitalagent.prompts.default import basic_stateless as prompts


class BasicStatelessFMAgent(Agent):
    def __init__(self, model_configs: dict, actions: str, limit_to_ctx: bool = True):
        Agent.__init__(self)
        self.model_configs = model_configs
        self.model = FoundationModel(**model_configs) if model_configs else None
        self.actions = actions
        self.limit_to_ctx = limit_to_ctx

    def reset(self, goal, html, screenshot, goal_image_urls=[]):
        self.goal = goal
        self.goal_images = [
            download_image_as_numpy_array(url) for url in goal_image_urls
        ]
        self.html_history = [html]
        self.screenshot_history = [screenshot]

    def update(self, html, screenshot, trace):
        self.trace = trace

        self.html_history.append(html)
        self.screenshot_history.append(screenshot)

    def act(self, **kwargs):
        # Build prompt
        if len(self.trace) > 0:
            trace_string = _trace_string(self)
        else:
            trace_string = ""

        variables = {
            "goal": self.goal,
            "actions": self.actions,
            "trace_string": trace_string,
            "html": self.html_history[-1],
            "screenshot_width": self.screenshot_history[-1].shape[1],
            "screenshot_height": self.screenshot_history[-1].shape[0],
            "goal_images": self.goal_images,
            "screenshot": self.screenshot_history[-1],
            "prev_screenshot": (
                self.screenshot_history[-2]
                if len(self.screenshot_history) > 1
                else None
            ),
        }

        prompt, images = prompts.render(**variables)

        messages = prompt_to_messages(prompt, images=images)

        # Execute prompt
        action, response = self.model.generate(
            messages=messages, return_raw=True, **kwargs
        )

        action = remove_thinking(action)

        meta = {}
        return action, meta
