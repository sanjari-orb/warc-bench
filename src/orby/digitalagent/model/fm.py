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
import time
from orby.digitalagent.model.usage_log import (
    log_anthropic_usage,
    log_gemini_usage,
    log_openai_usage,
    log_raw_response,
)
from anthropic import Anthropic
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


def _anthropic_response_text(response) -> str:
    """Return the text of an Anthropic response.

    The first content block is not necessarily the answer. Models with adaptive
    thinking enabled (Claude Sonnet 5, Opus 5 and later) put a ``thinking`` block
    first, whose ``text`` is None, so indexing ``content[0]`` silently yields None
    and every downstream parse fails on a NoneType.

    Raises:
        ValueError: if the response contains no text block at all.
    """
    for block in response.content:
        if getattr(block, "type", None) == "text" and block.text is not None:
            return block.text
    raise ValueError(
        "Anthropic response contained no text block "
        f"(stop_reason={response.stop_reason!r}, "
        f"blocks={[getattr(b, 'type', None) for b in response.content]})."
    )


class GeminiRetryableError(Exception):
    """A Gemini request that failed for a reason worth retrying (429, 5xx, network)."""


def _gemini_interaction_input(messages: List[Dict[str, Any]]) -> tuple[str | None, list]:
    """Convert OpenAI-style messages to an Interactions API system_instruction and input.

    Only system and user messages are supported: every call is stateless
    (store=False) and carries its full context, as the agents here send it.
    Images must be data URLs or http(s) URLs; anything else raises ValueError.
    """
    system_texts, items = [], []
    for message in messages:
        role = message["role"]
        if role not in ("system", "user"):
            raise ValueError(f"Gemini provider supports system and user messages only, got {role!r}")
        content = message["content"]
        parts = [{"type": "text", "text": content}] if isinstance(content, str) else content
        for part in parts:
            if part["type"] == "text":
                if not part["text"]:
                    continue
                if role == "system":
                    system_texts.append(part["text"])
                else:
                    items.append({"type": "text", "text": part["text"]})
            elif part["type"] == "image_url":
                if role == "system":
                    raise ValueError("Gemini system_instruction cannot hold images")
                url = part["image_url"]["url"]
                if url.startswith("data:"):
                    header, _, data = url.partition(",")
                    mime = header[len("data:"):].split(";")[0] or "image/png"
                elif url.startswith(("http://", "https://")):
                    data, mime = download_image_as_base64_str(url), "image/png"
                else:
                    raise ValueError(f"Unsupported image URL scheme: {url[:30]!r}")
                items.append({"type": "image", "mime_type": mime, "data": data})
            else:
                raise ValueError(f"Unsupported content type for Gemini: {part['type']!r}")
    return ("\n\n".join(system_texts) or None), items


def _gemini_interaction_text(interaction: dict) -> str:
    """The answer text of an interaction: its model_output steps, without thoughts.

    Returns "" when there is no model output (blocked, failed or cut off); the
    caller's parser then fails the step, as for other providers' refusals.
    """
    return "".join(
        content.get("text", "")
        for step in interaction.get("steps") or []
        if step.get("type") == "model_output"
        for content in step.get("content") or []
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
                os.environ.get("MOSAIC_MODEL_HOST_URL", ""),
            )
            if not self.model_host_url:
                raise ValueError(
                    "No host URL for the 'mosaic' provider. Pass host_url, or set "
                    "MOSAIC_MODEL_HOST_URL to your own model server."
                )
            if "host_url" in kwargs:
                del kwargs["host_url"]

            self.processor = AutoProcessor.from_pretrained(self.model_name)
        elif self.model_provider == "mosaic-vllm":
            self.model_host_url = kwargs.get(
                "host_url",
                os.environ.get("MOSAIC_VLLM_MODEL_HOST_URL", ""),
            )
            if not self.model_host_url:
                raise ValueError(
                    "No host URL for the 'mosaic-vllm' provider. Pass host_url, or "
                    "set MOSAIC_VLLM_MODEL_HOST_URL to your own vLLM server."
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
            # Fireworks' OpenAI-compatible endpoint returns the same usage
            # fields as OpenAI (cached and reasoning tokens included), so its
            # calls can be logged by log_openai_usage.
            api_key = os.environ.get("FIREWORKS_API_KEY")
            if not api_key:
                raise ValueError("FIREWORKS_API_KEY is not set.")
            self.model = OpenAI(
                api_key=api_key,
                base_url="https://api.fireworks.ai/inference/v1",
            )
            self.model = self.model.chat.completions.create
        elif self.model_provider == "gemini":
            # Google's recommended interface: the Interactions API through the
            # google-genai SDK. It reports cached and thinking tokens separately.
            from google import genai

            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY is not set.")
            # Keep the client itself: it closes its HTTP connection when it is
            # garbage collected, which would break the bound create method.
            self._gemini_client = genai.Client(api_key=api_key)
            self.model = self._gemini_client.interactions.create
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
            # A dropped connection says nothing about the model; without these
            # one network blip ended the whole task with a score of 0.
            openai.APIConnectionError,
            anthropic.APIConnectionError,
            GeminiRetryableError,
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

        # An unset sampling parameter means "do not send it". Passing None
        # through would be rejected by every provider.
        for _sampling_param in ("temperature", "top_p", "top_k", "frequency_penalty"):
            if generate_kwargs.get(_sampling_param, False) is None:
                del generate_kwargs[_sampling_param]

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
            # OpenAI reasoning models reject max_tokens; they take max_completion_tokens.
            token_arg = (
                {"max_completion_tokens": max_tokens}
                if self.model_provider == "openai"
                else {"max_tokens": max_tokens}
            )
            _t0 = time.time()
            raw = self.cached_raw_generate(self.model)(
                model=self._model_server_model_name,
                messages=messages,
                **token_arg,
                **generate_kwargs,
            )
            if self.model_provider in ("openai", "fireworks"):
                log_openai_usage(
                    self._model_server_model_name,
                    raw,
                    time.time() - _t0,
                    provider=self.model_provider,
                )
                log_raw_response(raw)
            if return_raw:
                return raw.choices[0].message.content, raw
            else:
                return raw.choices[0].message.content
        elif self.model_provider == "anthropic":
            if "frequency_penalty" in generate_kwargs:
                del generate_kwargs["frequency_penalty"]
            messages = self._convert_image_format_for_anthropic(messages)

            _t0 = time.time()
            raw = self.cached_raw_generate(self.model)(
                model=self._model_server_model_name,
                messages=messages,
                max_tokens=max_tokens,
                **generate_kwargs,
            )
            log_anthropic_usage(self._model_server_model_name, raw, time.time() - _t0)
            # Uncomment for debugging
            # print(f"{'\033[32m'}LLM says: {_anthropic_response_text(raw)} {'\033[0m'}")

            if return_raw:
                return _anthropic_response_text(raw), raw
            else:
                return _anthropic_response_text(raw)
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
            # print(f"{'\033[32m'}LLM says: {_anthropic_response_text(raw)} {'\033[0m'}")

            if return_raw:
                return raw
            else:
                return _anthropic_response_text(raw)

        elif self.model_provider == "gemini":
            from google.genai._gaos.lib.compat_errors import (
                APIConnectionError as GeminiConnectionError,
                InternalServerError as GeminiServerError,
                RateLimitError as GeminiRateLimitError,
            )

            system, items = _gemini_interaction_input(messages)
            extra = generate_kwargs.get("extra_body") or {}
            unknown = set(extra) - {"generation_config", "service_tier"}
            if unknown:
                raise ValueError(f"Unsupported extra_body keys for Gemini: {sorted(unknown)}")
            generation_config = {"max_output_tokens": max_tokens, **(extra.get("generation_config") or {})}
            if generate_kwargs.get("temperature") is not None:
                generation_config["temperature"] = generate_kwargs["temperature"]
            request = {
                "model": self._model_server_model_name,
                "input": items,
                "generation_config": generation_config,
                # Each step carries its full context, so keep nothing server-side.
                "store": False,
                "service_tier": extra.get("service_tier", "standard"),
            }
            if system:
                request["system_instruction"] = system
            _t0 = time.time()
            try:
                interaction = self.model(**request, timeout=generate_kwargs.get("timeout", 600))
            except (GeminiConnectionError, GeminiServerError, GeminiRateLimitError) as ex:
                raise GeminiRetryableError(f"Gemini request failed: {type(ex).__name__}: {str(ex)[:300]}") from ex
            raw = interaction.model_dump(mode="json", exclude_none=True)
            log_gemini_usage(self._model_server_model_name, raw, time.time() - _t0)
            text = _gemini_interaction_text(raw)
            if return_raw:
                return text, raw
            return text

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
