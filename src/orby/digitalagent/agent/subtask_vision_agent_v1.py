from dataclasses import dataclass

from orby.digitalagent.agent import Agent
from orby.digitalagent.model import FoundationModel
from orby.digitalagent.agent.utils import prompt_to_messages
from orby.digitalagent.prompts.default import subtask_vision_agent_v1 as prompts
from orby.digitalagent.utils.action_parsing_utils import extract_content_by_tags


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


class SubtaskVisionAgentV1(Agent):
    """
    The Subtask Vision Agent V1 is a pure-vision agent aims to complete short-horizon tasks (typically 5 steps or less).
    It uses 1 model as the executor and the reward model. Given a goal received from a user, the executor model is
    prompted to generate CoT and the immediate next BrowserGym coordinate action. The reward model is used to evaluate
    if the goal is achieved and optionally provide an answer.

    Some sanity experiments shows that large proprietary models (e.g. GPT-4o) are not able to generate the correct
    coordinates for the BrowserGym actions.
    """

    def __init__(
        self,
        actions: str,
        model_configs: dict,
    ):
        Agent.__init__(self)

        # The same model is used for both the executor and the reward model
        # The executor model is used to generate the action and CoT
        # The reward model is used to evaluate if the goal is achieved and optionally provide an answer
        self.model_configs = model_configs
        self.model = FoundationModel(**self.model_configs)

        # The action hints are the actions that the agent can take as a string
        self.action_hints = actions

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
            "screenshot_width": self.current_screenshot.shape[1],
            "screenshot_height": self.current_screenshot.shape[0],
        }

        # First use the reward model to determine if we should end the task
        reward_model_prompt, images = prompts.render(**variables, block="reward_model")
        reward_model_messages = prompt_to_messages(reward_model_prompt, images=images)
        reward_model_response = self.model.generate(
            messages=reward_model_messages, **kwargs
        )

        reward_model_response = self._parse_reward_model_response(reward_model_response)
        if reward_model_response.should_end:
            action = self._create_action_from_reward_model_response(
                reward_model_response
            )
            return action, {}

        # If the reward model does not indicate that we should end the task
        # We generate an action using the executor model
        executor_prompt, images = prompts.render(**variables, block="executor")
        messages = prompt_to_messages(executor_prompt, images=images)
        executor_response = self.model.generate(messages=messages, **kwargs)
        executor_response = self._parse_model_response(executor_response)
        self.history.append([executor_response.thinking, executor_response.action])
        action = executor_response.action

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
                return f"{SVA_RETURN_ACTION}('{reward_model_response.answer}')"
            else:
                return f"{SVA_RETURN_ACTION}('{SVA_DEFAULT_ANSWER}')"
        else:
            # We cannot achieve the goal, so we report this to the user
            if reward_model_response.reasoning:
                return f"{SVA_REPORT_INFEASIBLE_ACTION}('{reward_model_response.reasoning}')"
            else:
                return f"{SVA_REPORT_INFEASIBLE_ACTION}('{SVA_DEFAULT_INFEASIBLE_REASONING}')"

    def _create_history_str(self):
        """
        Create a string representation of the action history
        """
        history_str = ""
        for i, (thought, action) in enumerate(self.history):
            history_str += f"({i+1}) Thought: {thought} | Action: {action}\n"
        return history_str
