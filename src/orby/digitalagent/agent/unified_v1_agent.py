import re

from orby.digitalagent.agent import Agent
from orby.digitalagent.model import FoundationModel
from orby.digitalagent.agent.utils import prompt_to_messages, screenshots_differ
from orby.digitalagent.utils.action_parsing_utils import extract_content_by_tags
from orby.digitalagent.utils.action_grounding_utils import (
    extract_coordinates_from_string,
)
from orby.digitalagent.utils.image_utils import download_image_as_numpy_array
from orby.digitalagent.prompts.default import unified_v1 as prompts


class UnifiedV1FMAgent(Agent):
    SCREENSHOT_CHANGE_PROMPT = (
        "No change in screenshot",
        "Screenshot changed from this action",
    )
    HTML_CHANGE_PROMPT = ("No change in HTML", "HTML changed from this action")
    SUPPORTED_MOUSE_ACTIONS = [
        "mouse_move",
        "mouse_up",
        "mouse_down",
        "mouse_click",
        "mouse_dblclick",
        "mouse_upload_file",
    ]

    def __init__(
        self,
        model_configs: dict,
        actions: str,
        context: str = "",
        debug: bool = False,
    ):
        """
        This agent is very similar to the BasicStatelessFMAgent.
        1. It merges trace representation into the main prompt template.
        2. It uses a different representation of the trace; the trace contains: thinkings,
            action descriptions, actions, errors, html changes, and screenshot changes.
        3. When doing coordinate-based actions, it calls an additional FoundationModel to
            do the job.

        Args:
            model_configs::dict: The configuration dictionary for the FoundationModel.
            actions::str: A string containing the actions that the agent can take, used
                for system prompts.
            context::str: The context of the task, which may include user information and
                the current date. Defaults to an empty string.
            debug::bool: A flag to enable debug mode.
        """
        Agent.__init__(self)
        if "specialized_grounder" in model_configs:
            specialized_grounder_configs = model_configs.pop("specialized_grounder")
        else:
            specialized_grounder_configs = {
                "provider": "fireworks",
                "name": "accounts/orby/models/llavanext-mistral7b-ooshf6",
                "temperature": 0.0,
                "top_p": 0.3,
                "max_tokens": 128,
            }
        self.model = FoundationModel(**model_configs)
        self.specialized_grounder_model = FoundationModel(
            **specialized_grounder_configs
        )
        self.actions = actions
        self.context = context
        self.debug = debug

        if self.debug:
            print(
                """
Created Unified V1 agent with
- Model config: {model_configs}
- Coordinate grounder config: {coord_grounder_config}
- context: {context}
""".format(
                    model_configs=str(model_configs),
                    coord_grounder_config=str(specialized_grounder_configs),
                    context=context.replace("\n", " "),
                )
            )

    def set_context(self, context: str) -> None:
        """
        Set the context of the task.

        Args:
            context::str: The context of the task, which may include user information and
                the current date.
        """
        self.context = context

    def reset(
        self, goal: str, html: str, screenshot: bytes, goal_image_urls: list[str] = []
    ) -> None:
        """
        Reset the agent's internal state, if any.

        Args:
            goal::str: The goal of the current task.
            html::str: The HTML representation of the starting environment. (could be axtree)
            screenshot::Any: The screenshot of the starting environment. (usually numpy.ndarray)
            goal_image_urls::List[str]: A list of URLs of images that are relevant to the goal.
        """
        self.goal = goal
        self.goal_images = [
            download_image_as_numpy_array(url) for url in goal_image_urls
        ]
        self.html_history = [html]
        self.screenshot_history = [screenshot]
        self.trace = []

    def update(
        self, html: str, screenshot: bytes, trace: list[tuple[str, str]]
    ) -> None:
        """
        Update the agent's internal state based on new observations from the environment.

        Args:
            html::str: The HTML representation of the current environment. (could be axtree)
            screenshot::Any: The screenshot of the current environment. (usually numpy.ndarray)
            trace::List[Tuple[str, str]]: A list of tuples containing the previous actions taken
                and the error messages from all previous actions.
        """
        self.html_history.append(html)
        self.screenshot_history.append(screenshot)

        # If we are updating before any action is taken, we don't need to update the trace
        if not trace:
            return

        # We are always provided the entire trace, but we just use the last element
        # This is very similar to the _trace_string construction in prompts_20241007.py
        action, error = trace[-1]
        screenshot_change_text = self.SCREENSHOT_CHANGE_PROMPT[
            int(
                screenshots_differ(
                    self.screenshot_history[-1], self.screenshot_history[-2]
                )
            )
        ]
        html_change_text = self.HTML_CHANGE_PROMPT[
            int(self.html_history[-1] != self.html_history[-2])
        ]
        self.trace[-1].update(
            {
                "action": action,
                "error": error,
                "html_change": html_change_text,
                "screenshot_change": screenshot_change_text,
            }
        )

    def act(self, **kwargs) -> tuple[str, dict]:
        """
        Act based on the current state of the agent.

        Args:
            **kwargs: Any additional arguments required for generating the action, passed to
                the FM for the generation call.

        Returns:
            tuple[str, dict]: A tuple containing
                1. The action to be taken.
                2. A dictionary containing the meta information about the action.
        """
        # Create prompt
        variables = {
            "goal": self.goal,
            "actions": self.actions,
            "context": self.context,
            "goal_images": self.goal_images,
            "html": self.html_history[-1],
            "screenshot": self.screenshot_history[-1],
            "trace": self.trace,
        }
        prompt, images = prompts.render(**variables, block="unified_agent")
        messages = prompt_to_messages(prompt, images=images)

        # generate model output and extract necessary information, including the action
        # print("Messages: ", end="")
        # self._print_messages(messages)
        output = self.model.generate(
            messages=messages,
            return_raw=False,
            **kwargs,
        )
        if self.debug:
            print("Model output: ", output)
        meta = extract_content_by_tags(
            output, ["thinking", "action description", "action"]
        )
        thinking = meta.get("thinking", "")
        action_description = meta.get("action description", "")
        action = meta.get("action", "")

        # If we encounter a supported coordinate-based action, we call our specialized grounder
        # to regenerate the coordinate
        if self._is_supported_mouse_action(action):
            if self.debug:
                print("Regenerating coordinates for coordinate-based action.")
            action = self._regenerate_coordinates_action(action, action_description)
            if self.debug:
                print("New action: ", action)

        # Store model status for future use
        current_status = {
            "thinking": thinking,
            "action_description": action_description,
            # These needs to be populated (again) after the action is executed
            "action": action,
            "error": "",
            "html_change": "",
            "screenshot_change": "",
        }
        self.trace.append(current_status)

        return action, meta

    def _is_supported_mouse_action(self, action: str) -> bool:
        if not action:
            return False
        for action_type in self.SUPPORTED_MOUSE_ACTIONS:
            if action_type in action:
                return True
        return False

    def _print_messages(self, messages: list[dict]) -> None:
        """
        Print the messages in a human-readable format.

        Args:
            messages::List[Dict]: A list of dictionaries containing the messages to be printed.
        """
        for message in messages:
            print(f"Role: {message['role']}")
            if isinstance(message["content"], str):
                print(message["content"])
            else:
                for content in message["content"]:
                    if isinstance(content, str):
                        print(content)
                    elif content["type"] == "image_url":
                        print("<Image>")
                    else:
                        print(content["text"])

    def _regenerate_coordinates_action(
        self,
        action: str,
        action_description: str,
    ) -> str:
        """
        Regenerate the coordinates for the coordinate-based actions
        using the specialized grounder.

        Args:
            action::str: The original action string.
            action_description::str: The description of the action.

        Returns:
            str: The regenerated action string.
        """
        screenshot_width = self.screenshot_history[-1].shape[1]
        screenshot_height = self.screenshot_history[-1].shape[0]
        variables = {
            "screenshot": self.screenshot_history[-1],
            "action_description": action_description,
            "screenshot_width": screenshot_width,
            "screenshot_height": screenshot_height,
        }
        prompt, images = prompts.render(**variables, block="coordinate_grounder")
        messages = prompt_to_messages(prompt, user_delimiter="Human:\n", images=images)
        if self.debug:
            self._print_messages(messages)

        output = self.specialized_grounder_model.generate(
            messages=messages,
            return_raw=False,
        )
        if self.debug:
            print("Output: ", output)
        coordinates = extract_coordinates_from_string(output)

        if coordinates == None:
            if self.debug:
                print(
                    "Failed to regenerate coordinates! Could not find coordinates in the output. Use the old coordinates instead."
                )
            return action

        if self.debug:
            print("Coordinates: ", coordinates)
        absoulte_coords = (
            int(coordinates[0] * screenshot_width + 0.5),
            int(coordinates[1] * screenshot_height + 0.5),
        )
        new_action = self._replace_coordinates(action, absoulte_coords)

        return new_action

    def _replace_coordinates(
        self, action_string: str, new_coords: tuple[float, float]
    ) -> str:
        """
        Replace the coordinates in the action string with the new coordinates.

        Args:
            action_string (str): The action string to replace the coordinates in.
            new_coords (tuple[float, float]): The new coordinates to replace the old ones with.

        Returns:
            str: The action string with the new coordinates.
        """
        # Regex to find the first two numbers in the function
        pattern = re.compile(r"(\w+)\((\d+), (\d+),?")
        match = pattern.search(action_string)

        if match:
            func_name, _, _ = match.groups()
            new_x, new_y = new_coords
            replacement = f"{func_name}({new_x}, {new_y}"
            return action_string.replace(match.group(0), replacement)

        return action_string
