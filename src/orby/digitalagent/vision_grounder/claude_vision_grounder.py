import re
import logging
import numpy as np
from typing import Any, Dict, List, Union, Optional
from typing_extensions import override
from PIL import Image

from orby.digitalagent.model.fm import FoundationModel
from orby.digitalagent.vision_grounder.base_vision_grounder import BaseVisionGrounder
from orby.digitalagent.agent.utils import prompt_to_messages

logger = logging.getLogger(__name__)


class ClaudeVisionGrounder(BaseVisionGrounder):
    """
    A vision grounder implementation that uses Claude to identify coordinates
    on screenshots based on natural language descriptions. Uses the tool use
    capability of Claude.

    This class uses Claude's vision capabilities to find UI elements and
    extract their coordinates from screenshots using the tool_use capability
    with mouse_move action.
    """

    DEFAULT_PROMPT_TEMPLATE = """
You are a computer vision assistant that helps users find elements on a screen.

I will provide you with a screenshot and a description of an element to find. 
Your task is to:
1. Carefully examine the screenshot
2. Find the exact element that matches the description: "{{ description }}"
3. Use the mouse_move tool to indicate the coordinates where the user should click

Here is the screenshot:
<image:screenshot>

IMPORTANT RULES:
- The coordinates should point to the center of the element
- The top-left corner of the screen is (0, 0)
- The bottom-right corner is ({{ width }}, {{ height }})
- Be precise in your identification
- You MUST use the mouse_move tool to provide the coordinates

Again, the element description is: "{{ description }}".
"""

    def __init__(
        self,
        model_provider: str = "anthropic",
        model_name: str = "claude-3-7-sonnet-20250219",
        model: Optional[FoundationModel] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        prompt_template_str_or_file: str = "",
        **model_kwargs,
    ):
        """
        Initialize the ClaudeVisionGrounder.

        Args:
            model_provider (str): The provider for the foundation model (default: "anthropic")
            model_name (str): The name of the model to use (default: "claude-3-opus-20240229")
            model (Optional[FoundationModel]): An optional pre-initialized FoundationModel instance
            max_tokens (int): Maximum tokens to generate in the model response
            temperature (float): Temperature for model generation (0.0 = deterministic)
            prompt_template_str_or_file (str): Template string or path to template file
            **model_kwargs: Additional arguments to pass to the FoundationModel constructor
        """
        # If no prompt template provided, use the default
        if not prompt_template_str_or_file:
            prompt_template_str_or_file = self.DEFAULT_PROMPT_TEMPLATE

        super().__init__(
            model_provider=model_provider,
            model_name=model_name,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            prompt_template_str_or_file=prompt_template_str_or_file,
            **model_kwargs,
        )

    @override
    def ground(
        self,
        screenshot: Union[str, Image.Image, bytes, np.ndarray],
        description: str,
        **generate_kwargs,
    ) -> tuple[int, int] | None:
        """
        Override the base ground method to include the tool definition in the API call.

        Args:
            screenshot: The screenshot to analyze (can be a string, PIL Image, bytes, or numpy array)
            description: Description of what to find
            **generate_kwargs: Additional arguments for the model

        Returns:
            Coordinates as (x, y) tuple or None if not found
        """
        # Setup the mouse_move tool definition
        tools = [
            {
                "name": "mouse_move",
                "description": "Move the mouse cursor to a specific coordinate on the screen",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["mouse_move"],
                            "description": "The action to perform",
                        },
                        "coordinate": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "minItems": 2,
                            "maxItems": 2,
                            "description": "The x,y coordinates to move the mouse to",
                        },
                    },
                    "required": ["action", "coordinate"],
                },
            }
        ]

        # Add tools to the generate_kwargs
        generate_kwargs["tools"] = tools

        # Call the parent implementation with the updated kwargs
        return super().ground(screenshot, description, **generate_kwargs)

    def _parse_output(
        self, text_output: str, raw_output: Any, width: int, height: int
    ) -> tuple[int, int] | None:
        """
        Parse Claude's output to extract the coordinates from tool_use with mouse_move.

        Args:
            text_output (str): The text output from Claude
            raw_output (Any): The raw output from Claude
            width (int): Width of the image in pixels
            height (int): Height of the image in pixels

        Returns:
            tuple[int, int] | None: The (x, y) coordinates or None if not found
        """
        # First try to extract from the raw_output
        try:
            # For Anthropic API structure - check if content is a list
            if hasattr(raw_output, "content") and isinstance(raw_output.content, list):
                for item in raw_output.content:
                    if hasattr(item, "type") and item.type == "tool_use":
                        if hasattr(item, "input") and "coordinate" in item.input:
                            coordinates = item.input["coordinate"]
                            if isinstance(coordinates, list) and len(coordinates) == 2:
                                return (int(coordinates[0]), int(coordinates[1]))

            # Alternative structure for different response formats
            if hasattr(raw_output, "tool_use"):
                tool_use = raw_output.tool_use
                if hasattr(tool_use, "input") and "coordinate" in tool_use.input:
                    coordinates = tool_use.input["coordinate"]
                    if isinstance(coordinates, list) and len(coordinates) == 2:
                        return (int(coordinates[0]), int(coordinates[1]))

            # Check if raw_output is a dict (OpenAI style response)
            if isinstance(raw_output, dict) and "tool_calls" in raw_output:
                for tool_call in raw_output["tool_calls"]:
                    if tool_call.get("function", {}).get("name") == "mouse_move":
                        import json

                        args = json.loads(tool_call["function"]["arguments"])
                        if "coordinate" in args:
                            coords = args["coordinate"]
                            if isinstance(coords, list) and len(coords) == 2:
                                return (int(coords[0]), int(coords[1]))
        except Exception as e:
            logger.warning(f"Error parsing raw tool output: {e}")

        # Fallback: Try to extract from the text output using regex
        try:
            # Look for JSON-like tool calls in the text
            json_pattern = (
                r'{"action":\s*"mouse_move",\s*"coordinate":\s*\[(\d+),\s*(\d+)\]}'
            )
            match = re.search(json_pattern, text_output)
            if match:
                return (int(match.group(1)), int(match.group(2)))

            # Look for array notation [x, y]
            array_pattern = r"\[(\d+),\s*(\d+)\]"
            match = re.search(array_pattern, text_output)
            if match:
                return (int(match.group(1)), int(match.group(2)))

            # Look for parentheses notation (x, y)
            paren_pattern = r"\((\d+),\s*(\d+)\)"
            match = re.search(paren_pattern, text_output)
            if match:
                return (int(match.group(1)), int(match.group(2)))

            # Look for coordinate words
            coord_pattern = r"coordinates?:?\s*(?:\()?(\d+)[,\s]+(\d+)(?:\))?"
            match = re.search(coord_pattern, text_output, re.IGNORECASE)
            if match:
                return (int(match.group(1)), int(match.group(2)))

        except Exception as e:
            logger.warning(f"Error parsing text output: {e}")

        logger.error("Failed to extract coordinates from Claude's response")
        logger.error(f"Raw output: {raw_output}")
        return None
