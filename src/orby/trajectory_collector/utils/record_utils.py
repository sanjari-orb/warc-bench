"""
Utility functions for compiling and storing trajectory data.
Copied from Cheng's PR.
"""

import boto3
import uuid
import typing
import json
import warnings
import numpy as np
from PIL import Image
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.duration_pb2 import Duration

from fm.action_data_pb2 import (
    WebState,
    ActionData,
    Viewport,
    AgentState,
    BrowserGymObservation,
)
from fm.trajectory_data_pb2 import TrajectoryData
from fm.llm_data_pb2 import LLMInteraction, LLMMessage, LLMContent
from pb.v1alpha1.document_pb2 import DocumentBlob
from pb.v1alpha1.element_pb2 import Rect
from orby.digitalagent.utils import image_utils
from orby.digitalagent.utils import file_utils

WEB_STATE_FINGERPRINT_LENGTH = 16
ACTION_DATA_FINGERPRINT_LENGTH = 12


class TrajectoryDataRecorder:
    def __init__(self, s3_bucket: str, s3_path: str, fingerprint: str) -> None:
        """
        A temporary storage for trajectory data before compiling and uploading to s3.

        Args:
            s3_bucket (str): The name of the s3 bucket to store the trajectory data.
            s3_path (str): The directory path in the s3 bucket to store the trajectory data.
            fingerprint (str): a random hash id of the trajectory data.
        """
        self.s3_bucket = s3_bucket
        self.s3_path = s3_path
        self.s3_client = boto3.client("s3")
        self.fingerprint = fingerprint

        # Information to store
        self.trajectory_data = TrajectoryData()

    def set_domain(self, domain: str) -> None:
        """
        Set domain, the domain name of the URL where the trajectory started.

        Args:
            domain (str): The domain name of the URL where the trajectory started.
        """
        self.trajectory_data.domain = domain

    def set_goal(self, goal: str) -> None:
        """
        Set the goal that the trajectory data is trying to achieve.

        Args:
            goal (str): The goal that the trajectory data is trying to achieve.
        """
        self.trajectory_data.goal = goal

    def append_action(
        self,
        action_string: str,
        after_state: WebState,
        before_state: WebState | None = None,
        agent_state: AgentState | None = None,
        trace: bytes | None = None,
        domain: str | None = None,
    ) -> None:
        """
        Append one actiond data to the trajectory data.

        Args:
            action_string (str): The string representation of the action in BrowserGym format.
            after_state (WebState): The state of the webpage after the action was executed.
            before_state (WebState): The state of the webpage before the action was executed.
                Defaults to None, in which case the before state is not recorded and we rely on the
                after_state of the previous action for this.
            agent_state (AgentState, optional): The state of the agent after the action was executed.
                Defaults to None, in which case the agent state is not recorded.
            trace (bytes, optional): The trace of the action. Defaults to None.
            domain (str, optional): The domain name of the URL where the action was executed.
                Defaults to None, in which case we use the domain of the recorder set previously.

        Raises:
            ValueError: If the domain is not set here or in the recorder.
        """
        if domain is None:
            if self.trajectory_data.domain == "":
                raise ValueError(
                    "Domain is not set. Either provide the domain parameter or set the domain using set_domain method."
                )
            else:
                domain = self.trajectory_data.domain

        self.trajectory_data.actions.append(
            record_action_data_from_browser_gym_interaction(
                domain=domain,
                action_string=action_string,
                before_state=before_state,
                after_state=after_state,
                agent_state=agent_state,
                trace=trace,
            )
        )

    def set_result(
        self,
        success: bool,
        answer: str = "",
        error: int | None = None,
    ) -> None:
        """
        Set the result of the trajectory data.

        Args:
            success (bool): Whether the trajectory was successful.
            answer (str, optional): The answer to the goal if the trajectory was successful.
                Defaults to "", which means that the correct output is the final WebState.
            error (TrajectoryData.ResultFailure.FailureMessage, optional): The error message if the trajectory was unsuccessful.
                Defaults to None, in which case the action must have succeeded.

        Raises:
            ValueError: If the error message is not provided when the trajectory is unsuccessful.
        """
        if success:
            self.trajectory_data.success.CopyFrom(
                TrajectoryData.ResultSuccess(answer=answer)
            )
        else:
            if error is None:
                raise ValueError(
                    "Error message is required when the result is a failure."
                )
            self.trajectory_data.failure.CopyFrom(
                TrajectoryData.ResultFailure(failure_message=error)
            )

    def compile(self) -> TrajectoryData:
        """
        Compile the trajectory data into a TrajectoryData protobuf message.

        Returns:
            TrajectoryData: The compiled trajectory data.

        Raises:
            ValueError: If the domain, goal, actions, or result is not set.
        """
        if (
            (not self.trajectory_data.domain)
            or (not self.trajectory_data.goal)
            or (len(self.trajectory_data.actions) == 0)
        ):
            raise ValueError(
                "Domain, goal, and actions must be set before compiling the trajectory data."
            )
        if self.trajectory_data.WhichOneof("result") is None:
            print(
                "Warning: Result is not set. Assuming the trajectory failed and the reason is unknown."
            )
            self.trajectory_data.failure.CopyFrom(
                TrajectoryData.ResultFailure(
                    failure_message=TrajectoryData.ResultFailure.FailureMessage.UNKNOWN_ERROR
                )
            )

        return self.trajectory_data

    def compile_and_upload(self) -> None:
        """
        Compile the trajectory data and upload it to the s3 bucket.
        """
        trajectory_data = self.compile()
        s3_uri = f"s3://{self.s3_bucket}/{self.s3_path}/{self.fingerprint}.pb.xz"

        # Save the object to a file
        with file_utils.open(s3_uri, "wb") as f:
            f.write(trajectory_data.SerializeToString())


def record_agent_state(
    llm_interactions: list[dict[str, typing.Any] | LLMInteraction],
    memory: str | dict | None = None,
    failed_agent_state: AgentState | None = None,
) -> AgentState:
    """
    Record the agent state as an AgentState protobuf message.

    Args:
        llm_calls (dict[str, typing.Any]): The LLM calls made by the agent this round.
        memory (str): The memory of the agent. Defaults to None, in which case the agent has no memory.
        failed_agent_state (AgentState, optional): The previously failed agent state.
            Defaults to None, which means that this is the agent's first attempt.

    Returns:
        AgentState: The compiled agent state protobuf message.

    Raises:
        ValueError: If the prompt type is not text or image.
        TypeError: If the prompt content or memory is not a string or a dictionary.
    """
    agent_state = AgentState()

    for llm_interaction in llm_interactions:
        if isinstance(llm_interaction, dict):
            # the llm_interaction is a dictionary, which mean that we need to convert it to a protobuf message
            llm_interaction_pb = LLMInteraction()
            llm_interaction_pb.model_family = llm_interaction["model_family"]
            llm_interaction_pb.model_name = llm_interaction["model_name"]

            for prompt in llm_interaction["prompts"]:
                prompt_message = LLMMessage()
                prompt_message.role = prompt["role"]

                # There is an edge case where the content is a string instead of a list.
                # This must be checked and addressed before everything else.
                if isinstance(prompt["content"], str):
                    prompt_message.llm_contents.append(
                        LLMContent(text=prompt["content"])
                    )
                elif isinstance(prompt["content"], list):
                    for content in prompt["content"]:
                        if content["type"] == "text":
                            prompt_message.llm_contents.append(
                                LLMContent(text=content["text"])
                            )
                        elif content["type"] == "image_url":
                            prompt_message.llm_contents.append(
                                LLMContent(image_url=content["image_url"]["url"])
                            )
                        else:
                            raise ValueError("Prompt type must be text or image_url.")
                else:
                    raise TypeError("Prompt content must be a string or a dictionary.")
                llm_interaction_pb.llm_messages.append(prompt_message)
            llm_interaction_pb.response = llm_interaction["response"]

            agent_state.llm_interactions.append(llm_interaction_pb)
        else:
            # the llm_interaction is already a protobuf message
            agent_state.llm_interactions.append(llm_interaction)

    if memory is not None:
        if isinstance(memory, str):
            agent_state.memory = memory
        elif isinstance(memory, dict):
            agent_state.memory = json.dumps(memory)
        else:
            raise TypeError("Memory must be a string or a dictionary.")

    if failed_agent_state is not None:
        agent_state.previous_failed_agent_state.CopyFrom(failed_agent_state)

    return agent_state


def record_action_data_from_browser_gym_interaction(
    domain: str,
    action_string: str,
    after_state: WebState,
    before_state: WebState | None = None,
    agent_state: AgentState | None = None,
    trace: bytes | None = None,
) -> ActionData:
    """
    Compile the action data into an ActionData protobuf message.

    Args:
        domain (str): The domain name of the URL where the action was executed.
        action_string (str): The string representation of the action for BrowserGym.
        after_state (WebState): The state of the webpage after the action was executed.
        before_state (WebState): The state of the webpage before the action was executed.
            Defaults to None, in which case the before state is not recorded and we rely on the
            after_state of the previous action for this.
        agent_state (AgentState, optional): The state of the agent after the action was executed.
            Defaults to None, in which case the agent state is not recorded.
        trace (bytes, optional): The trace of the action. Defaults to None.

    Returns:
        ActionData: The compiled action data protobuf message.
    """
    action_data = ActionData()

    action_data.id = uuid.uuid4().hex[:ACTION_DATA_FINGERPRINT_LENGTH]
    action_data.domain = domain

    if before_state is not None:
        action_data.before_state.CopyFrom(before_state)
    action_data.after_state.CopyFrom(after_state)

    if agent_state is not None:
        action_data.agent_state.CopyFrom(agent_state)

    if trace is not None:
        action_data.playwright_trace = trace

    action_data.browser_gym_action.action_string = action_string

    return action_data


def record_web_state_from_browser_gym_observation(
    observation: dict[str, typing.Any],
    fingerprint: str | None = None,
    reward: float | None = None,
    truncated: bool | None = None,
    terminated: bool | None = None,
) -> WebState:
    """
    Record the current web state as a WebState protobuf message.

    Args:
        observation (dict[str, typing.Any]): The observation data from the browser gym environment.
        fingerprint (str, optional): The fingerprint of the web state. Defaults to None, in which case a
            random fingerprint is generated
        reward (float, optional): The reward for the current state. Defaults to None.
        truncated (bool, optional): Whether the episode was truncated. Defaults to None.
        terminated (bool, optional): Whether the episode was terminated. Defaults to None.

    Returns:
        WebState: The compiled web state protobuf message.
    """
    web_state = WebState()
    web_state.fingerprint = (
        fingerprint or uuid.uuid4().hex[:WEB_STATE_FINGERPRINT_LENGTH]
    )
    web_state.url = observation["url"]
    web_state.viewport.CopyFrom(
        record_viewport_from_image_nparray(observation["screenshot"])
    )
    if "orby_viewport_size" in observation:
        web_state.viewport.viewport_rect.width = observation["orby_viewport_size"][
            "width"
        ]
        web_state.viewport.viewport_rect.height = observation["orby_viewport_size"][
            "height"
        ]
    else:
        warnings.warn(
            "No viewport size found in the observation. This is only allowed during testing. Please check your orbot extension setup."
        )
    if (
        "orby_root_element" in observation
        and observation["orby_root_element"] is not None
    ):
        web_state.root_element.CopyFrom(observation["orby_root_element"])
    else:
        warnings.warn(
            "No root element found in the observation. This is only allowed during testing. Please check your orbot extension setup."
        )

    browser_gym_observation = BrowserGymObservation()

    if reward is not None:
        browser_gym_observation.reward = float(reward)
    if truncated is not None:
        browser_gym_observation.truncated = bool(truncated)
    if terminated is not None:
        browser_gym_observation.terminated = bool(terminated)

    if "chat_messages" in observation and observation["chat_messages"] is not None:
        for chat_message in observation["chat_messages"]:
            browser_gym_observation.chat_messages.append(
                BrowserGymObservation.ChatMessage(
                    role=chat_message["role"],
                    timestamp=Timestamp(seconds=int(chat_message["timestamp"])),
                    message=chat_message["message"],
                )
            )

    if "goal" in observation and observation["goal"] is not None:
        browser_gym_observation.legacy_goal = str(observation["goal"])

    if "goal_object" in observation and observation["goal_object"] is not None:
        for goal_object in observation["goal_object"]:
            browser_gym_observation.goals.append(
                LLMContent(text=goal_object["text"])
                if "text" in goal_object
                else LLMContent(image_url=goal_object["image_url"])
            )

    if "open_pages_urls" in observation and observation["open_pages_urls"] is not None:
        browser_gym_observation.open_pages_urls.extend(
            [str(url) for url in observation["open_pages_urls"]]
        )

    if (
        "active_page_index" in observation
        and observation["active_page_index"] is not None
    ):
        browser_gym_observation.active_page_index = int(
            observation["active_page_index"][0]
        )

    browser_gym_observation.dom = json.dumps(observation["dom_object"]).encode("utf-8")
    browser_gym_observation.axtree = json.dumps(observation["axtree_object"]).encode(
        "utf-8"
    )

    if (
        "extra_element_properties" in observation
        and observation["extra_element_properties"] is not None
    ):
        browser_gym_observation.extra_element_properties = json.dumps(
            observation["extra_element_properties"]
        ).encode("utf-8")

    if (
        "focused_element_bid" in observation
        and observation["focused_element_bid"] is not None
    ):
        browser_gym_observation.focused_element_bid = str(
            observation["focused_element_bid"]
        )

    if "last_action" in observation and observation["last_action"] is not None:
        browser_gym_observation.last_action = str(observation["last_action"])

    if (
        "last_action_error" in observation
        and observation["last_action_error"] is not None
    ):
        browser_gym_observation.last_action_error = str(
            observation["last_action_error"]
        )

    if "elapsed_time" in observation and observation["elapsed_time"] is not None:
        browser_gym_observation.elapsed_time.CopyFrom(
            Duration(seconds=int(observation["elapsed_time"][0]))
        )

    web_state.browser_gym_observation.CopyFrom(browser_gym_observation)
    return web_state


def record_viewport_from_image_nparray(
    screenshot: np.array,
    bbox_xywh: tuple[float, float, float, float] | None = None,
) -> Viewport:
    """
    Record the viewport of the webpage.

    Args:
        screenshot (bytes): The screenshot of the webpage.
        bbox_xywh (tuple[float, float, float, float]): The bounding box of the screenshot (x, y, width, height).
            Defaults to None, in which case we do not have information about the viewport location.

    Returns:
        Viewport: The compiled viewport protobuf message.
    """
    screenshot_bytes = image_utils.pil_image_to_bytes(
        Image.fromarray(screenshot, mode="RGB"), "JPEG"
    )
    screenshot_blob = DocumentBlob(
        mime_type="image/jpeg",
        content=screenshot_bytes,
    )
    viewport = Viewport(
        screenshot=screenshot_blob,
    )

    if bbox_xywh is not None:
        viewport.viewport_rect.CopyFrom(
            Rect(
                x=bbox_xywh[0],
                y=bbox_xywh[1],
                width=bbox_xywh[2],
                height=bbox_xywh[3],
            )
        )

    return viewport
