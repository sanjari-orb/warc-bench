"""
Utility functions for data processing.
"""

# TODO: consider moving this to digital-agent

import re
import json
import numpy as np
from cdifflib import CSequenceMatcher
from PIL import Image
from typing import Literal

import orby.digitalagent.utils.s3_utils as s3_utils
import orby.digitalagent.utils.image_utils as image_utils
from fm.trajectory_data_pb2 import TrajectoryData
from fm.action_data_pb2 import ActionData, WebState
from orby.digitalagent.model.fm import FoundationModel


def check_trajectory_result(td: TrajectoryData) -> Literal["successful", "failed", "infeasible", "unknown"]:
    """
    Check if the result of the trajectory is successful, failed, infeasible, or unknown.
    """
    if td.failure.failure_message == TrajectoryData.ResultFailure.FailureMessage.FAILURE_MESSAGE_UNSPECIFIED:
        return "successful"
    elif td.failure.failure_message == TrajectoryData.ResultFailure.FailureMessage.REPORT_INFEASIBLE:
        return "infeasible"
    elif td.failure.failure_message == TrajectoryData.ResultFailure.FailureMessage.UNKNOWN_ERROR:
        return "unknown"
    else:
        return "failed"


def screenshots_differ(
    screenshot1: bytes | str | np.ndarray | Image.Image,
    screenshot2: bytes | str | np.ndarray | Image.Image,
    image_mse_threshold: float = 0.01,
    normalize: bool = False,
) -> bool:
    """
    Decide if two screenshots differ by comparing their Mean Squared Error (MSE).
    The screenshots can be in bytes, string, numpy array, or PIL Image format.

    Args:
        screenshot1 (bytes | str | np.ndarray | Image.Image): The first screenshot
        screenshot2 (bytes | str | np.ndarray | Image.Image): The second screenshot
        image_mse_threshold (float): The Mean Squared Error (MSE) threshold for comparing
            screenshots. 0 means the screenshots must be identical, higher values mean the
            screenshots can be more different. Default is 1.
        normalize (bool): Whether to normalize the screenshots before comparing them. Default is False.
    Returns:
        bool: True if the screenshots differ, False otherwise
    """
    screenshot1_pil = image_utils.convert_image_to_pil_image(screenshot1)
    screenshot2_pil = image_utils.convert_image_to_pil_image(screenshot2)

    width1, height1 = screenshot1_pil.size
    width2, height2 = screenshot2_pil.size
    if width1 != width2 or height1 != height2:
        return True

    screenshot1_np = np.array(screenshot1_pil)
    screenshot2_np = np.array(screenshot2_pil)
    if normalize:
        screenshot1_np = screenshot1_np / 255.0
        screenshot2_np = screenshot2_np / 255.0
    mse = np.mean((screenshot1_np - screenshot2_np) ** 2)
    if mse > image_mse_threshold:
        return True

    return False


def axtrees_differ(
    axtree1: str,
    axtree2: str,
    axtree_similarity_threshold: float = 0.9999,
    max_axtree_length: int = 50000,
) -> bool:
    """
    Decide if two accessibility trees differ by comparing their similarity.
    The similarity is calculated using cdifflib's CSequenceMatcher.

    Args:
        axtree1 (str): The first accessibility tree
        axtree2 (str): The second accessibility tree
        axtree_similarity_threshold (float): The similarity threshold for comparing accessibility
            trees. The value ranges from 0 to 1, where 0 means the trees are completely different.
            Default is 0.99.
        max_axtree_length (int): The maximum length of the accessibility tree content to compare.
    """
    # If the lengths of the AXTrees are too long, we need to truncate them
    # TODO: maybe there is a better way
    axtree1 = _keep_the_middle_part_of_string(axtree1, max_axtree_length)
    axtree2 = _keep_the_middle_part_of_string(axtree2, max_axtree_length)
    axtree_similarity = CSequenceMatcher(None, axtree1, axtree2).ratio()
    if axtree_similarity < axtree_similarity_threshold:
        return True
    return False


def web_states_differ(
    webstate1: WebState,
    webstate2: WebState,
    image_mse_threshold: float = 0.01,
    axtree_similarity_threshold: float = 0.9999,
    max_axtree_length: int = 50000,
) -> bool:
    """
    Check if two WebState protobufs differ. Checks the URL, screenshot, HTML content,
    and accessibility tree content.

    Args:
        webstate1 (WebState): The first WebState protobuf
        webstate2 (WebState): The second WebState protobuf
        image_mse_threshold (float): The Mean Squared Error (MSE)threshold for comparing
            screenshots. 0 means the screenshots are identical, higher values mean the
            screenshots are more different. Default is 1.
        axtree_similarity_threshold (float): The similarity threshold for comparing accessibility
            trees. The value ranges from 0 to 1, where 0 means the trees are completely different.
            Default is 0.99.
        max_axtree_length (int): The maximum length of the accessibility tree content to compare.

    Returns:
        bool: True if the WebState protobufs differ, False otherwise
    """
    # If the URLs are different, the WebStates differ
    if webstate1.url != webstate2.url:
        return True

    # If the screenshot contents are different, the WebStates differ
    # We use Mean Squared Error (MSE) to compare the screenshots
    if screenshots_differ(
        webstate1.viewport.screenshot.content,
        webstate2.viewport.screenshot.content,
        image_mse_threshold,
    ):
        return True

    # If the HTML contents are different, the WebStates differ
    # TODO: Implement HTML content comparison

    # If the accessibility tree contents are different, the WebStates differ
    # We use cdifflib's CSequenceMatcher to compare the accessibility trees
    axtree1 = webstate1.browser_gym_observation.axtree
    axtree2 = webstate2.browser_gym_observation.axtree
    if axtrees_differ(axtree1, axtree2, axtree_similarity_threshold, max_axtree_length):
        return True

    return False


def _keep_the_middle_part_of_string(string: str, length: int) -> str:
    """
    Helper. Keep the middle part of a string.

    Args:
        string (str): The string
        length (int): The length of the middle part

    Returns:
        str: The middle part of the string
    """
    if len(string) <= length:
        return string
    return string[
        max(0, (len(string) - length) // 2) : min(
            len(string), (len(string) + length) // 2
        )
    ]


def read_trajectory_data_protobuf_from_s3(s3_client, s3_uri: str) -> TrajectoryData:
    """
    Read a TrajectoryData protobuf from an S3 URI.

    Args:
        s3_client (boto3.client): The boto3 S3 client
        s3_bucket (str): The S3 bucket name
        s3_key (str): The S3 key

    Returns:
        TrajectoryData: The TrajectoryData protobuf
    """
    s3_bucket, s3_key = s3_utils.get_s3_bucket_and_key_from_uri(s3_uri)
    response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
    data = response["Body"].read()
    trajectory_data = TrajectoryData()
    trajectory_data.ParseFromString(data)
    return trajectory_data


def write_trajectory_data_protobuf_to_s3(
    s3_client, s3_uri: str, trajectory_data: TrajectoryData
) -> None:
    """
    Write a TrajectoryData protobuf to an S3 URI.

    Args:
        s3_client (boto3.client): The boto3 S3 client
        s3_bucket (str): The S3 bucket name
        s3_key (str): The S3 key
        trajectory_data (TrajectoryData): The TrajectoryData protobuf
    """
    s3_bucket, s3_key = s3_utils.get_s3_bucket_and_key_from_uri(s3_uri)
    s3_client.put_object(
        Bucket=s3_bucket, Key=s3_key, Body=trajectory_data.SerializeToString()
    )


# TODO (chc012): move this and the following functions to a digital agent utils file
def clean_browsergym_action_string(action_string: str) -> str:
    """
    Clean up a BrowserGym action string.

    Args:
        action_string (str): The action string to clean

    Returns:
        str: The cleaned action string
    """
    return action_string.strip().strip("`").strip().replace("python", "", 1).strip()


def extract_quoted_text(input_string: str) -> str | None:
    """
    Extracts the text within quotes from an input string.

    Args:
        input_string (str): The input string

    Returns:
        str: The text within quotes if found, None otherwise
    """
    match = re.search(r'["\'](.*?)["\']', input_string)
    if match:
        return match.group(1)  # Extracts the text within quotes
    return None  # Returns None if no quoted text is found


def create_goal_from_trajectory_actions(
    model: FoundationModel,
    actions: list[ActionData],
    goal: str,
    answer: str,
    max_tokens: int = 1000,
    temperature: float = 0.0,
) -> tuple[str, str, int]:
    """
    Helper. Create a goal string from a list of actions using LLM query.

    Args:
        model (FoundationModel): The Foundation Model instance
        actions (list[TrajectoryData.ActionData]): The list of actions
        goal (str): The goal string
        answer (str): The answer string
        max_tokens (int): The maximum number of tokens for the LLM query
        temperature (float): The temperature for the LLM query

    Returns:
        str: The goal string
        str: The answer string
        int: The cutoff point
    """
    content = _create_goal_assignment_llm_content_from_actions(actions, goal, answer)
    response = model.generate(
        messages=[{"role": "user", "content": content}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    goal, answer, cutoff = _collect_goal_from_llm_response(response, goal, answer)
    return goal, answer, cutoff


# TODO: move prompt construction to a separate prompt utils file
def _create_goal_assignment_llm_content_from_actions(
    actions: list[ActionData],
    goal: str,
    answer: str,
) -> list[dict[str, str]]:
    """
    Helper. Create the content for the goal assignment LLM query.

    Args:
        actions (list[TrajectoryData.ActionData]): The list of actions

    Returns:
        str: The content string
    """
    content = []
    content.append(
        {
            "type": "text",
            "text": """\
You are a superintelligence AI that can understand human interactions with websites.
You will be given a sequence of web page screenshots and actions on the pages. This is the RECORDING of a user interacting with a website.
You will also be given the goal of the user's interaction, as well as the answer, if any, that the user provided to achieve the goal.

Please answer the following questions and provide your step-by-step reasoning for the answers:
1. Does the interaction accurately reflect the user's goal and accomplishes it? Yes or No.
2. If No to the above question, what is the actual (NEW) goal of this interaction? If Yes, put "NA" here.
3. Should the user provide a textual answer to solve the NEW goal? Yes or No, or NA.
4. If Yes to the above question, what is the answer to the NEW goal? If No, put "NA" here.
5. Does the entire interaction contribute to the NEW goal? Yes or No, or NA.
6. If No to the above question, at which point should we cutoff the interaction? Respond with the index of the action in the recording. \
If Yes, put "NA" here.

For example, if the goal is to "find the date of the next birthday event of an employee", the answer would be that date as a string. \
But if that answer is not provided and not visible in the recording, then this goal will be considered as not achieved. \
In this case, you need to find a NEW goal that has been achieved in the recording.
Another example: if the original goal is to "Submit a form inquiring about the newest car maintainence package of XYZ car wash", and the recording \
shows a user filling in a form one field at a time, BUT did not press the submit button, the NEW goal should be changed to "Fill in the form \
inquiring about the newest car maintainence package of XYZ car wash". There would be no textual answer in this case.
One last example: if the new goal is to "Find the phone number of ABC lawyer's office", and the phone number has already been send to the user \
through a message at action 6, but the user continues to interact with the website, all remaining actions are deviating from the NEW goal. \
In this case, the cutoff point should be at action 6, the last action that contributes to the NEW goal.

Please make the goal as specific as possible, and provide a detailed explanation of why you think this is the goal.

### START OF RECORDING ###
""",
        }
    )

    for i in range(len(actions)):
        actiondata = actions[i]
        content.append(
            {
                "type": "text",
                "text": "Action {idx}: ".format(idx=i + 1)
                + actiondata.browser_gym_action.action_string
                + "\nScreenshot:",
            }
        )
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/png;base64,{}".format(
                        image_utils.convert_image_bytes_to_base64_str(
                            actiondata.after_state.viewport.screenshot.content,
                            "png",
                        )
                    )
                },
            }
        )

    content.append(
        {
            "type": "text",
            "text": """\
### END OF RECORDING ###

The old goal of the user's interaction is to: {old_goal}
The textual answer provided by the user is: {answer}
Please note: if an answer is provided here, please tend to trust the content of this answer. It may have been extracted from part of the website that is not visible in the screenshots.

Please provide your ANSWER in the following format:
{{
    "reasoning_goal": "", # Please output your step-by-step reasoning for decisions about the goal.
    "old_goal_accomplished": "", # Does the interaction accurately reflect the user's goal and accomplishes it? Yes or No.
    "new_goal": "", # If No to the above question, what is the actual (NEW) goal of this interaction? If Yes, put "NA" here.
    "reasoning_answer": "", # Please output your step-by-step reasoning for decisions about the answer.
    "textual_answer_needed": "", # If not, should the user provide a textual answer to solve the NEW goal? Yes or No, or NA.
    "textual_answer": "", # If Yes to the above question, what is the answer to the NEW goal? If No, put "NA" here.
    "reasoning_cutoff": "", # Please output your step-by-step reasoning for decisions about the cutoff point.
    "entire_interaction_contributes": "", # Does the entire interaction contribute to the NEW goal? Yes or No, or NA.
    "cutoff_point": "" # If No to the above question, at which point should we cutoff the interaction? Respond with the index of the action in the recording. If Yes, put "NA" here.
}}
Please do not output anything else!

### ANSWER ###
""".format(
                old_goal=goal, answer=answer if answer else "No textual answer provided"
            ),
        }
    )

    return content


def _collect_goal_from_llm_response(
    response: str, old_goal: str, old_answer: str
) -> tuple[str, str, int]:
    """
    Helper. Collect the goal from the LLM response.

    Args:
        response (str): The LLM response
        old_goal (str): The old goal string
        old_answer (str): The old answer string

    Returns:
        str: The goal string
        str: The answer string
        int: The cutoff point
    """
    response = response.strip().strip("`").strip().strip("json").strip()
    response_dict: dict[str, str] = json.loads(response)

    # We collect the cutoff point, if there is one
    entire_interaction_contributes = (
        True
        if (
            "entire_interaction_contributes" in response_dict
            and response_dict["entire_interaction_contributes"] != "No"
        )
        else False
    )
    cutoff_point = (
        int(response_dict["cutoff_point"])
        if ("cutoff_point" in response_dict and not entire_interaction_contributes)
        else -1
    )

    # If we do not need to change anything, we will return the old goal and old answer
    old_goal_accomplished = (
        True if response_dict["old_goal_accomplished"] == "Yes" else False
    )
    if old_goal_accomplished:
        return old_goal, old_answer, cutoff_point

    new_goal = response_dict["new_goal"]

    # If we need to change the goal but there is no answer, we will return the new goal and an empty string
    textual_answer_needed = (
        True if response_dict["textual_answer_needed"] == "Yes" else False
    )
    if not textual_answer_needed:
        return new_goal, "", cutoff_point

    # Finally, if we need to change the goal and provide a textual answer, we will return them both
    new_answer = response_dict["textual_answer"]

    return new_goal, new_answer, cutoff_point


def extract_bid_from_browsergym_action_string(action_string: str) -> str | None:
    """
    Extract the BrowserGym ID (BID) from a BrowserGym action string.

    Args:
        action_string (str): The BrowserGym action string

    Returns:
        str: The BID if found, None otherwise
    """
    match = re.search(r"\((['\"])(.*?)\1", action_string)
    if match:
        return match.group(2)
    return None


def extract_coordinate_from_browsergym_action_string(
    action_string: str,
) -> tuple[int, int]:
    """
    Extract the x and y coordinates from a BrowserGym action string.

    Args:
        action_string (str): The BrowserGym action string

    Returns:
        tuple[int, int]: The x and y coordinates
    """
    numbers = re.findall(r"-?\d+\.?\d*", action_string)
    # Convert the first two to floats
    return tuple([float(num) for num in numbers[:2]])
