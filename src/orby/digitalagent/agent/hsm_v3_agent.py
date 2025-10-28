from typing import Type
from copy import deepcopy
import re

from orby.digitalagent.agent import Agent
from orby.digitalagent.model import FoundationModel
from orby.digitalagent.utils.action_utils import clean_action
from orby.digitalagent.agent.utils import (
    prompt_to_messages,
    remove_thinking,
)
from orby.digitalagent.utils.image_utils import download_image_as_numpy_array
from orby.digitalagent.prompts.default import hsm_v3
from orby.digitalagent.utils.action_parsing_utils import extract_key_value_pairs


class _PlannerAgent(Agent):
    """
    A simple planner implementation that generates the next step described in natural language.
    """

    def __init__(
        self, model_configs: dict, actions: str, limit_to_ctx: bool = True, **kwargs
    ):
        Agent.__init__(self, **kwargs)
        self.model_configs = model_configs
        self.model = FoundationModel(**model_configs) if model_configs else None
        self.actions = actions
        self.limit_to_ctx = limit_to_ctx

    def reset(self, goal, html, screenshot, goal_image_urls=[]):
        self.goal = goal
        self.goal_images = [
            download_image_as_numpy_array(url) for url in goal_image_urls
        ]
        self.html_history = [html]
        self.screenshot_history = [screenshot]

    def update(self, html, screenshot, trace):
        self.trace = trace
        self.html_history.append(html)
        self.screenshot_history.append(screenshot)

    def _planning_prompt(self, previous_steps: str, progress: str):
        variables = {
            "goal": self.goal,
            "actions": self.actions,
            "trace_string": previous_steps,
            "html": self.html_history[-1],
            "goal_images": self.goal_images,
            "screenshot": self.screenshot_history[-1],
            "progress": progress,
            "prev_screenshot": (
                self.screenshot_history[-2]
                if len(self.screenshot_history) > 1
                else None
            ),
        }
        prompt, images = hsm_v3.render(**variables, block="planning")
        messages = prompt_to_messages(prompt, images=images)

        return messages

    def act(self, previous_steps: str, progress: str, **kwargs):
        """
        Takes the overall goal, previous steps, and current progress as the input and produces the next step described in natural language.
        For example, execute("Click on the login button."), stop("The task is infeasible."). See prompt template for the full action space.
        """
        planning_messages = self._planning_prompt(previous_steps, progress)
        return remove_thinking(
            self.model.generate(messages=planning_messages, **kwargs)
        )


class _ExecutorAgent(Agent):
    """
    An agent that translates a step described in natural language into executable code and describe the code.
    """

    def __init__(
        self, model_configs: dict, actions: str, limit_to_ctx: bool = True, **kwargs
    ):
        Agent.__init__(self, **kwargs)
        self.model_configs = model_configs
        self.actions = actions
        self.model = FoundationModel(**model_configs) if model_configs else None
        self.limit_to_ctx = limit_to_ctx

    def reset(self, goal, html, screenshot, goal_image_urls=[]):
        self.goal = goal
        self.goal_images = [
            download_image_as_numpy_array(url) for url in goal_image_urls
        ]
        self.html_history = [html]
        self.screenshot_history = [screenshot]
        self.trace = []

    def update(self, html, screenshot, trace):
        self.html_history.append(html)
        self.screenshot_history.append(screenshot)

    def _execution_prompt(self):
        variables = {
            "goal": self.goal,
            "actions": self.actions,
            "html": self.html_history[-1],
            "screenshot_width": self.screenshot_history[-1].shape[1],
            "screenshot_height": self.screenshot_history[-1].shape[0],
            "goal_images": self.goal_images,
            "screenshot": self.screenshot_history[-1],
            "prev_screenshot": (
                self.screenshot_history[-2]
                if len(self.screenshot_history) > 1
                else None
            ),
        }

        prompt, images = hsm_v3.render(**variables, block="execution")
        messages = prompt_to_messages(prompt, images=images)
        return messages

    def act(self, **kwargs):
        """
        Returns an executable action in Python and a natural language description of the action.
        """
        execution_messages = self._execution_prompt()
        output = self.model.generate(messages=execution_messages, **kwargs)
        output = remove_thinking(output)
        meta = extract_key_value_pairs(output, ["Action", "Description"])
        action_description = meta.get("Description", "")
        action = meta.get("Action", "")
        self.trace.append(
            [f"{action_description} - {action}" if action_description else action, ""]
        )

        # There are some cases where the model outputs the action in the second line, without the key "Action"
        if not action:
            pattern = (
                r"\b\w+\(\S*?\)"  # Matches any word characters followed by parentheses
            )
            match = re.search(pattern, output)
            if match:
                action = match.group()

        return action, action_description


class HsmV3Agent(Agent):
    """
    A sample agent implementation of hierarchical agent with standalone planner and executor agents.
    """

    def __init__(
        self,
        model_configs: dict,
        actions: str,
        limit_to_ctx: bool = True,
        max_call_depth: int = 3,
        executor_cls: Type[Agent] = _ExecutorAgent,
    ):
        Agent.__init__(self)

        self.model = FoundationModel(**model_configs) if model_configs else None
        planner_model_configs = None
        if "planner" in model_configs:
            planner_model_configs = model_configs["planner"]
            del model_configs["planner"]

        executor_model_configs = None
        if "executor" in model_configs:
            executor_model_configs = model_configs["executor"]
            del model_configs["executor"]

        if not planner_model_configs:
            planner_model_configs = model_configs
        if not executor_model_configs:
            executor_model_configs = model_configs

        self.model_configs = model_configs
        self.actions = actions
        self.limit_to_ctx = limit_to_ctx
        self.previous_steps = []
        self.progress = ""
        self.executor_message = ""
        self.max_call_depth = max_call_depth

        self.planner = _PlannerAgent(
            planner_model_configs, actions, limit_to_ctx, parent_agent=self
        )
        self.executor = executor_cls(
            executor_model_configs, actions, limit_to_ctx, parent_agent=self
        )

    def reset(self, goal, html, screenshot, goal_image_urls=[]):
        self.planner.reset(goal, html, screenshot, goal_image_urls=goal_image_urls)
        self.executor.reset("", html, screenshot)

        self.goal = goal
        self.html_history = [html]
        self.screenshot_history = [screenshot]
        self.previous_steps = []
        self.executor_message = ""

    def update(self, html, screenshot, trace):
        self.trace = trace

        self.html_history.append(html)
        self.screenshot_history.append(screenshot)

        self.executor.update(html, screenshot, "")
        self.planner.update(html, screenshot, trace)

    def _parse_plan(self, plan):
        step_to_execute = None
        success_message = None
        infeasible_message = None

        def execute(step):
            nonlocal step_to_execute
            step_to_execute = step

        def send_msg_to_user(text):
            nonlocal success_message
            success_message = text

        def report_infeasible(text):
            nonlocal infeasible_message
            infeasible_message = text

        def noop(wait_ms=500):
            pass

        try:
            exec(
                clean_action(plan),
                {
                    "execute": execute,
                    "complete": send_msg_to_user,
                    "stop": report_infeasible,
                    "noop": noop,
                },
            )
        except Exception as e:
            return str(e), None, None, None
        return None, step_to_execute, success_message, infeasible_message

    def _executor_send_msg_to_user(self, text):
        self.executor_message = text

    def _executor_report_infeasible(self, text):
        self.executor_message = text

    def _act(self, **kwargs):
        self.act_call_depth += 1
        if self.act_call_depth > self.max_call_depth:
            return "noop()", {}
        previous_plan_str = "\n".join(
            f"Step {i+1}: {step}" for i, step in enumerate(self.previous_steps)
        )
        for _ in range(3):
            planner_output = self.planner.act(
                previous_plan_str, self.progress, **kwargs
            )
            parsed_planner_output = extract_key_value_pairs(
                planner_output, ["progress", "next_step"]
            )
            planner_output = parsed_planner_output.get("next_step", "")
            self.progress = parsed_planner_output.get("progress", "")
            error, plan, success, infeasible = self._parse_plan(planner_output)
            if error is None:
                break
            previous_plan_str += (
                "\n" + f"Next step candidate: {planner_output}\nResult: {error}"
            )
        if plan is None:
            self.previous_steps.append(
                [
                    clean_action(planner_output),
                    "The task is not completed yet. What else can you try?",
                ]
            )
            if success:
                return f"send_msg_to_user({repr(success)})", {}
            if infeasible:
                return f"report_infeasible({repr(infeasible)})", {}
            return planner_output, {}
        self.trace = []
        self.previous_steps.append(plan)
        self.executor.reset(plan, self.html_history[-1], self.screenshot_history[-1])
        self.planner.update(self.html_history[-1], self.screenshot_history[-1], "")
        action, action_description = self.executor.act(**kwargs)
        self.previous_steps[-1] = action_description
        try:
            cleaned_action = clean_action(action)
            exec(
                cleaned_action,
                {
                    "send_msg_to_user": self._executor_send_msg_to_user,
                    "report_infeasible": self._executor_report_infeasible,
                },
            )
            if self.executor_message:
                self.previous_steps[-1] += "\nResult: " + self.executor_message
                return self._act(**kwargs)
        except:
            pass
        return action, {}

    def act(self, **kwargs):
        self.act_call_depth = 0
        return self._act(**kwargs)

    def get_state_dict(self) -> dict:
        state_dict = super().get_state_dict()
        state_dict["previous_steps"] = deepcopy(self.previous_steps)
        state_dict["executing"] = self.executing
        state_dict["executor_message"] = self.executor_message
        state_dict["progress"] = self.progress
        state_dict["planner_state_dict"] = self.planner.get_state_dict()
        state_dict["executor_state_dict"] = self.executor.get_state_dict()
        return state_dict

    def load_state_dict(self, state_dict: dict) -> None:
        self.previous_steps = state_dict["previous_steps"]
        self.executing = state_dict["executing"]
        self.executor_message = state_dict["executor_message"]
        self.progress = state_dict["progress"]
        self.planner.load_state_dict(state_dict["planner_state_dict"])
        self.executor.load_state_dict(state_dict["executor_state_dict"])
        super().load_state_dict(state_dict)
