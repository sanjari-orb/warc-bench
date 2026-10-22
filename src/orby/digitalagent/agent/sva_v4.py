import ast
import inspect
from dataclasses import dataclass

from orby.digitalagent.agent import Agent
from orby.digitalagent.model import FoundationModel
from orby.digitalagent.agent.utils import prompt_to_messages
from orby.digitalagent.prompts.default import sva_v4 as prompts
from orby.digitalagent.prompts.default import sva_v4_note as note_prompts
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

    # The prompt template, the response tag that holds the model's step text,
    # and the tag used for that text in the step history.
    PROMPT = prompts
    THINKING_TAG = SVA_THINKING_TAG
    HISTORY_TAG = "thought"

    # For models that answer on a 0-1000 grid (coordinate_space
    # "normalized_1000"), this prompt sentence is replaced so the prompt
    # states the grid instead of pixels.
    PIXEL_COORDINATES_SENTENCE = (
        "Pixel coordinates originate from the top left corner of the image, where the first "
        "coordinate refers to the horizontal/width axis and the second refers to the vertical/height axis."
    )
    NORMALIZED_COORDINATES_SENTENCE = (
        "Coordinates are integers on a 0 to 1000 grid over this screenshot, independent of its size in "
        "pixels: (0, 0) is the top left corner and (1000, 1000) the bottom right, where the first coordinate "
        "refers to the horizontal/width axis and the second refers to the vertical/height axis. "
        "Use this grid for every x and y in your actions."
    )
    # Action arguments that are screen positions, by axis. scroll's delta_x and
    # delta_y are distances, so they stay as they are.
    COORDINATE_ARGS = {
        "click": {"x": "x", "y": "y"},
        "hover": {"x": "x", "y": "y"},
        "type": {"x": "x", "y": "y"},
        "scroll": {"x": "x", "y": "y"},
        "drag_and_release": {"x1": "x", "y1": "y", "x2": "x", "y2": "y"},
    }

    def __init__(
        self,
        actions: str,
        model_configs: dict,
        action_history_length: int = 5,
    ):
        super().__init__()

        # Single model for both evaluation and action generation. The
        # coordinate convention is for the agent, not the API, so take it out.
        self.model_configs = dict(model_configs)
        self.coordinate_space = self.model_configs.pop("coordinate_space", None)
        if self.coordinate_space not in (None, "normalized_1000"):
            raise ValueError(f"Unknown coordinate_space: {self.coordinate_space!r}")
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
        prompt, images = self.PROMPT.render(**variables)
        if self.coordinate_space == "normalized_1000":
            if self.PIXEL_COORDINATES_SENTENCE not in prompt:
                raise ValueError("The prompt has no pixel-coordinate sentence to replace.")
            prompt = prompt.replace(self.PIXEL_COORDINATES_SENTENCE, self.NORMALIZED_COORDINATES_SENTENCE)
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
            text_response, [self.THINKING_TAG, SVA_ACTION_TAG]
        )
        thinking, action = contents[self.THINKING_TAG], contents[SVA_ACTION_TAG]

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
        if self.coordinate_space == "normalized_1000":
            action = self._grid_to_pixels(action)
        return eval(action)

    def _grid_to_pixels(self, action: str) -> str:
        """Rewrite an action's 0-1000 grid positions as pixels of the current screenshot.

        x_px = round(x * width / 1000) and y_px = round(y * height / 1000),
        after clamping to 0-1000 (edge positions can come back slightly outside
        the grid), capped at the last pixel. Arguments must be literals; anything else raises
        ValueError, which fails the step like any other invalid action.
        """
        try:
            call = ast.parse(action.strip(), mode="eval").body
        except SyntaxError as ex:
            raise ValueError(f"Invalid action: {action}") from ex
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
            raise ValueError(f"Invalid action: {action}")
        name = call.func.id
        axes = self.COORDINATE_ARGS.get(name)
        if not axes:
            return action
        try:
            args = [ast.literal_eval(a) for a in call.args]
            kwargs = {k.arg: ast.literal_eval(k.value) for k in call.keywords}
            bound = inspect.signature(getattr(BrowserGymActions, name)).bind(*args, **kwargs)
        except (ValueError, TypeError, SyntaxError) as ex:
            raise ValueError(f"Invalid action: {action}") from ex
        height, width = self.screenshot_history[-1].shape[:2]
        size = {"x": width, "y": height}
        for arg, axis in axes.items():
            value = bound.arguments.get(arg)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"Invalid {arg} in action: {action}")
            pixel = round(min(max(value, 0), 1000) * size[axis] / 1000)
            # 1000 maps to one past the last pixel; keep it on screen.
            bound.arguments[arg] = min(pixel, size[axis] - 1)
        return f"{name}(" + ", ".join(f"{k}={v!r}" for k, v in bound.arguments.items()) + ")"

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
            history_str += f"<{self.HISTORY_TAG}>{thought}</{self.HISTORY_TAG}>\n"
            history_str += f"<action>{action}</action>\n"
            history_str += "\n"

        # Remove the last newline
        history_str = history_str.rstrip()

        return image_dict, history_str


class SvaV4Note(SvaV4):
    """
    SVA V4 with a prompt that does not ask for written-out reasoning.

    The model reasons internally and replies with a one-line <note> for the
    step history plus the action. Claude Opus 5.5 declines the original
    prompt, which asks for the reasoning in a visible <thinking> section.
    """

    PROMPT = note_prompts
    THINKING_TAG = "note"
    HISTORY_TAG = "note"
