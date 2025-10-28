"""
Action space implemented with the BrowserGym action space.
"""

from typing import Literal

from orby.digitalagent.actions.base import Actions


class BrowserGymActions(Actions):
    """
    Action space implemented with the BrowserGym action space.
    We convert actions in our action space to one or more BrowserGym actions.
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

    @staticmethod
    def click(
        x: float,
        y: float,
        button: Literal["left", "right"] = "left",
        double: bool = False,
    ):
        """
        Click on a location with a mouse button.
        See the base Actions class for more details.
        """
        if double:
            return f"mouse_dblclick({x}, {y}, button='{button}')"
        else:
            return f"mouse_click({x}, {y}, button='{button}')"

    # TODO: keep an eye on if the model provides both answer and infeasible_reason
    # and mess up the response
    @staticmethod
    def complete(answer: str = "", infeasible_reason: str = ""):
        """
        Complete the task and optionally provide the user some feedback.
        See the base Actions class for more details.
        """
        answer = BrowserGymActions._clean_text(answer)
        infeasible_reason = BrowserGymActions._clean_text(infeasible_reason)

        if answer:
            return f'send_msg_to_user({repr(answer)})'
        elif infeasible_reason:
            return f'report_infeasible({repr(infeasible_reason)})'
        else:
            return "send_msg_to_user('')"

    @staticmethod
    def drag_and_release(x1: float, y1: float, x2: float, y2: float):
        """
        Drag and release the mouse button at a location.
        See the base Actions class for more details.
        """
        return f"mouse_drag_and_drop({x1}, {y1}, {x2}, {y2})"

    @staticmethod
    def hover(x: float, y: float):
        """
        Hover over a location.
        See the base Actions class for more details.
        """
        return f"mouse_move({x}, {y})"

    @staticmethod
    def key_press(keys: list[str]):
        """
        Press one or a combination of keys at the same time on the keyboard.
        See the base Actions class for more details.
        """
        for i, key in enumerate(keys):
            if key == "Control":
                keys[i] = "ControlOrMeta"
        
        keys_str = "+".join(keys)
        # Handle all the go_back() cases
        if keys_str in ["ControlOrMeta+BracketLeft", "ControlOrMeta+ArrowLeft", "Alt+ArrowLeft"]:
            return "go_back()"
        elif keys_str in ["ControlOrMeta+BracketRight", "ControlOrMeta+ArrowRight", "Alt+ArrowRight"]:
            return "go_forward()"
        return f"keyboard_press('{keys_str}')"

    @staticmethod
    def scroll(x: float, y: float, delta_x: float = 0, delta_y: float = 100):
        """
        Scroll the mouse wheel in the x and y directions.
        See the base Actions class for more details.
        """
        return f"mouse_move({x}, {y})\nscroll({delta_x}, {delta_y})"

    @staticmethod
    def type(x: float, y: float, text: str):
        """
        Type text into a location.
        See the base Actions class for more details.
        """
        text = BrowserGymActions._clean_text(text)
        return f"mouse_click({x}, {y})\nkeyboard_type('{text}')"

    @staticmethod
    def wait(ms: int = 1000):
        """
        Wait for a specified amount of time.
        See the base Actions class for more details.
        """
        return f"noop(wait_ms={ms})"

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Clean the text to be used in the BrowserGym action space.
        """
        return text.encode("unicode_escape").decode("utf-8")


# Export the action space
click = BrowserGymActions.click
complete = BrowserGymActions.complete
drag_and_release = BrowserGymActions.drag_and_release
hover = BrowserGymActions.hover
key_press = BrowserGymActions.key_press
scroll = BrowserGymActions.scroll
type = BrowserGymActions.type
wait = BrowserGymActions.wait
