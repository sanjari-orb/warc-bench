import base64
import concurrent.futures as cf
import pandas as pd
import pickle
import re
import requests
from tqdm import tqdm
from typing import Any, Callable

import orby.digitalagent.utils.image_utils as image_utils


def predict_with_mosaic_endpoint_and_output_accuracy(
    mosaic_endpoint: str,
    df: pd.DataFrame,
    metric_fn: Callable[[Any, Any], bool] = lambda x, y: x == y,
    prompt_column: str = "prompt",
    label_column: str = "label",
    prediction_column: str = "prediction",
    output_column: str = "output",
    max_new_tokens: int = 100,
    timeout: float = 120,
    max_workers: int = 8,
    display_pbar: bool = True,
):
    """
    Combine the prediction and accuracy calculation in one function.

    Args:
        mosaic_endpoint (str): The URL of the MosaicML model endpoint
        df (pd.DataFrame): The DataFrame containing the data to evaluate.
            The DataFrame must contain the prompt_column and label_column.
        metric_fn (Callable[..., bool]): The metric function to use for comparison.
            The function should take two arguments and return a boolean.
            Default is a function that checks for equality.
        prompt_column (str): The name of the column containing the prompts.
        label_column (str): The name of the column containing the true labels. Default is 'answer'.
        prediction_column (str): The name of the column to store the predictions. Default is 'prediction'.
        output_column (str): The name of the column to store the correctness. Default is 'correct'.
        max_new_tokens (int): The maximum number of tokens to generate. Default is 100.
        timeout (float): The timeout for the model request in seconds. Default is 120.
        max_workers (int): The maximum number of threads to use. Default is 8.
        display_pbar (bool): Whether to display a progress bar. Default is True.

    Returns:
        float: The accuracy
    """
    predict_with_mosaic_endpoint_multithreaded(
        df=df,
        mosaic_endpoint=mosaic_endpoint,
        prompt_column=prompt_column,
        prediction_column=prediction_column,
        max_workers=max_workers,
        max_new_tokens=max_new_tokens,
        timeout=timeout,
        display_pbar=display_pbar,
    )
    accuracy = mark_predictions_and_calculate_accuracy(
        df=df,
        metric_fn=metric_fn,
        label_column=label_column,
        prediction_column=prediction_column,
        output_column=output_column,
    )

    return accuracy


def convert_image_list_to_pickle_data(images: list[bytes]) -> bytes:
    """
    Convert a list of images as bytes to pickle data.

    Args:
        images (list[bytes]): The list of images as bytes

    Returns:
        bytes: The pickle data
    """
    return pickle.dumps(images)


def predict_with_mosaic_endpoint(
    mosaic_endpoint: str,
    prompt: str,
    image: bytes | None = None,
    images: list[bytes] | None = None,
    max_new_tokens: int = 100,
    timeout: float = 120,
):
    """
    Make a prediction using the model endpint served on MosaicML GPU cluster.

    Args:
        mosaic_endpoint (str): The URL of the MosaicML model endpoint
        prompt (str): The prompt to provide to the model
        image (bytes | None): The image to provide to the model.
            Only one of 'image' and 'images' can be provided. Default is None.
        images (list[bytes] | None): A list of images to provide to the model.
            Only one of 'image' and 'images' can be provided. Default is None.
        max_new_tokens (int): The maximum number of tokens to generate. Default is 100.
        timeout (float): The timeout for the request in seconds. Default is 120.

    Returns:
        str: The textual prediction from the model
    """
    if (image is None and images is None) or (image is not None and images is not None):
        raise ValueError("Exactly one of 'image' and 'images' must be provided")

    # create request data
    request_data = {
        "prompt": prompt,
        "max_new_tokens": max_new_tokens,
    }
    if image is not None:
        request_data["image"] = image_utils.convert_image_bytes_to_base64_str(
            image, "JPEG"
        )
    else:
        request_data["images"] = base64.b64encode(
            convert_image_list_to_pickle_data(images)
        ).decode("utf-8")

    response = requests.post(
        mosaic_endpoint,
        json=request_data,
        timeout=timeout,
    ).text

    # TODO: this is a makeshift way of finding the prediction in the response
    answer_breaker = prompt[-10:]
    prediction = response.split(answer_breaker)[-1].strip()

    return prediction


def predict_with_mosaic_endpoint_multithreaded(
    df: pd.DataFrame,
    mosaic_endpoint: str,
    prompt_column: str = "prompt",
    prediction_column: str = "prediction",
    max_workers: int = 8,
    max_new_tokens: int = 100,
    timeout: float = 120,
    display_pbar: bool = True,
) -> None:
    """
    Make predictions using the model endpoint served on MosaicML GPU cluster, in a
    multithreaded manner. The DataFrame provided is edited in place to add the predictions.

    Args:
        df (pd.DataFrame): The DataFrame containing the data to predict on.
            The DataFrame must contain exactly one of 'image' and 'images' column.
        mosaic_endpoint (str): The URL of the MosaicML model endpoint
        prompt_column (str): The name of the column containing the prompts.
            The DataFrame must contain this column. Default is 'prompt'.
        prediction_column (str): The name of the column to store the predictions.
            Default is 'prediction'.
        max_workers (int): The maximum number of threads to use. Default is 8.
        max_new_tokens (int): The maximum number of tokens to generate. Default is 100.
        timeout (float): The timeout for the request in seconds. Default is 120.
        display_pbar (bool): Whether to display a progress bar. Default is True.

    Returns:
        None

    Raises:
        ValueError: If the DataFrame contais neither or both 'image' and 'images' column
        AssertionError: If the DataFrame does not contain the prompt column specified
    """
    # The df must contain exactly one of 'image' and 'images' column and a 'prompt' column
    has_image_column = "image" in df.columns
    has_images_column = "images" in df.columns
    if (has_image_column and has_images_column) or (
        not has_image_column and not has_images_column
    ):
        raise ValueError(
            "Exactly one of 'image' and 'images' column must be present in the DataFrame"
        )
    assert (
        prompt_column in df.columns
    ), "DataFrame must contain a prompt column named {}".format(prompt_column)

    with tqdm(total=len(df), disable=(not display_pbar)) as pbar:
        with cf.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    predict_with_mosaic_endpoint,
                    mosaic_endpoint=mosaic_endpoint,
                    prompt=row[prompt_column],
                    image=row["image"] if has_image_column else None,
                    images=row["images"] if has_images_column else None,
                    max_new_tokens=max_new_tokens,
                    timeout=timeout,
                ): row
                for _, row in df.iterrows()
            }
            for future in cf.as_completed(futures):
                row = futures[future]
                try:
                    prediction = future.result()
                    df.loc[row.name, prediction_column] = prediction
                except Exception as e:
                    df.loc[row.name, prediction_column] = str(e)
                pbar.update(1)


def mark_predictions_and_calculate_accuracy(
    df: pd.DataFrame,
    metric_fn: Callable[[Any, Any], bool] = lambda x, y: x == y,
    label_column: str = "label",
    prediction_column: str = "prediction",
    output_column: str = "correct",
):
    """
    Mark the predictions in the DataFrame as correct or incorrect based on a metric function
    and calculate the accuracy.

    Args:
        df (pd.DataFrame): The DataFrame containing the data to evaluate.
            The provided label_column, prediction_column, and output_column must be present.
        metric_fn (Callable[..., bool]): The metric function to use for comparison.
            The function should take two arguments and return a boolean.
            Default is a function that checks for equality.
        label_column (str): The name of the column containing the true labels. Default is 'answer'.
        prediction_column (str): The name of the column containing the predictions. Default is 'prediction'.
        output_column (str): The name of the column to store the correctness. Default is 'correct'.

    Returns:
        float: The accuracy

    Raises:
        ValueError: If the DataFrame does not contain the specified columns
        ValueError: If the DataFrame already contains the output column
    """
    if (label_column not in df.columns) or (prediction_column not in df.columns):
        raise ValueError(
            "The DataFrame must contain the column '{}', and '{}'".format(
                label_column,
                prediction_column,
            )
        )
    if output_column in df.columns:
        raise ValueError(
            "The DataFrame already contains the column '{}'. Doing so will override this column".format(
                output_column
            )
        )

    df[output_column] = df.apply(
        lambda row: metric_fn(row[label_column], row[prediction_column]), axis=1
    ).astype(int)
    accuracy = df[output_column].mean()
    return accuracy


def extract_bbox_from_string(sentence: str) -> tuple[float, float, float, float] | None:
    """
    Extract the bounding box coordinates from a string and return them as a tuple of floats.

    Args:
        sentence (str): The string to search for bounding box coordinates

    Returns:
        Optional[tuple[float, float, float, float]]: The bounding box coordinates as a tuple of floats if found,
            else None
    """
    pattern = (
        r"\((\-?\d+\.?\d*),\s*(\-?\d+\.?\d*),\s*(\-?\d+\.?\d*),\s*(\-?\d+\.?\d*)\)"
    )

    # Search for the pattern in the string
    match = re.search(pattern, sentence)

    if match:
        # Extract the matched groups and convert them to float or int
        elements = []
        for i in range(1, 5):
            element = float(match.group(i))
            elements.append(element)
        return tuple(elements)
    else:
        return None  # Return None if no match is found
