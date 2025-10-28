from copy import deepcopy

from orby.digitalagent.agent import Agent
from orby.digitalagent.model import FoundationModel
from orby.digitalagent.utils.action_utils import clean_action
from orby.digitalagent.agent.utils import (
    screenshots_differ,
    prompt_to_messages,
    remove_thinking,
)
from orby.digitalagent.utils.image_utils import download_image_as_numpy_array
from orby.digitalagent.prompts.default import pixel_coord_executor
from orby.digitalagent.utils.action_utils import (
    determine_error_type,
    READABLE_ERROR_MESSAGES,
    ActionError,
)
from orby.digitalagent.utils.action_parsing_utils import extract_key_value_pairs


class PixelCoordExecutorAgent(Agent):
    """
    An agent that is capable of completing simpler tasks that require <5 steps to complete.
    """

    def __init__(
        self, model_configs: dict, actions: str, limit_to_ctx: bool = True, **kwargs
    ):
        Agent.__init__(self, **kwargs)
        self.model_configs = model_configs
        self.actions = actions
        self.model = FoundationModel(**model_configs) if model_configs else None
        self.limit_to_ctx = limit_to_ctx
        self.template = pixel_coord_executor

    def reset(self, goal, html, screenshot, goal_image_urls=[]):
        self.goal = goal
        self.goal_images = [
            download_image_as_numpy_array(url) for url in goal_image_urls
        ]
        self.html_history = [html]
        self.screenshot_history = [screenshot]
        self.trace = []

    def update(self, html, screenshot, trace):
        self.html_history.append(html)
        self.screenshot_history.append(screenshot)

    def _execution_prompt(self, trace_string: str):
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

        prompt, images = self.template.render(**variables)
        messages = prompt_to_messages(prompt, images=images)

        return messages

    def act(self, environment_feedback, **kwargs):
        """
        Takes the screenshot, HTML, and current planned action, and generates the grounded action
        """
        if not environment_feedback:
            if len(self.screenshot_history) >= 2:
                if screenshots_differ(
                    self.screenshot_history[-1], self.screenshot_history[-2]
                ):
                    environment_feedback = "Success."
                else:
                    environment_feedback = "Nothing happened."
            else:
                environment_feedback = "Executed."
        else:
            error_type = determine_error_type(environment_feedback)
            if error_type != ActionError.UNKNOWN:
                environment_feedback = READABLE_ERROR_MESSAGES[error_type]
        if self.trace:
            self.trace[-1][1] = environment_feedback
        execution_messages = self._execution_prompt(
            "\n".join([f"{step[0]}: {step[1]}" for step in self.trace])
        )
        output = self.model.generate(messages=execution_messages, **kwargs)
        output = remove_thinking(output)
        meta = extract_key_value_pairs(output, ["Action", "Description"])
        action_description = meta.get("Description", "")
        action = meta.get("Action", "")
        self.trace.append(
            [f"{action_description} - {action}" if action_description else action, ""]
        )
        return action
