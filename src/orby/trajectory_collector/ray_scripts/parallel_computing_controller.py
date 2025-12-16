"""
Entry point for generating data with Ray cluster.
"""

import argparse
import boto3
import dotenv
import os
import ray
import time
import pandas as pd
from tqdm import tqdm

from orby.trajectory_collector.ray_scripts.frequency_limiter import FrequencyLimiter
from orby.trajectory_collector.ray_scripts.parallel_computing_tasks import (
    trajectory_collection,
    trajectory_collection_multiprocess,
    trajectory_collection_multiprocess_ray_task,
)

dotenv.load_dotenv()


class ParallelComputingController:
    def __init__(
        self,
        source_parquet_path: str,
        s3_save_uri: str,
        is_webarena_crawl: bool,
        num_raw_data: int | None = None,
        data_per_batch: int = 16,
        request_per_minute: int = 100,
        max_steps: int = 10,
        agent_name: str = "basic",
        agent_model_provider: str = "openai",
        agent_model_name: str = "gpt-4o-2024-08-06",
        temperature: float = 0.0,
        max_tokens: int = 500,
        max_repetitive_actions: int = 5,
        dp_max_retries: int = 3,
        additional_model_kwargs: dict = {},
        additional_browserenv_kwargs: dict = {},
        timeout: int = None,
        verbose: bool = False,
    ):
        """
        Initialize the Ray remote tasks for generating trajectories.

        Args:
            source_parquet_path (str): The path to the local file or a s3 path containing the raw data.
            s3_save_uri (str): The S3 uri to save the generated data.
            num_raw_data (int, optional): The number of raw data points to generate. Defaults to None.
            is_webarena_crawl (bool): Is the crawl being done on webarena
                websites. Setting this will automatically take care of logging into these sites.
            data_per_batch (int, optional): The number of raw data points to multi-process in each ray task. Defaults to 16.
            request_per_minute (int, optional): The number of requests allowed per minute. If None, no limit is applied.
                Defaults to 100.
            max_steps (int, optional): The maximum number of steps to attempt for each trajectory. Defaults to 10.
            agent_name (str, optional): The name of the agent to use for generating the task data. Defaults to "basic".
            agent_model_provider (str, optional): The model provider of the agent to use for generating the task data. Defaults to "openai".
            agent_model_name (str, optional): The model name of the agent to use for generating the task data. Defaults to "gpt-4o-2024-08-06".
            temperature (float, optional): The temperature for the agent model. Defaults to 0.0.
            max_tokens (int, optional): The maximum number of tokens for the agent model. Defaults to 500.
            max_repetitive_actions (int, optional): The maximum number of repetitive actions allowed before truncating the task. Defaults to 5.
            dp_max_retries (int, optional): The maximum number of retries for each raw data point. Defaults to 3.
            additional_model_kwargs (dict, optional): Additional keyword arguments for the agent model. Defaults to {}.
            additional_browserenv_kwargs (dict, optional): Additional keyword arguments for the browser environment. Defaults to {}.
            timeout (int, optional): The timeout for the data generation tasks. Defaults to None.
            verbose (bool, optional): Whether to print verbose logs. Defaults to False.
        """
        self.source_parquet_path = source_parquet_path
        self.s3_save_bucket, self.s3_save_path = (
            self._convert_s3_uri_to_bucket_and_path(s3_save_uri)
        )
        self.num_raw_data = num_raw_data
        self.data_per_batch = data_per_batch
        self.max_steps = max_steps
        self.agent_name = agent_name
        self.agent_model_provider = agent_model_provider
        self.agent_model_name = agent_model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_repetitive_actions = max_repetitive_actions
        self.dp_max_retries = dp_max_retries
        self.additional_model_kwargs = additional_model_kwargs
        self.additional_browserenv_kwargs = additional_browserenv_kwargs
        self.timeout = timeout
        self.verbose = verbose
        self.is_webarena_crawl = is_webarena_crawl

        # The list of task refs that are currently running
        self.running_task_refs = []
        # The raw data of webpages and actions
        self.raw_dataset = self._get_raw_data()
        # The frequency limiter for the data generation tasks
        if request_per_minute is None:
            self.frequency_limiter = None
        else:
            self.frequency_limiter = FrequencyLimiter.remote(
                request_limit=request_per_minute,
                time_window_sec=60,
            )

        self._print_if_verbose(
            """\
ParallelComputingController is created with
    source_parquet_path: {},
    s3_save_uri: {},
    request_per_minute: {},
    num_raw_data: {},
    max_steps: {},
    agent_name: {},
    agent_model_provider: {},
    agent_model_name: {},
    temperature: {},
    max_tokens: {},
    max_repetitive_actions: {},
    dp_max_retries: {},
    additional_model_kwargs: {},
    additional_browserenv_kwargs: {},
    timeout: {},
    verbose: {}
""".format(
                source_parquet_path,
                s3_save_uri,
                request_per_minute,
                num_raw_data,
                max_steps,
                agent_name,
                agent_model_provider,
                agent_model_name,
                temperature,
                max_tokens,
                max_repetitive_actions,
                dp_max_retries,
                additional_model_kwargs,
                additional_browserenv_kwargs,
                timeout,
                verbose,
            )
        )

    def start(self, multiprocess: bool | str = False) -> list[int]:
        """
        Start the data generation process.

        Args:
            multiprocess (bool | str): Whether to use multiprocessing.
                If "ray", use Ray to generate the data.
                If "local" or True, use the local machine to generate the data.
                If False, generate the data without multiprocessing.

        Returns:
            list[int]: 1 if the particular data generation task is successful, 0 otherwise
        """
        self._print_if_verbose("Starting the data generation tasks...")
        if multiprocess == "ray":
            results = self._start_with_ray()
        elif multiprocess == "local" or multiprocess == True:
            results = self._start_with_multiprocess()
        else:
            results = self._start_with_singleprocess()
        print("Data generation is done.")
        return results

    def _start_with_singleprocess(self) -> list[int]:
        """
        Generate the data without multiprocessing.

        Returns:
            list[int]: 1 if the particular data generation task is successful, 0 otherwise
        """
        results = []
        with tqdm(total=len(self.raw_dataset), disable=self.verbose) as pbar:
            for _, raw_data_row in self.raw_dataset.iterrows():
                result = trajectory_collection(
                    input_data_row=raw_data_row,
                    s3_save_bucket=self.s3_save_bucket,
                    s3_save_path=self.s3_save_path,
                    is_webarena_crawl=self.is_webarena_crawl,
                    frequency_limiter=self.frequency_limiter,
                    max_steps=self.max_steps,
                    agent_name=self.agent_name,
                    agent_model_provider=self.agent_model_provider,
                    agent_model_name=self.agent_model_name,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    max_repetitive_actions=self.max_repetitive_actions,
                    dp_max_retries=self.dp_max_retries,
                    additional_model_kwargs=self.additional_model_kwargs,
                    additional_browserenv_kwargs=self.additional_browserenv_kwargs,
                    verbose=self.verbose,
                )
                results.append(result)
                pbar.update(1)

        return results

    def _start_with_multiprocess(self) -> list[int]:
        """
        Use the local machine and multiprocessing to generate the data.

        Returns:
            list[int]: 1 if the particular data generation task is successful, 0 otherwise
        """
        if self.num_raw_data is not None and self.num_raw_data < len(self.raw_dataset):
            self.raw_dataset = self.raw_dataset.iloc[: self.num_raw_data]

        results = []
        # Due to playwright memory leak and python multiprocessing behavior (releases resources
        # only when all processes are done), we have to batch iterate the raw data and do
        # multiprocessing for each batch.
        for _, batch in tqdm(
            self.raw_dataset.groupby(self.raw_dataset.index // self.data_per_batch),
            disable=self.verbose,
        ):
            batch_results = trajectory_collection_multiprocess(
                input_data_df=batch,
                s3_save_bucket=self.s3_save_bucket,
                s3_save_path=self.s3_save_path,
                is_webarena_crawl=self.is_webarena_crawl,
                frequency_limiter=self.frequency_limiter,
                max_steps=self.max_steps,
                agent_name=self.agent_name,
                agent_model_provider=self.agent_model_provider,
                agent_model_name=self.agent_model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                max_repetitive_actions=self.max_repetitive_actions,
                dp_max_retries=self.dp_max_retries,
                additional_model_kwargs=self.additional_model_kwargs,
                additional_browserenv_kwargs=self.additional_browserenv_kwargs,
                verbose=self.verbose,
            )
            results.extend(batch_results)

        return results

    def _start_with_ray(self) -> list[int]:
        """
        Schedule the data generation tasks.

        Returns:
            list[int]: 1 if the particular data generation task is successful, 0 otherwise
        """
        if self.num_raw_data is not None and self.num_raw_data < len(self.raw_dataset):
            self.raw_dataset = self.raw_dataset.iloc[: self.num_raw_data]

        # Due to playwright memory leak and python multiprocessing behavior (releases resources
        # only when all processes are done), we have to batch iterate the raw data and do
        # multiprocessing for each batch.
        for _, batch in tqdm(
            self.raw_dataset.groupby(self.raw_dataset.index // self.data_per_batch),
            disable=self.verbose,
        ):
            task_ref = trajectory_collection_multiprocess_ray_task.remote(
                input_data_df=batch,
                s3_save_bucket=self.s3_save_bucket,
                s3_save_path=self.s3_save_path,
                is_webarena_crawl=self.is_webarena_crawl,
                frequency_limiter=self.frequency_limiter,
                max_steps=self.max_steps,
                agent_name=self.agent_name,
                agent_model_provider=self.agent_model_provider,
                agent_model_name=self.agent_model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                max_repetitive_actions=self.max_repetitive_actions,
                dp_max_retries=self.dp_max_retries,
                additional_model_kwargs=self.additional_model_kwargs,
                additional_browserenv_kwargs=self.additional_browserenv_kwargs,
                verbose=self.verbose,
                timeout=self.timeout,
            )
            self.running_task_refs.append(task_ref)

        # Wait for all the tasks to finish
        task_results = ray.get(self.running_task_refs)
        results = [
            dp_result for task_result in task_results for dp_result in task_result
        ]
        return results

    def _get_raw_data(self) -> pd.DataFrame:
        """
        Using the path to the local file or a s3 path, get the raw action data.
        """
        self._print_if_verbose(
            "Reading the list of data paths at {}...".format(self.source_parquet_path)
        )
        raw_dataset = pd.read_parquet(self.source_parquet_path)
        self._print_if_verbose("Dataset has {} rows".format(raw_dataset.count()))
        return raw_dataset

    def _print_if_verbose(self, *args, **kwargs) -> None:
        """
        Verbose print wrapper.
        """
        try:
            if self.verbose:
                print(*args, **kwargs)
        except Exception as e:
            # This should never happen
            raise ValueError("Illegal print arguments with error: {}".format(e))

    def _convert_s3_uri_to_bucket_and_path(self, s3_uri: str) -> tuple[str, str]:
        """
        Convert the S3 uri to the bucket and path.

        Args:
            s3_uri (str): The S3 uri.

        Returns:
            tuple[str, str]: The bucket and path.
        """
        s3_uri = s3_uri.strip().strip("/")
        s3_uri = s3_uri.replace("s3://", "")
        bucket, path = s3_uri.split("/", 1)
        return bucket, path


def download_orbot_extension_from_s3(s3_uri: str) -> None:
    """
    Download the orbot extension from the S3 uri.

    Args:
        s3_uri (str): The S3 uri.
    """
    s3 = boto3.client("s3")
    local_dir = os.environ["ORBY_EXTENSION_PATH"]

    s3_uri = s3_uri.strip("s3://")
    bucket_name, s3_folder = s3_uri.split("/", 1)

    # Ensure the local directory exists
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)

    # List objects within the specified S3 folder
    for obj in s3.list_objects_v2(Bucket=bucket_name, Prefix=s3_folder)["Contents"]:
        # Get the path of the S3 object and the local path to download
        s3_file_path = obj["Key"]
        local_file_path = os.path.join(
            local_dir, os.path.relpath(s3_file_path, s3_folder)
        )
        # Create any local subdirectories if they do not exist
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
        # Download the file
        s3.download_file(bucket_name, s3_file_path, local_file_path)

    print(f"Downloaded the orbot extension from {s3_uri} to {local_dir}")


def main(args):
    print("START of the multi-node collection process...")
    start = time.time()
    controller = ParallelComputingController(
        source_parquet_path=args.source_s3_uri,
        s3_save_uri=args.save_s3_uri,
        num_raw_data=args.max_trajectories,
        data_per_batch=1,
        request_per_minute=args.request_per_minute,
        max_steps=args.max_steps,
        agent_name="hsm_v2",
        agent_model_provider="anthropic",
        agent_model_name="claude-3-5-sonnet-20241022",
        temperature=0.3,
        max_tokens=500,
        max_repetitive_actions=3,
        dp_max_retries=1,
        timeout=args.timeout,
        verbose=args.verbose,
    )
    results = controller.start(multiprocess="ray")
    print()
    print("Data generation is done.")
    print("Number of raw data processed: {}".format(len(results)))
    print("Successful generation: {}".format(sum(results)))
    print("Failed generation: {}".format(len(results) - sum(results)))
    print("Took {} seconds.".format(int(time.time() - start)))
    print("END of the multi-node collection process.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        """\
Initiate the distributed action data crawler.
WARNING: Please refrain from using this script directly and use `scripts/trajectory_collector_ray_job_submit.sh` instead.
"""
    )
    parser.add_argument(
        "--source_s3_uri",
        type=str,
        required=True,
        help="The S3 uri of the raw data parquet.",
    )
    parser.add_argument(
        "--save_s3_uri",
        type=str,
        required=True,
        help="The S3 uri to save the generated data.",
    )
    parser.add_argument(
        "--max_trajectories",
        type=int,
        required=True,
        help="The maximum number of trajectories to generate.",
    )
    parser.add_argument(
        "--max_steps",
        type=int,
        required=True,
        help="The maximum number of steps to attempt for each trajectory.",
    )
    parser.add_argument(
        "--orbot_extension_s3_uri",
        type=str,
        default="s3://orby-osu-va/orbot_extension/dist-103024/",
        help="The S3 uri to download the orbot extension from. Defaults to s3://orby-osu-va/orbot_extension.",
    )
    parser.add_argument(
        "--request_per_minute",
        type=int,
        default=200,
        help="The number of requests allowed per minute. Defaults to 100.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="The timeout for the data generation tasks. Defaults to None.",
    )
    parser.add_argument(
        "--verbose",
        type=bool,
        default=True,
        help="Whether to print verbose logs. Defaults to False.",
    )
    parser.add_argument(
        "--num_cpus",
        type=int,
        default=32,
        help="The number of CPUs to use for the Ray cluster. Defaults to 32.",
    )
    args = parser.parse_args()

    main(args)
