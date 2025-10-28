from abc import ABCMeta, abstractmethod
from copy import deepcopy
from typing import Any, List, Dict
from retry import retry

from orby.digitalagent.model import FoundationModel
from orby.digitalagent.agent import utils as agent_utils
from fm import llm_data_pb2


def trace_generate(original_act_func):
    """
    !! Please do not modify without review !!

    Wrapper function which modify's an Agent's
    act method, so that it records any FoundationModel.generate()
    calls made within it, inside Agent.llm_trace field.
    """

    def wrapper(self, *args, **kwargs):
        # Store the original generate method
        original_generate = self.model.generate
        self.per_act_trace = []

        def traced_generate(**kwargs):
            response = original_generate(**kwargs)
            # TODO: Make the return response an object
            # instead of variable
            if type(response) == tuple:
                # Only find the exact response string
                stored_response = response[0]
            else:
                stored_response = str(response)
            llm_messages = agent_utils.convert_messages_to_llm_interactions(
                kwargs["messages"]
            )
            trace_obj = llm_data_pb2.LLMInteraction(
                model_family=self.model.model_provider,
                model_name=self.model.model_name,
                llm_messages=llm_messages,
                response=str(stored_response),
            )
            self.per_act_trace.append(trace_obj)
            parent = self.parent_agent
            while parent:
                parent.per_act_trace.append(trace_obj)
                parent = parent.parent_agent

            return response

        self.model.generate = traced_generate

        try:
            # Execute the actual method (act)
            result = original_act_func(self, *args, **kwargs)
            self.llm_trace.append(self.per_act_trace)
            return result
        finally:
            self.model.generate = original_generate

    return wrapper


class LoggingMetaWrapper(ABCMeta):
    """
    !! Please do not modify without review !!

    Meta class to transform an Agent so that it's LLM call
    can be logged within Agent.llm_trace.
    """

    def __new__(meta, name, bases, namespace):
        if "act" in namespace:
            namespace["act"] = trace_generate(namespace["act"])
        return super().__new__(meta, name, bases, namespace)


class Agent(metaclass=LoggingMetaWrapper):
    def __init__(self, **kwargs):
        self.model = None
        self.model_configs = kwargs.get("model_configs", {})
        self.html_history: List[str] = []
        self.screenshot_history: List[Any] = []
        self.goal: str = ""
        self.trace: List[Any] = []
        # Field will be modified by meta class. !! Do not use
        # in child classes!!
        # Contains a list of LLM calls made corresponding to
        # each invocation of self.act()
        self.llm_trace: List[List[llm_data_pb2.LLMInteraction]] = []
        self.parent_agent = kwargs.get("parent_agent", None)

    @abstractmethod
    def reset(self, goal, html, screenshot, goal_image_urls=[]) -> None:
        """
        Reset the agent's internal state, if any.

        Args:
            goal::str: The goal of the current task.
            html::str: The HTML representation of the current environment. (could be axtree)
            screenshot::Any: The screenshot of the current environment. (usually numpy.ndarray)
            goal_image_urls::List[str]: A list of URLs of images that are relevant to the goal.
        """
        pass

    @abstractmethod
    def update(self, html, screenshot, trace) -> None:
        """
        Update the agent's internal state based on new observations from the environment.

        Args:
            html::str: The HTML representation of the current environment. (could be axtree)
            screenshot::Any: The screenshot of the current environment. (usually numpy.ndarray)
            trace::List[Any]: A list of tuples containing the previous actions taken and the error messages from all previous actions.
        """
        pass

    @abstractmethod
    def act(self, **kwargs) -> str:
        """
        Generate an action based on the agent's internal state.

        Args:
            **kwargs: Any additional arguments required for generating the action, passed to the FM for the generation call.
        """
        return ""

    def get_state_dict(self) -> dict:
        """
        Return a dictionary containing the agent's internal state, which can be used to completely recover the state of the agent.

        What this dictionary contains is up to the agent implementation, but usually contains:
        * The agent's history of HTML representations and viewport screenshots
        * The agent's goal and goal-associated images
        * The agent's trace of previous actions
        * Sub-agent states, if any

        Returns:
            dict: A dictionary containing the agent's internal state.
        """
        return deepcopy(
            {
                "actions": self.actions,
                "html_history": self.html_history,
                "screenshot_history": self.screenshot_history,
                "goal": self.goal,
                "goal_images": getattr(self, "goal_images", []),
                "trace": self.trace,
                "model_configs": self.model_configs,
            }
        )

    def load_state_dict(self, state_dict: dict) -> None:
        """
        Load the agent's internal state from a dictionary to replay a step of execution.

        Args:
            state_dict::dict: A dictionary containing the agent's internal state.
        """
        self.actions = state_dict["actions"]
        self.html_history = state_dict["html_history"]
        self.screenshot_history = state_dict["screenshot_history"]
        self.goal = state_dict["goal"]
        self.goal_images = state_dict["goal_images"]
        self.trace = state_dict["trace"]
        self.model_configs = state_dict["model_configs"]

        self.model = FoundationModel(**self.model_configs)
