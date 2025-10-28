from dataclasses import dataclass
from typing import Literal

from orby.digitalagent.agent import Agent
from orby.digitalagent.model import FoundationModel
from orby.digitalagent.agent.agent import trace_generate
from orby.digitalagent.agent.utils import prompt_to_messages
from orby.digitalagent.prompts.default import sva_v2 as prompts
from orby.digitalagent.utils.action_parsing_utils import extract_content_by_tags
from orby.digitalagent.vision_grounder import ClaudeVisionGrounder
from orby.digitalagent.utils.action_parsing_utils import extract_action


SVA_THINKING_TAG = "thinking"
SVA_ACTION_TAG = "action"
SVA_SHOULD_END_TAG = "should_end"
SVA_GOAL_ACHIEVED_TAG = "goal_achieved"
SVA_ANSWER_TAG = "answer"
SVA_REASONING_TAG = "reasoning"
SVA_RETURN_ACTION = "send_msg_to_user"
SVA_REPORT_INFEASIBLE_ACTION = "report_infeasible"
SVA_DEFAULT_ANSWER = "Task completed successfully."
SVA_DEFAULT_INFEASIBLE_REASONING = "Task deemed infeasible."

SVA_V2_EXECUTOR_ACTIONS = ["noop", "scroll", "hover", "click", "type", "drag_and_drop"]
SVA_V2_EXECUTOR_ACTION_HINTS = """\
noop(wait_ms: float = 1000)
    Do nothing and wait.
    Args:
        wait_ms (float): The amount of time to wait in milliseconds.
    Examples:
        noop()
        noop(500)

scroll(<ELEMENT_DESCRIPTION>, delta_x: float, delta_y: float)
    Scroll horizontally and vertically.
    Args:
        <ELEMENT_DESCRIPTION> (str): The description of the element to scroll over. Be specific about what the element is and where it is.
        delta_x (float): The amount to scroll horizontally.
        delta_y (float): The amount to scroll vertically.
    Examples:
        scroll("The left menu column with the name 'Navigation'", 0, 200)

hover(<ELEMENT_DESCRIPTION>)
    Move the mouse to hover over and focus on a location.
    Args:
        <ELEMENT_DESCRIPTION> (str): The description of the element to move the mouse to. Be specific about what the element is and where it is.
    Examples:
        mouse_move("The small + sign in the top right corner of the page used to create a new chat")

click(<ELEMENT_DESCRIPTION>, button: Literal['left', 'middle', 'right'] = 'left', clicks: int = 1)
    Move the mouse to a location and click a mouse button.
    Args:
        <ELEMENT_DESCRIPTION> (str): The description of the element to click on. Be specific about what the element is and where it is.
        button (Literal['left', 'middle', 'right']): The button to click.
        clicks (int): The number of clicks to perform.
    Examples:
        mouse_click("Send email button")
        mouse_click("Click the box to agree to the terms of service", button="left")

type(<ELEMENT_DESCRIPTION>, text: str, press_enter: bool = False)
    Types a string of text through the keyboard.
    Args:
        <ELEMENT_DESCRIPTION> (str): The description of the element to type text on. Be specific about what the element is and where it is.
        text (str): The text to type.
        press_enter (bool): Whether to press enter after typing the text.
    Examples:
        keyboard_type("The search bar", "Hello world!")
        keyboard_type("The search bar", "Hello world!", press_enter=True)

drag_and_drop(<ELEMENT_DESCRIPTION_1>, <ELEMENT_DESCRIPTION_2>)
    Drag and drop from a location to a location.
    Args:
        <ELEMENT_DESCRIPTION_1> (str): The description of the element to drag from. Be specific about what the element is and where it is.
        <ELEMENT_DESCRIPTION_2> (str): The description of the element to drag to. Be specific about what the element is and where it is.
    Examples:
        mouse_drag_and_drop("The slider button for volume control in the bottom left corner of the screen", "The middle of the slider for volume control")
"""


@dataclass
class RewardModelResponse:
    """
    The response from the reward model
    """

    should_end: bool
    goal_achieved: bool
    answer: str
    reasoning: str


@dataclass
class ExecutorResponse:
    """
    The response from the executor model
    """

    action: str
    thinking: str


class SvaV2(Agent):
    """
    The Subtask Vision Agent V2 builds on top of the V1 agent with several key changes:
    - Split responsibility between the exuector and a pure-vision grounder.
    - The executor's action space is now changed to be more focused on outputting natural language
        descriptions of the elements to be interacted with.
    - The grounder takes care of converting the natural language descriptions into coordinates.
    """

    def __init__(
        self,
        actions: str,
        model_configs: dict,
        grounder_model_name: Literal["claude", "nova"] = "claude",
    ):
        Agent.__init__(self)

        # The same model is used for both the executor and the reward model
        # The executor model is used to generate the action and CoT
        # The reward model is used to evaluate if the goal is achieved and optionally provide an answer
        self.model_configs = model_configs
        self.model = FoundationModel(**self.model_configs)

        # The grounder model is used to convert the natural language descriptions into coordinates
        self.grounder_model_name = grounder_model_name
        if self.grounder_model_name == "claude":
            # We need to wrap the ground method in a wrapper to trace the LLM calls
            ClaudeVisionGrounder.ground = trace_generate(ClaudeVisionGrounder.ground)
            self.grounder = ClaudeVisionGrounder()
            self.grounder.parent_agent = self
            self.grounder.llm_trace = []
        elif self.grounder_model_name == "nova":
            raise NotImplementedError(
                "Amazon Nova Act vision grounder is not yet supported."
            )
        else:
            raise ValueError(f"Invalid grounder model name: {self.grounder_model_name}")

        # The action hints are the actions that the agent can take as a string
        # WARNING: the provided action space string is not used in the prompt
        # We create our own action space
        self.action_hints = SVA_V2_EXECUTOR_ACTION_HINTS

        # The goal of the current task
        self.goal = None

        # The current screenshot of the task
        self.current_screenshot = None

        # The action history of the agent
        self.history = None

    def reset(self, goal, html, screenshot, goal_image_urls=[]):
        self.goal = goal
        self.current_screenshot = screenshot
        self.history = []

    def update(self, html, screenshot, trace):
        self.current_screenshot = screenshot

    def act(self, **kwargs):
        history_str = self._create_history_str()

        variables = {
            "goal": self.goal,
            "action_hints": self.action_hints,
            "screenshot": self.current_screenshot,
            "history": history_str,
        }

        # First use the reward model to determine if we should end the task
        reward_model_response = self._query_reward_model(variables, **kwargs)
        if reward_model_response.should_end:
            action = self._create_action_from_reward_model_response(
                reward_model_response
            )
        else:
            # If the reward model does not indicate that we should end the task
            # We generate an action using the executor model
            executor_response = self._query_executor(variables, **kwargs)
            self.history.append([executor_response.thinking, executor_response.action])
            nl_action = executor_response.action

            # Use the grounder to convert the natural language action into coordinates
            action = self._query_grounder(nl_action)

        return action, {}

    def _query_reward_model(self, variables: dict, **kwargs) -> RewardModelResponse:
        """
        Query the reward model with the given variables.

        Args:
            variables (dict): The variables to pass to the reward model

        Returns:
            RewardModelResponse: The response from the reward model
        """
        reward_model_prompt, images = prompts.render(**variables, block="reward_model")

        reward_model_messages = prompt_to_messages(reward_model_prompt, images=images)
        reward_model_response = self.model.generate(
            messages=reward_model_messages, **kwargs
        )

        reward_model_response = self._parse_reward_model_response(reward_model_response)
        return reward_model_response

    def _query_executor(self, variables: dict, **kwargs) -> ExecutorResponse:
        """
        Query the executor with the given variables.

        Args:
            variables (dict): The variables to pass to the executor

        Returns:
            ExecutorResponse: The response from the executor
        """
        executor_prompt, images = prompts.render(**variables, block="executor")

        messages = prompt_to_messages(executor_prompt, images=images)
        executor_response = self.model.generate(messages=messages, **kwargs)

        executor_response = self._parse_model_response(executor_response)
        return executor_response

    def _query_grounder(self, nl_action: str) -> str:
        """
        Query the grounder with the given natural language action.

        Args:
            nl_action (str): The natural language action to ground

        Returns:
            str: The grounded action

        Raises:
            ValueError: If the action in the executor response is not found in the action space
        """

        def noop(wait_ms: float = 1000) -> str:
            """
            Do nothing and wait.
            """
            return f"noop(wait_ms={wait_ms})"

        def scroll(element_description: str, delta_x: float, delta_y: float) -> str:
            """
            Scroll horizontally and vertically.
            """
            coordinates = self.grounder.ground(
                self.current_screenshot, element_description
            )
            if coordinates is None:
                raise ValueError(
                    f"Failed to ground element description: {element_description}"
                )
            return f"mouse_move({coordinates[0]}, {coordinates[1]})\nscroll({delta_x}, {delta_y})"

        def hover(element_description: str) -> str:
            """
            Move the mouse to hover over and focus on a location.
            """
            coordinates = self.grounder.ground(
                self.current_screenshot, element_description
            )
            if coordinates is None:
                raise ValueError(
                    f"Failed to ground element description: {element_description}"
                )
            return f"mouse_move({coordinates[0]}, {coordinates[1]})"

        def click(
            element_description: str,
            button: Literal["left", "middle", "right"] = "left",
            clicks: int = 1,
        ) -> str:
            """
            Move the mouse to a location and click a mouse button.
            """
            coordinates = self.grounder.ground(
                self.current_screenshot, element_description
            )
            if coordinates is None:
                raise ValueError(
                    f"Failed to ground element description: {element_description}"
                )
            if clicks > 1:
                return f"mouse_dblclick({coordinates[0]}, {coordinates[1]}, button='{button}')"
            else:
                return f"mouse_click({coordinates[0]}, {coordinates[1]}, button='{button}')"

        def type(element_description: str, text: str, press_enter: bool = False) -> str:
            """
            Types a string of text through the keyboard.
            """
            coordinates = self.grounder.ground(
                self.current_screenshot, element_description
            )
            if coordinates is None:
                raise ValueError(
                    f"Failed to ground element description: {element_description}"
                )
            if press_enter:
                return f"mouse_dblclick({coordinates[0]}, {coordinates[1]})\nkeyboard_type('{text}')\nkeyboard_press('Enter')"
            else:
                return f"mouse_dblclick({coordinates[0]}, {coordinates[1]})\nkeyboard_type('{text}')"

        def drag_and_drop(
            element_description_1: str, element_description_2: str
        ) -> str:
            """
            Drag and drop from a location to a location.
            """
            coordinates_1 = self.grounder.ground(
                self.current_screenshot, element_description_1
            )
            coordinates_2 = self.grounder.ground(
                self.current_screenshot, element_description_2
            )
            if coordinates_1 is None:
                raise ValueError(
                    f"Failed to ground element description: {element_description_1}"
                )
            if coordinates_2 is None:
                raise ValueError(
                    f"Failed to ground element description: {element_description_2}"
                )
            return f"mouse_drag_and_drop({coordinates_1[0]}, {coordinates_1[1]}, {coordinates_2[0]}, {coordinates_2[1]})"

        # Try to be safe and only evaluate actions that are in the action space
        if extract_action(nl_action) in SVA_V2_EXECUTOR_ACTIONS:
            action = eval(nl_action)
        else:
            raise ValueError(f"Invalid action: {nl_action}")

        return action

    def _parse_model_response(self, text_response: str) -> ExecutorResponse:
        """
        We assume the response is in the following format:
        <thinking>THINKING</thinking>
        <action>ACTION</action>

        Args:
            text_response (str): The response from the model

        Returns:
            tuple[str, str]: The action and the thinking

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
            raise ValueError("No action found in the response.")

        return ExecutorResponse(action, thinking)

    def _parse_reward_model_response(
        self, reward_model_response: str
    ) -> RewardModelResponse:
        """
        We assume the response is in the following format:
        <should_end>SHOULD_END</should_end>
        <goal_achieved>GOAL_ACHIEVED</goal_achieved>
        <answer>ANSWER</answer>
        <reasoning>REASONING</reasoning>
        If we cannot find the tags, we will return False for the should_end, False for the goal_achieved,
        "" for the answer, and "" for the reasoning.

        Args:
            reward_model_response (str): The response from the reward model

        Returns:
            RewardModelResponse: The response from the reward model
        """
        contents = extract_content_by_tags(
            reward_model_response,
            [
                SVA_SHOULD_END_TAG,
                SVA_GOAL_ACHIEVED_TAG,
                SVA_ANSWER_TAG,
                SVA_REASONING_TAG,
            ],
        )

        if contents[SVA_SHOULD_END_TAG] is not None:
            should_end = contents[SVA_SHOULD_END_TAG].strip().lower() == "true"
        else:
            should_end = False
        if contents[SVA_GOAL_ACHIEVED_TAG] is not None:
            goal_achieved = contents[SVA_GOAL_ACHIEVED_TAG].strip().lower() == "true"
        else:
            goal_achieved = False
        if contents[SVA_ANSWER_TAG] is not None:
            answer = contents[SVA_ANSWER_TAG].strip()
        else:
            answer = ""
        if contents[SVA_REASONING_TAG] is not None:
            reasoning = contents[SVA_REASONING_TAG].strip().replace("\n", " ")
        else:
            reasoning = ""

        return RewardModelResponse(should_end, goal_achieved, answer, reasoning)

    def _create_action_from_reward_model_response(
        self, reward_model_response: RewardModelResponse
    ) -> str:
        """
        Create a return action from the reward model response

        Args:
            reward_model_response (RewardModelResponse): The response from the reward model

        Returns:
            str: The return action
        """
        if reward_model_response.goal_achieved:
            # If the goal is achieved, we return the answer or simply report success
            if reward_model_response.answer:
                return f"{SVA_RETURN_ACTION}('{reward_model_response.answer.strip()}')"
            else:
                return f"{SVA_RETURN_ACTION}('{SVA_DEFAULT_ANSWER}')"
        else:
            # We cannot achieve the goal, so we report this to the user
            if reward_model_response.reasoning:
                return f"{SVA_REPORT_INFEASIBLE_ACTION}('{reward_model_response.reasoning.strip()}')"
            else:
                return f"{SVA_REPORT_INFEASIBLE_ACTION}('{SVA_DEFAULT_INFEASIBLE_REASONING}')"

    def _create_history_str(self):
        """
        Create a string representation of the action history

        Returns:
            str: The action history in the format of (i) Thought: <thought> | Action: <action>
        """
        history_str = ""
        for i, (thought, action) in enumerate(self.history):
            history_str += f"({i+1}) Thought: {thought} | Action: {action}\n"
        return history_str
