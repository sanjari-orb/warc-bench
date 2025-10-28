"""
Evaluate the single-step success rate of an executor agnet, by the definition of HSM v3.
WARNING:
- Results may not be directly comparable, as different model may use different action hint and thus grounding method.
- Results can fluctuate, especially action description ROUGE F1. Mutliple run is adviced during actual usage.
"""

from typing import Any, Type
from tqdm import tqdm
import ast
import concurrent.futures as cf
import copy
import dataclasses
import pandas as pd
import numpy as np

from orby.protos.fm.action_data_pb2 import WebState
from orby.digitalagent.agent import Agent
import orby.digitalagent.utils.dom_utils as dom_utils
import orby.digitalagent.utils.action_grounding_utils as ag_utils
import orby.digitalagent.utils.action_parsing_utils as ap_utils
import orby.digitalagent.utils.image_utils as image_utils


@dataclasses.dataclass
class ExecutorOutput:
    """
    A class to store the dissected output of an executor agent.
    """

    browsergym_action_info: ap_utils.BrowserGymActionInfo
    action_description: str | None = None


@dataclasses.dataclass
class ExecutorEvaluationStatistics:
    """
    A class to store the evaluation statistics of an executor agent.
    """

    n: int

    action_accuracy: float
    n_correct_actions: int

    value_accuracy: float
    n_correct_values: int
    n_all_values: int

    action_description_average_rouge_score: float

    element_accuracy: float | None = None
    n_correct_elements: int | None = None
    n_all_elements: int | None = None

    bid_accuracy: float | None = None
    n_correct_bids: int | None = None
    n_all_bids: int | None = None

    coordinate_within_bbox_accuracy: float | None = None
    n_correct_coordinates: int | None = None
    n_all_coordinates: int | None = None


def evaluate_executor(
    model_configs: dict[str, Any],
    executor_cls: Type[Agent],
    dataset: str | pd.DataFrame | list[str] | list[pd.DataFrame],
    num_runs: int = 1,
    output_dir: str | None = None,
    max_workers: int | None = -1,
    additional_executor_class_kwargs: dict[str, Any] = {},
    additional_executor_act_kwargs: dict[str, Any] = {},
    display_pbar: bool = True,
    verbose: bool = True,
) -> tuple[list[pd.DataFrame], list[ExecutorEvaluationStatistics]]:
    """
    Evaluate a provided model and executor agent on a list of single-step success rate datasets.
    WARNING:
    - Results may not be directly comparable, as different model may use different action hint and thus grounding method.
    - Results can fluctuate, especially action description ROUGE F1. Mutliple run is adviced during actual usage.

    Args:
        model_configs (dict[str, typing.Any]): A dictionary containing the model configuration to use for evaluation.
        executor_cls (typing.Type[Agent]): The executor agent class to use for evaluation.
        dataset (str | pd.DataFrame | list[str] | list[pd.DataFrame]): The dataset(s) to evaluate on.
            If a string, it must be the path to one parquet file. The dataset will be loaded from the specified path.
            If a DataFrame, it will be used as is.
            If a list of strings, each string must be the path to one parquet file. The datasets will be loaded from the specified paths.
            If a list of DataFrames, each DataFrame will be used as is.
        num_runs (int, optional): The number of times to run the evaluation. Defaults to 1.
        output_dir (str | None, optional): The directory to save the evaluation results as a parquet file.
            If None, the results will not be saved.
            Defaults to None.
        max_workers (int | None, optional): The maximum number of workers to use for evaluation.
            If None or < 0, the number of workers will be set to the minimum between the number of CPU cores and 32.
            Defaults to -1.
        display_pbar (bool, optional): Whether to display a progress bar. Defaults to True.

    Returns:
        list[pd.DataFrame]: A list of DataFrames containing the evaluation results.
        list[ExecutorEvaluationStatistics]: A list containing the evaluation statistics.
    """
    max_workers = max_workers if max_workers and max_workers > 0 else None
    # datasets are deepcopied
    datasets = _prepare_datasets(dataset)

    output_datasets = []
    output_statistics = []

    counter = 0
    for _ in range(num_runs):
        for _, dataset in enumerate(datasets):
            dataset = copy.deepcopy(dataset)
            with tqdm(total=len(dataset), disable=not display_pbar) as pbar:
                with cf.ThreadPoolExecutor(max_workers=max_workers) as thread:
                    futures = {
                        thread.submit(
                            run_executor_on_single_dp,
                            executor_cls=executor_cls,
                            model_configs=model_configs,
                            goal=dataset.loc[row.name, "goal"],
                            action_hints=dataset.loc[row.name, "action_hints"],
                            web_state_bytes=dataset.loc[row.name, "web_state"],
                            strict_action_format=dataset.loc[row.name, "strict"],
                            additional_executor_class_kwargs=additional_executor_class_kwargs,
                            additional_executor_act_kwargs=additional_executor_act_kwargs,
                        ): row
                        for _, row in dataset.iterrows()
                    }
                    for future in cf.as_completed(futures):
                        row = futures[future]
                        try:
                            result = future.result()
                            dataset.loc[row.name, "predicted_action"] = (
                                result.browsergym_action_info.action_type
                            )
                            dataset.loc[row.name, "predicted_bids"] = (
                                str(result.browsergym_action_info.bids)
                                if result.browsergym_action_info.bids is not None
                                else None
                            )
                            dataset.loc[row.name, "predicted_coordinates"] = (
                                str(result.browsergym_action_info.absolute_coordinates)
                                if result.browsergym_action_info.absolute_coordinates
                                is not None
                                else None
                            )
                            dataset.loc[row.name, "predicted_value"] = str(
                                result.browsergym_action_info.value
                            )
                            dataset.loc[row.name, "predicted_action_description"] = (
                                result.action_description
                            )
                            dataset.loc[row.name, "error"] = None
                        except Exception as e:
                            dataset.loc[row.name, "predicted_action"] = None
                            dataset.loc[row.name, "predicted_bids"] = None
                            dataset.loc[row.name, "predicted_coordinates"] = None
                            dataset.loc[row.name, "predicted_value"] = None
                            dataset.loc[row.name, "predicted_action_description"] = None
                            dataset.loc[row.name, "error"] = str(e)
                        pbar.update(1)

            if output_dir:
                dataset.to_parquet(
                    output_dir
                    + ("" if output_dir[-1] == "/" else "/")
                    + f"evaluation_result_{counter}.parquet"
                )

            statistics = _calculate_statistics(dataset)
            if verbose:
                print("Evaluation Statistics:")
                print(
                    "- Action Accuracy: {}, ({}/{})".format(
                        statistics.action_accuracy,
                        statistics.n_correct_actions,
                        statistics.n,
                    )
                )
                print(
                    "- Element Accuracy: {}, ({}/{})".format(
                        statistics.element_accuracy,
                        statistics.n_correct_elements,
                        statistics.n_all_elements,
                    )
                )
                print(
                    "- Bid Accuracy: {}, ({}/{})".format(
                        statistics.bid_accuracy,
                        statistics.n_correct_bids,
                        statistics.n_all_bids,
                    )
                )
                print(
                    "- Coordinate Within Bounding Box Accuracy: {}, ({}/{})".format(
                        statistics.coordinate_within_bbox_accuracy,
                        statistics.n_correct_coordinates,
                        statistics.n_all_coordinates,
                    )
                )
                print(
                    "- Value Accuracy: {}, ({}/{})".format(
                        statistics.value_accuracy,
                        statistics.n_correct_values,
                        statistics.n_all_values,
                    )
                )
                print(
                    "- Action Description Average ROUGE Score: {} ({})".format(
                        statistics.action_description_average_rouge_score, statistics.n
                    )
                )

            output_datasets.append(dataset)
            output_statistics.append(statistics)

            counter += 1

    return output_datasets, output_statistics


def run_executor_on_single_dp(
    executor_cls: Type[Agent],
    model_configs: dict[str, Any],
    goal: str,
    action_hints: str,
    web_state_bytes: bytes,
    strict_action_format: bool = False,
    additional_executor_class_kwargs: dict[str, Any] = {},
    additional_executor_act_kwargs: dict[str, Any] = {},
) -> ExecutorOutput:
    """
    Run an executor agent on a single SSSR dataset point.

    Args:
        executor_cls (typing.Type[Agent]): The executor agent class to use for evaluation.
        model_configs (dict[str, typing.Any]): A dictionary containing the model configuration to use for evaluation.
        goal (str): The goal of the dataset point.
        action_hints (str): The action hints of the dataset point.
        web_state_bytes (bytes): The web state of the dataset point.
        strict_action_format (bool, optional): Whether to enforce strict action format. Defaults to False.

    Returns:
        ExecutorOutput: The output of the executor agent.
    """
    # Get observations from the web state
    web_state = WebState.FromString(web_state_bytes)
    html_str = dom_utils.html_to_string(web_state.root_element)
    screenshot_array = image_utils.convert_image_bytes_to_numpy(
        web_state.viewport.screenshot.content
    )

    # Create and run the executor agent
    executor = executor_cls(
        model_configs=model_configs,
        actions=action_hints,
        **additional_executor_class_kwargs,
    )
    executor.reset(goal, html_str, screenshot_array)
    action, action_description = executor.act(**additional_executor_act_kwargs)
    if not isinstance(action_description, str):
        action_description = None

    if not action:
        # If the agent returns an empty action, we assume it failed
        raise ValueError("The agent returned an empty action")

    # Extract the output of the executor agent
    browsergym_action_info = ap_utils.extract_info_from_browsergym_action(action)

    # If strict action output is not enforced, we fill in the coordinates if they are missing
    if (
        not strict_action_format
        and browsergym_action_info.bids is not None
        and browsergym_action_info.absolute_coordinates is None
    ):
        browsergym_action_info = fill_in_coordinates(browsergym_action_info, web_state)

    return ExecutorOutput(
        browsergym_action_info=browsergym_action_info,
        action_description=action_description,
    )


def fill_in_coordinates(
    browsergym_action_info: ap_utils.BrowserGymActionInfo, web_state: WebState
) -> ap_utils.BrowserGymActionInfo:
    """
    Find the absolute coordinates of the elements with the given bids.

    Args:
        browsergym_action_info (ap_utils.BrowserGymActionInfo): The action info to fill in the coordinates for.
        web_state (fm.action_data_pb2.WebState): The web state to search for the elements in.

    Returns:
        ap_utils.BrowserGymActionInfo: The action info with the coordinates filled in.
    """
    browsergym_action_info.absolute_coordinates = []
    for bid in browsergym_action_info.bids:
        element = dom_utils.find_element_by_bid(web_state.root_element, bid)
        if element is not None:
            center_point = (
                element.bounding_box.x + element.bounding_box.width / 2,
                element.bounding_box.y + element.bounding_box.height / 2,
            )
            browsergym_action_info.absolute_coordinates.append(center_point)
        else:
            # We put some faith in the annotation and assume that the reason we can't find the element
            # is because it is recorded with bid in the node.id field, instead of as an attribute
            element = dom_utils.find_element_by_bid(
                web_state.root_element, bid, bid_location="id"
            )
            if element is not None:
                center_point = (
                    element.bounding_box.x + element.bounding_box.width / 2,
                    element.bounding_box.y + element.bounding_box.height / 2,
                )
                browsergym_action_info.absolute_coordinates.append(center_point)
    if browsergym_action_info.absolute_coordinates == []:
        # We couldn't find any element with the given bids
        # We set the coordinates to (-1, -1) to indicate this
        browsergym_action_info.absolute_coordinates.append((-1, -1))

    return browsergym_action_info


def _calculate_statistics(dataset: pd.DataFrame) -> ExecutorEvaluationStatistics:
    # Calculate action accuracy
    num_correct_actions = 0
    for _, row in dataset.iterrows():
        predicted_action = row["predicted_action"]
        alternative_predicted_action = ""
        if not row["strict"]:
            alternative_predicted_action = ap_utils.get_alternative_action(
                predicted_action
            )
        if (
            row["action_type"] == predicted_action
            or row["action_type"] == alternative_predicted_action
        ):
            num_correct_actions += 1
    action_accuracy = num_correct_actions / len(dataset)

    # Calculate element accuracy
    num_correct_bid_elements = 0
    num_all_bid_elements = 0
    num_correct_coordinate_elements = 0
    num_all_coordinate_elements = 0
    for _, row in dataset.iterrows():
        # There is a special case where the GT does not contain any element
        # specification, which means that if the prediction contains any
        # element specification, it is incorrect.
        if row["bids"] is None and row["bboxes"] is None:
            if (
                row["predicted_bids"] is not None
                or row["predicted_coordinates"] is not None
            ):
                # We prioritize the bid specification over the coordinate specification
                num_all_bid_elements += 1
        else:
            if row["strict"]:
                # If we are enforcing strict element format, we prioritize the
                # bid specification over the coordinate specification.
                # We assume there are only 2 situations:
                # 1. The GT contains only bbox
                # 2. The GT contains only bids at first, and we filled in the
                #    bbox for the GT previously
                if row["bids"] is not None:
                    num_all_bid_elements += 1
                    if _correct_bids(row):
                        num_correct_bid_elements += 1
                elif row["bboxes"] is not None:
                    num_all_coordinate_elements += 1
                    if _correct_coordinates(row):
                        num_correct_coordinate_elements += 1
            else:
                # If we are not enforcing strict element format, we mark either
                # one type of element specification as correct if the GT exist
                # and the prediction is correct.
                if _correct_bids(row):
                    num_all_bid_elements += 1
                    num_correct_bid_elements += 1
                elif _correct_coordinates(row):
                    num_all_coordinate_elements += 1
                    num_correct_coordinate_elements += 1
                else:
                    num_all_bid_elements += 1

    if num_all_bid_elements > 0:
        bid_accuracy = num_correct_bid_elements / num_all_bid_elements
    else:
        bid_accuracy = None
    if num_all_coordinate_elements > 0:
        coordinate_within_bbox_accuracy = (
            num_correct_coordinate_elements / num_all_coordinate_elements
        )
    else:
        coordinate_within_bbox_accuracy = None
    if num_all_bid_elements + num_all_coordinate_elements > 0:
        element_accuracy = (
            num_correct_bid_elements + num_correct_coordinate_elements
        ) / (num_all_bid_elements + num_all_coordinate_elements)
    else:
        element_accuracy = None

    # Calculate value accuracy
    num_correct_values = 0
    num_actions_with_values = 0
    for _, row in dataset.iterrows():
        if row["value"] is not None:
            num_actions_with_values += 1

            if (
                row["predicted_value"] is None
                or row["predicted_value"] == "None"
                or row["predicted_value"] == ""
            ):
                continue
            predicted_value = str(ast.literal_eval(row["predicted_value"])[0])
            if (
                row["value"].replace(" ", "").strip().lower()
                == predicted_value.replace(" ", "").strip().lower()
            ):
                num_correct_values += 1
    if num_actions_with_values > 0:
        value_accuracy = num_correct_values / num_actions_with_values
    else:
        value_accuracy = None

    # Calculate action description ROUGE score
    action_description_average_rouge_score = dataset.apply(
        lambda row: ag_utils.rouge_1_f1_metric(
            row["predicted_action_description"], row["action_description"]
        ),
        axis=1,
    ).sum() / len(dataset)

    return ExecutorEvaluationStatistics(
        n=len(dataset),
        action_accuracy=action_accuracy,
        n_correct_actions=num_correct_actions,
        element_accuracy=element_accuracy,
        n_correct_elements=num_correct_bid_elements + num_correct_coordinate_elements,
        n_all_elements=num_all_bid_elements + num_all_coordinate_elements,
        bid_accuracy=bid_accuracy,
        n_correct_bids=num_correct_bid_elements,
        n_all_bids=num_all_bid_elements,
        coordinate_within_bbox_accuracy=coordinate_within_bbox_accuracy,
        n_correct_coordinates=num_correct_coordinate_elements,
        n_all_coordinates=num_all_coordinate_elements,
        value_accuracy=value_accuracy,
        n_correct_values=num_correct_values,
        n_all_values=num_actions_with_values,
        action_description_average_rouge_score=action_description_average_rouge_score,
    )


def _correct_bids(row: pd.Series) -> bool:
    """
    Check if the predicted bids are correct.
    """
    # If both the GT and the prediction are None, we consider it correct
    if row["bids"] is None and row["predicted_bids"] is None:
        return True
    # If one of the GT or the prediction is None, the prediction must be incorrect
    if row["bids"] is None or row["predicted_bids"] is None:
        return False

    bids = ast.literal_eval(row["bids"])
    predicted_bids = ast.literal_eval(row["predicted_bids"])

    # If the number of predicted bids is different from the number of GT bids, something is wrong
    if len(bids) != len(predicted_bids):
        return False

    for bid, predicted_bid in zip(bids, predicted_bids):
        # We convert each bid to a list of options and check if the predicted bid is in the options
        if not isinstance(bid, list):
            bid = [bid]
        if predicted_bid not in bid:
            return False

    return True


def _correct_coordinates(row: pd.Series) -> bool:
    """
    Check if the predicted coordinates are correct.
    """
    if row["bboxes"] is None and row["predicted_coordinates"] is None:
        return True
    if row["bboxes"] is None or row["predicted_coordinates"] is None:
        return False

    bboxes = ast.literal_eval(row["bboxes"])
    predicted_coordinates = ast.literal_eval(row["predicted_coordinates"])
    # If the number of predicted coordinates is different from the number of
    # GT bounding boxes, we consider it incorrect
    if len(bboxes) != len(predicted_coordinates):
        return False

    for bbox, predicted_coordinate in zip(bboxes, predicted_coordinates):
        # Convert each bbox to a list of options and check if the predicted coordinate is
        # in any one of the options
        if not isinstance(bbox[0], list):
            bbox = [bbox]
        any_correct = any(
            [
                ag_utils.within_bbox_metric(
                    bbox_option, predicted_coordinate, bbox_format="xywh"
                )
                for bbox_option in bbox
            ]
        )
        if not any_correct:
            return False
    return True


def _prepare_datasets(
    dataset: str | pd.DataFrame | list[str] | list[pd.DataFrame],
) -> list[pd.DataFrame]:
    """
    Create a list of datasets from the provided dataset(s).

    Args:
        dataset (str | pd.DataFrame | list[str] | list[pd.DataFrame]): The dataset(s) to create.
            If a string, it must be the path to one parquet file. The dataset will be loaded from the specified path.
            If a DataFrame, it will be deepcopied and used as is.
            If a list of strings, each string must be the path to one parquet file. The datasets will be loaded from the specified paths.
            If a list of DataFrames, each DataFrame will be deepcopied and used as is.

    Returns:
        list[pd.DataFrame]: A list of datasets.
    """
    # Get the dataset into the correct format
    datasets = []
    if isinstance(dataset, str):
        dataset = pd.read_parquet(dataset)
        datasets.append(dataset)
    elif isinstance(dataset, pd.DataFrame):
        datasets.append(dataset)
    elif isinstance(dataset, list):
        for d in dataset:
            if isinstance(d, str):
                datasets.append(pd.read_parquet(d))
            elif isinstance(d, pd.DataFrame):
                datasets.append(d)
    else:
        raise ValueError(
            "dataset must be a string, a DataFrame, or a list of strings or DataFrames"
        )

    # Preemtively replace all values that represent None with None
    for dataset in datasets:
        dataset.replace(r"(?i)^(nan|none)$", None, regex=True, inplace=True)
        dataset.replace(np.nan, None, inplace=True)

    # if any web_state is a string, convert it to bytes
    for dataset in datasets:
        for i, row in dataset.iterrows():
            if isinstance(row["web_state"], str):
                dataset.loc[i, "web_state"] = ast.literal_eval(row["web_state"])

    # Fill in the bounding box of each ground truth element if it is missing
    for dataset in datasets:
        for i, row in dataset.iterrows():
            # Sometimes row["bboxes"] or row["bid"] is a numpy nd.array
            # We need to convert it to a string
            if isinstance(row["bboxes"], np.ndarray):
                dataset.loc[i, "bboxes"] = (
                    str(row["bboxes"]).replace("array(", "").replace(")", "")
                )
            if isinstance(row["bids"], np.ndarray):
                dataset.loc[i, "bids"] = (
                    str(row["bids"]).replace("array(", "").replace(")", "")
                )

            if not row["strict"] and row["bboxes"] is None and row["bids"] is not None:
                # We only do this conversion if we do not require strict action format
                # and the bounding box is missing but the bids are present
                bboxes = []
                for bid in ast.literal_eval(row["bids"]):
                    ws = WebState.FromString(row["web_state"])
                    # It is possible that each bid is a list of multiple valid bids
                    # In this case we also create a list of valid bounding boxes
                    if isinstance(bid, list):
                        bbox_options = []
                        for b in bid:
                            bbox = _find_bbox_of_bid(b, ws)
                            if bbox is not None:
                                bbox_options.append(bbox)
                        if bbox_options:
                            bboxes.append(bbox_options)
                    else:
                        bbox = _find_bbox_of_bid(bid, ws)
                        if bbox is not None:
                            bboxes.append(bbox)
                if bboxes:
                    dataset.loc[i, "bboxes"] = str(bboxes)
                else:
                    # If we couldn't find the bounding box of any bid
                    # we have no choice but to set strict to True
                    dataset.loc[i, "strict"] = True

    return datasets


def _find_bbox_of_bid(bid: str, ws: WebState) -> list[int] | None:
    """
    Find the bounding box of the element with the given bid.

    Args:
        bid (str): The bid of the element.
        ws (fm.action_data_pb2.WebState): The web state to search for the element in.

    Returns:
        list[int] | None: The bounding box of the element, or None if the element is not found.
    """
    element = dom_utils.find_element_by_bid(ws.root_element, bid)
    if element is not None:
        return [
            element.bounding_box.x,
            element.bounding_box.y,
            element.bounding_box.width,
            element.bounding_box.height,
        ]
    else:
        # We put some faith in the annotation and assume that the reason we can't find the element
        # is because it is recorded with bid in the node.id field, instead of as an attribute
        element = dom_utils.find_element_by_bid(ws.root_element, bid, bid_location="id")
        if element is not None:
            return [
                element.bounding_box.x,
                element.bounding_box.y,
                element.bounding_box.width,
                element.bounding_box.height,
            ]
    return None
