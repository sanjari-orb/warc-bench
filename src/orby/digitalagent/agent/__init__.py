from .agent import Agent, LoggingMetaWrapper

from .sva_v4 import SvaV4
from .claude_cua import ClaudeComputerUseAgent
from .browsergym_agent_wrapper import wrap_agent_cls
from orby.digitalagent.configs.webarena_lite import webarena_lite_env_ids
from orby.digitalagent.configs.webarena_easy import env_ids as wa_easy_env_ids
from orby.digitalagent.configs.workarena import l1_env_ids as workarena_l1_env_ids
from orby.trajectory_collector.utils import webarena_openended_task

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
    "subtaskbench_test": {
        "env_ids": [f"browsergym/subtaskbench.online.{i}" for i in range(216)] 
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
}
