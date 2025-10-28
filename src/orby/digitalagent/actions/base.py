"""
Base class for all (pure vision) actions.
"""

from abc import ABC, abstractmethod
from typing import Literal
import inspect


class Actions(ABC):
    """
    Base class for all (pure vision) actions.
    This strictly defines the action space we can implement. All subclass implementations must
    contain a subset of the actions defined in the action_space list. The implementation must
    do what the original docstring says.

    DO NOT modify the docstrings of the actions. They are used by all action implementations
    as the docstrings provided to the model in the prompt.
    """

    action_space = [
        "click",
        "complete",
        "drag_and_release",
        "hover",
        "key_press",
        "scroll",
        "type",
        "wait",
    ]

    @classmethod
    def get_action_space(cls):
        """
        Get all action names.
        """
        return cls.action_space

    @classmethod
    def print_docstrings(cls):
        """
        Print the docstring of the entire action space.
        """
        docstring_list = []
        for action_name in cls.get_action_space():
            signature = action_name + str(
                inspect.signature(getattr(Actions, action_name))
            )
            docstring_list.append(signature)
            doc = inspect.getdoc(getattr(Actions, action_name))
            for line in doc.split("\n"):
                docstring_list.append(" " * 4 + line)
            docstring_list.append("")

        # Remove the last empty line
        docstring_list.pop()
        return "\n".join(docstring_list)

    @staticmethod
    @abstractmethod
    def click(
        x: float,
        y: float,
        button: Literal["left", "right"] = "left",
        double: bool = False,
    ):
        """
        Move the mouse to a location and click a mouse button.
        Can be used to click a button, select a checkbox, focus on a input field, etc.
        Args:
            x (float): The x coordinate of the location to click.
            y (float): The y coordinate of the location to click.
            button (Literal["left", "right"]): The button to click.
            double (bool): Whether to double click.
        Examples:
            click(324.5, 12)
            click(119, 34, button="right")
            click(34.1, 720, double=True)
            click(230, 100, button="left", double=False)
        """
        pass

    @staticmethod
    @abstractmethod
    def complete(answer: str = "", infeasible_reason: str = ""):
        """
        Complete the task and optionally provide the user some feedback.
        Fill in the answer if the completion of the task requires providing a response to the user.
        Fill in the infeasible_reason if the task is infeasible.
        DO NOT fill in both answer and infeasible_reason at the same time.
        Args:
            answer (str): The answer to the task, if any.
            infeasible_reason (str): The reason the task is infeasible, if any.
        Examples:
            complete(answer='''To request a refund, you need to call the customer service at 123-456-7890.''')
            complete(infeasible_reason='''The task is infeasible because the user has not provided a valid email address.''')
            complete()
            complete(answer='''{\\n  \"name\": \"John\",\\n  \"age\": 30,\\n  \"city\": \"New York\"\\n}''')
        """
        pass

    @staticmethod
    @abstractmethod
    def drag_and_release(x1: float, y1: float, x2: float, y2: float):
        """
        Press down the left mouse button at a location, drag the mouse to another location, and release the mouse button.
        Can be used for selecting a section of text, dragging a slider, etc.
        Args:
            x1 (float): The x coordinate of the location to press down the left mouse button.
            y1 (float): The y coordinate of the location to press down the left mouse button.
            x2 (float): The x coordinate of the location to release the left mouse button.
            y2 (float): The y coordinate of the location to release the left mouse button.
        Examples:
            drag_and_release(10.5, 200, 10.5, 230)
        """
        pass

    @staticmethod
    @abstractmethod
    def hover(x: float, y: float):
        """
        Move the mouse to a location and stay there.
        Can be used to focus on a location, pop up a tooltip, navigate a dropdown menu, etc.
        Args:
            x (float): The x coordinate of the location to hover over.
            y (float): The y coordinate of the location to hover over.
        Examples:
            hover(102, 720)
        """
        pass

    @staticmethod
    @abstractmethod
    def key_press(keys: list[str]):
        """
        Press one or a combination of keys at the same time on the keyboard.
        Can be used
        - As various shortcuts of the current environment (e.g. ["Control", "a"], ["Control", "f"]).
        - To complete a search with ["Enter"].
        - And any other common actions that can be performed with a keyboard in the relevant application.
        This should NOT be used to type a string of text. Use the type action for that.
        The list of allowed keys are:
        - F1, F2, F3, F4, F5, F6, F7, F8, F9, F10, F11, F12
        - 0, 1, 2, 3, 4, 5, 6, 7, 8, 9
        - a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z
        - Backspace, Tab, Enter, Shift, Control, Alt, Delete
        - ArrowUp, ArrowDown, ArrowLeft, ArrowRight
        - Home, End, PageUp, PageDown
        Args:
            keys (list[str]): The list of keys to press.
        Examples:
            key_press(["Control", "a"]) # Select all
            key_press(["Control", "f"]) # Open the search bar
            key_press(["Enter"]) # Submit a form
            key_press(["F12"]) # Open the developer tools in a browser
        """
        pass

    @staticmethod
    @abstractmethod
    def scroll(x: float, y: float, delta_x: float = 0, delta_y: float = 100):
        """
        Move the mouse to a location and scroll the mouse wheel in the x and y directions.
        Can be used to scroll a webpage, scroll a dropdown menu, etc.
        Args:
            x (float): The x coordinate of the location to scroll over.
            y (float): The y coordinate of the location to scroll over.
            delta_x (float): The amount to scroll horizontally.
            delta_y (float): The amount to scroll vertically.
        Examples:
            scroll(102, 320)
            scroll(102, 320, 0, 200)
            scroll(90, 32.7, 0, -300)
            scroll(620, 105, 68, 49.6)
        """
        pass

    @staticmethod
    @abstractmethod
    def type(x: float, y: float, text: str):
        """
        Focus on a location and type a string of text in it.
        Can be used to type in a text field, search bar, edit a document, etc.
        Args:
            x (float): The x coordinate of the location to type text in.
            y (float): The y coordinate of the location to type text in.
            text (str): The text to type.
        Examples:
            type(102, 70.6, "\\nThank you for the coffee!\\n")
            type(44, 120, "Best sellers")
        """
        pass

    @staticmethod
    @abstractmethod
    def wait(ms: int = 1000):
        """
        Wait for a specified amount of time.
        Can be used to wait for a webpage to load, a long form to display, etc.
        Args:
            ms (int): The amount of time to wait in milliseconds.
        Examples:
            wait()
            wait(1000)
            wait(500)
        """
        pass
