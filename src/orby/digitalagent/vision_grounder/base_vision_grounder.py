import logging
from abc import ABC, abstractmethod
from typing import Union, Optional, Any, Dict, List
import numpy as np
from PIL import Image

from orby.digitalagent.model.fm import FoundationModel
from orby.digitalagent.utils.image_utils import convert_image_to_pil_image
from orby.prompt_utils import Template
from orby.digitalagent.agent.utils import prompt_to_messages


logger = logging.getLogger(__name__)


class BaseVisionGrounder(ABC):
    """
    Abstract base class for vision grounders that can identify coordinates on screenshots
    based on natural language descriptions.

    A VisionGrounder uses a foundation model to process a screenshot and a description,
    then returns coordinates of where to click based on that description.
    """

    HUMAN_DELIMITER = "Human:\n"

    def __init__(
        self,
        model_provider: str,
        model_name: str,
        model: Optional[FoundationModel] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        prompt_template_str_or_file: str = "",
        **model_kwargs,
    ):
        """
        Initialize the VisionGrounder.

        Args:
            model_provider (str): The provider for the foundation model
            model_name (str): The name of the model to use
            model (Optional[FoundationModel]): An optional pre-initialized FoundationModel instance
            max_tokens (int): Maximum tokens to generate in the model response
            temperature (float): Temperature for model generation (0.0 = deterministic)
            prompt_template_str_or_file (str): Template string or path to template file
                This template can be used by child classes in their _create_prompt implementation
            **model_kwargs: Additional arguments to pass to the FoundationModel constructor
        """
        self.model = model or FoundationModel(
            provider=model_provider, name=model_name, **model_kwargs
        )
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.prompt_template = Template(prompt_template_str_or_file)

    def ground(
        self,
        screenshot: Union[str, Image.Image, bytes, np.ndarray],
        description: str,
        **generate_kwargs,
    ) -> tuple[int, int] | None:
        """
        Find the coordinates on the screenshot that match the given description.

        This implementation:
        1. Prepares the image for the model
        2. Creates a prompt using the child class's _create_prompt method
        3. Calls the model
        4. Parses the output using the child class's _parse_output method

        Args:
            screenshot (Union[str, Image.Image, bytes, np.ndarray]): The screenshot to analyze
            description (str): A natural language description of the element to find
            **generate_kwargs: Additional arguments to pass to model.generate

        Returns:
            tuple[int, int] | None: The (x, y) coordinates where the described element is located,
                                   or None if the element couldn't be found or an error occurred

        Raises:
            RuntimeError: If an error occurs during image preparation, model generation, or output parsing
        """
        # Prepare the prompt
        try:
            messages, width, height = self._create_prompt(screenshot, description)
        except Exception as e:
            logger.error(f"Error creating prompt: {e}")
            raise RuntimeError(f"Error creating prompt: {e}")

        # Generate a response from the model
        try:
            text_output, raw_output = self.model.generate(
                messages=messages,
                max_tokens=generate_kwargs.pop("max_tokens", self.max_tokens),
                return_raw=True,
                temperature=generate_kwargs.pop("temperature", self.temperature),
                **generate_kwargs,
            )
        except Exception as e:
            logger.error(f"Error generating model response: {e}")
            raise RuntimeError(f"Error generating model response: {e}")

        # Parse the output using the child class implementation
        try:
            coordinates = self._parse_output(text_output, raw_output, width, height)

            # Return None if parsing returned None
            if coordinates is None:
                return None

            # Validate that coordinates are a tuple of two numbers
            if not isinstance(coordinates, tuple) or len(coordinates) != 2:
                logger.error(
                    f"Invalid coordinates format: {coordinates}. Expected (x, y) tuple."
                )
                return None

            x, y = coordinates

            # Validate that x and y are numeric
            if not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
                logger.error(
                    f"Invalid coordinates: ({x}, {y}). x and y must be numeric values."
                )
                return None

            # Log coordinates that are outside the image bounds but don't modify them
            if not (0 <= x <= width and 0 <= y <= height):
                logger.info(
                    f"Coordinates {coordinates} are outside image bounds ({width}x{height})"
                )

            return coordinates

        except Exception as e:
            logger.error(f"Error parsing model output: {e}")
            return None

    def _prepare_image_for_model(
        self, image: Union[str, Image.Image, bytes, np.ndarray]
    ) -> tuple[np.ndarray, int, int]:
        """
        Prepare an image for the model by converting it to the appropriate format.

        Args:
            image: The image to prepare (base64 string, PIL Image, bytes, or numpy array)

        Returns:
            tuple: (image_array, width, height) where:
                - image_array (np.ndarray): A numpy array representation of the image
                - width (int): The width of the image in pixels
                - height (int): The height of the image in pixels
        """
        # If it's already a numpy array, just extract dimensions and return
        if isinstance(image, np.ndarray):
            # Check if it's an RGB/RGBA image with shape (h, w, channels)
            if len(image.shape) == 3:
                height, width = image.shape[0], image.shape[1]
                return image, width, height
            else:
                pil_image = Image.fromarray(image)
                width, height = pil_image.size
                return np.array(pil_image), width, height

        # Convert other formats to PIL Image
        pil_image = convert_image_to_pil_image(image)
        width, height = pil_image.size

        # Convert to numpy array
        image_array = np.array(pil_image)

        return image_array, width, height

    def _create_prompt(
        self,
        image: Union[str, Image.Image, bytes, np.ndarray],
        description: str,
        user_delimiter: str = HUMAN_DELIMITER,
    ) -> tuple[List[Dict[str, Any]], int, int]:
        """
        Create a prompt for the model based on the screenshot and description.

        Args:
            image: The screenshot to analyze
            description: Description of the element to find
            user_delimiter: The delimiter for the user prompt, default is "Human:\n"

        Returns:
            List[Dict[str, Any]]: The formatted messages prompt ready to be sent to the model
            int: The width of the image in pixels
            int: The height of the image in pixels
        """
        image_array, width, height = self._prepare_image_for_model(image)
        prompt, images = self.prompt_template.render(
            description=description,
            screenshot=image_array,
            width=width,
            height=height,
        )

        if user_delimiter not in prompt:
            logger.info(
                f"User delimiter {user_delimiter} not found in prompt. Adding it to the top of the prompt."
            )
            prompt = user_delimiter + prompt

        messages = prompt_to_messages(
            prompt, images=images, user_delimiter=user_delimiter
        )
        return messages, width, height

    @abstractmethod
    def _parse_output(
        self, text_output: str, raw_output: Any, width: int, height: int
    ) -> tuple[int, int] | None:
        """
        Parse the model output to extract the coordinates.

        Args:
            text_output: The text output from the model
            raw_output: The raw output from the model
            width: Width of the image in pixels
            height: Height of the image in pixels

        Returns:
            tuple[int, int] | None: The (x, y) coordinates or None if not found
        """
        pass
