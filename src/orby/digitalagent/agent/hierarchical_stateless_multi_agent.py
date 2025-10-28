from copy import deepcopy
import re

from orby.digitalagent.agent import Agent
from orby.digitalagent.model import FoundationModel
from orby.digitalagent.agent.utils import (
    screenshots_differ,
    prompt_to_messages,
    remove_thinking,
)
from orby.digitalagent.utils.image_utils import download_image_as_numpy_array
from orby.digitalagent.prompts.prompts_20241007 import PLAN_TRACE_PROMPT, _trace_string
from orby.digitalagent.prompts.default import hierarchical_stateless_multi as prompts


class HierarchicalStatelessFMGroundingAgent(Agent):
    """
    A simple grounder agent that performs relatively simple grounding tasks with immediate trace feedback.
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
        self.trace = []

    def update(self, html, screenshot, trace):
        self.trace = trace

        self.html_history.append(html)
        self.screenshot_history.append(screenshot)

    def _execution_prompt(self, plan: str):
        trace_string = _trace_string(self)

        variables = {
            "goal": self.goal,
            "actions": self.actions,
            "trace_string": trace_string,
            "html": self.html_history[-1],
            "plan": plan,
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

        prompt, images = prompts.render(**variables, block="grounding")
        messages = prompt_to_messages(prompt, images=images)

        return messages

    def act(self, plan, **kwargs):
        """
        Takes the screenshot, HTML, and current planned action, and generates the grounded action
        """
        execution_messages = self._execution_prompt(plan)
        action = self.model.generate(messages=execution_messages, **kwargs)

        action = remove_thinking(action)

        return action


class HierarchicalStatelessFMPlannerAgent(Agent):
    """
    A simple planner implementation that generates a few next steps, and is able to replan based on the execution trace.
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

    def _planning_prompt(self, previous_plan):
        plan_string = PLAN_TRACE_PROMPT.format(executed_plan=previous_plan)

        variables = {
            "goal": self.goal,
            "actions": self.actions,
            "trace_string": plan_string,
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

    def act(self, previous_plan, **kwargs):
        """
        Takes the overall goal, the current screenshot/html, and previous plan execution trace (if any),
        and generates the next few steps of the plan, each on a separate line.
        """
        planning_messages = self._planning_prompt(previous_plan)
        plan = self.model.generate(messages=planning_messages, **kwargs)

        plan = remove_thinking(plan)

        return plan


class HierarchicalStatelessFMMultiAgent(Agent):
    """
    A sample agent implementation of hierarchical agent with standalone planner and grounder agents.
    """

    def __init__(self, model_configs: dict, actions: str, limit_to_ctx: bool = True):
        Agent.__init__(self)

        planner_model_configs = None
        if "planner" in model_configs:
            planner_model_configs = model_configs["planner"]
            del model_configs["planner"]

        grounder_model_configs = None
        if "grounder" in model_configs:
            grounder_model_configs = model_configs["grounder"]
            del model_configs["grounder"]

        if not planner_model_configs:
            planner_model_configs = model_configs
        if not grounder_model_configs:
            grounder_model_configs = model_configs

        self.model_configs = model_configs
        self.model = FoundationModel(**model_configs) if model_configs else None
        self.actions = actions
        self.limit_to_ctx = limit_to_ctx
        self.plan_history = []

        self.current_plan = []
        self.executed_plan = []
        self.plan_step = 0
        self.max_ground_step = 3
        self.ground_step = 0

        self.planner = HierarchicalStatelessFMPlannerAgent(
            planner_model_configs, actions, limit_to_ctx, parent_agent=self
        )
        self.grounder = HierarchicalStatelessFMGroundingAgent(
            grounder_model_configs, actions, limit_to_ctx, parent_agent=self
        )

    def reset(self, goal, html, screenshot, goal_image_urls=[]):
        self.planner.reset(goal, html, screenshot, goal_image_urls=goal_image_urls)
        self.grounder.reset("", html, screenshot)

        self.goal = goal
        self.html_history = [html]
        self.screenshot_history = [screenshot]

    def update(self, html, screenshot, trace):
        self.trace = trace

        self.html_history.append(html)
        self.screenshot_history.append(screenshot)

        grounder_trace = self.trace[-self.ground_step :] if self.ground_step > 0 else []
        self.grounder.update(html, screenshot, grounder_trace)

    def _grounding_succeeded(self):
        variables = {
            "goal": self.current_plan[self.plan_step],
            "html": self.html_history[-1],
            "screenshot": self.screenshot_history[-1],
            "prev_screenshot": self.screenshot_history[-2],
        }

        prompt, images = prompts.render(**variables, block="grounding_verifier")
        messages = prompt_to_messages(prompt, images=images)

        response = self.model.generate(messages=messages)

        return response.lower().strip().startswith("yes")

    def act(self, **kwargs):

        if self.ground_step > 0:
            # If grounding has been performed in a previous step, check if the action was successful
            # this is a very crude check for changes in state
            success = self._grounding_succeeded()

            self.executed_plan.append((self.current_plan[self.plan_step], success))
            self.planner.update(
                self.html_history[-1], self.screenshot_history[-1], self.executed_plan
            )
            if success:
                # Grounding was successful, move to the next step in the plan
                self.plan_step += 1
                self.ground_step = 0
            elif self.ground_step >= self.max_ground_step:
                # Grounding failed after a few retries, replan
                self.current_plan = []
                self.plan_step = 0
                self.ground_step = 0

        if self.plan_step >= len(self.current_plan):
            # Plan has been exhausted, replan
            self.current_plan = []
            self.plan_step = 0
            self.ground_step = 0

        if not self.current_plan:
            plan = self.planner.act(
                "\n".join([str(x) for x in self.executed_plan]), **kwargs
            )

            # Parse the plan from numbered list to a list

            if "<feedback>" in plan and "</feedback>" in plan:
                feedback = re.search(r"<feedback>([\w\W]*?)</feedback>", plan).group(1)
                self.executed_plan.append(
                    ("Feedback from the environment:" + feedback.strip(), True)
                )
                plan = plan.replace(f"<feedback>{feedback}</feedback>", "")

            self.current_plan = [x for x in plan.split("\n") if len(x.strip()) > 0]
            self.plan_step = 0

            if len(self.current_plan) == 0:
                # No plan generated, return noop
                return "noop()", {}

        if self.ground_step == 0:
            # Reset grounder context to only contain grounding history for the current plan step
            self.grounder.reset(
                self.current_plan[self.plan_step],
                self.html_history[-1],
                self.screenshot_history[-1],
            )

        # Perform grounding
        action = self.grounder.act(self.current_plan[self.plan_step], **kwargs)
        self.ground_step += 1

        return action, {}

    def get_state_dict(self) -> dict:
        state_dict = super().get_state_dict()
        state_dict["plan_history"] = deepcopy(self.plan_history)
        state_dict["current_plan"] = deepcopy(self.current_plan)
        state_dict["executed_plan"] = deepcopy(self.executed_plan)
        state_dict["plan_step"] = self.plan_step
        state_dict["max_ground_step"] = self.max_ground_step
        state_dict["ground_step"] = self.ground_step
        state_dict["planner_state_dict"] = self.planner.get_state_dict()
        state_dict["grounder_state_dict"] = self.grounder.get_state_dict()
        return state_dict

    def load_state_dict(self, state_dict: dict) -> None:
        self.plan_history = state_dict["plan_history"]
        self.current_plan = state_dict["current_plan"]
        self.executed_plan = state_dict["executed_plan"]
        self.plan_step = state_dict["plan_step"]
        self.max_ground_step = state_dict["max_ground_step"]
        self.ground_step = state_dict["ground_step"]
        self.planner.load_state_dict(state_dict["planner_state_dict"])
        self.grounder.load_state_dict(state_dict["grounder_state_dict"])

        super().load_state_dict(state_dict)
