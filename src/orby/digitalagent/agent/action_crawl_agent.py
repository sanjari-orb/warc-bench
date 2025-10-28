from orby.digitalagent.agent import Agent
from orby.digitalagent.model import FoundationModel
from orby.digitalagent.agent.utils import (
    prompt_to_messages,
    screenshots_differ,
    produce_fake_details,
)
from orby.digitalagent.utils.action_parsing_utils import extract_content_by_tags
from orby.digitalagent.utils.image_utils import download_image_as_numpy_array
from orby.digitalagent.prompts.default import action_crawler as prompts

WA_DOMAIN_DESCRIPTION = "This website corresponds to an application which is either a map/shopping/shopping admin or a reddit website."


class ActionCrawlAgent(Agent):
    SCREENSHOT_CHANGE_PROMPT = (
        "No change in screenshot",
        "Screenshot changed from this action",
    )
    HTML_CHANGE_PROMPT = ("No change in HTML", "HTML changed from this action")

    def __init__(
        self,
        model_configs: dict,
        actions: str,
        debug: bool = False,
    ):
        """
        This agent performs a random action crawl on the website, where
        it randomly selects an HTML element to interact with at each step of
        the trajectory. The main purpose is to explore the website meaningfully
        like a human would by interacting with interesting buttons on the page and recording how the observation space changes.

        Args:
            model_configs::dict: The configuration dictionary for the FoundationModel.
            actions::str: A string containing the actions that the agent can take, used
                for system prompts.
            debug::bool: A flag to enable debug mode.
        """
        Agent.__init__(self)
        self.model = FoundationModel(**model_configs)
        self.actions = actions
        self.debug = debug
        self.original_landing_page = None

        if self.debug:
            print(
                """
Created Action Crawling agent with
- Model config: {model_configs}
""".format(
                    model_configs=str(model_configs),
                )
            )

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
        self.original_landing_page = screenshot

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
            "description": WA_DOMAIN_DESCRIPTION,
            "html": self.html_history[-1],
            "screenshot": self.screenshot_history[-1],
            "trace": self.trace,
            "original_landing_page": self.original_landing_page,
            "fake_details": produce_fake_details(),
        }
        prompt, images = prompts.render(**variables, block="action_crawler")
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
        meta = extract_content_by_tags(output, ["action description", "action"])
        action_description = meta.get("action description", "")
        action = meta.get("action", "")

        # Store model status for future use
        current_status = {
            "action_description": action_description,
            # These needs to be populated (again) after the action is executed
            "action": action,
            "error": "",
            "html_change": "",
            "screenshot_change": "",
        }
        self.trace.append(current_status)

        if "exit" in action:
            action = "report_infeasible('We landed at a wrong page')"
        return action, meta

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
