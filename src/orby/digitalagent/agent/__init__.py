from .agent import Agent, LoggingMetaWrapper

from .sva_v4 import SvaV4, SvaV4Note
from .claude_cua import ClaudeComputerUseAgent
from .browsergym_agent_wrapper import wrap_agent_cls
from orby.digitalagent.configs.webarena_lite import webarena_lite_env_ids
from orby.digitalagent.configs.webarena_easy import env_ids as wa_easy_env_ids
from orby.digitalagent.configs.workarena import l1_env_ids as workarena_l1_env_ids
from orby.trajectory_collector.utils import webarena_openended_task
import json as _json
from pathlib import Path as _Path

# Test tasks checked to run correctly; see benchmark_test_whitelist.json for
# the excluded tasks and why.
_TEST_WHITELIST = _Path(__file__).parents[2] / "subtask_benchmark" / "environments" / "benchmark_test_whitelist.json"
with open(_TEST_WHITELIST) as _f:
    _test_task_ids = _json.load(_f)["task_ids"]

ENV_CONFIGS = {
    "miniwob": {
        "env_prefix": "browsergym/miniwob",
    },
    "webarena": {
        "env_prefix": "browsergym/webarena",
    },
    "visualwebarena": {
        "env_prefix": "browsergym/visualwebarena",
    },
    "workarena": {
        "env_prefix": "browsergym/workarena",
    },
    "workarena_l1": {
        "env_ids": workarena_l1_env_ids,
    },
    "subtaskbench_manual": {
        "env_ids": [f"browsergym/subtaskbench.online.{i}" for i in range(60)]
    },
    "subtaskbench_synthetic": {
        "env_ids": [f"browsergym/subtaskbench.online.{i}" for i in range(60, 239)]
    },
    # Run with SUBTASK_BENCHMARK_FILE=benchmark_test.json so these ids load the
    # test tasks rather than the benchmark.json tasks that share the ids.
    "subtaskbench_test": {
        "env_ids": [f"browsergym/subtaskbench.{task_id}" for task_id in _test_task_ids]
    },
    "subtaskbench_train": {
        "env_ids": [f"browsergym/subtaskbench.online_train.{i}" for i in range(1443)]
    },
    "subtaskbench_full": {
        "env_ids": [f"browsergym/subtaskbench.online.{i}" for i in range(239)]
        + [f"browsergym/subtaskbench.online_train.{i}" for i in range(1443)]
    },
}

AGENT_NAME_TO_BUILDER = {
    "claude_cua": wrap_agent_cls(
        ClaudeComputerUseAgent,
        action_subsets=["chat", "infeas", "coord"],
        allow_multiple_actions=True,
    ),
    "sva_v4": wrap_agent_cls(
        SvaV4,
        action_subsets=["chat", "infeas", "coord", "nav"],
        allow_multiple_actions=True,
        use_orbot_dom=False,
    ),
    "sva_v4_note": wrap_agent_cls(
        SvaV4Note,
        action_subsets=["chat", "infeas", "coord", "nav"],
        allow_multiple_actions=True,
        use_orbot_dom=False,
    ),
}
