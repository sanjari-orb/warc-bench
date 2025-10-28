"""
Contains the implementation of the HsmV4Agent, a hierarchical agent with standalone planner and executor agents,
This agent builds on top of the HSM V3 agent. It is meant to be an experimental agent to check whether boosting
coordinate-based action accuracy of an agent can improve its performance over specific datasets.

Changes from HSM v3:
- Main agent checks whether its previous action made a change to the state of the environment.
    - If true, the behavior should be the same as HSM v3.
    - If false, the agent should retry the last action with vision-only action wihtout updating the plan.
- Similar to Unified v2, the executor agent should consult a specialized grounder (UGround) when generating
    coordinates for vision-only actions.
"""

from typing import Type
from copy import deepcopy
from browsergym.core.action.highlevel import HighLevelActionSet
import re

from orby.digitalagent.agent import Agent
from orby.digitalagent.model import FoundationModel
from orby.digitalagent.utils.action_utils import clean_action
from orby.digitalagent.agent.utils import (
    prompt_to_messages,
    remove_thinking,
)
from orby.digitalagent.utils.image_utils import download_image_as_numpy_array
from orby.digitalagent.prompts.default import hsm_v4 as hsm_v4_prompt_templates
from orby.digitalagent.utils.action_parsing_utils import (
    extract_key_value_pairs,
    COORDINATE_ACTIONS,
    MULTI_COORDINATE_ACTIONS,
)
from orby.trajectory_collector.utils.data_utils import (
    screenshots_differ,
    axtrees_differ,
)
from orby.digitalagent.utils.action_grounding_utils import (
    extract_coordinates_from_string,
)


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
        prompt, images = hsm_v4_prompt_templates.render(**variables, block="planning")
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
        self,
        model_configs: dict,
        actions: str,
        vision_only_actions: str,
        limit_to_ctx: bool = True,
        **kwargs,
    ):
        Agent.__init__(self, **kwargs)
        self.model_configs = model_configs
        self.actions = actions
        self.vision_only_actions = vision_only_actions
        self.model = FoundationModel(**model_configs) if model_configs else None
        self.limit_to_ctx = limit_to_ctx

        # UGround model for specialized grounding of vision-only actions
        self.specialized_grounder_model = FoundationModel(
            provider="mosaic-vllm",
            name="osunlp/UGround-V1-72B",
            temperature=0.0,
            max_tokens=128,
        )

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

    def _execution_prompt(self, vision_only: bool = False):
        # If we are doing vision-only action, we need to change list of possible
        # actions and use a different prompt block
        if vision_only:
            action_hints = self.vision_only_actions
            prompt_template_block = "execution_vision_only"
        else:
            action_hints = self.actions
            prompt_template_block = "execution"

        variables = {
            "goal": self.goal,
            "actions": action_hints,
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

        prompt, images = hsm_v4_prompt_templates.render(
            **variables, block=prompt_template_block
        )
        messages = prompt_to_messages(prompt, images=images)
        return messages

    def _is_vision_action(self, action: str) -> bool:
        """
        Check whether the action is a vision-only action.
        """
        for vision_action_type in COORDINATE_ACTIONS + MULTI_COORDINATE_ACTIONS:
            if action.startswith(vision_action_type):
                return True
        return False

    def _extract_and_normalize_coordinates(
        self, output: str, screenshot_width: int | float, screenshot_height: int | float
    ) -> list[int] | None:
        """
        Extract and normalize all coordinates from the output of the specialized grounder.

        Args:
            output::str: The output of the specialized grounder.

        Returns:
            list[list[int]]: The list of all extracted and normalized coordinates.
        """
        normalized_coordinates = extract_coordinates_from_string(output)
        if normalized_coordinates is None:
            return None
        absolute_coordinates = [
            int(normalized_coordinates[0] / 1000 * screenshot_width + 0.5),
            int(normalized_coordinates[1] / 1000 * screenshot_height + 0.5),
        ]
        return absolute_coordinates

    def _extract_element_descriptions(self, action_description: str) -> list[str]:
        """
        Extract all the element descriptions from the action description.
        Currently this just means that we give special treatment to the "mouse_drag_and_drop" action.

        Args:
            action_description::str: The description of the action.

        Returns:
            list[str]: The list of all extracted element descriptions.
        """
        match = re.search(r"Drag the element (.*?), Drop to (.*?)$", action_description)
        if match:
            source = match.group(1)
            destination = match.group(2)
            return [source, destination]
        return [action_description]

    def _replace_all_coordinates(
        self, func_str: str, coordinates_list: list[list[float]]
    ) -> str:
        """
        Replace all the coordinates in the action with the new coordinates.

        Args:
            action::str: The original action string.
            coordinates_list::list[list[int]]: The list of all new coordinates.

        Returns:
            str: The new action string.
        """
        values = [coord for coords in coordinates_list for coord in coords]
        # Match function name and parameters using regex
        match = re.match(r"(\w+)\((.*?)\)", func_str)
        if not match:
            return func_str  # Return as is if not a valid function-like string
        func_name, params = match.groups()
        param_list = [p.strip() for p in params.split(",")]
        # Replace the first few parameters with numbers from the list
        num_replacements = min(len(values), len(param_list))
        param_list[:num_replacements] = map(str, values)
        # Construct the modified function string
        new_func_str = f"{func_name}({', '.join(param_list)})"

        return new_func_str

    def _reground_vision_action(self, action: str, action_description: str) -> str:
        """
        Reground the vision-only action with a specialized grounder (UGround).

        Args:
            action::str: The original action string.
            action_description::str: The description of the action.

        Returns:
            str: The regenerated action string.
        """
        element_descriptions = self._extract_element_descriptions(action_description)
        screenshot_width = self.screenshot_history[-1].shape[1]
        screenshot_height = self.screenshot_history[-1].shape[0]

        coordinates_list = []
        for element_description in element_descriptions:
            variables = {
                "screenshot": self.screenshot_history[-1],
                "action_description": element_description,
                "screenshot_width": screenshot_width,
                "screenshot_height": screenshot_height,
            }
            prompt, images = hsm_v4_prompt_templates.render(
                **variables, block="coordinate_grounder"
            )
            messages = prompt_to_messages(
                prompt, user_delimiter="Human:\n", images=images
            )
            output = self.specialized_grounder_model.generate(
                messages=messages,
                return_raw=False,
            )
            coordinates = self._extract_and_normalize_coordinates(
                output,
                screenshot_width=screenshot_width,
                screenshot_height=screenshot_height,
            )
            # If any of the coordinates are not found, we return the original action
            if coordinates is None:
                return action
            # Otherwise, we save the coordinates for later replacement
            coordinates_list.append(coordinates)

        # Otherwise, we replace the coordinates in the action
        new_action = self._replace_all_coordinates(action, coordinates_list)
        return new_action

    def act(self, vision_only: bool = False, **kwargs):
        """
        Returns an executable action in Python and a natural language description of the action.
        """
        execution_messages = self._execution_prompt(vision_only=vision_only)
        output = self.model.generate(messages=execution_messages, **kwargs)
        output = remove_thinking(output)
        meta = extract_key_value_pairs(output, ["Action", "Description"])
        action_description = meta.get("Description", "")
        action = clean_action(meta.get("Action", ""))
        if action == "":
            action = "noop()"
            action_description = "Some error occurred."
        self.trace.append(
            [f"{action_description} - {action}" if action_description else action, ""]
        )

        if self._is_vision_action(action):
            action = self._reground_vision_action(action, action_description)

        return action, action_description


class HsmV4Agent(Agent):
    """
    An agent implementation of hierarchical agent with standalone planner and executor agents.
    This agent builds on top of the HSM V3 agent. It is meant to be an experimental agent checks whether boosting
    coordinate-based action accuracy of an agent can improve its performance over specific datasets.

    Changes from HSM v3:
    - Main agent checks whether its previous action made a change to the state of the environment.
        - If true, the behavior should be the same as HSM v3.
        - If false, the agent should retry the last action with vision-only action wihtout updating the plan.
    - Similar to Unified v2, the executor agent should consult a specialized grounder (UGround) when generating
        coordinates for vision-only actions.
    """

    def __init__(
        self,
        model_configs: dict,
        actions: str,
        vision_only_action_subsets: str,
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
        self.last_action_retried = False

        # We need some special code here to handle vision-only actions
        vision_only_actions = HighLevelActionSet(
            subsets=vision_only_action_subsets,  # allow the agent to also use x,y coordinates
            strict=False,  # less strict on the parsing of the actions
            multiaction=False,  # disable to agent to take multiple actions at once
            demo_mode="off",  # disable visual effects
        )
        vision_only_action_headers = vision_only_actions.describe(
            with_long_description=True, with_examples=True
        )

        self.planner = _PlannerAgent(
            planner_model_configs, actions, limit_to_ctx, parent_agent=self
        )
        self.executor = executor_cls(
            model_configs=executor_model_configs,
            actions=actions,
            vision_only_actions=vision_only_action_headers,
            limit_to_ctx=limit_to_ctx,
            parent_agent=self,
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

    def _generate_plan(self, **kwargs) -> str:
        """
        Generate a new plan with the planner agent.

        Args:
            **kwargs: Additional arguments to pass to the planner agent's model generation.

        Returns:
            str: The generated plan.
        """
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
        self.planner.update(self.html_history[-1], self.screenshot_history[-1], "")

        return plan

    def _generate_action(
        self, plan: str, vision_only: bool = False, **kwargs
    ) -> tuple[str, dict]:
        """
        Generate a new action with the executor agent and a plan.

        Args:
            plan: The plan to execute.
            **kwargs: Additional arguments to pass to the executor agent's model generation.

        Returns:
            tuple[str, dict]: The generated action and metadata.
        """
        self.executor.reset(plan, self.html_history[-1], self.screenshot_history[-1])
        action, action_description = self.executor.act(
            vision_only=vision_only, **kwargs
        )
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

    def _retry_last_action(self) -> bool:
        """
        Check whether we should retry the last planned action.
        Currently, we retry the last action with vision-only action if the last action
        did not make a change to the state of the environment.

        Returns:
            bool: Whether we should retry the last action.
        """
        # If we have already retried the last action, we should not retry again
        if self.last_action_retried:
            self.last_action_retried = False
            return False

        # If we have not executed any actions yet, we should not retry
        if len(self.screenshot_history) < 2 or len(self.html_history) < 2:
            return False

        previous_screenshot = self.screenshot_history[-2]
        previous_html = self.html_history[-2]
        current_screenshot = self.screenshot_history[-1]
        current_html = self.html_history[-1]

        screenshot_changed = screenshots_differ(
            previous_screenshot,
            current_screenshot,
            image_mse_threshold=0.1,
        )
        html_changed = axtrees_differ(previous_html, current_html)

        should_retry = not (screenshot_changed or html_changed)
        self.last_action_retried = should_retry

        return should_retry

    def _act(self, **kwargs):
        if self._retry_last_action():
            # If we need to retry the last action with vision-only action,
            # we keep the previous plan and execute a vision-only action
            plan = self.previous_steps[-1]
            action, metadata = self._generate_action(plan, vision_only=True, **kwargs)
        else:
            # Otherwise, we generate a new plan and execute it
            plan = self._generate_plan(**kwargs)
            action, metadata = self._generate_action(plan, vision_only=False, **kwargs)

        return action, metadata

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
