from faker import Faker
import numpy as np
import random
import re
from typing import List, Dict
import warnings

from orby.digitalagent.utils.image_utils import numpy_to_base64
from fm import llm_data_pb2

# TODO: make sure removing the \n\n from the user delimiter works for sva_v3
HUMAN_DELIMITER = "\n\nHuman:"
ASSISTANT_DELIMITER = "\n\nAssistant:"


def prepare_image_input(arr):
    return {
        "type": "image_url",
        "image_url": {"url": f"data:image/png;base64,{numpy_to_base64(arr)}"},
    }


def screenshots_differ(screenshot1, screenshot2):
    return (screenshot1.shape != screenshot2.shape) or (
        screenshot1 != screenshot2
    ).any()


def prompt_to_messages(
    prompt: str,
    *,
    user_delimiter: str = HUMAN_DELIMITER,
    assistant_delimiter: str = ASSISTANT_DELIMITER,
    images: dict[str, np.ndarray] = {},
) -> list[dict]:
    """
    Converts a prompt string into a list of messages for the user and assistant.

    The user prompt can contain images and text, where images are specified as <image_KEY>, where KEY is a key in the images dictionary.

    If the prompt does not start with the user delimiter, the first part of the prompt before the user delimiter is considered a system prompt.
    """

    image_keys_unused = set(images.keys())

    def process_user_prompt(prompt):
        user_content = []
        if assistant_delimiter in prompt:
            prompt = prompt.split(assistant_delimiter)[0]

        for part in re.split(r"(<image:[^>]+>)", prompt):
            if len(part) == 0:
                continue
            if part.startswith("<image:") and part.endswith(">"):
                key = part[len("<image:") : -1]
                user_content.append(prepare_image_input(images[key]))
                image_keys_unused.discard(key)
            else:
                user_content.append({"type": "text", "text": part})

        return user_content

    messages = []
    role = "system" if not prompt.startswith(user_delimiter) else "user"
    for line in prompt.split(user_delimiter):
        if line.strip() == "":
            continue
        if role == "system":
            # System prompts are text-only
            messages.append({"role": role, "content": line})
            role = "user"
        elif role == "user":
            if assistant_delimiter in line:
                user_content, assistant_content = line.split(assistant_delimiter)
                messages.append(
                    {"role": role, "content": process_user_prompt(user_content)}
                )
                role = "assistant"
                content = []
                content.append({"type": "text", "text": assistant_content})
                messages.append({"role": role, "content": content})
                role = "user"
            else:
                user_content = process_user_prompt(line)
                messages.append({"role": role, "content": user_content})

    if len(image_keys_unused) > 0:
        warnings.warn(
            f"Unused image keys during prompt-to-messages conversion: {image_keys_unused}"
        )

    return messages


def remove_thinking(response, cot_open_tag="<thinking>", cot_close_tag="</thinking>"):
    # Remove content between COT tags from the response

    response = re.sub(rf"{cot_open_tag}[\W\w]*?{cot_close_tag}", "", response)

    return response


def draw_coordinate_lines(image, step=100, color=(255, 0, 255)):
    image = image.copy()

    # Draw horizontal lines
    for i in range(step - 1, image.shape[0], step):
        image[i, :, :] = color

    # Draw vertical lines
    for i in range(step - 1, image.shape[1], step):
        image[:, i, :] = color

    return image


def convert_messages_to_llm_interactions(
    messages: List[Dict[str, str]],
) -> List[llm_data_pb2.LLMMessage]:
    """
    Takes messages (expected input for FoundationModel.generate()) and
    converts them into a list of llm_data_pb2.LLMMessage objects.

    Args:
    messages (list): Open AI format of input messages passed into model.generate() calls
    """

    def convert_message_content_to_llm_content(content):
        llm_contents = []
        if type(content) == str:
            return [llm_data_pb2.LLMContent(text=content)]
        elif type(content) == list:
            for c in content:
                if c["type"] == "text":
                    llm_contents.append(llm_data_pb2.LLMContent(text=str(c["text"])))
                elif c["type"] == "image_url":
                    # Extract the base64 part from 'data:image/...;base64,...'
                    data_url = c["image_url"]["url"]
                    base64_str = data_url.split(",")[1]

                    llm_contents.append(llm_data_pb2.LLMContent(image_url=base64_str))
                else:
                    raise ValueError("Found unknown content type: ", c)
            return llm_contents
        raise ValueError("Could not convert content")

    llm_messages = []
    for message in messages:
        llm_messages.append(
            llm_data_pb2.LLMMessage(
                # We are assuming OpenAI api format of messages
                role=message["role"],
                llm_contents=convert_message_content_to_llm_content(
                    message["content"],
                ),
            )
        )
    return llm_messages


def convert_llm_interactions_to_messages(
    llm_messages: List[llm_data_pb2.LLMMessage],
) -> List[Dict[str, str]]:
    """
    Takes a list of llm_data_pb2.LLMMessage objects and converts them into messages (expected input for FoundationModel.generate()).

    Returns:
    messages (list): Open AI format of input messages passed into model.generate() calls
    """

    def convert_llm_content_to_message_content(message: llm_data_pb2.LLMMessage):
        llm_contents = []
        for content in message.llm_contents:
            if content.HasField("text"):
                llm_content = {"type": "text", "text": content.text}
            elif content.HasField("image_url"):
                llm_content = {
                    "type": "image_url",
                    "image_url": {"url": "data:image/png;base64," + content.image_url},
                }
            else:
                raise ValueError("Provide text/image LLM content")
            llm_contents.append(llm_content)
        return {"role": message.role, "content": llm_contents}

    fm_messages = []
    for message in llm_messages:
        fm_messages.append(convert_llm_content_to_message_content(message))
    return fm_messages


def produce_fake_details(n=3):
    """Utility to produce fake details"""
    faker = Faker()
    loc = faker.local_latlng()

    data = {
        "Person name": [faker.name() for _ in range(n)],
        "Address": [faker.address() for _ in range(n)],
        "Phone number": [faker.phone_number() for _ in range(n)],
        "Email": [
            (faker.email().split("@")[0] + "@" + faker.domain_name()) for _ in range(n)
        ],
        "Date": [str(faker.date_this_decade()) for _ in range(n)],
        "Number": [str(random.randint(0, 100)) for _ in range(n)],
        "Username": [faker.user_name() for _ in range(n)],
        "Project": [f"{faker.word()}_{faker.word()}" for _ in range(n)],
        "Location": [f"{loc[2]}, {loc[3]}" for _ in range(n)],
    }
    text = ""
    for key, values in data.items():
        text += f' * {key}: {"," .join(values)}\n'
    return text
