"""
This module contains the class that is used to collect trajectories for a single task.
"""

import browsergym.core  # register the openended task as a gym environment

# Import webarena openended tasks to register them
import orby.trajectory_collector.utils.webarena_openended_task

import typing
import hashlib
from browsergym.core.env import BrowserEnv

import orby.digitalagent.utils.env_utils as env_utils
import orby.trajectory_collector.utils.record_utils as record_utils
from orby.trajectory_collector.task_completion_verifier import TaskCompletionVerifier
from orby.digitalagent.utils.action_parsing_utils import extract_action, extract_info_from_browsergym_action
from orby.digitalagent.agent import AGENT_NAME_TO_BUILDER

from fm.trajectory_data_pb2 import TrajectoryData

TRAJECTORY_DATA_FINGERPRINT_LENGTH = 20
TRAJECTORY_COLLECTOR_STARTING_MESSAGE = """\
A SingleTaskTrajectoryCollector is initialized with
    domain_name: {domain_name},
    start_url: {start_url},
    save_s3_bucket: {save_s3_bucket},
    save_s3_path: {save_s3_path},
    agent_name: {agent_name},
    goal_string: {goal_string},
    max_steps: {max_steps},
    temperature: {temperature},
    max_tokens: {max_tokens},
    frequency_penalty: {frequency_penalty},
    agent_model_provider: {agent_model_provider},
    agent_model_name: {agent_model_name},
    max_repetitive_actions: {max_repetitive_actions}.
    additional_model_kwargs: {additional_model_kwargs}.
    additional_browserenv_kwargs: {additional_browserenv_kwargs}.
"""
INITIAL_WEB_STATE_ACTION = "START_OF_TRAJECTORY"
COMPLETE_ACTION = "send_msg_to_user"
REPORT_INFEASIBLE_ACTION = "report_infeasible"


class SingleTaskTrajectoryCollector:
    def __init__(
        self,
        domain_name: str,
        start_url: str,
        save_s3_bucket: str,
        save_s3_path: str,
        agent_name: str,
        goal_string: str,
        max_steps: int,
        is_webarena_crawl: bool = False,
        context: str = "",
        task_id: str = None,
        temperature: float = 0.0,
        max_tokens: int = 300,
        frequency_penalty: float = 0.0,
        agent_model_provider: str = "openai",
        agent_model_name: str = "gpt-4o-2024-08-06",
        max_repetitive_actions: int = 5,
        additional_model_kwargs: dict[str, typing.Any] = {},
        additional_browserenv_kwargs: dict[str, typing.Any] = {},
        verbose: bool = False,
        replay_params: dict[str, typing.Any] = {},
    ):
        """
        Initialize a trajectory collector for a single task.

        Args:
            domain_name (str): The domain where the task is going to be completed.
            start_url (str): The URL where the task starts.
            save_s3_bucket (str): The S3 bucket where the collected data is saved.
            save_s3_path (str): The path in the S3 bucket where the collected data is saved.
            agent_name (str): The name of the agent that is used to complete the task.
            goal_string (str): The goal (guiding text) for the task.
            max_steps (int): The maximum number of steps the agent can take to complete the task.
            is_webarena_crawl (bool): Is the crawl being done on webarena websites.
                Setting this will automatically take care of logging into these sites.
            task_id (str): The unique identifier for the task. Defaults to None, in which case a unique task id is generated.
            temperature (float): The temperature used by models in the agent. Defaults to 0.0.
            max_tokens (int): The maximum number of output tokens used by models in the agent. Defaults to 300.
            frequency_penalty (float): The frequency penalty used by models in the agent. Defaults to 0.0.
            agent_model_provider (str): The provider of the model used by the agent. Defaults to "openai".
            agent_model_name (str): The model used by the agent. Defaults to "gpt-4o-2024-08-06".
            max_repetitive_actions (int): The maximum number of repetitive actions allowed before the task is truncated.
                Defaults to 5.
            additional_model_kwargs (dict[str, typing.Any]): Additional keyword arguments for the agent model. Defaults to {}.
                Note that:
                    1. This can be used to override existing model settings. e.g. if main model temperature is set to 1.0 but a
                        "temperature" key-value pair is set in this dictionary, the agent will use the value in this dictionary.
                    2. This can be used to load any sub agent model configurations. For example, the following dictionary is legal:
                        {
                            "planner": {
                                "provider": "openai",
                                "name": "gpt-4o-2024-08-06",
                                "temperature": 0.0,
                                "max_tokens": 300,
                                "frequency_penalty": 1.0,
                            },
                            "grounder": {
                                "provider": "anthropic",
                                "name": "claude-3-5-sonnet-20241022",
                                "temperature": 0.0,
                                "max_tokens": 300,
                                "frequency_penalty": 1.0,
                            }
                        }
            additional_browserenv_kwargs (dict[str, typing.Any]): Additional keyword arguments for the browser environment. Defaults to {}.
            verbose (bool): Whether to print verbose output.
            replay_params (dict[str, typing.Any]): Additional keyword arguments for the replay agent. Defaults to {}.
        """
        self.goal_string_with_context = goal_string  # Context will be added later
        self.max_steps = max_steps
        self.agent_name = agent_name
        self.verbose = verbose

        # We use the domain name and the goal string to create a unique task id
        self.task_id = (
            hashlib.sha256((domain_name + goal_string).encode()).hexdigest()[
                :TRAJECTORY_DATA_FINGERPRINT_LENGTH
            ]
            if task_id is None
            else task_id
        )

        # initialize the trajectory data recorder
        self.trajectory_data_recorder = record_utils.TrajectoryDataRecorder(
            s3_bucket=save_s3_bucket,
            s3_path=save_s3_path,
            fingerprint=self.task_id,
        )
        self.trajectory_data_recorder.set_domain(domain_name)
        self.trajectory_data_recorder.set_goal(goal_string)

        # take out some special configurations
        task_completion_verifier_configs = additional_model_kwargs.pop(
            "task_completion_verifier", {}
        )

        # Create the agent
        model_configs = {
            "provider": agent_model_provider,
            "name": agent_model_name,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "frequency_penalty": frequency_penalty,
        }
        model_configs.update(additional_model_kwargs)
        agent_kwargs = {
            "model_configs": model_configs,
        }
        if agent_name.startswith("replay"):
            agent_kwargs["replay_params"] = replay_params
        self.agent = AGENT_NAME_TO_BUILDER[agent_name](
            **agent_kwargs,
        )

        # set the context of the agent
        if context != "":
            if agent_name.startswith("unified"):
                self.agent.agent.set_context(context)
            else:
                self.goal_string_with_context = "{goal}\nHere are some information about the user you are helping and the current state of the world:\n{context}".format(
                    goal=goal_string, context=context
                )

        # Extract the task_completion_verifier configurations from the model_configs
        # TODO: there is definitely a better way of doing this
        if task_completion_verifier_configs == {}:
            task_completion_verifier_configs = {
                k: v
                for k, v in additional_model_kwargs.items()
                if not isinstance(v, dict)
            }

        self.task_completion_verifier = TaskCompletionVerifier(
            model_provider=agent_model_provider,
            model_name=agent_model_name,
            max_repetitive_actions=max_repetitive_actions,
            temperature=temperature,
            max_tokens=max_tokens,
            additional_model_kwargs=task_completion_verifier_configs,
        )

        # Initialize the before_state; the first before_state is empty
        self.before_state = None

        # initlialize the environment
        environment = (
            "browsergym/wa_openended" if is_webarena_crawl else "browsergym/openended"
        )
        self.env: BrowserEnv = env_utils.make(
            id=environment,
            task_kwargs={"start_url": start_url},
            wait_for_user_message=False,
            action_mapping=self.agent.action_set.to_python_code,
            **additional_browserenv_kwargs,
        )

        if self.verbose:
            print(
                TRAJECTORY_COLLECTOR_STARTING_MESSAGE.format(
                    domain_name=domain_name,
                    start_url=start_url,
                    save_s3_bucket=save_s3_bucket,
                    save_s3_path=save_s3_path,
                    agent_name=agent_name,
                    goal_string=goal_string,
                    max_steps=max_steps,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    frequency_penalty=frequency_penalty,
                    agent_model_provider=agent_model_provider,
                    agent_model_name=agent_model_name,
                    max_repetitive_actions=max_repetitive_actions,
                    additional_model_kwargs=additional_model_kwargs,
                    additional_browserenv_kwargs=additional_browserenv_kwargs,
                )
            )

    def run(self):
        """
        Run the trajectory collection.
        """
        # initialize the environment and the agent
        env_output: tuple[dict[str, typing.Any]] = self.env.reset()
        after_observation, _ = env_output
        # We need to do this every time we have a new observation
        after_observation = self._pad_observation_with_goal(after_observation)
        self.agent.reset(after_observation)
        self._save_initial_information(after_observation)

        done = False
        success = False
        answer = ""
        error = ""
        while not done:
            # Do one step of the task
            action_string, action_metadata = self.agent.act(after_observation)
            if self.agent_name.startswith("replay"):
                # Remove the extra empty llm trace at the end added by the wrapper in agent.py.
                while not self.agent.llm_trace[-1]:
                    self.agent.llm_trace.pop()
            if not self.agent_name.startswith("basic"):
                llm_response = self.agent.llm_trace[-1][-1].response
                action_metadata["llm_interactions"] = self.agent.llm_trace[-1]
            else:
                llm_response = action_string
            after_observation, reward, terminated, truncated, _ = self.env.step(
                action_string
            )
            # We need to do this every time we have a new observation
            after_observation = self._pad_observation_with_goal(after_observation)
            if self.verbose:
                print(
                    "Task id: {task_id}, Step: {step}, Action: {action}".format(
                        task_id=self.task_id,
                        step=len(self.agent.trace),
                        action=action_string,
                    )
                )

            # Check if the task is done; report answer or error if done
            success, answer, report_infeasible, repetitive_actions = (
                self._check_success_status(
                    action_string,
                    llm_response,
                    after_observation,
                )
            )

            max_steps_reached = truncated or (
                len(self.agent.llm_trace) > self.max_steps
            )
            error_occurred = (
                report_infeasible or repetitive_actions or max_steps_reached
            )
            done = success or terminated or error_occurred

            # Save the current step of the trajectory
            self._save_step_information(
                action_string=action_string,
                after_observation=after_observation,
                reward=reward,
                browsergym_terminated=terminated,
                browsergym_truncated=truncated,
                max_steps_reached=max_steps_reached,
                report_infeasible=report_infeasible,
                repetitive_actions=repetitive_actions,
                success=success,
                done=done,
                action_metadata=action_metadata,
                answer=answer,
            )

            error = (
                self.trajectory_data_recorder.trajectory_data.failure.failure_message
            )

        if self.verbose:
            print(
                "Task {task_id} is done. Success: {success}, Answer: {answer}, error {error}.".format(
                    task_id=self.task_id,
                    success=success,
                    answer=answer,
                    error=error,
                )
            )

    def upload_trajectory_data(self):
        """
        Upload the trajectory data to S3 after the trajectory collection is done.

        Raises:
            AssertError: If there is no data to upload.
        """
        assert (
            len(self.trajectory_data_recorder.trajectory_data.actions) > 0
        ), "No data to upload."
        # Compile and upload the trajectory data
        self.trajectory_data_recorder.compile_and_upload()

    def _pad_observation_with_goal(
        self, observation: dict[str, typing.Any]
    ) -> dict[str, typing.Any]:
        """
        Pad the observation with the goal string. This is a makeshift way of solving the issue that
        the goal is not included in the openended task observation. We need to do this every time
        we have a new observation.

        Args:
            observation (dict[str, typing.Any]): The observation from the environment.

        Returns:
            dict[str, typing.Any]: The padded observation.
        """
        observation["goal"] = self.goal_string_with_context
        observation["goal_object"] = [
            {"type": "text", "text": self.goal_string_with_context}
        ]
        return observation

    def _save_initial_information(
        self, initial_observation: dict[str, typing.Any]
    ) -> None:
        """
        Save the initial information at the start of the trajectory.

        Args:
            initial_observation (dict[str, typing.Any]): The initial observation of the environment.
        """
        # The trajectory must be empty at the start
        assert len(self.trajectory_data_recorder.trajectory_data.actions) == 0
        self._save_step_information(
            action_string=INITIAL_WEB_STATE_ACTION,
            after_observation=initial_observation,
            reward=0.0,
            browsergym_terminated=False,
            browsergym_truncated=False,
            max_steps_reached=False,
            report_infeasible=False,
            repetitive_actions=False,
            success=False,
            done=False,
        )

    def _save_step_information(
        self,
        action_string: str,
        after_observation: dict[str, typing.Any],
        reward: float,
        browsergym_terminated: bool,
        browsergym_truncated: bool,
        max_steps_reached: bool,
        report_infeasible: bool,
        repetitive_actions: bool,
        success: bool,
        done: bool,
        action_metadata: dict[str, typing.Any] | None = None,
        answer: str | None = None,
    ) -> None:
        """
        Save the information of the current step of the trajectory.
        Action and agent information is saved in the last ActionData object,
        and the observation information is saved in the current ActionData object.

        Args:
            action (str): The action that was taken.
            after_observation (dict[str, typing.Any]): The observation after the action.
            reward (float): The reward received from the environment.
            browsergym_terminated (bool): Whether the environment terminated the episode.
            browsergym_truncated (bool): Whether the environment truncated the episode.
            max_steps_reached (bool): Whether the maximum number of steps was reached.
            report_infeasible (bool): Whether the agent believes the task is infeasible.
            repetitive_actions (bool): Whether the agent took too much repetitive actions.
            success (bool): Whether the task was completed successfully.
            done (bool): Whether the task is done.
            answer (str | None): The answer to the task, if there is any. Defaults to None.
            action_metadata (dict[str, typing.Any]): The metadata of the action, contains agent state.
                Defaults to None, in which case the agent state is not saved or empty.
        """
        after_state = record_utils.record_web_state_from_browser_gym_observation(
            observation=after_observation,
            reward=reward,
            terminated=browsergym_terminated,
            truncated=browsergym_truncated,
        )
        if action_metadata:
            agent_state = record_utils.record_agent_state(
                llm_interactions=action_metadata["llm_interactions"],
                memory=(
                    action_metadata["memory"] if "memory" in action_metadata else None
                ),
                failed_agent_state=(
                    action_metadata["failed_agent_state"]
                    if "failed_agent_state" in action_metadata
                    else None
                ),
            )
        else:
            agent_state = None

        self.trajectory_data_recorder.append_action(
            action_string=action_string,
            before_state=self.before_state,
            after_state=after_state,
            agent_state=agent_state,
        )

        # we store the current after_state as the before_state for the next action
        self.before_state = after_state

        if done:
            # If done, we need to save the final observation and the result of the task
            self._save_result(
                success=success,
                answer=answer,
                max_steps_reached=max_steps_reached,
                report_infeasible=report_infeasible,
                repetitive_actions=repetitive_actions,
            )

    def _save_result(
        self,
        success: bool,
        answer: str,
        max_steps_reached: bool,
        report_infeasible: bool,
        repetitive_actions: bool,
    ) -> None:
        """
        Save the result of the crawled trajectory.

        Args:
            success (bool): Whether the task was completed successfully.
            answer (str): The answer to the task, if there is any.
            max_steps_reached (bool): Whether the maximum number of steps was reached.
            report_infeasible (bool): Whether the agent believes the task is infeasible.
            repetitive_actions (bool): Whether the agent took repetitive actions.
        """
        if success:
            self.trajectory_data_recorder.set_result(
                success=success,
                answer=answer,
            )
        else:
            if max_steps_reached:
                error = TrajectoryData.ResultFailure.FailureMessage.MAX_STEPS_EXCEEDED
            elif report_infeasible:
                error = TrajectoryData.ResultFailure.FailureMessage.REPORT_INFEASIBLE
            elif repetitive_actions:
                error = TrajectoryData.ResultFailure.FailureMessage.REPETITIVE_ACTIONS
            else:
                error = TrajectoryData.ResultFailure.FailureMessage.UNKNOWN_ERROR

            self.trajectory_data_recorder.set_result(
                success=success,
                error=error,
            )

    def _check_success_status(
        self,
        action_string: str,
        last_llm_response: str,
        current_observation: dict[str, typing.Any],
    ) -> tuple[bool, str, bool, bool]:
        """
        Check if the task is done.

        Args:
            action_string (str): The action that was taken by the agent.
            last_llm_response (str): The last llm_response that contains the action
                taken by the agent.
            current_observation (dict[str, typing.Any]): The most recent observation
                from the environment after the action.

        Returns:
            bool: Whether the completion verifier believes the task is successful.
            str: The answer to the task, if there is any.
            bool: Whether the completion verifier believes the task is infeasible.
            bool: Whether the agent took too much repetitive actions.
        """
        self.task_completion_verifier.update(
            current_observation=current_observation,
            current_action=action_string,
            current_llm_response=last_llm_response,
        )

        repetitive_actions = self.task_completion_verifier.check_repetitive_actions()
        
        # TODO: temporary solution to just trust the agent
        # Eventually we want to add some type of evaluation aid during goal generation
        # and an extra layer of model-based task completion verification using the aid
        # to provide a more accurate decision on if the trajectoy is complete or not.
        if extract_action(action_string) == COMPLETE_ACTION:
            success = True
            infeasible = False
            answer = extract_info_from_browsergym_action(action_string).value[0]
        elif extract_action(action_string) == REPORT_INFEASIBLE_ACTION:
            success = False
            infeasible = True
            answer = extract_info_from_browsergym_action(action_string).value[0]
        else:
            success = False
            infeasible = False
            answer = ""

        # if (
        #     extract_action(action_string) == COMPLETE_ACTION
        #     or extract_action(action_string) == REPORT_INFEASIBLE_ACTION
        # ):
        #     # We only check if the task is successful or infeasible if the agent took
        #     # a complete or report infeasible action
        #     success, infeasible, answer = (
        #         self.task_completion_verifier.check_task_completion_status()
        #     )
        # else:
        #     success = False
        #     infeasible = False
        #     answer = ""

        return success, answer, infeasible, repetitive_actions
