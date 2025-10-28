import re
from openai import OpenAI

import orby.digitalagent.utils.eval_utils as eval_utils
import orby.digitalagent.utils.image_utils as image_utils


def get_action_description_from_gpt_4o(
    client: OpenAI,
    image: bytes,
    bbox_xywh: tuple[float, float, float, float],
) -> str:
    """
    Using GPT-4v, generate a description of the action based on the image and bounding box.

    Args:
        client (OpenAI): The OpenAI client
        image (bytes): The image as bytes
        bbox (tuple[float, float, float, float]): The bounding box in the format (x, y, w, h)
            x and y are the coordinates of the top-left corner, and w and h are the width and height.

    Returns:
        str: The description of the action
    """
    bbox_xyxy = image_utils.convert_bbox_xywh_to_xyxy(bbox_xywh)
    image_pil = image_utils.convert_image_bytes_to_pil_image(image)
    image_utils.draw_red_arrow(image_pil, bbox_xyxy)
    prompt = """\
You are a superhuman AI that can navigate the web and understand user intentions.
You have been given the screenshot of a webpage before a user conduct an ACTION over an ELEMENT on the webpage.
The element is highlighted in a red bounding box and pointed to by a red arrow.
Your task is to provide a perfect description of the ACTION.

Please follow these rules when generating the description:
1. Think of each description as an instruction that the ACTION tries to follow. Do NOT provide a description that the action cannot achieve by itself.
2. The description should be as accurate as possible; there should not be another possible action on this webpage that can also fits this action description.
3. If there is no visible difference between the before and after screenshots, still try to provide a description based on the ACTION and the context of the ELEMENT.
4. The appropriate description depends on the situation of the webpage before the ACTION. The same ACTION can have different descriptions based on the situation. For example, pressing the same button can open or close a tab based on the situation.
5. You should use the content around the ELEMENT to make your description more accurate and unique. For example, if there are several input boxes, use texts surrounding it to make your description unique to one of them.
6. The description you provide should contain these components, if possible:
    Causal description: Describe the ACTION based on its immediate result; for example, "navigate to the new graduate career opportunities page" or "go to the product details page of <a particular computer name>",
    Appearance description: Describe the ACTION by a verb and a description of the element, along with other necessary information to make the description precise; for example, "click on the 'read more' button" or "close the settings tab". When describing the element's color, do NOT use the color of the bounding box,
You need to describe the ACTION by combining the information from these 2 types of description above; for example, "navigate to the new graduate career opportunities page by clicking on the 'learn more' button".
7. DO NOT put any information about the element's color, location, or size in the description.
8. When describing an ACTION over a spreadsheet ELEMENT, you should provide the row and column of the cell that the ACTION is performed on; for example, "edit the cell in row 3, column E".

Please do NOT output anything else. Please do NOT decorate the output with any additional text.

Answer: \
"""
    content = []
    content.append(
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{image_utils.convert_pil_image_to_base64_str(image_pil, 'JPEG')}",
                "detail": "high",
            },
        }
    )
    content.append({"type": "text", "text": prompt})
    response = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {
                "role": "user",
                "content": content,
            }
        ],
        temperature=0,
        max_tokens=300,
    )
    return response.choices[0].message.content


def extract_coordinates_from_string(sentence: str) -> tuple[float, float] | None:
    """
    Locate the first occurrence of a pair of coordinates in a string and return them
    as a tuple of floats.

    Args:
        sentence (str): The string to search for coordinates

    Returns:
        Optional[tuple[float, float]]: The coordinates as a tuple of floats if found,
            else None
    """
    # Regular expression to match coordinates (float, float)
    coordinate_pattern = r"\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)"

    # Search for the first occurrence of the pattern
    match = re.search(coordinate_pattern, sentence)

    # If a match is found, return the tuple of floats, else return None
    if match:
        return float(match.group(1)), float(match.group(2))

    return None


def rouge_1_f1_metric(prediction: str | None, label: str | None) -> float:
    """
    Calculate the ROUGE score between a prediction and a label.

    Args:
        prediction (str): The predicted text
        label (str): The ground truth text
        alpha (float): The weight for recall in the ROUGE score. Default is 0.5.

    Returns:
        float: The ROUGE score between the prediction and the label
    """
    if prediction is None or label is None or len(prediction) == 0 or len(label) == 0:
        return 0.0

    # Tokenize the prediction and label
    prediction_tokens = set(prediction.split())
    label_tokens = set(label.split())

    # Calculate precision, recall, and F1 score
    precision = len(prediction_tokens.intersection(label_tokens)) / len(
        prediction_tokens
    )
    recall = len(prediction_tokens.intersection(label_tokens)) / len(label_tokens)
    f1_score = (
        (2 * precision * recall) / (precision + recall) if precision + recall > 0 else 0
    )

    return f1_score


def within_bbox_metric(
    bbox_label: tuple[float, float, float, float] | str,
    point_prediction: tuple[float, float] | str,
    bbox_format: str = "xyxy",
) -> bool:
    """
    Determine if a point is within a bounding box. Alternatively, if the prediction is
        a substring of the label string when no bbox and point are found, we consider
        the prediction to be correct if they are substrings of each other.

    Args:
        bbox (tuple[float, float, float, float] | str): The bounding box as a tuple
            of floats or a string
        point (tuple[float, float] | str): The point as a tuple of floats or a string
        bbox_format (str): The format of the bounding box, either "xyxy" or "xywh".
            Default is 'xyxy', which means it represent the coordinates of the top-left
            and bottom-right corner.
            Can be 'xywh', which means it represent the coordinates of the top-left
            corner and the width and height.

    Returns:
        bool: True if the point is within the bounding box, else False
    """
    if isinstance(bbox_label, str):
        bbox_label = bbox_label.strip().lower()
        bbox_label = eval_utils.extract_bbox_from_string(bbox_label)
    if isinstance(point_prediction, str):
        point_prediction = point_prediction.strip().lower()
        point_prediction = extract_coordinates_from_string(point_prediction)

    if bbox_label is None and point_prediction is None:
        # if both are None, it means that the predicted and actual answer may
        # indicate no element found
        return (bbox_label in point_prediction) or (point_prediction in bbox_label)

    if bbox_label is None or point_prediction is None:
        return False

    if bbox_format == "xywh":
        bbox_label = image_utils.convert_bbox_xywh_to_xyxy(bbox_label)

    x1, y1, x2, y2 = bbox_label
    x, y = point_prediction

    return x1 <= x <= x2 and y1 <= y <= y2


def within_bbox_0_to_999_coordinates_metric(
    label: str,
    prediction: str,
    bbox_format: str = "xyxy",
) -> bool:
    """
    Determine if the prediction is correct by checking if the predicted coordinates
    are within the bounding box / are both None. The coordinates are expected to be
    in the range of 0 to 999.

    Args:
        label (str): The label containing the bounding box
        prediction (str): The predicted bounding box

    Returns:
        bool: True if the entire prediction is correct, else False
    """
    point_prediction = prediction.strip().lower()
    point = extract_coordinates_from_string(point_prediction)
    point = (point[0] / 1000, point[1] / 1000)
    return within_bbox_metric(label, point, bbox_format=bbox_format)


def with_bbox_and_correct_action_info_metric(
    label: str,
    prediction: str,
) -> bool:
    """
    Determine if the prediction is correct by checking if the predicted coordinates
    are within the bounding box / are both None and if the predicted action is correct.

    Args:
        label (str): The label containing the bounding box and the action
        prediction (str): The predicted bounding box and action

    Returns:
        bool: True if the entire prediction is correct, else False
    """
    gt_bbox, gt_action_type, gt_action_arg = label.split("\n")
    try:
        pred_coords, pred_action_type, pred_action_arg = prediction.split("\n")
    except ValueError:
        # if the prediction does not contain all the required information, it is incorrect
        return False

    bbox_correct = within_bbox_metric(gt_bbox, pred_coords)

    gt_action_type = gt_action_type.strip().lower()
    pred_action_type = pred_action_type.strip().lower()
    action_type_correct = gt_action_type == pred_action_type

    gt_action_arg = gt_action_arg.strip().lower()
    pred_action_arg = pred_action_arg.strip().lower()
    action_arg_correct = gt_action_arg == pred_action_arg

    return bbox_correct and action_type_correct and action_arg_correct
