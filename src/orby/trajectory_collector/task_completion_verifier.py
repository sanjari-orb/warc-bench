"""
Contains the TaskCompletionVerifier class, which is used to verify if a task
has been completed and output answer if any.
"""

import dotenv
import os
import json
import typing
import collections

import orby.digitalagent.agent.utils as prompt_utils
import orby.trajectory_collector.utils.data_utils as data_utils
from orby.digitalagent.model.fm import FoundationModel
import numpy as np
dotenv.load_dotenv()


class TaskCompletionVerifier:
    def __init__(
        self,
        model_provider: str = "openai",
        model_name: str = "gpt-4o-2024-08-06",
        max_repetitive_actions: int = 5,
        temperature: float = 0.0,
        max_tokens: int = 500,
        additional_model_kwargs: dict = {},
    ):
        """
        Initialize the TaskCompletionVerifier.

        Args:
            model (str): The model to use for task completion verification.
            max_repetitive_actions (int): The maximum number of repetitive actions
                allowed before the task is truncated.
        """
        model_configs = {
            "provider": model_provider,
            "name": model_name,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        model_configs.update(additional_model_kwargs)
        self.model = FoundationModel(**model_configs)
        self.max_repetitive_actions = max_repetitive_actions
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.action_history: list[str] = []
        self.screenshot_history: list[np.ndarray] = []
        self.llm_response_history: list[str] = []

    def update(
        self,
        current_observation: dict[str, typing.Any],
        current_action: str,
        current_llm_response: str,
    ) -> None:
        """
        Update the internal state of the verifier with the current observation and action.

        Args:
            current_observation (dict): the observation just received from the agent
            current_action (str): the action just taken by the agent
            current_llm_response (str): the llm response just produced by the agent
        """
        self.screenshot_history.append(current_observation["screenshot"])
        self.action_history.append(current_action)
        self.llm_response_history.append(current_llm_response)

    def check_task_completion_status(self) -> tuple[bool, bool, str]:
        """
        Check if the task has been completed or is infeasible and output the answer if any.
        Retry 3 times if the response is not a valid JSON.

        Returns:
            bool: True if the task has been completed, False otherwise.
            bool: True if the task is infeasible, False otherwise.
            str: The answer if the task has been completed, empty string otherwise.
        """
        messages = self._construct_prompt_messages()

        response = self.model.generate(
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        success, answer, infeasible = self._parse_llm_response(response)
        return success, infeasible, answer

    def check_repetitive_actions(self) -> bool:
        """
        Check if the agent has been taking repetitive actions too many times.

        Returns:
            bool: True if the agent has been taking repetitive actions too many
                times, False otherwise.
        """
        action_counts = collections.Counter(
            [action for action in self.action_history if "scroll" not in action]
        )
        if len(action_counts) == 0:
            # If there is no previous action satisfying the constraint, we do not have repeated actions.
            return False
        if max(action_counts.values()) > self.max_repetitive_actions:
            return True
        return False

    # TODO: move prompt construction to a separate prompt utils file
    def _construct_prompt_messages(self) -> list[dict]:
        """
        Construct the prompt messages for the task completion verifier.

        Returns:
            list[dict]: The prompt messages.
        """
        history_strings = []
        for i in range(len(self.action_history) - 1):
            # We don't want to include the last action in the history.
            # Instead we include it as the current action later.
            history_strings.append("Step {}:".format(i + 1))
            history_strings.append(self.action_history[i])
            history_strings.append("")
        history_str = "\n".join(history_strings)

        content = []
        content.append(
            {
                "type": "text",
                "text": """\
You are a superintelligent and unbaised AI agent that serves as a judge in a competition.
The players are trying to use a web browser to complete tasks.
Your job is to determine if a task has been completed successfully by a player, and extract the answer the player provided.
You will be provided with the goal of the task, the action the player has taken so far, and the current screenshot of the web page.
The goal can be a question or a task that the player is trying to complete.

The goal of the task is: {goal}

The player has taken the following actions:
{history_str}

The last action the player took is:
{current_action}

The current screenshot of the web page is:\
""".format(
                    goal=str(self.current_observation["goal"]),
                    history_str=history_str,
                    current_action=self.action_history[-1],
                ),
            }
        )
        content.append(
            prompt_utils.prepare_image_input(self.current_observation["screenshot"])
        )
        content.append(
            {
                "type": "text",
                "text": """\
Please determine if the player has successfully completed the task.
NOTE: if the task requires a textual answer, do NOT mark it as completed until the player provides an answer through its action.
If you believe the player has completed the task, determine if the player needs to provide an answer. Output that answer if any.
{
    "reasoning": "" # Please output your step-by-step reasoning for determining if the player has successfully completed the task and what the answer is, if any
    "success": "" # The answer to the question "Has the player successfully completed the task?"; the answer can only be "yes" or "no"
    "answer_required": "" # "yes" if the player should provide an answer, "No" if the answer is the last web page the player visits
    "answer": "" # What you think the answer to the task is If yes to answer_required, or an empty string "" if no textual answer required. Give the answer AS IF you were the player
}
Please DO NOT output anything else!

Answer:
""",
            }
        )

        messages = [{"role": "user", "content": content}]
        return messages

    def _parse_llm_response(
        self,
        response: str,
    ) -> tuple[bool, str]:
        """
        Parse the response from the model output of task completion verifier.

        Args:
            response (str): The response from the task completion verifier.

        Returns:
            tuple[bool, str]: A tuple containing the success status and the answer, if any.
        """
        response = (
            response.strip().strip("`").strip().strip("json").strip().replace("\n", " ")
        )
        try:
            response_dict: dict[str, str] = json.loads(response)
        except json.decoder.JSONDecodeError as _:
            response = (
                response.strip()
                .strip("`")
                .strip()
                .strip("json")
                .strip()
                .replace("\n", " ")
            )
            response_dict: dict[str, str] = json.loads(response)
        success = True if "yes" in response_dict["success"].lower() else False
        answer = str(response_dict["answer"])
        return success, answer
