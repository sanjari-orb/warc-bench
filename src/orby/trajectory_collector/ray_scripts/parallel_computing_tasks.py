"""
Remote function to generate a set of simple task data from a batch of raw data points.
"""

import time
import pandas as pd
import ray
import random
import hashlib
import traceback
from urllib.parse import urlparse
from tqdm import tqdm

from orby.trajectory_collector.ray_scripts.frequency_limiter import FrequencyLimiter
from orby.trajectory_collector.single_task_trajectory_collector import (
    SingleTaskTrajectoryCollector,
)
import orby.digitalagent.utils.s3_utils as s3_utils
from orby.digitalagent.utils import process_utils


TRAJECTORY_DATA_FINGERPRINT_LENGTH = 20


@ray.remote(num_cpus=1, max_retries=0)
def trajectory_collection_multiprocess_ray_task(
    input_data_df: pd.DataFrame,
    s3_save_bucket: str,
    s3_save_path: str,
    is_webarena_crawl: bool,
    frequency_limiter: FrequencyLimiter,
    max_steps: int = 10,
    agent_name: str = "basic",
    agent_model_provider: str = "openai",
    agent_model_name: str = "gpt-4o-2024-08-06",
    temperature: float = 0.0,
    max_tokens: int = 500,
    frequency_penalty: float = 1.0,
    max_repetitive_actions: int = 5,
    additional_model_kwargs: dict = {},
    additional_browserenv_kwargs: dict = {},
    dp_max_retries: int = 3,
    verbose: bool = False,
    timeout: float = 10 * 60,  # 10 minutes
) -> list[int]:
    """
    Using Ray, generate a set of data from a batch of raw data points.
    See `trajectory_collection_multiprocess` for more details.
    """
    return trajectory_collection_multiprocess(
        input_data_df=input_data_df,
        s3_save_bucket=s3_save_bucket,
        s3_save_path=s3_save_path,
        is_webarena_crawl=is_webarena_crawl,
        frequency_limiter=frequency_limiter,
        max_steps=max_steps,
        agent_name=agent_name,
        agent_model_provider=agent_model_provider,
        agent_model_name=agent_model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        frequency_penalty=frequency_penalty,
        max_repetitive_actions=max_repetitive_actions,
        additional_model_kwargs=additional_model_kwargs,
        additional_browserenv_kwargs=additional_browserenv_kwargs,
        dp_max_retries=dp_max_retries,
        verbose=verbose,
        timeout=timeout,
    )


def trajectory_collection_multiprocess(
    input_data_df: pd.DataFrame,
    s3_save_bucket: str,
    s3_save_path: str,
    is_webarena_crawl: bool,
    frequency_limiter: FrequencyLimiter,
    max_steps: int = 10,
    agent_name: str = "basic",
    agent_model_provider: str = "openai",
    agent_model_name: str = "gpt-4o-2024-08-06",
    temperature: float = 0.0,
    max_tokens: int = 500,
    frequency_penalty: float = 1.0,
    max_repetitive_actions: int = 5,
    dp_max_retries: int = 3,
    additional_model_kwargs: dict = {},
    additional_browserenv_kwargs: dict = {},
    verbose: bool = False,
    timeout: float = 10 * 60,  # 10 minutes
) -> list[int]:
    """
    Use one machine and multiprocessing to generate the data.

    Args:
        input_data_df (pd.DataFrame): A DataFrame of raw data points.
        s3_save_bucket (str): The S3 bucket to save the generated data.
        s3_save_path (str): The S3 path to save the generated data.
        is_webarena_crawl (bool): Is the crawl being done on webarena websites.
            Setting this will automatically take care of logging into these sites.
        frequency_limiter (FrequencyLimiter): A frequency limiter object to limit the number of requests.
            If None, no frequency limit is applied.
        max_steps (int): The maximum number of steps for each task.
        agent_name (str): The name of the agent to use for generating the task data.
        agent_model_name (str): The model name of the agent to use for generating the task data.
        temperature (float): The temperature for the agent model.
        max_tokens (int): The maximum number of tokens for the agent model.
        frequency_penalty (float): The frequency penalty for the agent model.
        max_repetitive_actions (int): The maximum number of repetitive actions allowed before truncating the task.
        dp_max_retries (int): The maximum number of retries for each raw data point.
        additional_model_kwargs (dict): Additional keyword arguments for the agent model.
        additional_browserenv_kwargs (dict): Additional keyword arguments for the browser environment.
        verbose (bool): Whether to print verbose logs.

    Returns:
        list[int]: A list of flags indicating whether the task generation is successful for each raw data point.
    """
    results = []
    for _, raw_data_row in tqdm(input_data_df.iterrows()):
        result = 0
        try:
            process_utils.run_with_timeout(
                trajectory_collection,
                timeout_seconds=timeout,
                input_data_row=raw_data_row,
                s3_save_bucket=s3_save_bucket,
                s3_save_path=s3_save_path,
                is_webarena_crawl=is_webarena_crawl,
                frequency_limiter=frequency_limiter,
                max_steps=max_steps,
                agent_name=agent_name,
                agent_model_provider=agent_model_provider,
                agent_model_name=agent_model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                frequency_penalty=frequency_penalty,
                max_repetitive_actions=max_repetitive_actions,
                dp_max_retries=dp_max_retries,
                additional_model_kwargs=additional_model_kwargs,
                additional_browserenv_kwargs=additional_browserenv_kwargs,
                verbose=verbose,
            )
            result = 1
        except TimeoutError as _:
            print("TimeoutError: Some tasks took too long, omitting them.")
        results.append(result)
    return results


def trajectory_collection(
    input_data_row: pd.Series,
    s3_save_bucket: str,
    s3_save_path: str,
    is_webarena_crawl: bool,
    frequency_limiter: FrequencyLimiter = None,
    max_steps: int = 10,
    agent_name: str = "basic",
    agent_model_provider: str = "openai",
    agent_model_name: str = "gpt-4o-2024-08-06",
    temperature: float = 0.0,
    max_tokens: int = 500,
    frequency_penalty: float = 0.0,
    max_repetitive_actions: int = 5,
    dp_max_retries: int = 3,
    additional_model_kwargs: dict = {},
    additional_browserenv_kwargs: dict = {},
    verbose: bool = False,
) -> int:
    """
    Generate a set of data from a batch of raw data points. Upload to s3.

    Args:
        input_data_row (pd.Series): A row of raw data point.
        s3_save_bucket (str): The S3 bucket to save the generated data.
        s3_save_path (str): The S3 path to save the generated data.
        is_webarena_crawl (bool): Is the crawl being done on webarena websites.
            Setting this will automatically take care of logging into these sites.
        frequency_limiter (FrequencyLimiter): A frequency limiter object to limit the number of requests.
            If None, no frequency limit is applied.
        max_steps (int): The maximum number of steps for each task.
        agent_name (str): The name of the agent to use for generating the task data.
        agent_model_name (str): The model name of the agent to use for generating the task data.
        temperature (float): The temperature for the agent model.
        max_tokens (int): The maximum number of tokens for the agent model.
        frequency_penalty (float): The frequency penalty for the agent model.
        max_repetitive_actions (int): The maximum number of repetitive actions allowed before truncating the task.
        dp_max_retries (int): The maximum number of retries for each raw data point.
        additional_model_kwargs (dict): Additional keyword arguments for the agent model.
        additional_browserenv_kwargs (dict): Additional keyword arguments for the browser environment.
        verbose (bool): Whether to print verbose logs.

    Returns:
        list[int]: A list of flags indicating whether the task generation is successful for each raw data point.
            1 indicates success, 0 indicates failure.
    """
    if frequency_limiter is not None:
        time.sleep(ray.get(frequency_limiter.wait_for.remote()))

    if "action_urls" not in input_data_row:
        print(input_data_row["base_url"])
        start_url = input_data_row["base_url"]
    else:
        parsed_url = urlparse(random.choice(input_data_row["action_urls"]))
        start_url = (
            ("https://" + input_data_row["base_url"])
            if not parsed_url.scheme
            else (parsed_url.scheme + "://" + parsed_url.netloc)
        )
    task_id = hashlib.sha256(
        (input_data_row["base_url"] + input_data_row["goal"]).encode()
    ).hexdigest()[:TRAJECTORY_DATA_FINGERPRINT_LENGTH]

    # if the task data already exists, skip
    if s3_utils.check_s3_file_exists(
        f"s3://{s3_save_bucket}/{s3_save_path}/{task_id}.pb"
    ) or s3_utils.check_s3_file_exists(
        f"s3://{s3_save_bucket}/{s3_save_path}/{task_id}.pb.xz"
    ):
        print(f"Task data already exists for task ID {task_id}. Skipping...")
        return 1

    replay_params = {}
    if agent_name.startswith("replay"):
        replay_params = {
            "replay_trajectory_proto": input_data_row["replay_trajectory_proto"],
            "replay_skip_last_steps": input_data_row["replay_skip_last_steps"],
        }

    task_collector = SingleTaskTrajectoryCollector(
        domain_name=input_data_row["base_url"],
        start_url=start_url,
        save_s3_bucket=s3_save_bucket,
        save_s3_path=s3_save_path,
        is_webarena_crawl=is_webarena_crawl,
        agent_name=agent_name,
        goal_string=input_data_row["goal"],
        max_steps=max_steps,
        context=input_data_row.get("context", ""),
        task_id=task_id,
        temperature=temperature,
        max_tokens=max_tokens,
        frequency_penalty=frequency_penalty,
        agent_model_provider=agent_model_provider,
        agent_model_name=agent_model_name,
        max_repetitive_actions=max_repetitive_actions,
        additional_model_kwargs=additional_model_kwargs,
        additional_browserenv_kwargs=additional_browserenv_kwargs,
        verbose=verbose,
        replay_params=replay_params,
    )

    # Try running multiple times if necessary
    no_error = False
    for i in range(dp_max_retries):
        try:
            task_collector.run()
            no_error = True
        except Exception as e:
            print(f"Try {i+1} failed. Error in generating task data: {e}")
            continue

        if frequency_limiter is not None:
            frequency_limiter.update.remote()
        break

    # Try to upload any data collected to S3
    task_collector.upload_trajectory_data()

    return int(no_error)
