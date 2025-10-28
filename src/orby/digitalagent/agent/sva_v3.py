from dataclasses import dataclass

from orby.digitalagent.agent import Agent
from orby.digitalagent.model import FoundationModel
from orby.digitalagent.agent.utils import prompt_to_messages
from orby.digitalagent.prompts.default import sva_v3 as prompts
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
SVA_SHOULD_END_TAG = "should_end"
SVA_GOAL_ACHIEVED_TAG = "goal_achieved"
SVA_ANSWER_TAG = "answer"
SVA_REASONING_TAG = "reasoning"


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


class SvaV3(Agent):
    """
    The SVA V3 agent is a pure-vision agent aims to complete short-horizon tasks (typically 5 steps or less).
    It uses 1 model as the executor and the reward model. Given a goal received from a user, the executor model is
    prompted to generate CoT and the immediate next BrowserGym coordinate action. The reward model is used to evaluate
    if the goal is achieved and optionally provide an answer.

    Building on top of both SVA V1 and V2, we
    - Take the simpler agent design approach as SVA V1
    - Create custom action space similar to SVA V2
    - Additionally, allow the executor to see the screenshot of all actions in history in the prompt
    """

    def __init__(
        self,
        actions: str,
        model_configs: dict,
        reward_model_configs: dict | None = None,
        action_history_length: int = 5,
    ):
        super().__init__()

        # The executor model is used to generate the action and CoT
        self.model_configs = model_configs
        self.model = FoundationModel(**self.model_configs)

        # Hard-coded reward model
        # TODO: remove
        # reward_model_configs = {
        #     "provider": "anthropic",
        #     "name": "claude-sonnet-4-20250514",
        #     "temperature": 0,
        #     "max_tokens": 512,
        # }

        # The reward model is used to evaluate if the goal is achieved and optionally provide an answer
        # prefer to be and default to the same model as the executor model for trace generation
        if reward_model_configs:
            self.reward_model_configs = reward_model_configs
            self.reward_model = FoundationModel(**self.reward_model_configs)
        else:
            self.reward_model_configs = self.model_configs
            # shallow copy to allow trace generation
            self.reward_model = self.model

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
        # that inherit from SvaV3, we need to call the _act method instead of act
        # to avoid duplicate tracing. Otherwise, the llm_trace field will contain
        # duplicate traces.
        return self._act(**kwargs)

    def _act(self, **kwargs):
        """Wrapper to avoid duplicate tracing when calling from child class"""
        image_dict, history_str = self._create_history_str()

        variables = {
            "goal": self.goal,
            "action_hints": self.action_hints,
            "current_screenshot": self.screenshot_history[-1],
            "history": history_str,
        }
        variables.update(image_dict)

        # First use the reward model to determine if we should end the task
        reward_model_prompt, images = prompts.render(**variables, block="reward_model")
        reward_model_messages = prompt_to_messages(reward_model_prompt, images=images)
        reward_model_response = self.reward_model.generate(
            messages=reward_model_messages, **kwargs
        )

        reward_model_response = self._parse_reward_model_response(reward_model_response)
        if reward_model_response.should_end:
            # If the reward model indicates that we should end the task
            # We use the complete action to return to the user
            action = self._create_action_from_reward_model_response(
                reward_model_response
            )
        else:
            # If the reward model does not indicate that we should end the task
            # We generate an action using the executor model
            executor_prompt, images = prompts.render(**variables, block="executor")
            messages = prompt_to_messages(executor_prompt, images=images)
            executor_response = self.model.generate(messages=messages, **kwargs)
            executor_response = self._parse_model_response(executor_response)

            if self.action_history_length != 0:
                self.response_history.append(
                    [executor_response.thinking, executor_response.action]
                )
                if self.action_history_length > 0:
                    self.response_history = self.response_history[
                        -self.action_history_length :
                    ]

            action = self._convert_response_to_browsergym_action(
                executor_response.action
            )

        print("Grounded action:", action)
        return action, {}

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
            return complete(answer=reward_model_response.answer)
        else:
            return complete(infeasible_reason=reward_model_response.reasoning)

    # TODO: consider moving this looping logic inside the prompt template
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
