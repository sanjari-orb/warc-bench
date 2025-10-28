import base64
import copy
import hashlib
import logging
import os
import pickle
import redis
import requests
from typing import Any, Dict, List
import warnings

import openai
import anthropic
from anthropic import Anthropic
import fireworks.client
from openai import OpenAI
from retry import retry
from transformers import AutoModelForCausalLM, AutoModelForVision2Seq, AutoProcessor

from orby.digitalagent.utils.image_utils import (
    download_image_as_base64_str,
    base64_to_image,
)
from orby.digitalagent.model.model_router import lookup_endpoint


logger = logging.getLogger(__name__)
ELASTICACHE_HOST = os.environ.get(
    "ELASTICACHE_HOST",
    "fm-calls-valkey-cache-at5ld8.serverless.use2.cache.amazonaws.com",
)


class FoundationModel:
    """
    A common class to instantiate foundation models and use them to generate text.
    For API models like OpenAI and Anthropic, API access keys should be set as environment variables.
    """

    def __init__(
        self,
        provider: str = "openai",
        name: str | None = None,
        use_cache="none",
        **kwargs,
    ) -> None:
        """
        Initialize the FoundationModel.

        Args:
           provider (str, optional): The provider of the language model. Defaults to "openai".
           name (str, optional): The specific model to use. Defaults to None.
           **kwargs: Additional arguments specific to the language model provider.
        """
        self.model_provider = provider
        # Model name to record
        self.model_name = name
        # Internal model name used for making the call to model server
        self._model_server_model_name = name
        self.generate_kwargs = kwargs

        assert (
            self.model_name is not None
        ), "`name` must be provided to initialize FoundationModel."
        if use_cache == "elasticache":
            if ELASTICACHE_HOST:
                try:
                    self.cache = redis.Redis(
                        host=ELASTICACHE_HOST, ssl=True, socket_timeout=5
                    )
                    self.cache.ping()
                except (
                    redis.exceptions.ConnectionError,
                    redis.exceptions.TimeoutError,
                ):
                    warnings.warn(
                        "Could not connect to the cache server. Disabling cache."
                    )
                    self.cache = None
            else:
                warnings.warn("ELASTICACHE_HOST not set. Disabling cache.")
                self.cache = None
        elif use_cache == "none":
            self.cache = None
        else:
            raise ValueError(
                f"Invalid value for `use_cache` (supported values: 'none', 'elasticache'): {use_cache}."
            )

        if self.model_provider == "openai":
            self.model = OpenAI(
                api_key=os.environ.get("OPENAI_API_KEY"),
            )
            self.model = self.model.chat.completions.create
        elif self.model_provider == "anthropic":
            self.model = Anthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY"),
            )
            self.model = self.model.messages.create
            self.generate_kwargs["timeout"] = self.generate_kwargs.get("timeout", 120)
        elif self.model_provider == "anthropic_beta":
            client = Anthropic(api_key=os.environ.get("ANTHROPIC_BETA_API_KEY"))
            self.model = client.beta.messages.create
            self.generate_kwargs["timeout"] = self.generate_kwargs.get("timeout", 120)
        elif self.model_provider == "huggingface":
            self.processor = AutoProcessor.from_pretrained(self.model_name)

            AutoModelClass = (
                AutoModelForVision2Seq
                if any(x in self.model_name.lower() for x in ["llava", "qwen2-vl"])
                else AutoModelForCausalLM
            )

            self.model = AutoModelClass.from_pretrained(self.model_name)
        elif self.model_provider == "mosaic":
            self.model_host_url = kwargs.get(
                "host_url",
                os.environ.get("MOSAIC_MODEL_HOST_URL", "https://orby-osu.ngrok.app"),
            )
            if "host_url" in kwargs:
                del kwargs["host_url"]

            self.processor = AutoProcessor.from_pretrained(self.model_name)
        elif self.model_provider == "mosaic-vllm":
            self.model_host_url = kwargs.get(
                "host_url",
                os.environ.get(
                    "MOSAIC_VLLM_MODEL_HOST_URL", "http://model.internal.orby.ai/v1"
                ),
            )
            if "host_url" in kwargs:
                del kwargs["host_url"]
            self.model_host_url, self._model_server_model_name = lookup_endpoint(
                self.model_host_url, self.model_name
            )
            self.model = OpenAI(
                api_key="EMPTY",
                base_url=self.model_host_url,
            )
            self.model = self.model.chat.completions.create
        elif self.model_provider == "fireworks":
            fireworks.client.api_key = os.environ.get("FIREWORKS_API_KEY")

            self.model = fireworks.client.ChatCompletion.create
        else:
            raise ValueError(f"Invalid model provider: {self.model_provider}.")

    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Convert a list of messages into a formatted prompt string.

        Args:
            messages (list): A list of messages, where each message is a dictionary with 'role' and 'content' keys.

        Returns:
            str: The formatted prompt string.
        """

        USER_PROMPT = "\n\nUser:"
        BOT_PROMPT = "\n\nBot:"
        prompt = ""
        is_last_message_user = False

        for message in messages:
            if message["role"] == "user":
                assert isinstance(
                    message["content"], str
                ), "User message content must be a string, otherwise a dedicated processor should be available."
                prompt += USER_PROMPT + message["content"]
                is_last_message_user = True
            elif message["role"] == "assistant":
                prompt += BOT_PROMPT + message["content"]
                is_last_message_user = False
        if is_last_message_user:
            prompt += BOT_PROMPT

        return prompt

    def extract_image_list_from_messages(
        self, messages: List[Dict[str, str]]
    ) -> List[str]:
        """
        Extract the image URLs from the multimodal messages format.

        Args:
            messages (List[Dict[str, str]]): The messages in the multimodal messages format.

        Returns:
            List[str]: The list of image URLs.
        """
        image_list = []
        for message in messages:
            if isinstance(message["content"], list):
                for content in message["content"]:
                    if content["type"] == "image_url":
                        image_url = content["image_url"]["url"]

                        if image_url.startswith("data:image/png;base64,"):
                            image_base64 = image_url[len("data:image/png;base64,") :]
                        else:
                            image_base64 = download_image_as_base64_str(image_url)
                        image_list.append(image_base64)

        return image_list

    def messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Convert a list of messages into a formatted prompt string, using the processor if available.

        Args:
            messages (list): A list of messages, where each message is a dictionary with 'role' and 'content' keys.

        Returns:
            str: The formatted prompt string.
        """

        try:
            # Huggingface processor doesn't work well with string "content" in messages, need to convert to {"type": "text", "text": [content]}

            new_messages = []
            for message in messages:
                if isinstance(message["content"], str):
                    new_messages.append(
                        {
                            "role": message["role"],
                            "content": [{"type": "text", "text": message["content"]}],
                        }
                    )
                elif isinstance(message["content"], list):
                    # also replace image_url messages with {"type": "image"}
                    new_content = []
                    for content in message["content"]:
                        if content["type"] == "image_url":
                            new_content.append({"type": "image"})
                        else:
                            new_content.append(content)
                    new_messages.append(
                        {"role": message["role"], "content": new_content}
                    )

            prompt = self.processor.apply_chat_template(
                new_messages, add_generation_prompt=True
            )
            return prompt
        except ValueError:
            return self._messages_to_prompt(messages)

    def _convert_image_format_for_anthropic(
        self, messages: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Convert the image URLs in the multimodal messages format to the format expected by the Anthropic API.

        Instead of the "image_url" format where base64 strings are formatted into "data:<image_type>;base64,<image_data>",
        Anthropic expects images to be passed as "image" type, with "type", "media_type", and "data" fields.

        Args:
            messages (List[Dict[str, str]]): The messages in the multimodal messages format.

        Returns:
            List[Dict[str, str]]: The messages in the format expected by the Anthropic API.
        """

        new_messages = []
        for message in messages:
            if isinstance(message["content"], list):
                new_content_list = []
                for content in message["content"]:
                    if content["type"] == "image_url":
                        image_url = content["image_url"]["url"]

                        if image_url.startswith("data:"):
                            image_base64 = image_url.split(",")[1]
                            media_type = (
                                image_url.split(",")[0].split(":")[1].split(";")[0]
                            )
                        else:
                            image_base64 = download_image_as_base64_str(image_url)
                            image = base64_to_image(image_base64)
                            media_type = "image/" + image.format.lower()

                        new_content = {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64,
                            },
                        }
                        new_content_list.append(new_content)
                    else:
                        new_content_list.append(content)
                new_message = {k: v for k, v in message.items() if k != "content"}
                new_message["content"] = new_content_list
                new_messages.append(new_message)
            else:
                new_messages.append(message)

        return new_messages

    def cached_raw_generate(self, func):
        def wrapper(**kwargs):
            if self.cache is None:
                return func(**kwargs)

            key = copy.deepcopy(kwargs)
            key["model_provider"] = self.model_provider
            if hasattr(self, "model_host_url"):
                key["model_host_url"] = self.model_host_url
            # sort by keys to reduce accidental misses
            key = dict(sorted(key.items()))
            key = pickle.dumps(key)
            m = hashlib.sha512()
            m.update(key)
            key = m.digest()
            if cached := self.cache.get(key):
                return pickle.loads(cached)
            result = func(**kwargs)
            self.cache.set(key, pickle.dumps(result))
            return result

        return wrapper

    # TODO: return structured response for better handling of tracing
    @retry(
        (
            openai.APITimeoutError,
            anthropic.APITimeoutError,
            openai.InternalServerError,
            anthropic.InternalServerError,
            openai.UnprocessableEntityError,
            anthropic.UnprocessableEntityError,
            openai.RateLimitError,
            anthropic.RateLimitError,
        ),
        tries=10,
        delay=1,
        backoff=1,
    )
    def generate(
        self,
        *,
        messages: List[Dict[str, str]],
        max_tokens: int = 512,
        return_raw: bool = False,
        additional_inputs: dict = {},
        **kwargs,
    ) -> tuple[str, Any]:
        """
        Generate text based on the given prompt.

        Args:
            messages (List[Dict[str, str]]): The prompt for text generation, in the multimodal messages format.
                See https://platform.openai.com/docs/api-reference/making-requests for an example.

            max_tokens (int, optional): The maximum number of tokens to generate. Defaults to 512.

            additional_inputs (dict, optional): Additional inputs specific to processor of a Hugging Face model.
                Defaults to an empty dictionary.

            **kwargs: Additional arguments specific to the language model provider.

        Returns:
            str: The generated text.
        """

        generate_kwargs = copy.deepcopy(self.generate_kwargs)
        generate_kwargs.update(kwargs)

        if "max_tokens" in generate_kwargs:
            max_tokens = generate_kwargs["max_tokens"]
            del generate_kwargs["max_tokens"]

        if messages[0]["role"] == "system":
            if self.model_provider in ["fireworks"]:
                # Fireworks and Mosaic VLLM don't support system prompts, so we need to combine it with the first user prompt
                system_content = (
                    [{"type": "text", "text": messages[0]["content"]}]
                    if isinstance(messages[0]["content"], str)
                    else messages[0]["content"]
                )
                if len(messages) > 1 and messages[1]["role"] == "user":
                    first_user_message = messages[1]
                    first_user_content = (
                        [{"type": "text", "text": first_user_message["content"]}]
                        if isinstance(first_user_message["content"], str)
                        else first_user_message["content"]
                    )
                    messages = [
                        {"role": "user", "content": system_content + first_user_content}
                    ] + messages[2:]
                else:
                    messages = [{"role": "user", "content": system_content}] + messages[
                        1:
                    ]
            elif self.model_provider == "anthropic":
                # Anthropic doesn't support "system" as a role, but as a separate "system" argument
                system_prompt = (
                    messages[0]["content"]
                    if isinstance(messages[0]["content"], str)
                    else messages[0]["content"][0]["text"]
                )
                generate_kwargs["system"] = [
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
                messages = messages[1:]

        if self.model_provider == "huggingface":
            prompt = self.messages_to_prompt(messages)
            images = self.extract_image_list_from_messages(messages)
            args = {
                "text": prompt,
                "return_tensors": "pt",
            }
            if len(images) > 0:
                args["images"] = [base64_to_image(img) for img in images]
            inputs = self.processor(**args, **additional_inputs)
            output = self.cached_raw_generate(self.model.generate)(
                **inputs, max_new_tokens=max_tokens, **generate_kwargs
            )
            output_text = self.processor.decode(output[0], skip_special_tokens=True)

            if return_raw:
                return output_text, output
            else:
                return output_text
        elif (
            self.model_provider == "openai"
            or self.model_provider == "mosaic-vllm"
            or self.model_provider == "fireworks"
        ):
            raw = self.cached_raw_generate(self.model)(
                model=self._model_server_model_name,
                messages=messages,
                max_tokens=max_tokens,
                **generate_kwargs,
            )
            if return_raw:
                return raw.choices[0].message.content, raw
            else:
                return raw.choices[0].message.content
        elif self.model_provider == "anthropic":
            if "frequency_penalty" in generate_kwargs:
                del generate_kwargs["frequency_penalty"]
            messages = self._convert_image_format_for_anthropic(messages)
            
            raw = self.cached_raw_generate(self.model)(
                model=self._model_server_model_name,
                messages=messages,
                max_tokens=max_tokens,
                **generate_kwargs,
            )
            # Uncomment for debugging
            # print(f"{'\033[32m'}LLM says: {raw.content[0].text} {'\033[0m'}")

            if return_raw:
                return raw.content[0].text, raw
            else:
                return raw.content[0].text
        elif self.model_provider == "anthropic_beta":
            if "frequency_penalty" in generate_kwargs:
                del generate_kwargs["frequency_penalty"]
            messages = self._convert_image_format_for_anthropic(messages)
            
            # Enabling thinking with Claude Computer Use tool doesn't support setting temperature value to anything other than 1
            generate_kwargs.pop("temperature")
            raw = self.cached_raw_generate(self.model)(
                model=self._model_server_model_name,
                messages=messages,
                max_tokens=max_tokens,
                **generate_kwargs,
            )
            # Uncomment for debugging
            # print(f"{'\033[32m'}LLM says: {raw.content[0].text} {'\033[0m'}")

            if return_raw:
                return raw
            else:
                return raw.content[0].text

        elif self.model_provider == "mosaic":
            # adopted from multimodal/scripts/inference/client.py
            prompt = self.messages_to_prompt(messages)
            images = self.extract_image_list_from_messages(messages)

            output = self.cached_raw_generate(requests.post)(
                self.model_host_url,
                json={
                    "prompt": prompt,
                    "images": images,
                    "max_new_tokens": max_tokens,
                    **generate_kwargs,
                },
            )

            prompt_in_response = prompt.replace("<image>", " ")
            generated_text = output.text[len(prompt_in_response) :]

            if return_raw:
                return generated_text, output
            else:
                return generated_text
        else:
            raise ValueError(f"Invalid model provider: {self.model_provider}.")
