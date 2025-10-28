"""
Action space for Claude Computer Use Tool mapped to Playwright actions.
"""

from typing import Literal


class ClaudeComputerUseActions:
    """
    Action space for Claude Computer Use Tool that maps directly to Playwright actions.
    This converts Claude Computer Use actions to Playwright action strings.
    """

    # Claude Computer Use supported actions
    action_space = [
        "left_click",
        "right_click", 
        "double_click",
        "left_click_drag",
        "type",
        "key",
        "scroll",
        "mouse_move",
        "wait",
        "screenshot",
        "complete"  # Special action for task completion
    ]

    # Unsupported actions that should raise errors
    unsupported_actions = [
        "middle_click",
        "triple_click", 
        "left_mouse_down",
        "left_mouse_up",
        "hold_key"
    ]

    @staticmethod
    def left_click(x: float, y: float):
        """
        Click with left mouse button at coordinates.
        Maps to Playwright mouse_click action.
        """
        return f"mouse_click({x}, {y}, button='left')"

    @staticmethod 
    def right_click(x: float, y: float):
        """
        Click with right mouse button at coordinates.
        Maps to Playwright mouse_click action.
        """
        return f"mouse_click({x}, {y}, button='right')"

    @staticmethod
    def double_click(x: float, y: float):
        """
        Double click with left mouse button at coordinates.
        Maps to Playwright mouse_dblclick action.
        """
        return f"mouse_dblclick({x}, {y}, button='left')"

    @staticmethod
    def left_click_drag(x1: float, y1: float, x2: float, y2: float):
        """
        Click and drag from start coordinates to end coordinates.
        Maps to Playwright mouse_drag_and_drop action.
        """
        return f"mouse_drag_and_drop({x1}, {y1}, {x2}, {y2})"

    @staticmethod
    def type(text: str):
        """
        Type text using keyboard.
        Maps to Playwright keyboard_type action.
        Note: Claude Computer Use type doesn't require coordinates.
        """
        text = ClaudeComputerUseActions._clean_text(text)
        return f"keyboard_type('{text}')"

    @staticmethod
    def key(keys: str):
        """
        Press key combination.
        Maps to Playwright keyboard_press action.
        
        Args:
            keys (str): Key combination string from Claude Computer Use
        """
        # Convert Claude key format to Playwright format
        playwright_keys = ClaudeComputerUseActions._convert_keys_to_playwright(keys)
        return f"keyboard_press('{playwright_keys}')"

    @staticmethod
    def scroll(x: float, y: float, scroll_direction: str, scroll_amount: int = 3):
        """
        Scroll in specified direction.
        Maps to Playwright scroll action.
        If coordinates are provided, moves mouse to that position first.
        """
        # Convert direction and amount to delta values
        delta_x, delta_y = ClaudeComputerUseActions._convert_scroll_to_deltas(
            scroll_direction, scroll_amount
        )
        return f"mouse_move({x}, {y})\nscroll({delta_x}, {delta_y})"

    @staticmethod
    def mouse_move(x: float, y: float):
        """
        Move mouse to coordinates.
        Maps to Playwright mouse_move action.
        """
        return f"mouse_move({x}, {y})"

    @staticmethod
    def wait(duration: int = 1000):
        """
        Wait for specified duration in milliseconds.
        Maps to Playwright noop action.
        """
        return f"noop(wait_ms={duration})"

    @staticmethod
    def screenshot():
        """
        Take screenshot action.
        Maps to Playwright noop with short wait for screen stabilization.
        """
        return f"noop(wait_ms=500)"

    @staticmethod
    def complete(answer: str = "", infeasible_reason: str = ""):
        """
        Complete the task with optional answer or infeasible reason.
        Maps to Playwright send_msg_to_user or report_infeasible actions.
        """
        answer = ClaudeComputerUseActions._clean_text(answer)
        infeasible_reason = ClaudeComputerUseActions._clean_text(infeasible_reason)

        if answer:
            return f'send_msg_to_user({repr(answer)})'
        elif infeasible_reason:
            return f'report_infeasible({repr(infeasible_reason)})'
        else:
            return "send_msg_to_user('')"

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Clean text for use in Playwright actions.
        Same cleaning as BrowserGym actions.
        """
        return text.encode("unicode_escape").decode("utf-8")

    @staticmethod
    def _convert_keys_to_playwright(key_string: str) -> str:
        """
        Convert Claude Computer Use key format to Playwright key format.
        
        Args:
            key_string (str): Key combination like "ctrl+s", "alt+tab", "Enter"
            
        Returns:
            str: Playwright-compatible key string
        """
        if not key_string:
            return ""
        
        # Handle common key mappings for Playwright
        key_mappings = {
            "ctrl": "Control",
            "alt": "Alt", 
            "shift": "Shift",
            "cmd": "Meta",  # Mac command key
            "meta": "Meta",
            "enter": "Enter",
            "tab": "Tab",
            "space": "Space",
            "backspace": "Backspace", 
            "delete": "Delete",
            "up": "ArrowUp",
            "down": "ArrowDown",
            "left": "ArrowLeft", 
            "right": "ArrowRight",
            "home": "Home",
            "end": "End",
            "pageup": "PageUp",
            "pagedown": "PageDown"
        }
        
        # Split by + and normalize
        keys = [key.strip().lower() for key in key_string.split('+')]
        result = []
        
        for key in keys:
            if key in key_mappings:
                result.append(key_mappings[key])
            elif len(key) == 1 and key.isalnum():
                # Single character keys
                result.append(key)
            elif key.startswith('f') and key[1:].isdigit():
                # Function keys F1-F12
                result.append(key.upper())
            else:
                # Use key as-is, capitalize first letter
                result.append(key.capitalize())
                
        return "+".join(result)

    @staticmethod
    def _convert_scroll_to_deltas(direction: str, amount: int) -> tuple[float, float]:
        """
        Convert Claude scroll direction and amount to Playwright delta values.
        
        Args:
            direction (str): Scroll direction ("up", "down", "left", "right")
            amount (int): Scroll amount
            
        Returns:
            tuple[float, float]: (delta_x, delta_y) for Playwright scroll
        """
        # Default scroll multiplier
        multiplier = amount * 100 if amount > 0 else 100
        
        if direction == "down":
            return (0, multiplier)
        elif direction == "up":
            return (0, -multiplier)
        elif direction == "right":
            return (multiplier, 0)
        elif direction == "left":
            return (-multiplier, 0)
        else:
            # Default to down if direction is unclear
            return (0, multiplier)

    @classmethod
    def get_action_space(cls):
        """
        Get all supported action names.
        """
        return cls.action_space

    @classmethod
    def get_unsupported_actions(cls):
        """
        Get all unsupported action names that should raise errors.
        """
        return cls.unsupported_actions


# Export action functions for easy import
left_click = ClaudeComputerUseActions.left_click
right_click = ClaudeComputerUseActions.right_click
double_click = ClaudeComputerUseActions.double_click
left_click_drag = ClaudeComputerUseActions.left_click_drag
type = ClaudeComputerUseActions.type
key = ClaudeComputerUseActions.key
scroll = ClaudeComputerUseActions.scroll
mouse_move = ClaudeComputerUseActions.mouse_move
wait = ClaudeComputerUseActions.wait
screenshot = ClaudeComputerUseActions.screenshot
complete = ClaudeComputerUseActions.complete
