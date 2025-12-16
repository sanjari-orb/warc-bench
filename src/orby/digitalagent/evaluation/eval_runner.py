"""
Module that runs evaluations specified in a config.
"""

from datetime import datetime
import importlib
import io
from joblib import Parallel, delayed
import os
import pandas as pd
import random
import string
import subprocess
import sys
import time
import tempfile
from typing import Callable, Optional
import urllib
import yaml
from collections import defaultdict

import browsergym.core  # register the openended task as a gym environment
import browsergym.miniwob  # register miniwob tasks as gym environments
import browsergym.webarena  # register webarena tasks as gym environments
import browsergym.visualwebarena  # register visualwebarena tasks as gym environments
#`import browsergym.workarena  # register workarena tasks as gym environments
import gymnasium as gym
from copy import deepcopy
from tqdm.auto import tqdm

import orby.digitalagent.environments.webarena_service as wa_service
from orby.digitalagent.evaluation.eval_loop import run_examples_in_subprocess
from orby.digitalagent.evaluation.eval_config import (
    AgentConfig,
    BenchmarkConfig,
    RunnerConfig,
    EvalConfig,
    ModelConfig,
    list_models,
)
from orby.digitalagent.evaluation.eval_metrics import (
    start_recording,
    finish_recording,
    report_metrics,
)
from orby.digitalagent.agent import ENV_CONFIGS
from orby.digitalagent.model.fm import FoundationModel
from concurrent.futures import ThreadPoolExecutor, as_completed


def resolve_attr(full_path):
    """Dynamically resolve a deeply nested attribute from a module path."""
    module_path, attr_name = full_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, attr_name)


def generate_id(digits: int = 6):
    characters = string.digits + string.ascii_uppercase + string.ascii_lowercase
    return "".join(random.choices(characters, k=digits))


def select_env_ids(
    env_ids: list[str], env_prefix: str, full_env_ids: list[str]
) -> list[str]:
    if env_prefix:
        env_ids = [
            f"{env_prefix}.{env_id}" if not env_id.startswith(env_prefix) else env_id
            for env_id in env_ids
        ]
    for env_id in env_ids:
        if env_id not in full_env_ids:
            raise ValueError(f"Environment {env_id} not found.")
    return env_ids


def shuffle_env_ids(env_ids: list[str], shuffle_seed: int) -> list[str]:
    env_ids.sort(reverse=True)
    
    # if shuffle_seed:
    #     random.seed(shuffle_seed)
    # random.shuffle(env_ids)
    return env_ids


def get_env_ids_and_task_kwargs(
    benchmark: BenchmarkConfig, shuffle_seed: int | None = None
) -> tuple[list[str], Optional[list[dict]]]:
    """
    Returns a tuple of
    list[str]: List of environment IDs strings which correspond to
        the gym environment name
    Optional[list[dict]]: List of dicts corresponding to the kwargs which
        gym.make should be called with. Default value is None.
        The args are passed for openended tasks to capture information like start_url.
    """
    env_ids = []
    task_kwargs = None
    if "env_prefix" in ENV_CONFIGS[benchmark.dataset]:
        env_ids = [
            id
            for id in gym.envs.registry.keys()
            if id.startswith(ENV_CONFIGS[benchmark.dataset]["env_prefix"])
        ]

        # If it is an openended environment, use the mechanism to
        # sample from the url_pool
        if "openended" in ENV_CONFIGS[benchmark.dataset]["env_prefix"]:
            # Duplicate the env_id #max_examples number of times
            env_ids = env_ids * benchmark.max_examples
            if not benchmark.url_pool:
                raise ValueError(
                    "Open ended benchmarks need to specify BenchmarkConfig.url_pool"
                )

            url_pool = resolve_attr(benchmark.url_pool)

            task_kwargs = []
            for i in range(benchmark.max_examples):
                url_idx = i % len(url_pool)
                task_kwargs.extend([{"start_url": url_pool[url_idx]}])

    if "env_ids" in ENV_CONFIGS[benchmark.dataset]:
        env_ids = [
            id
            for id in gym.envs.registry.keys()
            if id in ENV_CONFIGS[benchmark.dataset]["env_ids"]
        ]
    if benchmark.example_ids:
        env_ids = select_env_ids(
            benchmark.example_ids,
            ENV_CONFIGS[benchmark.dataset].get("env_prefix", ""),
            env_ids,
        )
    if benchmark.example_ids_to_skip:
        env_ids = [
            id
            for id in env_ids
            if id not in benchmark.example_ids_to_skip
        ]
    env_ids = shuffle_env_ids(env_ids, shuffle_seed)

    if benchmark.max_examples > 0:
        env_ids = env_ids[: benchmark.max_examples]
        env_ids = shuffle_env_ids(env_ids, shuffle_seed)

    return env_ids, task_kwargs


def wait_for_models(model_config: ModelConfig, timeout_secs: int = 3600):
    """Waits for all models specified in the agent config to be ready and raise exceptions if they failed to become ready within timeout_secs."""
    start_time = time.time()
    model_configs = list_models(model_config)

    for config in model_configs:
        if config.provider != "mosaic-vllm":
            continue
        model = FoundationModel(provider="mosaic-vllm", name=config.name)
        while True:
            try:
                response = model.generate(
                    messages=[
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": "Are you ready?"}],
                        }
                    ]
                )
                print(f"Response received from model {config.name}: {response}")
                break
            except Exception as e:
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout_secs:
                    raise TimeoutError(
                        f"Model {config.name} is still not ready after {elapsed_time} secs. Latest error: {e}"
                    )
                print(f"Model {config.name} is not ready. Retrying in 30 seconds...")
                time.sleep(30)


def _get_unique_run_id(
    config: EvalConfig | None = None,
) -> str:
    if config and config.run_name:
        run_id = config.run_name + "-" + generate_id()
    elif "RUN_NAME" in os.environ:
        run_id = os.environ["RUN_NAME"] + "-" + generate_id()
    else:
        run_id = generate_id()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{run_id}_{timestamp}"


def _get_output_dir_for_run(
    config: EvalConfig,
    benchmark_name: str | None = None,
    agent_name: str | None = None,
) -> str | None:
    if not config.runner:
        raise ValueError("Runner config is not specified.")
    if not config.runner.output_dir:
        return None
    if not config.run_id:
        config.run_id = _get_unique_run_id(config)
    return os.path.join(
        config.runner.output_dir,
        config.run_id,
        f"{benchmark_name}_{agent_name}",
    )


def run_single_benchmark(
    runner_config: RunnerConfig,
    benchmark: BenchmarkConfig,
    agent: AgentConfig,
    output_dir: str | None = None,
    instance_ip: str | None = None,
    instance_release_callback: Callable[None, None] | None = None,
) -> tuple[float, str | None]:
    """Runs a single benchmark and returns a score and a visualization URL."""
    env_ids, task_kwargs = get_env_ids_and_task_kwargs(
        benchmark, shuffle_seed=runner_config.seed
    )
    if task_kwargs:
        assert len(env_ids) == len(
            task_kwargs
        ), f"Expect arguments for every environment ID, found {len(env_ids)} envs and {len(task_kwargs)} args."

    # verify instance_ip and instance_release_callback are both None or both not None

    if instance_ip:
        assert (
            instance_release_callback
        ), "instance_release_callback should be provided if instance_ip is provided"
        print(f"Using WA service instance with IP {instance_ip}")
        setup_wa_ips(instance_ip)

    visualizer_url = None
    wait_for_models(agent.model)
    if output_dir:
        visualizer_url = "https://vis.orbyapi.com/runs/?path=" + urllib.parse.quote(
            output_dir
        )
        print("Visualizer: ", visualizer_url)

    if benchmark.reset_env and "webarena" in benchmark.dataset:
        # Reset the server
        subprocess.run(["bash", "scripts/reset_remote_wa_vwa.sh"])

    if benchmark.dataset == "visualwebarena":
        env_ids_with_reset = [
            env_id
            for env_id in env_ids
            if env_id in browsergym.visualwebarena.VISUALWEBARENA_TASK_IDS_WITH_RESET
        ]
        env_ids = [
            env_id
            for env_id in env_ids
            if env_id
            not in browsergym.visualwebarena.VISUALWEBARENA_TASK_IDS_WITH_RESET
        ]

        print("Evaluating environments with reset:")
        rewards_with_reset = []
        with tqdm(total=len(env_ids_with_reset)) as pbar:
            processed = 0
            while processed < len(env_ids_with_reset):
                batch = env_ids_with_reset[
                    processed : processed + runner_config.batch_size
                ]
                try:
                    r = run_examples_in_subprocess(
                        batch,
                        None,
                        agent,
                        benchmark,
                        debug_dir=output_dir,
                        timeout=runner_config.timeout_secs,
                    )
                except Exception as e:
                    print(f"{batch} failed after retries: {e}")
                    r = [0] * len(batch)

                rewards_with_reset.extend(r)
                processed += len(batch)
                pbar.update(len(batch))

    def run_examples(
        batch: list[str], task_kwargs: Optional[list[dict]]
    ) -> tuple[list[float], int]:
        """
        Args:
        batch: List of example IDs
        task_kwargs: Corresponding list of task_kwargs which gym.make should
            be called with. Primarily used for passing in start_url for open-ended tasks.
        """
        return run_examples_in_subprocess(
            batch,
            task_kwargs,
            agent,
            benchmark,
            debug_dir=output_dir,
            timeout=runner_config.timeout_secs,
        ), len(batch)

    rewards = []
    if runner_config.threads == 1:
        rewards = []
        # If we are running in single thread, we can run the examples in the main thread
        with tqdm(total=len(env_ids)) as pbar:
            for i in range(0, len(env_ids), runner_config.batch_size):
                batch = env_ids[i : i + runner_config.batch_size]
                if task_kwargs:
                    batched_kwargs = task_kwargs[i : i + runner_config.batch_size]
                else:
                    batched_kwargs = None
                try:
                    r, batch_size = run_examples(batch, batched_kwargs)
                    rewards.extend(r)
                    pbar.update(batch_size)
                except Exception as e:
                    print(f"Exception occurred for batch {batch}: {e}")
                    pbar.update(runner_config.batch_size)

    else:
        # Run the examples in parallel using ThreadPoolExecutor
        # TODO: consider consolidating code by using
        # orby/digitalagent/utils/joblib_parallel_with_tqdm.py
        with ThreadPoolExecutor(max_workers=runner_config.threads) as executor:
            # Submitting tasks to the thread pool
            future_to_batch = {}

            for i in range(0, len(env_ids), runner_config.batch_size):
                batch = env_ids[i : i + runner_config.batch_size]

                if task_kwargs:
                    batched_kwargs = task_kwargs[i : i + runner_config.batch_size]
                else:
                    batched_kwargs = None
                future_to_batch[
                    executor.submit(run_examples, batch, batched_kwargs)
                ] = batch

            # Collecting the results as they are completed
            with tqdm(total=len(env_ids)) as pbar:
                for future in as_completed(future_to_batch):
                    try:
                        r, batch_size = future.result()
                        rewards.extend(r)
                        pbar.update(batch_size)
                    except Exception as e:
                        print(
                            f"Exception occurred for batch {future_to_batch[future]}: {e}"
                        )
                        pbar.update(runner_config.batch_size)

    if benchmark.dataset == "visualwebarena":
        # merge final rewards
        final_rewards = []
        for env_id in env_ids:
            if env_id in browsergym.visualwebarena.VISUALWEBARENA_TASK_IDS_WITH_RESET:
                final_rewards.append(rewards_with_reset.pop(0))
            else:
                final_rewards.append(rewards.pop(0))
        rewards = final_rewards

    print("Success rate:", sum(rewards) / len(rewards))
    print("Visualizer: ", visualizer_url)

    if instance_release_callback:
        print(f"Release instances")
        instance_release_callback()

    return {
        "num_success": sum(rewards),
        "num_total": len(rewards),
        "visualizer_url": visualizer_url,
    }


def _validate_and_initialize_eval_config(config: EvalConfig) -> None:
    """
    Validate the eval config has benchmarks and agents, and initialize the evaluation config with unique run_id.
    """

    if not config.benchmarks:
        raise ValueError("No benchmarks are specified in the config.")

    if not config.agents:
        raise ValueError("No agents are specified in the config.")

    if not config.run_id:
        config.run_id = _get_unique_run_id(config)
    print(f"Validate and initialize the config with unique run id: {config.run_id}")


def _benchmark_batch_split(
    benchmark_name: str,
    benchmark: BenchmarkConfig,
    shuffle_seed: int | None = None,
    benchmark_split_separator: str = "SPLIT",
) -> dict[str, BenchmarkConfig]:
    """
    Split a benchmark into multiple benchmarks, assigning example_ids and names to each.
    """
    full_env_ids, args = get_env_ids_and_task_kwargs(
        benchmark, shuffle_seed=shuffle_seed
    )
    if args and benchmark.tasks_per_batch > len(full_env_ids):
        raise ValueError(
            "Openended tasks are not supported with benchmark splitting right now. Please try again without benchmark splitting."
        )

    if benchmark.tasks_per_batch <= 0:
        benchmark.example_ids = full_env_ids
        benchmark.name = benchmark_name if not benchmark.name else benchmark.name
        return {benchmark_name: benchmark}
    new_benchmarks = {}
    for start_idx in range(0, len(full_env_ids), benchmark.tasks_per_batch):
        stop_idx = min(start_idx + benchmark.tasks_per_batch, len(full_env_ids))
        batch_env_ids = full_env_ids[start_idx:stop_idx]
        new_benchmark = deepcopy(benchmark)
        new_benchmark.name = benchmark_name
        new_benchmark.tasks_per_batch = -1
        new_benchmark.example_ids = shuffle_env_ids(
            batch_env_ids, shuffle_seed=shuffle_seed
        )
        new_benchmark_id = (
            f"{benchmark_name}_{benchmark_split_separator}_{start_idx}_{stop_idx}"
        )
        new_benchmarks[new_benchmark_id] = new_benchmark
    return new_benchmarks


# TODO: add additional support for rerunning the same benchmark
# by supporting an optional num_runs parameter
def _divide_eval_config(full_config: EvalConfig) -> list[EvalConfig]:
    """
    Divide the full config into multiple configs, each with a single run.
    By an single run, we mean a run with a single benchmark (split), agent, and model config.
    We make sure that if we input each divided config back into this function, it outputs
    the same config in a list of length 1.
    For example, the following yaml
    ```
    benchmarks:
        webarena_1:
            dataset: webarena
        webarena_2:
            dataset: webarena
    agents:
        unified_v2:
            name: unified_v2
            model_config_names:
                - Qwen2-VL-7B-Instruct
                - uFEDh2_ba774
        hsm_v2:
            name: hsm_v2
            model_config_names:
                - Qwen2-VL-7B-Instruct
    model_configs:
        Qwen2-VL-7B-Instruct:
            provider: mosaic-vllm
            name: Qwen2-VL-7B-Instruct
            temperature: 0.0
            max_tokens: 1024
        uFEDh2_ba774:
            provider: mosaic-vllm
            name: uFEDh2_ba774
            temperature: 0.0
            max_tokens: 1024
    ```
    will be divided into 6 configs:
        - webarena_1, unified_v2, Qwen2-VL-7B-Instruct
        - webarena_1, unified_v2, uFEDh2_ba774
        - webarena_1, hsm_v2, Qwen2-VL-7B-Instruct
        - webarena_2, unified_v2, Qwen2-VL-7B-Instruct
        - webarena_2, unified_v2, uFEDh2_ba774
        - webarena_2, hsm_v2, Qwen2-VL-7B-Instruct

    Args:
        full_config (EvalConfig): The full config to divide

    Returns:
        list[EvalConfig]: The list of divided configs
    """
    template_config = deepcopy(full_config)
    template_config.benchmarks = {}
    template_config.agents = {}

    all_raw_benchmarks = deepcopy(full_config.benchmarks)
    # Split each benchmark into multiple benchmarks if tasks_per_batch is specified, and assign example_ids and names to each
    all_benchmarks = {}
    for benchmark_id, benchmark_config in all_raw_benchmarks.items():
        new_benchmarks = _benchmark_batch_split(
            benchmark_name=benchmark_id,
            benchmark=benchmark_config,
            shuffle_seed=full_config.runner.seed,
        )
        all_benchmarks.update(new_benchmarks)

    all_agents = deepcopy(full_config.agents)

    # We need to consolidate how models of agent is referenced; we use model_config_names only
    for agent_name in all_agents:
        if all_agents[agent_name].model is not None:
            raise NotImplementedError(
                "This method of evaluation currently does not support specifying model directly in the agent. Please use model_config_name or model_config_names and specify the model configs in the model_configs field instead."
            )
        elif all_agents[agent_name].model_config_name is not None:
            if all_agents[agent_name].model_config_names is not None:
                raise ValueError(
                    "Both model_config_name and model_config_names are specified in the agent config. Please specify only one."
                )
            all_agents[agent_name].model_config_names = [
                all_agents[agent_name].model_config_name
            ]
            all_agents[agent_name].model_config_name = None

    # We ensure that in each divided config, there is only one run.
    # We do this by making each divided config have a single benchmark, agent, and model config.
    divided_configs = []
    for benchmark_id, benchmark_config in all_benchmarks.items():
        for agent_name, agent_config in all_agents.items():
            template_agent_config = deepcopy(agent_config)
            template_agent_config.model = None
            template_agent_config.model_config_name = None
            template_agent_config.model_config_names = None

            for model_config_name in agent_config.model_config_names:
                new_config = deepcopy(template_config)
                new_config.benchmarks[benchmark_id] = benchmark_config
                new_config.agents[agent_name] = deepcopy(template_agent_config)
                new_config.agents[agent_name].model_config_name = model_config_name

                divided_configs.append(new_config)
    return divided_configs


def _create_all_wa_service_instances_multithreads(
    num_instances: int,
    max_worker: int = None,
    ttl_hours: int = None,
) -> tuple[list[str], list[str]]:
    """
    Creates the specified number of WA service instances and returns their public IPs.
    We do this in a distributed manner to speed up the process.

    Args:
        num_instances (int): The number of instances to create

    Returns:
        tuple[list[str], list[str]]: The instance IDs, public IPs, and callback functions of the created instances
    """

    instance_ids = []
    public_ips = []

    # TODO: consider consolidating code by using
    # orby/digitalagent/utils/joblib_parallel_with_tqdm.py
    with ThreadPoolExecutor(max_workers=max_worker) as executor:
        # Submitting tasks to the thread pool
        future_to_instance_id = {}
        for i in range(num_instances):
            future_to_instance_id[
                executor.submit(wa_service.create_instance, ttl_hours=ttl_hours)
            ] = i

        # Collecting the results as they are completed
        with tqdm(total=num_instances) as pbar:
            for future in as_completed(future_to_instance_id):
                try:
                    instance_id, public_ip = future.result()
                    instance_ids.append(instance_id)
                    public_ips.append(public_ip)
                except Exception as e:
                    print(
                        f"Exception occurred during WA environment creation: {e}",
                        file=sys.stderr,
                    )
                pbar.update(1)

    instance_release_callbacks = [
        lambda: wa_service.release_instance(instance_id)
        for instance_id in range(len(instance_ids))
    ]
    return instance_ids, public_ips, instance_release_callbacks


def _setup_and_run_all_eval_runs(
    configs: list[EvalConfig],
    instance_ips: list[str] | None = None,
    instance_release_callbacks: list[Callable[None, None]] | None = None,
) -> pd.DataFrame:
    """
    Setup and run all the evaluation runs specified in the configs.
    If use WA service, each instance_ip corresponds to a config, where only one benchmark and one agent is specified.

    Args:
        configs (list[EvalConfig]): The list of configs specifying the evaluation runs, where each config has exactly one benchmark and one agent
        instance_ips (list[str]): The public IPs of the WA service instances, defaults to None if not using WA service
        instance_release_callbacks (list[Callable[None, None]]): The list of callbacks to release the WA service instances, defaults to None if not using WA service

    Returns:
        pd.DataFrame: The results of the evaluation runs
    """
    results_rows = []
    # Ensure that the number of instance IPs match the number of runs needed
    if instance_ips or instance_release_callbacks:
        assert len(instance_ips) == len(
            configs
        ), "Number of instance IPs should match the number of benchmarks"
        assert len(instance_release_callbacks) == len(
            configs
        ), "Number of instance release callbacks should match the number of benchmarks"

    try:
        for i, config in enumerate(configs):
            print(f"Running trial {i+1}/{len(configs)}")

            # make sure the config has exactly one benchmark and one agent
            if len(config.benchmarks) != 1 or len(config.agents) != 1:
                raise ValueError(
                    "Each divided eval config should have exactly one benchmark, and agent."
                )
            benchmark_id, benchmark = list(config.benchmarks.items())[0]
            agent_name, agent = list(config.agents.items())[0]
            if not agent.model_config_name:
                raise ValueError(
                    "No model_config_name in agent. There should be exactly one model_config_name in agent."
                )
            if agent.model_config_name not in config.model_configs:
                raise ValueError(
                    f"Model config {agent.model_config_name} not found in model_configs."
                )
            agent.model = config.model_configs[agent.model_config_name]
            start_recording(
                name=f"{config.run_id}_{agent_name}_{agent.model_config_name}_{benchmark_id}",
                agent_name=f"{agent_name}_{agent.model_config_name}",
                agent_config=agent,
                model_config=agent.model,
                runner_config=config.runner,
                benchmarks=config.benchmarks,
            )
            output_dir = _get_output_dir_for_run(
                config,
                benchmark_name=benchmark.name,
                agent_name=f"{agent_name}_{agent.model_config_name}",
            )
            run_benchmark_result = run_single_benchmark(
                config.runner,
                benchmark,
                agent,
                output_dir=output_dir,
                instance_ip=instance_ips[i] if instance_ips else None,
                instance_release_callback=(
                    instance_release_callbacks[i]
                    if instance_release_callbacks
                    else None
                ),
            )
            results_rows.append(
                {
                    "benchmark": benchmark.name,
                    "benchmark_id": benchmark_id,
                    "agent": agent_name,
                    "model": agent.model_config_name,
                    **run_benchmark_result,
                }
            )
            finish_recording()

    except Exception as e:
        print(f"Exception occurred during evaluation run {i+1}: {e}", file=sys.stderr)
        raise e
    return pd.DataFrame(results_rows)


def aggregate_results_and_report_metrics_to_wandb(
    results: pd.DataFrame,
    full_eval_config: EvalConfig,
):
    # Check for duplicates
    duplicates = results.duplicated(
        subset=["benchmark", "agent", "model", "benchmark_id"]
    )
    if duplicates.any():
        raise ValueError("Duplicate (benchmark, agent, model, benchmark_id) found.")

    # Aggregate num_success and num_total
    aggregated = results.groupby(
        ["benchmark", "agent", "model", "visualizer_url"], as_index=False
    ).agg({"num_success": "sum", "num_total": "sum"})
    # Calculate score
    aggregated["score"] = aggregated["num_success"] / aggregated["num_total"]
    aggregated.sort_values(by=["benchmark", "agent", "model"], inplace=True)

    for (agent, model), agent_model_data in aggregated.groupby(["agent", "model"]):
        # Start recording for the unique agent
        start_recording(
            name=f"metrics_recording_{full_eval_config.run_id}_{agent}_{model}",
            agent_name=f"{agent}_{model}",
            agent_config=full_eval_config.agents[agent],
            model_config=full_eval_config.model_configs[model],
            runner_config=full_eval_config.runner,
            benchmarks={},
        )
        metrics = {
            f"{row['benchmark']}/SR": row["score"]
            for _, row in agent_model_data.iterrows()
        }
        report_metrics(metrics)
        finish_recording()

    return aggregated


def setup_wa_ips(wa_host_ip: str) -> None:
    """
    Set the webarena IP environment variables to the specified IP.

    Args:
        wa_host_ip (str): The main webarena IP
    """
    WEB_ARENA_HOST = f"http://{wa_host_ip}"
    os.environ["WEB_ARENA_HOST_IP"] = wa_host_ip
    os.environ["WEB_ARENA_HOST"] = WEB_ARENA_HOST
    os.environ["WA_SHOPPING"] = f"{WEB_ARENA_HOST}:7770"
    os.environ["WA_SHOPPING_ADMIN"] = f"{WEB_ARENA_HOST}:7780/admin"
    os.environ["WA_REDDIT"] = f"{WEB_ARENA_HOST}:9999"
    os.environ["WA_GITLAB"] = f"{WEB_ARENA_HOST}:8023"
    os.environ["WA_MAP"] = f"{WEB_ARENA_HOST}:3000"
    os.environ["WA_WIKIPEDIA"] = (
        f"{WEB_ARENA_HOST}:8888/wikipedia_en_all_maxi_2022-05/A/User:The_other_Kiwix_guy/Landing"
    )
    os.environ["WA_HOMEPAGE"] = f"{WEB_ARENA_HOST}:4399"


# TODO: add additional support for rerunning the same benchmark
# by supporting an optional num_runs parameter
def run_eval(
    config: EvalConfig,
) -> pd.DataFrame:

    _validate_and_initialize_eval_config(config)
    print(
        f"Now running evaluations for {config.run_name} with unique id {config.run_id}..."
    )
    result_df = _setup_and_run_all_eval_runs(
        configs=_divide_eval_config(config),
    )
    aggregated_df = aggregate_results_and_report_metrics_to_wandb(result_df, config)
    print("All Done!")
    return aggregated_df


def run_eval_with_wa_service(
    config: EvalConfig, max_ips: int = -1, subprocess: bool = False
) -> pd.DataFrame:
    """
    Run the evaluation specified in the config using the WA service.

    Args:
        config (EvalConfig): The config specifying the evaluation
        max_ips (int): The maximum number of instances to create and run on in parallel

    Returns:
        pd.DataFrame: The results of the evaluation
    """
    _validate_and_initialize_eval_config(config)

    # fix the reset_env flag for benchmarks
    for benchmark_id, benchmark_config in config.benchmarks.items():
        if benchmark_config.reset_env == True:
            print(
                f"Benchmark {benchmark_id} have reset_env set to True. Since we are using WA service, this is not needed. Setting reset_env to False."
            )
            benchmark_config.reset_env = False
    # Divide up the config specs into multiple configs, each with a single run
    configs = _divide_eval_config(config)
    print(
        f"Divided the evaluation {config.run_name} with unique id {config.run_id} into {len(configs)} runs."
    )
    if max_ips is None or max_ips < 0:
        max_ips = len(configs)

    # Run them in batches of max_ips
    result_df = pd.DataFrame()
    start_idx = 0
    while start_idx < len(configs):
        stop_idx = min(start_idx + max_ips, len(configs))
        config_batch = configs[start_idx:stop_idx]
        num_instances = len(config_batch)

        # Start the same number of WA service instances as the number of runs needed
        print("Create {} EC2 instances".format(num_instances))
        (
            instance_ids,
            public_ips,
            instance_release_callbacks,
        ) = _create_all_wa_service_instances_multithreads(
            num_instances=num_instances,
            max_worker=config.runner.threads,
            ttl_hours=config.runner.environment_ttl_hours,
        )

        if len(instance_ids) == 0:
            # If no instance was created, raise an error
            raise ValueError("No instance was successfully created!")
        elif len(instance_ids) < len(config_batch):
            # If some of the instances were not created, only run the number of instances created
            # Leave the rest for the next evaluation batch
            len_config_batch = len(instance_ids)
            print(
                "Number of instances created does not match the number of runs. Only running {} trials.".format(
                    len_config_batch
                )
            )
            stop_idx = start_idx + len_config_batch
            config_batch = configs[start_idx:stop_idx]
            print("Now running evaluation {} to {}".format(start_idx, stop_idx))

        # Run each config with the corresponding WA service instance, and collect the results
        print("Now running evaluations...")
        result_df_batch = _setup_and_run_all_eval_runs(
            config_batch,
            public_ips,
            instance_release_callbacks,
        )
        result_df = pd.concat([result_df, result_df_batch], ignore_index=True)
        # Move to the next batch
        start_idx = stop_idx
    if subprocess:
        print("Finished running evaluations in subprocess.")
        return result_df

    aggregated_df = aggregate_results_and_report_metrics_to_wandb(result_df, config)
    print("All Done!")
    return aggregated_df


def _run_single_eval_with_elastic_client(config, use_docker=False):
    with tempfile.NamedTemporaryFile(mode="w") as f:
        yaml.dump(config.dict(), f)
        f.flush()

        if use_docker:
            command = [
                "docker",
                "run",
                "-v",
                f"{f.name}:/digital-agent/run.yaml",
                "-e",
                f"OPENAI_API_KEY={os.environ.get('OPENAI_API_KEY', '')}",
                "-e",
                "MINIWOB_URL=file:///digital-agent/dependencies/miniwob-plusplus/miniwob/html/miniwob/",
                "-t",
                "eval_client",
                "python",
                "scripts/run_eval.py",
                "run.yaml",
                "-u",
                "-s",
            ]
        else:
            command = ["python", "scripts/run_eval.py", f.name, "-u", "-s"]

        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )

        # read last line of logs to get the result
        try:
            result = proc.stdout.splitlines()[-1]
            print(result)
            return pd.read_json(io.StringIO(result))
        except Exception as e:
            import traceback

            print(f"Error: {e}", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
            print(proc.stderr, file=sys.stderr)
            return pd.DataFrame()


def run_eval_with_elastic_client(
    config: EvalConfig, max_ips: int = -1, use_docker=False
) -> pd.DataFrame:
    """
    Run the evaluation specified in the config using the docker client with WA service.

    Args:
        config (EvalConfig): The config specifying the evaluation
        max_ips (int): The maximum number of instances to create and run on in parallel

    Returns:
        pd.DataFrame: The results of the evaluation
    """

    _validate_and_initialize_eval_config(config)
    # Divide up the config specs into multiple configs, each with a single run
    configs = _divide_eval_config(config)
    print(f"Divided the evaluation into {len(configs)} runs.")
    if max_ips is None or max_ips < 0:
        max_ips = len(configs)
    # Run them in batches of max_ips
    result_dfs = Parallel(n_jobs=max_ips, backend="multiprocessing")(
        delayed(_run_single_eval_with_elastic_client)(single_config, use_docker)
        for single_config in configs
    )
    result_df = pd.concat(result_dfs, ignore_index=True)
    aggregated_df = aggregate_results_and_report_metrics_to_wandb(result_df, config)
    print("All Done!")
    return aggregated_df
