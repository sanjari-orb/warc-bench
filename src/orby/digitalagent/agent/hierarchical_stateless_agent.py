from copy import deepcopy

from orby.digitalagent.agent import Agent
from orby.digitalagent.model import FoundationModel
from orby.digitalagent.agent.utils import prompt_to_messages, remove_thinking
from orby.digitalagent.utils.image_utils import download_image_as_numpy_array
from orby.digitalagent.prompts.prompts_20241007 import _trace_string
from orby.digitalagent.prompts.default import hierarchical_stateless as prompts


class HierarchicalStatelessFMAgent(Agent):
    def __init__(self, model_configs: dict, actions: str, limit_to_ctx: bool = True):
        Agent.__init__(self)
        self.model_configs = model_configs
        self.model = FoundationModel(**model_configs) if model_configs else None
        self.actions = actions
        self.limit_to_ctx = limit_to_ctx
        self.plan_history = []

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

    def _planning_prompt(self):
        trace_string = _trace_string(self)

        variables = {
            "goal": self.goal,
            "actions": self.actions,
            "trace_string": trace_string,
            "html": self.html_history[-1],
            "goal_images": self.goal_images,
            "screenshot": self.screenshot_history[-1],
            "plan_history": self.plan_history,
            "original_screenshot": self.screenshot_history[0],
        }

        if len(self.plan_history) > 0:
            variables["original_plan"] = self.plan_history[0]

        prompt, images = prompts.render(**variables, block="planning")
        messages = prompt_to_messages(prompt, images=images)

        return messages

    def _execution_prompt(self, plan: str):
        trace_string = _trace_string(self)

        variables = {
            "goal": plan,
            "actions": self.actions,
            "trace_string": trace_string,
            "html": self.html_history[-1],
            "plan": plan,
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

        prompt, images = prompts.render(**variables, block="grounding")
        messages = prompt_to_messages(prompt, images=images)

        return messages

    def act(self, **kwargs):
        planning_messages = self._planning_prompt()
        plan, _ = self.model.generate(
            messages=planning_messages, return_raw=True, **kwargs
        )

        plan = remove_thinking(plan)
        self.plan_history.append(plan)

        execution_messages = self._execution_prompt(plan)
        action, _ = self.model.generate(
            messages=execution_messages, return_raw=True, **kwargs
        )

        action = remove_thinking(action)

        meta = {}
        return action, meta

    def get_state_dict(self) -> dict:
        state_dict = super().get_state_dict()

        state_dict["plan_history"] = deepcopy(self.plan_history)

        return state_dict

    def load_state_dict(self, state_dict: dict) -> None:
        self.plan_history = state_dict["plan_history"]

        super().load_state_dict(state_dict)
