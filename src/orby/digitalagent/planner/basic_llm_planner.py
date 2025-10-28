from PIL import Image
from typing import List, Optional

import logging
import numpy as np
import re

from orby.digitalagent.agent import utils, Agent
from orby.digitalagent.model import FoundationModel
from orby.digitalagent.planner import constants


class BasicLLMPlanner(Agent):
    def __init__(self, model_name: str, model_provider: str):
        """
        Base class for an LLM based planner.
        """
        self.model = FoundationModel(name=model_name, provider=model_provider)

        SYSTEM_PROMPT = "You are an autonomous intelligent agent tasked with navigating a web browser. You will be given web-based tasks to analyze."

        self.summarizer = (
            SYSTEM_PROMPT
            + 'You are provided a screenshot of a webpage. The task a user is trying to perform on this page is "{task_description}". Here is a list of exact actions which the user has ALREADY performed on the page: {past_actions}. Can you provide a succinct textual summary describing the steps the user has done already in the plan which they would have thought of in order to complete the task?'
        )

        self.planner = (
            SYSTEM_PROMPT
            + "You are provided a screenshot of a webpage for reference. The task a user is trying to perform on this page is \n<task_description>\n{task_description}\n</task_description>\nHere is a summary of what has happened so far: \n <start of summary>\n {summary}\n<end of summary>\nBased on this can you first draft a high level plan of how to solve this task from this step onwards and then provide the textual description of the action the user should take on the current page next? Give the plan, think through it and in the end, provide a one line description of the **next** action enclosed in ```...```. Only output the final answer in ```...``` and no other text. Remember, that the lowest granularity of actions a user can do on a webpage are *clicking* on an html element, *typing* in an html element, *hovering* over an element, pressing a key/combination of keys or scrolling (although you may not need to do this if you can see the whole webpage!). Please note that the description of the next action you provide in ```...``` should only be should only be at an equal OR **higher** level of granularity of planning than this list of individual actions which the user can perform on the webpage. Ie, you can propose more complex tasks than just clicking/hovering, for eg: {low_level_vocab}. You can also perform some computations in memory if that information is already present in the current screenshot instead of suggesting actions to locate/store this information. \nTo reiterate, given the original task description and summary of past actions, suggest the next action which the user should take on the webpage (adhering to the constraints mentioned above)."
        )

        self.evaluator = (
            SYSTEM_PROMPT
            + "You are provided a screenshot of a webpage for reference on which the user is trying to execute statements A and B. They describe an action being taken on an HTML webpage, where A is a textual description and B is potentially describing the actual HTML element which is being acted upon. Are these statements approximately equivalent? Say yes if they are trying to do the same action on a webpage. Statement A is allowed to be more general/broader and B will refer to a more specific user action on the page, but they should generally be capturing the same user intent. A. {predicted_plan}\nB.{gold_plan}. Answer only in Yes/No in the first line. If No, also provide a reason for mismatch in a new line."
        )

        self.is_atomic = (
            SYSTEM_PROMPT
            + 'Here is a description of a small task you are trying to perform on a webpage: "{final_plan}". Can you classify whether this task is "atomic" or not? An atomic task is something a human would consider to be a single action on a webpage. Example of atomic tasks would be to click/hover on a single button or type a string into a html element etc.  Answer whether the task is atomic in a yes or no.'
        )

        self.decompose = (
            SYSTEM_PROMPT
            + 'Here is a description of a task a user is trying to perform on a webpage: `{final_plan}`. The screenshot of the page you are trying to perform this task is also provided for reference. Can you further break the task down so that it is "atomic". An atomic task is something a human would consider to be a single action on a webpage. Example of atomic tasks would be to click/hover on a single button or type a string into a html element etc. After breaking it down (only if necessary!, do not make the plan too granular), output the immediate next step which the user should take. Think step by step and provide a one line description of the next action in the end enclosed in ```...```.  Only output the final answer in ```...``` and no other text.'
        )

        self.debug_trace = {}
        super().__init__()

    def reset(self, goal, html, screenshot) -> None:
        # Set the current state of the planner.
        # TODO(sanjari): Since this is a one-step planner, we do not
        # need to handle maintaining trajectory state right
        # now
        self.html_history = [html]
        self.screenshot_history = [utils.base64_to_image(screenshot)]
        self.goal = goal
        self.trace = []
        self.debug_trace = {}

    def update(self, html, screenshot, trace) -> None:
        pass

    def act(
        self,
        metadata: dict,
        past_actions: List[str],
    ) -> str:
        """
        Args:
        metadata (dict): metadata dict storing fields to save for tracing
        past_actions (list): history of past actions performed prior to
        current planning step

        Returns:
        string response encapsulating next step in plan.
        """

        task_description = self.goal
        # Past actions
        past_actions = "\n".join(past_actions)
        # Load the screenshot
        screenshot_image = self.screenshot_history[0]

        # Define prompts for each step
        summary = self._simple_prompt(
            prompt=self.summarizer.format(
                task_description=task_description,
                past_actions=past_actions,
            ),
            image=screenshot_image,
        )
        logging.debug("Summary: ", summary)

        plan = self._simple_prompt(
            prompt=self.planner.format(
                task_description=task_description,
                summary=summary,
                low_level_vocab=str(constants.LOW_LEVEL_ACTIONS_VOCAB),
            ),
            image=screenshot_image,
        )
        logging.debug("(LLM) Plan: ", plan)

        final_plan = self._parse_output(plan)
        logging.debug("Parsed plan: ", final_plan)

        self.debug_trace = {
            "metadata": metadata,
            "intent": task_description,
            "past_actions": past_actions,
            "summary": summary,
            "plan": plan,
            "parsed_plan": final_plan,
        }
        return final_plan

    def decompose_before_comparing(self, output: str) -> str:
        """
        Optional utility step added to decompose the plan (output of self.act()
        further before evaluation.
        """
        is_atomic = self._simple_prompt(
            prompt=self.is_atomic.format(
                final_plan=output,
            )
        )
        if not self._is_yes(is_atomic):
            decompose = self._simple_prompt(
                prompt=self.decompose.format(
                    final_plan=output,
                ),
                image=self.screenshot_history[0],
            )
            output = self._parse_output(decompose)

        self.debug_trace["is_atomic"] = is_atomic
        self.debug_trace["decomposed_output"] = output
        return output

    def evaluate(self, output: str, label: str) -> int:
        """
        Returns a score representing plan's success or failure
        """
        is_same = self._simple_prompt(
            prompt=self.evaluator.format(
                predicted_plan=output,
                gold_plan=label,
            ),
            image=self.screenshot_history[0],
        )
        self.debug_trace["llm_eval"] = is_same

        logging.debug("Gold action: ", label)

        if self._is_yes(is_same):
            return 1
        return 0

    def _is_yes(self, output: str) -> bool:
        """Return whether a string response indicates 'Yes' or not."""
        if output.lower().startswith("yes"):
            return True
        return False

    def _parse_output(self, text):
        # Regular expression to match substrings enclosed in triple backticks
        pattern = r"```([^`]+)```"

        # Find all matches in the input text
        matches = re.findall(pattern, text)

        # Return the last match if any matches are found
        return matches[-1] if matches else None

    def _simple_prompt(
        self,
        prompt: str,
        image: Optional[Image.Image] = None,
        role: str = "user",
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ):
        """
        Returns:
        response (str)
        """
        content = [
            {"type": "text", "text": prompt},
        ]
        if image:
            content.append(utils.prepare_image_input(np.array(image)))
        messages = [
            {
                "role": role,
                "content": content,
            }
        ]
        return self.model.generate(
            messages=messages,
            max_tokens=max_tokens,
            return_raw=False,
            temperature=temperature,
        )
