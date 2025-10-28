import ast
import dataclasses
import re

from browsergym.core.action.parsers import _build_highlevel_action_parser


NOOP_ACTIONS = ["noop"]
SCROLL_ACTIONS = ["scroll"]
NO_PARAMETERS_ACTIONS = [
    "go_back",
    "go_forward",
    "tab_close",
    "new_tab",
]
VALUE_ONLY_ACTIONS = [
    "send_msg_to_user",
    "report_infeasible",
    "keyboard_down",
    "keyboard_up",
    "keyboard_press",
    "keyboard_type",
    "keyboard_insert_text",
    "goto",
    "tab_focus",
]
BID_ACTIONS = [
    "fill",
    "select_option",
    "click",
    "dblclick",
    "hover",
    "press",
    "focus",
    "clear",
    "upload_file",
]
COORDINATE_ACTIONS = [
    "mouse_move",
    "mouse_up",
    "mouse_down",
    "mouse_click",
    "mouse_dblclick",
    "mouse_upload_file",
]
MULTI_BID_ACTIONS = ["drag_and_drop"]
MULTI_COORDINATE_ACTIONS = ["mouse_drag_and_drop"]
COORDINATE_TO_BID_ACTION_CONVERSION_TABLE = {
    "mouse_move": "hover",
    "mouse_click": "click",
    "mouse_dblclick": "dblclick",
    "mouse_drag_and_drop": "drag_and_drop",
    "mouse_upload_file": "upload_file",
}
BID_TO_COORDINATE_ACTION_CONVERSION_TABLE = {
    value: key for key, value in COORDINATE_TO_BID_ACTION_CONVERSION_TABLE.items()
}


@dataclasses.dataclass
class BrowserGymActionInfo:
    """
    A class to store the dissected information of a BrowserGym action.
    """

    action_type: str
    bids: list[str] | None = None
    absolute_coordinates: list[tuple[float, float]] | None = None
    value: list | None = None


def monkey_patch_to_python_code(obs, coordinates_multiplier: float = 1):
    """
    Return a monkey patched python action parser which converts normalized
    coordinate inputs to unnormalized coordinates.

    Copied from https://github.com/orby-ai-engineering/BrowserGym/blob/b0ad675572e01cac0d7255100112de0828877148/browsergym/core/src/browsergym/core/action/highlevel.py#L303
    """
    height, width = obs["screenshot"].shape[:2]

    def to_python_code(self, action):
        """
        Converts the given high-level action string to browsergym-compatible python code.
        Args:
            action: the high-level action to parse.
        Returns:
            Executable python code that performs the action in a browsergym environment.
        """
        highlevel_code = action
        local_parser = _build_highlevel_action_parser()
        # do the actual parsing and convert each high-level action to
        # the corresponding python function call
        if self.strict:
            function_calls = local_parser.parse_string(highlevel_code, parse_all=True)
            function_calls = function_calls.as_list()
        else:
            function_calls = local_parser.search_string(
                highlevel_code
            )  # allow for multiple matches, skip anything in-between
            function_calls = sum(
                function_calls.as_list(), []
            )  # unpack multiple matches

        if not function_calls:
            raise ValueError("Received an empty action.")
        elif len(function_calls) > 1 and not self.multiaction:
            raise ValueError(
                "Received a multi-action, only single-actions are allowed."
            )

        python_code = ""
        # function definitions
        python_code += self.python_includes
        # function calls
        for function_name, function_args in function_calls:
            if function_name not in self.action_set:
                raise NameError(f"Invalid action type '{function_name}'.")
            # Modify float arguments by multiplying with viewport sizes
            modified_args = []

            # Unnormalize the coordinates for coord actions only
            # https://github.com/ServiceNow/BrowserGym/blob/12aa5e506dbf76e269af11fb214467c2495d5c59/browsergym/core/src/browsergym/core/action/highlevel.py#L63
            if (
                function_name.startswith("mouse_") or function_name == "scroll"
            ) and len(function_args) >= 2:
                x = function_args[0]
                y = function_args[1]
                x *= width * coordinates_multiplier
                y *= height * coordinates_multiplier
                modified_args = [x, y] + function_args[2:]
            else:
                modified_args = function_args

            python_code += (
                function_name
                + "("
                + ", ".join([repr(arg) for arg in modified_args])
                + ")\n"
            )

        return python_code

    return to_python_code


def extract_content_by_tags(text: str, tags: list[str]) -> dict[str, str | None]:
    """
    Extracts the first occurrence of content inside specified tags and returns a dictionary.

    Parameters:
        text (str): The input string containing various tags.
        tags (list[str]): A list of tag names to extract content from.

    Returns:
        dict[str, Optional[str]]: A dictionary where keys are tag names,
            and values are the first content string or None if the tag is not found.
    """
    extracted: dict[str, str | None] = {}

    for tag in tags:
        # Build a regex pattern dynamically for each tag
        pattern = rf"<{tag}>(.*?)</{tag}>"
        # Find the first match for the current tag
        match = re.search(pattern, text, re.DOTALL)
        # Assign None if no match, otherwise assign the matched string
        extracted[tag] = match.group(1) if match else None

    return extracted


def extract_key_value_pairs(text: str, keys: list[str]) -> dict[str, str | None]:
    """
    Extracts key-value pairs from text.

    Parameters:
        text (str): The input string containing various tags.
        keys (list[str]): A list of keys to extract content from.

    Returns:
        dict[str, Optional[str]]: A dictionary of extracted key-value pairs.
    """
    result = {}
    for key in keys:
        # Use regex to find the key followed by a colon, then extract the value until the next key or the end of string
        pattern = rf"{key}\s*:\s*(.+?)(?=(?:\n\w+\s*:)|$)"
        match = re.search(pattern, text, re.DOTALL)
        result[key] = match.group(1).strip() if match else None
    return result


def extract_action(text: str) -> str:
    """
    Extracts the text before the first instance of (...) in the string.

    Args:
        text (str): The input string.

    Returns:
        str: The action name before `(...)`. Returns an empty string if not found.
    """
    match = re.search(r"\b(\w+)\s*\(", text)
    return match.group(1) if match else ""


def extract_bid(text: str) -> str:
    """
    Extracts the first instance of content enclosed in single or double quotes.

    Args:
        text (str): The input string.

    Returns:
        str: The content inside the first pair of quotes. Returns an empty string if not found.
    """
    match = re.search(r'["\'](.*?)["\']', text)
    return match.group(1) if match else ""


def extract_info_from_browsergym_action(action_str: str) -> BrowserGymActionInfo:
    """
    Extracts information from a BrowserGym action string.

    Args:
        action_str (str): The action string to extract information from.

    Returns:
        BrowserGymActionInfo: The extracted information from the action string.
    """
    # Extract the action name
    action_type = extract_action(action_str)
    action_parameters = extract_values_maintain_types(action_str)

    ret = BrowserGymActionInfo(action_type=action_type)
    if action_type in BID_ACTIONS:
        # Bid actions have a string bid and potentially other parameters
        ret.bids = [str(action_parameters[0])]
        # store extra parameters as values
        if len(action_parameters) >= 2:
            ret.value = action_parameters[1:]
    elif action_type in COORDINATE_ACTIONS:
        # Coordinate actions have two float values
        ret.absolute_coordinates = [(action_parameters[0], action_parameters[1])]
        if len(action_parameters) >= 3:
            ret.value = action_parameters[2:]
    elif action_type in MULTI_BID_ACTIONS:
        # Multi-bid actions have two string bids and potentially other parameters
        ret.bids = [str(action_parameters[0]), str(action_parameters[1])]
        if len(action_parameters) >= 3:
            ret.value = action_parameters[2:]
    elif action_type in MULTI_COORDINATE_ACTIONS:
        # Multi-coordinate actions have four float values
        ret.absolute_coordinates = [
            (action_parameters[0], action_parameters[1]),
            (action_parameters[2], action_parameters[3]),
        ]
        if len(action_parameters) >= 5:
            ret.value = action_parameters[4:]
    elif action_type in VALUE_ONLY_ACTIONS:
        # Value-only actions have a single string parameter
        ret.value = action_parameters
    elif action_type in NOOP_ACTIONS:
        # Noop actions have default value of 1000 and no other parameters
        ret.value = [1000] if len(action_parameters) == 0 else action_parameters
    elif action_type in SCROLL_ACTIONS:
        ret.value = action_parameters
    elif action_type in NO_PARAMETERS_ACTIONS:
        # We do nothing for actions with no parameters
        pass

    return ret


def extract_values_maintain_types(string: str) -> list[str | float]:
    """
    Extracts values from a string while maintaining their types.

    Args:
        string (str): The input string containing values separated by commas.

    Returns:
        list[Any]: A list of extracted values with their correct types.
    """
    # Find the function arguments inside parentheses
    match = re.search(r"\w+\((.*)\)", string)
    if not match:
        return []

    content = match.group(1).strip()

    args_list = []
    # Use ast.parse to safely evaluate arguments
    tree = ast.parse(f"f({content})").body[0].value
    for arg in tree.args:
        args_list.append(ast.literal_eval(arg))  # Extract positional arguments
    for kw in tree.keywords:
        args_list.append(
            ast.literal_eval(kw.value)
        )  # Extract keyword arguments, ignoring names

    return args_list


def get_alternative_action(action: str) -> str:
    """
    Returns the alternative action for the given action.

    Args:
        action (str): The action to get the alternative for.

    Returns:
        str: The alternative action for the given action.
            An empty string if no alternative is found.
    """
    if action in COORDINATE_TO_BID_ACTION_CONVERSION_TABLE:
        return COORDINATE_TO_BID_ACTION_CONVERSION_TABLE[action]
    if action in BID_TO_COORDINATE_ACTION_CONVERSION_TABLE:
        return BID_TO_COORDINATE_ACTION_CONVERSION_TABLE[action]
    return ""
