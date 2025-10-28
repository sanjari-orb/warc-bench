from typing import Type
from copy import deepcopy

from orby.digitalagent.agent import Agent
from orby.digitalagent.model import FoundationModel
from orby.digitalagent.utils.action_utils import clean_action
from orby.digitalagent.agent.utils import (
    prompt_to_messages,
    remove_thinking,
)
from orby.digitalagent.utils.image_utils import download_image_as_numpy_array
from orby.digitalagent.prompts.default import hsm_v2 as prompts
from orby.digitalagent.agent.task_executors.hybrid_executor_agent import (
    HybridExecutorAgent,
)


class HighLevelPlannerAgent(Agent):
    """
    A simple planner implementation that generates the next step.
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

    def _planning_prompt(self, previous_steps: str):

        variables = {
            "goal": self.goal,
            "actions": self.actions,
            "trace_string": previous_steps,
            "html": self.html_history[-1],
            "goal_images": self.goal_images,
            "screenshot": self.screenshot_history[-1],
            "prev_screenshot": (
                self.screenshot_history[-2]
                if len(self.screenshot_history) > 1
                else None
            ),
        }

        prompt, images = prompts.render(**variables, block="planning")
        messages = prompt_to_messages(prompt, images=images)

        return messages

    def act(self, previous_steps: str, **kwargs):
        """
        Takes the overall goal, the current screenshot/html, and previous plan execution trace (if any),
        and generates the next few steps of the plan, each on a separate line.
        """
        planning_messages = self._planning_prompt(previous_steps)
        plan = self.model.generate(messages=planning_messages, **kwargs)

        plan = remove_thinking(plan)

        return plan


class HsmV2Agent(Agent):
    """
    A sample agent implementation of hierarchical agent with standalone planner and executor agents.
    """

    def __init__(
        self,
        model_configs: dict,
        actions: str,
        limit_to_ctx: bool = True,
        executor_cls: Type[Agent] = HybridExecutorAgent,
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
        self.current_step = ""
        self.executing = False
        self.executor_message = ""

        self.planner = HighLevelPlannerAgent(
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
        if not self.executing:
            previous_plan_str = "\n".join(
                f"Step {i+1}: {step[0]}\nResult: {step[1]}"
                for i, step in enumerate(self.previous_steps)
            )
            for _ in range(3):
                planner_output = self.planner.act(previous_plan_str, **kwargs)
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
            self.current_step = plan
            self.executing = True
            self.executor_message = ""
            self.previous_steps.append([plan, ""])
            self.executor.reset(
                plan, self.html_history[-1], self.screenshot_history[-1]
            )
            self.planner.update(self.html_history[-1], self.screenshot_history[-1], "")
        action = self.executor.act(self.trace[-1][1] if self.trace else "", **kwargs)
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
                self.previous_steps[-1][1] = self.executor_message
                self.executing = False
                return self._act(**kwargs)
        except:
            pass
        return action, {}

    def act(self, **kwargs):
        return self._act(**kwargs)

    def get_state_dict(self) -> dict:
        state_dict = super().get_state_dict()
        state_dict["previous_steps"] = deepcopy(self.previous_steps)
        state_dict["executing"] = self.executing
        state_dict["executor_message"] = self.executor_message
        state_dict["current_step"] = self.current_step
        state_dict["planner_state_dict"] = self.planner.get_state_dict()
        state_dict["executor_state_dict"] = self.executor.get_state_dict()
        return state_dict

    def load_state_dict(self, state_dict: dict) -> None:
        self.previous_steps = state_dict["previous_steps"]
        self.executing = state_dict["executing"]
        self.executor_message = state_dict["executor_message"]
        self.current_step = state_dict["current_step"]
        self.planner.load_state_dict(state_dict["planner_state_dict"])
        self.executor.load_state_dict(state_dict["executor_state_dict"])
        super().load_state_dict(state_dict)
