"""Registers the WARC-Bench subtasks as BrowserGym gym environments.

Importing this module registers one gym environment per task defined in
``orby/subtask_benchmark/environments/benchmark.json``, under the ids
``browsergym/subtaskbench.<task_id>`` (for example
``browsergym/subtaskbench.online.0``).

This replaces the external ``browsergym-subtaskbench`` package. Registration is
driven by the benchmark file rather than by hardcoded id ranges, so the set of
registered environments always matches the shipped task definitions.
"""

import logging

from orby.subtask_benchmark import config

from . import task
from .registration import register_task

logger = logging.getLogger(__name__)

ONLINE_SUBTASKBENCH_TASK_IDS: list[str] = []
TRAIN_SUBTASKBENCH_TASK_IDS: list[str] = []
ALL_SUBTASKBENCH_TASK_IDS: list[str] = []


def _register_all() -> None:
    """Register every task found in the benchmark configuration."""
    try:
        all_configs = config.get_config()
    except FileNotFoundError:
        logger.error(
            "Benchmark configuration not found; no subtaskbench environments "
            "were registered."
        )
        return

    seen = set()
    for task_config in all_configs:
        task_id = task_config.get("task_id")
        if not task_id:
            logger.warning("Skipping benchmark entry with no task_id: %r", task_config)
            continue
        if task_id in seen:
            logger.warning("Skipping duplicate task_id %r", task_id)
            continue
        seen.add(task_id)

        if not task_id.startswith("online"):
            logger.warning(
                "Skipping task_id %r: only 'online' and 'online_train' tasks are "
                "supported.",
                task_id,
            )
            continue

        gym_id = f"subtaskbench.{task_id}"
        register_task(
            gym_id,
            task.OnlineSubTaskBenchTask,
            task_kwargs={"task_id": task_id},
        )

        full_id = f"browsergym/{gym_id}"
        if task_id.startswith("online_train."):
            TRAIN_SUBTASKBENCH_TASK_IDS.append(full_id)
        else:
            ONLINE_SUBTASKBENCH_TASK_IDS.append(full_id)
        ALL_SUBTASKBENCH_TASK_IDS.append(full_id)


_register_all()
