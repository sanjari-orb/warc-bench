from dataclasses import dataclass
from typing import Dict, Any, Tuple, List

from orby.digitalagent.agent.sva_v3 import SvaV3, ExecutorResponse, RewardModelResponse
from orby.digitalagent.utils.action_parsing_utils import (
    extract_content_by_tags,
    extract_action,
)

import anthropic
import os
import re


@dataclass
class ClaudeComputerUseResponse:
    """
    The response from the Claude Computer Use model
    """
    action_type: str
    coordinates: Tuple[float, float] = None     # For drag actions, claude response uses this as the end coordinate
    start_coordinates: Tuple[float, float] = None  # start_coordinates is only predicted by claude cua for drag actions
    text: str = ""
    thinking: str = ""
    # Additional parameters for different Claude Computer Use actions
    scroll_direction: str = ""
    scroll_amount: int = 0
    key_combination: str = ""
    # Store raw action input for extensibility
    raw_action_input: Dict[str, Any] = None


class ClaudeComputerUseAgent(SvaV3):
    """
    ClaudeComputerUseAgent is based on SVA V3 but adapted for Claude's Computer Use model.
    
    Key differences from SVA V3:
    1. Uses different prompt templates optimized for Claude's Computer Use capabilities
    2. Handles Claude Computer Use action space and converts to SVA V3's BrowserGym action space
    3. Implements response parsing logic tailored to the unique tool use output format of Claude Computer Use
    4. Does not make explicit reward model calls because claude cua model is checks if the task is complete in the same turn
    
    This agent maintains the similar overall architecture and action space as SVA V3 (executor model calls)
    but with Claude-specific adaptations for action conversion and tool use integration.
    """

    def __init__(
        self,
        actions: str,
        model_configs: dict,
        action_history_length: int = -1,
        claude_prompt_template_path: str = None,
    ):
        """
        Initialize the ClaudeComputerUseAgent.
        
        Args:
            actions (str): Action space specification (inherited from parent)
            model_configs (dict): Configuration for the executor model
            action_history_length (int): Number of previous actions to include in history
            claude_prompt_template_path (str): Path to Claude-specific prompt templates
        """
        action_history_length = 0
        
        super().__init__(actions, model_configs, None, action_history_length)
        
        # Claude-specific prompt template path
        self.claude_prompt_template_path = claude_prompt_template_path
        
        # Initialize conversation history for Claude
        self.executor_messages = []
        
    def reset(self, goal, html, screenshot, goal_image_urls=[]):
        """Override reset to clear conversation history for new tasks."""
        super().reset(goal, html, screenshot, goal_image_urls)
        # Clear conversation history for new task
        self.executor_messages = []

    def _act(self, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """
        Override the act method to use Claude Computer Use specific prompting and action conversion.
        
        This method follows a single-turn execution pattern:
        1. Create Claude-formatted prompt with current screenshot and history
        2. Call Claude Computer Use model via self.model.generate()
        3. Parse response and convert to Playwright actions
        4. Return action and metadata
        
        Args:
            **kwargs: Additional arguments passed to the model (max_tokens, thinking_budget, etc.)
            
        Returns:
            Tuple[str, Dict[str, Any]]: The grounded Playwright action and metadata
        """
        # Create prompt variables for current turn
        variables = {
            "goal": self.goal,
            "current_screenshot": self.screenshot_history[-1],
        }
        
        # Use Claude Computer Use prompt template
        from orby.digitalagent.prompts.default import claude_cua as prompts
        from orby.digitalagent.agent.utils import prompt_to_messages
        
        # Generate current turn prompt
        executor_prompt, images = prompts.render(**variables, block="executor")
        current_messages = prompt_to_messages(executor_prompt, user_delimiter="Human:", images=images)
        
        # Add current messages to conversation history
        self.executor_messages.extend(current_messages)
        
        print(f"Conversation history now has {len(self.executor_messages)} messages")
        
        # Configure Claude Computer Use tools for the model
        tools = [
            {
                "type": "computer_20250124",  # Use latest Claude Computer Use version
                "name": "computer",
                "display_width_px": kwargs.get("display_width_px", 1280),
                "display_height_px": kwargs.get("display_height_px", 720),
                "display_number": kwargs.get("display_number", 1),
            }
        ]
        
        # Set up thinking parameter (enabled by default)
        thinking_config = {
            "type": "enabled", 
            "budget_tokens": kwargs.get("thinking_budget", 1024)  # Default budget if not provided
        }
        
        # Generate response from Claude Computer Use model
        executor_response = self.model.generate(
            messages=self.executor_messages, # Use the full conversation history
            return_raw=True,
            tools=tools,
            thinking=thinking_config,
            betas=["computer-use-2025-01-24"],  # Required beta flag for Claude Computer Use
            **{k: v for k, v in kwargs.items() if k not in ["thinking_budget", "display_width_px", "display_height_px", "display_number", "temperature"]}
        )
        print("Executor response: ", executor_response)

        # Extract only BetaTextBlock and BetaToolUseBlock content for conversation history
        response_content = []
        for content_block in executor_response.content:
            if hasattr(content_block, 'type'):
                if content_block.type == 'text':
                    # Extract text content and check for answer tags
                    text_content = content_block.text                    
                    response_content.append({
                        "type": "text",
                        "text": "Model thinking response was: " + text_content
                    })
                elif content_block.type == 'tool_use':
                    # Extract tool use content into dictionary format
                    response_content.append({
                        "type": "text",
                        "text": "Tool use was: " + str(content_block)
                    })
        print("Response content: ", response_content)
        # Add Claude's response to conversation history (only text and tool_use blocks)
        self.executor_messages.append({
            "role": "assistant",
            "content": response_content
        })
        
        # Parse the response and convert to ExecutorResponse format
        try:
            parsed_response = self._parse_model_response(executor_response)
            
            return parsed_response.action, {"thinking": parsed_response.thinking}
            
        except ValueError as e:
            # Handle unsupported actions - this should trigger retry logic outside
            print(f"Action conversion error: {e}")
            raise e

    def _parse_model_response(self, response) -> ExecutorResponse:
        """
        Parse the response from Claude Computer Use model and convert to ExecutorResponse.
        
        This method handles the BetaMessage structure from Claude Computer Use API,
        extracts thinking content from both BetaThinkingBlock and BetaTextBlock,
        and converts the computer use action to ExecutorResponse format.
        
        Args:
            response: The BetaMessage response from Claude Computer Use API
            
        Returns:
            ExecutorResponse: Parsed response compatible with SVA V3 format
            
        Raises:
            ValueError: If the response cannot be parsed or contains no tool use
        """
        from orby.digitalagent.actions.claude_cua_actions import complete
        
        # Check if response contains any tool use blocks or if Claude decided to end the turn (task complete)
        has_tool_use = any(
            hasattr(content_block, 'type') and content_block.type == 'tool_use'
            for content_block in response.content
        )
        is_end_turn = hasattr(response, 'stop_reason') and response.stop_reason == 'end_turn'
        
        # Handle task completion: either no tool use found or Claude explicitly ended the turn
        if not has_tool_use and is_end_turn:
            # No tool use found means that the task was completed - generate complete action with text response
            thinking_parts = []
            answer_text = ""
            
            for content_block in response.content:
                if hasattr(content_block, 'type'):
                    if content_block.type == 'thinking':
                        if hasattr(content_block, 'thinking'):
                            thinking_parts.append(content_block.thinking)
                    elif content_block.type == 'text':
                        if hasattr(content_block, 'text'):
                            answer_text = content_block.text

                            # Try to extract content from <answer> tags
                            answer_match = re.search(r'<answer>(.*?)</answer>', answer_text, re.DOTALL)
                            print("Answer match: ", answer_match)
                            if answer_match:
                                # Use content from answer tags if found
                                answer_text = answer_match.group(1).strip()
                                print("Extracted text: ", answer_text)

                            thinking_parts.append(answer_text)
            
            combined_thinking = ' '.join(thinking_parts).strip()
            
            # Generate complete action with the text response
            return ExecutorResponse(
                action=complete(answer=answer_text),
                thinking=combined_thinking
            )
        
        # Parse tool use response if there is a tool use block
        claude_response = self._parse_claude_computer_use_response(response)
        
        # Convert to ExecutorResponse for SVA V3 compatibility
        return ExecutorResponse(
            action=self._convert_claude_action_to_playwright(claude_response),
            thinking=claude_response.thinking
        )

    def _parse_claude_computer_use_response(self, response) -> ClaudeComputerUseResponse:
        """
        Parse the BetaMessage response from Claude Computer Use model.
        
        Extracts thinking content from BetaThinkingBlock and BetaTextBlock,
        and computer use action from BetaToolUseBlock.
        
        Args:
            response: The BetaMessage response from Claude Computer Tool API
            
        Returns:
            ClaudeComputerUseResponse: Parsed response containing action type, coordinates, and thinking
            
        Raises:
            ValueError: If the response cannot be parsed or is in an unexpected format
        """
        thinking_parts = []
        tool_use_block = None
        
        # Parse content blocks from the response
        for content_block in response.content:
            if hasattr(content_block, 'type'):
                if content_block.type == 'thinking':
                    # Extract thinking content from BetaThinkingBlock
                    if hasattr(content_block, 'thinking'):
                        thinking_parts.append(content_block.thinking)
                
                elif content_block.type == 'text':
                    # Extract text content from BetaTextBlock
                    if hasattr(content_block, 'text'):
                        thinking_parts.append(content_block.text)
                
                elif content_block.type == 'tool_use':
                    # Extract tool use block
                    if content_block.name == 'computer':
                        tool_use_block = content_block
        
        # Validate that we found a computer tool use
        if tool_use_block is None:
            raise ValueError("No computer tool use found in Claude response - task was completed.")
        
        # Extract action details from tool use block
        action_input = tool_use_block.input
        action_type = action_input.get('action', '')
        
        # Extract coordinates if present
        coordinates = None
        start_coordinates = None
        
        if 'coordinate' in action_input:
            coord = action_input['coordinate']
            if isinstance(coord, list) and len(coord) == 2:
                coordinates = (float(coord[0]), float(coord[1]))
        
        # Extract start coordinates for drag actions
        if 'start_coordinate' in action_input:
            start_coord = action_input['start_coordinate']
            if isinstance(start_coord, list) and len(start_coord) == 2:
                start_coordinates = (float(start_coord[0]), float(start_coord[1]))
        
        # Extract text if present (for type actions)
        action_text = action_input.get('text', '')
        
        # Extract scroll parameters if present
        scroll_direction = action_input.get('scroll_direction', '')
        scroll_amount = action_input.get('scroll_amount', 0)
        
        # Extract key combination if present
        key_combination = action_input.get('key', '')
        
        # Combine all thinking content
        combined_thinking = ' '.join(thinking_parts).strip()
        
        return ClaudeComputerUseResponse(
            action_type=action_type,
            coordinates=coordinates,
            start_coordinates=start_coordinates,
            text=action_text,
            thinking=combined_thinking,
            scroll_direction=scroll_direction,
            scroll_amount=scroll_amount,
            key_combination=key_combination,
            raw_action_input=action_input
        )

    def _convert_claude_action_to_playwright(self, claude_response: ClaudeComputerUseResponse) -> str:
        """
        Convert Claude Computer Use actions to Playwright action space.
        
        This is a key method that bridges the gap between Claude's action format
        and the Playwright actions expected by the execution environment.
        
        Args:
            claude_response (ClaudeComputerUseResponse): Parsed Claude Computer Use response
            
        Returns:
            str: Playwright action string that can be executed
            
        Raises:
            ValueError: If the Claude action cannot be converted to a valid Playwright action
        """
        from orby.digitalagent.actions.claude_cua_actions import ClaudeComputerUseActions
        
        action_type = claude_response.action_type
        coordinates = claude_response.coordinates
        
        # Check for unsupported actions first
        if action_type in ClaudeComputerUseActions.get_unsupported_actions():
            raise ValueError(f"Unsupported action '{action_type}' - not available in Claude Computer Use action space")
        
        if action_type == "left_click":
            if coordinates is None:
                raise ValueError("left_click action requires coordinates")
            return ClaudeComputerUseActions.left_click(coordinates[0], coordinates[1])
            
        elif action_type == "right_click":
            if coordinates is None:
                raise ValueError("right_click action requires coordinates")
            return ClaudeComputerUseActions.right_click(coordinates[0], coordinates[1])
            
        elif action_type == "double_click":
            if coordinates is None:
                raise ValueError("double_click action requires coordinates")
            return ClaudeComputerUseActions.double_click(coordinates[0], coordinates[1])
            
        elif action_type == "left_click_drag":
            # Extract start and end coordinates from parsed response
            start_coord = claude_response.start_coordinates
            end_coord = claude_response.coordinates
            
            if start_coord is None or end_coord is None:
                raise ValueError("left_click_drag action requires both start_coordinate and coordinate")
            
            return ClaudeComputerUseActions.left_click_drag(
                start_coord[0], start_coord[1], end_coord[0], end_coord[1]
            )
            
        elif action_type == "type":
            # Claude Computer Use type doesn't require coordinates
            return ClaudeComputerUseActions.type(claude_response.text)
            
        elif action_type == "key":
            # Convert key string to Playwright format
            return ClaudeComputerUseActions.key(claude_response.key_combination)
            
        elif action_type == "scroll":
            # Claude Computer Use scroll can include coordinates - pass them directly to scroll method
            if coordinates is not None:
                return ClaudeComputerUseActions.scroll(
                    coordinates[0], 
                    coordinates[1],
                    claude_response.scroll_direction, 
                    claude_response.scroll_amount
                )
            else:
                raise ValueError("Claude CUA scroll action outputted without coordinates")
            
        elif action_type == "mouse_move":
            if coordinates is None:
                raise ValueError("mouse_move action requires coordinates")
            return ClaudeComputerUseActions.mouse_move(coordinates[0], coordinates[1])
            
        elif action_type == "wait":
            # Extract wait time from raw_action_input, default to 1000ms
            duration = claude_response.raw_action_input.get('duration', 1000) if claude_response.raw_action_input else 1000
            return ClaudeComputerUseActions.wait(duration)
            
        elif action_type == "screenshot":
            # Convert screenshot to wait action for screen stabilization
            return ClaudeComputerUseActions.screenshot()
            
        else:
            raise ValueError(f"Unknown action type: {action_type}")
