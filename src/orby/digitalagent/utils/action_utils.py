import ast
import math
import re
from enum import Enum
from typing import Callable

from orby.digitalagent.utils import dom_utils
from orby.digitalagent.utils.action_parsing_utils import (
    BID_TO_COORDINATE_ACTION_CONVERSION_TABLE,
    extract_info_from_browsergym_action,
)
from pb.v1alpha1.element_pb2 import Element


class ActionError(Enum):
    UNKNOWN = "UNKNOWN"
    ELEMENT_ID_NOT_FOUND = "ELEMENT_ID_NOT_FOUND"
    INVALID_ELEMENT_ID = "INVALID_ELEMENT_ID"
    INVISIBLE_ELEMENT = "INVISIBLE_ELEMENT"
    UNEXPECTED_ELEMENT_TYPE = "UNEXPECTED_ELEMENT_TYPE"
    EMPTY_ACTION = "EMPTY_ACTION"
    INVALID_ACTION_TYPE = "INVALID_ACTION_TYPE"
    INVALID_VALUE = "INVALID_VALUE"
    UNEXPECTED_KEYWORD = "UNEXPECTED_KEYWORD"
    MULTIPLE_ACTIONS = "MULTIPLE_ACTIONS"
    OPTION_NOT_FOUND = "OPTION_NOT_FOUND"
    TIMEOUT = "TIMEOUT"
    NO_STATE_CHANGE = "NO_STATE_CHANGE"


_ERROR_MESSAGE = {
    "ValueError: Could not find element with bid ": ActionError.ELEMENT_ID_NOT_FOUND,
    "ValueError: expected a string, got ": ActionError.INVALID_ELEMENT_ID,
    "element is not visible": ActionError.INVISIBLE_ELEMENT,
    "Error: Error: Element is not a": ActionError.UNEXPECTED_ELEMENT_TYPE,
    "ValueError: Received an empty action.": ActionError.EMPTY_ACTION,
    "NameError: Invalid action type": ActionError.INVALID_ACTION_TYPE,
    "Malformed value": ActionError.INVALID_VALUE,
    "required positional argument": ActionError.INVALID_VALUE,
    "got an unexpected keyword argument": ActionError.UNEXPECTED_KEYWORD,
    "ValueError: Received a multi-action, only single-actions are allowed.": ActionError.MULTIPLE_ACTIONS,
    "did not find some options": ActionError.OPTION_NOT_FOUND,
    "TimeoutError: ": ActionError.TIMEOUT,
}

READABLE_ERROR_MESSAGES = {
    ActionError.UNKNOWN: "Unknown error.",
    ActionError.ELEMENT_ID_NOT_FOUND: "No element matches the provided bid.",
    ActionError.INVALID_ELEMENT_ID: "Invalid bid type. bid needs to be a string.",
    ActionError.INVISIBLE_ELEMENT: "The element is not visible.",
    ActionError.UNEXPECTED_ELEMENT_TYPE: "The type of the element is not supported for this action.",
    ActionError.EMPTY_ACTION: "Invalid action.",
    ActionError.INVALID_ACTION_TYPE: "Invalid action type.",
    ActionError.INVALID_VALUE: "Invalid argument.",
    ActionError.UNEXPECTED_KEYWORD: "Unexpected keyword argument in the function call.",
    ActionError.MULTIPLE_ACTIONS: "Received a multi-action, only single-actions are allowed.",
    ActionError.OPTION_NOT_FOUND: "The option is not found.",
    ActionError.TIMEOUT: "Executed.",
}

COORD_ACTION_TYPES = set(
    [
        "mouse_move",
        "mouse_up",
        "mouse_down",
        "mouse_click",
        "mouse_dblclick",
        "mouse_upload_file",
        "mouse_drag_and_drop",
    ]
)


def determine_error_type(action_error: str) -> ActionError:
    for message in _ERROR_MESSAGE:
        if message in action_error:
            return _ERROR_MESSAGE[message]
    return ActionError.UNKNOWN


def clean_action(action: str | None) -> str:
    """Removes quotes and numbers wrapping the action.

    For example, given
    ```
    click("123")
    ```
    the function will return
    click("123")

    If the action is None, the function will return an empty string.
    """
    if action is None:
        return ""
    action_lines = action.split("\n")
    actions = []
    for line in action_lines:
        # remove markdown
        if len(line.strip()) == 0 or line.startswith("```"):
            continue
        action = line.strip()
        action = re.sub(r"'\[(\d+)\]'", r"'\1'", action)
        action = re.sub(r"\[(\d+)\]", r"'\1'", action)
        actions.append(action)
    return "\n".join(actions)


def remove_thinking(response, cot_open_tag="<thinking>", cot_close_tag="</thinking>"):
    # Remove content between COT tags from the response
    response = re.sub(rf"{cot_open_tag}[\W\w]*?{cot_close_tag}", "", response)
    return response


def get_action_type(action_string):
    return action_string[: action_string.find("(")].strip()


def extract_coord(action_str) -> tuple[float, float] | None:
    action_type = get_action_type(action_str)
    if not action_type in COORD_ACTION_TYPES:
        return None
    action_str = action_str[action_str.find("(") + 1 :].strip()
    x = action_str[: action_str.find(",")]
    action_str = action_str[action_str.find(",") + 1 :]
    if action_str.find(",") < action_str.find(")"):
        y = action_str[: action_str.find(",")]
    else:
        y = action_str[: action_str.find(")")]
    return float(x), float(y)


def transform_coordinates(
    action_str: str, transform: Callable[[float, float], tuple[float, float]]
):
    """Transforms coordinates in Python calls."""
    tree = ast.parse(action_str)
    for body in tree.body:
        action_type = body.value.func.id
        if not (action_type.startswith("mouse_") or action_type == "scroll"):
            continue
        body.value.args[0].value, body.value.args[1].value = transform(
            body.value.args[0].value, body.value.args[1].value
        )
        if action_type == "mouse_drag_and_drop":
            body.value.args[2].value, body.value.args[3].value = transform(
                body.value.args[2].value, body.value.args[3].value
            )
    return ast.unparse(tree)


def normalize_coordinates(
    action_str: str,
    viewport_width: float = 1280,
    viewport_height: float = 720,
    ndigits: int = 4,
) -> str:
    """Normalizes coordinates in Python call string."""

    def transform(x: float, y: float) -> tuple[float, float]:
        return round(x / viewport_width, ndigits), round(y / viewport_height, ndigits)

    try:
        return transform_coordinates(action_str, transform)
    except Exception as e:
        return action_str


def extract_parameter(call_str: str, parameter_index: int = 0) -> str:
    """
    Extracts a parameter from a Python function call given as a string.
    """
    try:
        # Parse the string in 'eval' mode so that it expects a single expression.
        node = ast.parse(call_str, mode="eval")
    except SyntaxError as e:
        raise ValueError("Invalid Python expression") from e

    # Check that the parsed expression is a function call.
    if not isinstance(node.body, ast.Call):
        raise ValueError("The provided string does not represent a function call.")

    call_node = node.body

    if call_node.keywords:
        param = call_node.keywords[parameter_index]
    elif call_node.args:
        param = call_node.args[parameter_index]
    else:
        # No parameters were provided.
        return ""

    return ast.unparse(param)


def reground_bid_to_coord_action(
    bid_action: str,
    root_element: Element,
    viewport_width: int | float,
    viewport_height: int | float,
) -> str:
    """
    Based on a conversion table, re-ground the bid action to a coordinate action.

    Args:
        action (str): The action to be converted
        root_element (Element): The root element of the DOM, in Orby Element proto format

    Returns:
        str: The converted action, now using coordinates
    """
    for (
        bid_action_type,
        coord_action_type,
    ) in BID_TO_COORDINATE_ACTION_CONVERSION_TABLE.items():
        if bid_action.startswith(bid_action_type):
            # Extract the information from the bid action
            info = extract_info_from_browsergym_action(bid_action)

            parameters = []
            if info.bids is not None:
                # Convert the bid to a coordinate by finding its center point
                for bid in info.bids:
                    element = dom_utils.find_element_by_bid(root_element, bid)
                    center_x, center_y = dom_utils.find_center_point_of_element(element)
                    parameters.extend([center_x, center_y])
                # If the element is not at the top of the DOM, we cannot interact with it
                # by its center point. We return the original bid action.
                # Note (cheng, 02/19/2025): for some reason checking
                # (is_displayed == False and in_viewport == False) always returns True here.
                if element.at_top == False:
                    return bid_action
                # Suppose the center point is outside the viewport, we cannot convert it.
                # Instead, we return the original bid action.
                # TODO (cheng): a better thing to do here may be to check the part of the element within
                # the viewport through a min max check, but for now, we just check the center point.
                if any(
                    [
                        center_x < 0,
                        center_x > viewport_width,
                        center_y < 0,
                        center_y > viewport_height,
                    ]
                ):
                    return bid_action
                # If the center point is 0, 0, we have reason to believe that the element's location
                # was not properly recorded, so we return the original bid action.
                if math.isclose(center_x, 0, abs_tol=1e-3) and math.isclose(
                    center_y, 0, abs_tol=1e-3
                ):
                    return bid_action
            if info.value is not None:
                value = str(info.value).strip("[]")
                parameters.append(value)

            # Construct the coordinate action
            coord_action = f"{coord_action_type}({', '.join(map(str, parameters))})"
            return coord_action

    return bid_action
