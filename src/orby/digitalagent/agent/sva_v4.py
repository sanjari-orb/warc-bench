from dataclasses import dataclass

from orby.digitalagent.agent import Agent
from orby.digitalagent.model import FoundationModel
from orby.digitalagent.agent.utils import prompt_to_messages
from orby.digitalagent.prompts.default import sva_v4 as prompts
from orby.digitalagent.utils.action_parsing_utils import (
    extract_content_by_tags,
    extract_action,
)
from orby.digitalagent.actions.browsergym_actions import (
    BrowserGymActions,
    click,
    complete,
    drag_and_release,
    hover,
    key_press,
    scroll,
    type,
    wait,
)

SVA_THINKING_TAG = "thinking"
SVA_ACTION_TAG = "action"


@dataclass
class ExecutorResponse:
    """
    The response from the executor model
    """
    action: str
    thinking: str


class SvaV4(Agent):
    """
    The SVA V4 agent is a pure-vision agent aims to complete short-horizon tasks (typically 5 steps or less).
    It uses a single model call that first evaluates if the goal is achieved, then generates the appropriate action.
    
    Building on SVA V3, the key difference is:
    - Single model call instead of separate reward model + executor calls.
      Model first evaluates task completion, then generates action based on that evaluation.
      More efficient and potentially more coherent reasoning.
    """

    def __init__(
        self,
        actions: str,
        model_configs: dict,
        action_history_length: int = 5,
    ):
        super().__init__()

        # Single model for both evaluation and action generation
        self.model_configs = model_configs
        self.model = FoundationModel(**self.model_configs)

        # The action hints are the actions that the agent can take as a string
        # NOTE: the input actions is NOT used because we define our own action space
        self.action_hints = BrowserGymActions.print_docstrings()

        # The goal of the current task
        self.goal = None

        # The history of all screenshots, including the current screenshot
        self.screenshot_history = []

        # The action and thought history of the agent
        self.response_history = None

        # The action history length
        self.action_history_length = (
            action_history_length if action_history_length >= 0 else -1
        )

    def reset(self, goal, html, screenshot, goal_image_urls=[]):
        self.goal = goal
        self.screenshot_history = [screenshot]
        self.response_history = []

    def update(self, html, screenshot, trace):
        self.screenshot_history.append(screenshot)
        self.screenshot_history = self.screenshot_history[
            -(self.action_history_length + 1) :
        ]

    def act(self, **kwargs):
        # The trace_generate() in agent.py wraps the act method of every agent
        # and append the llm trace to the agent.llm_trace field. For child classes
        # that inherit from SvaV4, we need to call the _act method instead of act
        # to avoid duplicate tracing. Otherwise, the llm_trace field will contain
        # duplicate traces.
        return self._act(**kwargs)

    def _act(self, **kwargs):
        """Single model call for both evaluation and action generation"""
        image_dict, history_str = self._create_history_str()

        variables = {
            "goal": self.goal,
            "action_hints": self.action_hints,
            "current_screenshot": self.screenshot_history[-1],
            "history": history_str,
        }
        variables.update(image_dict)

        # Single model call that handles both evaluation and action generation
        prompt, images = prompts.render(**variables)
        messages = prompt_to_messages(prompt, images=images)
        model_response = self.model.generate(messages=messages, **kwargs)

        executor_response = self._parse_model_response(model_response)
        
        # Update response history for all actions (including complete)
        if self.action_history_length != 0:
            self.response_history.append(
                [executor_response.thinking, executor_response.action]
            )
            if self.action_history_length > 0:
                self.response_history = self.response_history[
                    -self.action_history_length :
                ]

        # Convert the action string to a browsergym action
        action = self._convert_response_to_browsergym_action(
            executor_response.action
        )

        print("Grounded action:", action)
        return action, {}

    def _parse_model_response(self, text_response: str) -> ExecutorResponse:
        """
        Parse the model response that contains thinking and action.
        Expected format:
        <thinking>THINKING</thinking>
        <action>ACTION</action>

        Args:
            text_response (str): The response from the model

        Returns:
            ExecutorResponse: The action and the thinking

        Raises:
            ValueError: If the action is not found in the response
        """
        contents = extract_content_by_tags(
            text_response, [SVA_THINKING_TAG, SVA_ACTION_TAG]
        )
        thinking, action = contents[SVA_THINKING_TAG], contents[SVA_ACTION_TAG]

        if thinking is not None:
            thinking = thinking.strip().replace("\n", " ")
        else:
            thinking = ""
        if action is not None:
            action = action.strip()
        if not action:
            raise ValueError(f"No action found in the response: {text_response}")

        return ExecutorResponse(action, thinking)

    # TODO: consider moving this to the action space class
    def _convert_response_to_browsergym_action(self, action: str) -> str:
        """
        Convert the response to an action
        """
        if extract_action(action) not in BrowserGymActions.get_action_space():
            raise ValueError(f"Invalid action: {action}")
        return eval(action)

    def _create_history_str(self) -> tuple[dict, str]:
        """
        Create a string representation of the action history

        Returns:
            tuple[dict, str]: The image dictionary and the history string
        """
        history_str = ""
        image_dict = {}

        assert len(self.screenshot_history) - 1 == len(self.response_history)

        for i, (screenshot, (thought, action)) in enumerate(
            zip(self.screenshot_history[:-1], self.response_history)
        ):
            # Add the screenshot to the image dictionary for prompt rendering
            image_name = f"screenshot_{i+1}"
            image_dict[image_name] = screenshot

            # Add the thought and action to the history string
            history_str += f"Step {i+1}:\n"
            history_str += f"<image:{image_name}>"
            history_str += f"<thought>{thought}</thought>\n"
            history_str += f"<action>{action}</action>\n"
            history_str += "\n"

        # Remove the last newline
        history_str = history_str.rstrip()

        return image_dict, history_str
