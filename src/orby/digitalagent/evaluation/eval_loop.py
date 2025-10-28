"""
Module that runs the agent for a specific example and records artifacts.
"""

from retry import retry
from typing import Optional
import random
import string
import logging
import os
import json
import time
import socket
import traceback

from browsergym.core.action.highlevel import HighLevelActionSet
import browsergym.visualwebarena  # register visualwebarena tasks as gym environments
import browsergym.workarena  # register workarena tasks as gym environments
import gymnasium as gym
from orby.digitalagent.utils import action_parsing_utils
from orby.digitalagent.utils import env_utils
from orby.digitalagent.utils import file_utils
from orby.digitalagent.utils import process_utils
from orby.digitalagent.agent import AGENT_NAME_TO_BUILDER
from orby.digitalagent.evaluation.eval_config import BenchmarkConfig, AgentConfig
from orby.trajectory_collector.utils import record_utils
from orby.protos.fm.trajectory_data_pb2 import TrajectoryData
from fm import action_data_pb2
import multiprocessing

import browsergym.subtaskbench
from subtask_benchmark.utils import (
    WebReplayServerSessionHandler,
    StaticWebAppServerSessionHandler,
)

logger = logging.getLogger(__name__)


def find_unused_port():
    """Finds an unused port on the system.

    Returns:
        int: An unused port number.
    """
    sock = socket.socket()
    sock.bind(("", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def run_example(
    example_env_name: str,
    task_kwargs: Optional[dict],
    agent_config: AgentConfig,
    benchmark_config: BenchmarkConfig,
    debug_dir: str | None = None,
    timeout: float = 10 * 60,
) -> float:
    start_time = time.time()
    logger.debug(f"Evaluating environment: {example_env_name}")
    agent_builder = AGENT_NAME_TO_BUILDER[agent_config.name]
    agent = agent_builder(
        model_configs=agent_config.model.model_dump(exclude_none=True)
    )
    server_handler = None

    try:
        kwargs = {}
        kwargs["evaluate_reward_on_terminal_msgs"] = True
        kwargs["ignore_html_observations"] = True
        kwargs["headless"] = benchmark_config.headless

        if "subtaskbench.online" in example_env_name:
            port = find_unused_port()
            server_handler = WebReplayServerSessionHandler(
                example_env_name.replace("browsergym/subtaskbench.", ""),
                browser_args={
                    "force-device-scale-factor": 1,
                    "allow-running-insecure-content": True,
                    "disable-web-security": True,
                    "disable-site-isolation-trials": True,
                    "disable-features": "VizDisplayCompositor",
                },
                viewport_width=benchmark_config.viewport_size.width,
                viewport_height=benchmark_config.viewport_size.height,
                debugging_port=port,
            )
            server_handler.setup_webreplay_server(
                run_headless=benchmark_config.headless
            )
            kwargs["cdp_port"] = port
            kwargs["connect_via_cdp"] = True

        elif "subtaskbench.static" in example_env_name:
            server_handler = StaticWebAppServerSessionHandler(
                example_env_name.replace("browsergym/subtaskbench.", ""), 3000
            )
            server_handler.setup_static_server(run_headless=benchmark_config.headless)
            kwargs["connect_via_cdp"] = False

        if benchmark_config.viewport_size:
            kwargs["viewport"] = benchmark_config.viewport_size.model_dump()
        # Handle uniquification of openended datasets
        if "openended" in example_env_name:
            env = env_utils.make(example_env_name, task_kwargs=task_kwargs, **kwargs)
            # Uniquify the env name since all the env_names will be
            # "browsergym/wa_openended" or "browsergym/openended" otherwise
            example_env_name = (
                example_env_name
                + "-"
                + "".join(random.choices(string.ascii_letters + string.digits, k=8))
            )
        else:
            env = env_utils.make(example_env_name, **kwargs)
    except gym.error.NameNotFound:
        logger.warning(f"Environment {example_env_name} not found.")
        return 0

    debug_output_dir = os.path.join(debug_dir, example_env_name) if debug_dir else None
    if debug_output_dir:
        file_utils.makedirs(debug_output_dir, exist_ok=True)

    try:
        # Wrap the whole environment interaction with a try catch and return 0 reward for this example if something fails
        obs, _ = env.reset()
        if agent.use_normalized_coords:
            HighLevelActionSet.to_python_code = (
                action_parsing_utils.monkey_patch_to_python_code(
                    obs, coordinate_multiplier=agent.coordinate_multiplier
                )
            )

        action_set = HighLevelActionSet(
            subsets=agent.action_subsets,  # allow the agent to also use x,y coordinates
            strict=False,  # less strict on the parsing of the actions
            multiaction=agent.allow_multiple_actions,  # disable to agent to take multiple actions at once
            demo_mode="off",  # disable visual effects
        )
        env.unwrapped.action_mapping = action_set.to_python_code

        done = False
        goal = obs["goal"]
        agent.reset(obs)
        n_steps = 0

        if debug_output_dir:
            trajectory_data = TrajectoryData()
            trajectory_data.base_url = ""
            trajectory_data.goal = goal

            # Start creating states for trajectory proto
            before_state = record_utils.record_web_state_from_browser_gym_observation(
                obs
            )
        while not done:
            action, _ = agent.act(obs)
            obs, reward, terminated, truncated, info = env.step(action)
            logger.debug("Step", n_steps + 1, ":", action, "-->", reward)
            if debug_output_dir:
                # Save details in trajectory proto
                after_state = (
                    record_utils.record_web_state_from_browser_gym_observation(
                        observation=obs,
                        reward=reward,
                        terminated=terminated,
                        truncated=truncated,
                    )
                )

                action_data = (
                    record_utils.record_action_data_from_browser_gym_interaction(
                        domain="",
                        action_string=action,
                        after_state=after_state,
                        before_state=before_state,
                        agent_state=action_data_pb2.AgentState(
                            llm_interactions=agent.llm_trace[-1]
                        ),
                    )
                )

                trajectory_data.actions.extend([action_data])

                # Make after the new before state for the next action
                before_state = after_state

            done = terminated or truncated
            if done or n_steps == benchmark_config.max_steps - 1:
                break
            if time.time() - start_time > timeout:
                logger.warning(f"Example '{example_env_name}' timing out...")
                reward = 0
                break
            n_steps += 1
    except Exception as ex:
        logger.warning(
            f"Exception occurred when running task '{example_env_name}': {ex}\n{traceback.format_exc()}"
        )
        reward = 0
        if isinstance(ex, RuntimeError):
            # Raise serious issues like RuntimeError, which is triggerd when the WorkArena instance is hibernating
            raise ex

    if debug_output_dir:
        # Save the reward. TODO: improve this and make it more informative
        if reward > 0:
            trajectory_data.success.CopyFrom(
                TrajectoryData.ResultSuccess(answer=f"Got reward {reward}")
            )
        else:
            trajectory_data.failure.CopyFrom(
                TrajectoryData.ResultFailure(
                    failure_message=TrajectoryData.ResultFailure.FailureMessage.FAILURE_MESSAGE_UNSPECIFIED
                )
            )
        if time.time() - start_time > timeout:
            logger.warning(
                f"Example '{example_env_name}' is saving the file in the buffer time..."
            )
        # Save the object to a file
        with file_utils.open(
            os.path.join(debug_output_dir, "trajectory.pb.xz"), "wb"
        ) as f:
            f.write(trajectory_data.SerializeToString())

        debugging_data_row = {
            "example": example_env_name,
            "goal": goal,
            "reward": reward,
            "success": reward > 0,
            "model_configs": json.dumps(agent_config.model.model_dump()),
            "agent_name": agent_config.name,
            "steps": n_steps + 1,
            "debug_output_dir": debug_output_dir,
        }
        # save json file
        with file_utils.open(os.path.join(debug_output_dir, "results.json"), "w") as f:
            json.dump(debugging_data_row, f)

    # Ask the env to close nicely first
    env.close()
    # Explictly clean up the server processes as the atexit call seems
    # not working in the server class. It is ok to call cleanup() multiple
    # times as it's guarded by try/except block. This is only for subtaskbench.
    if server_handler:
        try:
            server_handler.cleanup()
        except Exception as ex:
            logger.warning(
                f"Exception occurred when closing server handler '{example_env_name}': {ex}\n{traceback.format_exc()}"
            )

    logger.debug("Final reward:", reward)
    return reward


def run_examples(
    example_env_names: list[str],
    task_kwargs: Optional[list[dict]],
    agent_config: AgentConfig,
    benchmark_config: BenchmarkConfig,
    debug_dir: str | None = None,
    timeout: float = 10 * 60,
    output_queue=None,
):
    rewards = []
    for i, example_env_name in enumerate(example_env_names):
        result = run_example(
            example_env_name,
            None if not task_kwargs else task_kwargs[i],
            agent_config,
            benchmark_config,
            debug_dir=debug_dir,
            timeout=timeout,
        )
        rewards.append(result)
    if output_queue:
        output_queue.put(rewards)


@retry((TimeoutError), tries=3, delay=2)
def run_examples_in_subprocess(
    example_env_names: list[str],
    task_kwargs: Optional[list[dict]],
    agent_config: AgentConfig,
    benchmark_config: BenchmarkConfig,
    debug_dir: str | None = None,
    timeout=10 * 60,
) -> list[float]:
    output_queue = multiprocessing.Queue()
    process_utils.run_with_timeout(
        run_examples,
        (timeout + 20)  # Adding some buffer time to gracefully finish.
        * len(example_env_names),
        example_env_names,
        task_kwargs,
        agent_config,
        benchmark_config,
        debug_dir=debug_dir,
        timeout=timeout,
        output_queue=output_queue,
    )
    if not output_queue.empty():
        result = output_queue.get()
        return result
    else:
        return [0] * len(example_env_names)
