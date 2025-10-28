from .agent import Agent, LoggingMetaWrapper
from .basic_agent import BasicFMAgent
from .basic_stateless_agent import BasicStatelessFMAgent
from .hierarchical_stateless_agent import HierarchicalStatelessFMAgent
from .hierarchical_stateless_multi_agent import HierarchicalStatelessFMMultiAgent
from .action_crawl_agent import ActionCrawlAgent
from .hsm_v2_agent import HsmV2Agent
from .hsm_v3_agent import HsmV3Agent
from .hsm_v4_agent import HsmV4Agent
from .basic_cot_agent import BasicCoTFMAgent
from .unified_v1_agent import UnifiedV1FMAgent
from .unified_v2_agent import UnifiedV2FMAgent
from .subtask_vision_agent_v1 import SubtaskVisionAgentV1
from .subtask_hybrid_agent_v1 import SubtaskHybridAgentV1
from .sva_v2 import SvaV2
from .sva_v3 import SvaV3
from .sva_v4 import SvaV4
from .replay_sva_v3 import ReplaySvaV3, ReplayAndGenerateSvaV3
from .claude_cua import ClaudeComputerUseAgent
from .browsergym_agent_wrapper import wrap_agent_cls
from orby.digitalagent.configs.webarena_lite import webarena_lite_env_ids
from orby.digitalagent.configs.webarena_easy import env_ids as wa_easy_env_ids
from orby.digitalagent.configs.workarena import l1_env_ids as workarena_l1_env_ids
from .task_executors.pixel_coord_executor_agent import PixelCoordExecutorAgent
from orby.trajectory_collector.utils import webarena_openended_task

WEBARENA_ACTION_CRAWL_URLS = [
    "host:7780",
    "host:8023",
    "host:3000",
    "host:7770",
    "host:9999",
]

ENV_CONFIGS = {
    "miniwob": {
        "env_prefix": "browsergym/miniwob",
    },
    "webarena": {
        "env_prefix": "browsergym/webarena",
    },
    "wa_action_crawl": {"env_prefix": "browsergym/wa_openended"},
    "webarena-lite": {"env_ids": webarena_lite_env_ids},
    "webarena-mini": {
        "env_ids": [
            "browsergym/webarena.24",
            "browsergym/webarena.50",
            "browsergym/webarena.148",
            "browsergym/webarena.191",
            "browsergym/webarena.231",
            "browsergym/webarena.262",
            "browsergym/webarena.268",
            "browsergym/webarena.354",
            "browsergym/webarena.356",
            "browsergym/webarena.530",
            # github
            "browsergym/webarena.132",
            "browsergym/webarena.168",
            "browsergym/webarena.258",
            "browsergym/webarena.259",
            "browsergym/webarena.293",
            "browsergym/webarena.357",
            # shopping
            "browsergym/webarena.14",
            "browsergym/webarena.22",
            "browsergym/webarena.48",
            "browsergym/webarena.114",
            "browsergym/webarena.126",
            "browsergym/webarena.145",
            # reddit
            "browsergym/webarena.28",
        ]
    },
    "webarena-easy": {"env_ids": wa_easy_env_ids},
    "webarena-impossible-bids": {
        "env_ids": [
            "browsergym/webarena.742",
            "browsergym/webarena.746",
            "browsergym/webarena.747",
            "browsergym/webarena.748",
            "browsergym/webarena.749",
            "browsergym/webarena.750",
            "browsergym/webarena.751",
            "browsergym/webarena.752",
            "browsergym/webarena.753",
            "browsergym/webarena.754",
            "browsergym/webarena.755",
            "browsergym/webarena.756",
        ],
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
        "env_ids": [f"browsergym/subtaskbench.online.{i}" for i in range(215)] 
    },
    "subtaskbench_train": {
        "env_ids": [f"browsergym/subtaskbench.online_train.{i}" for i in range(1443)]
    },
    "subtaskbench_full": {
        "env_ids": [f"browsergym/subtaskbench.online.{i}" for i in range(239)]
        + [f"browsergym/subtaskbench.online_train.{i}" for i in range(1443)]
    },
}

AGENT_NAME_TO_CLASS = {
    "basic": BasicFMAgent,
    "basic_stateless": BasicStatelessFMAgent,
    "hierarchical_stateless": HierarchicalStatelessFMAgent,
    "hierarchical_stateless_multi": HierarchicalStatelessFMMultiAgent,
    "hsm_v2": HsmV2Agent,
    "hsm_v3": HsmV3Agent,
    "basic_cot": BasicCoTFMAgent,
    "unified_v1": UnifiedV1FMAgent,
    "unified_v2": UnifiedV2FMAgent,
    "action_crawler": ActionCrawlAgent,
}

AGENT_NAME_TO_BUILDER = {
    "basic": wrap_agent_cls(BasicFMAgent),
    "basic_stateless": wrap_agent_cls(BasicStatelessFMAgent),
    "hierarchical_stateless": wrap_agent_cls(HierarchicalStatelessFMAgent),
    "hierarchical_stateless_multi": wrap_agent_cls(HierarchicalStatelessFMMultiAgent),
    "hsm_v2": wrap_agent_cls(
        HsmV2Agent, use_normalized_coords=True, allow_multiple_actions=True
    ),
    "hsm_v2_pixel": wrap_agent_cls(
        HsmV2Agent, use_normalized_coords=False, allow_multiple_actions=True
    ),
    "hsm_v2_pixel_coord_only": wrap_agent_cls(
        HsmV2Agent, executor_cls=PixelCoordExecutorAgent, allow_multiple_actions=True
    ),
    "hsm_v3_miniwob": wrap_agent_cls(
        HsmV3Agent,
        allow_multiple_actions=True,
        use_orbot_dom=True,
        orbot_dom_options={
            "compact": False,
            "skip_visibility_check": True,
            "keep_all_attributes": True,
        },
        max_html_tokens=26000,
        action_subsets=["bid", "chat", "infeas", "coord"],
        bid_to_coordinate_conversion=False,
    ),
    "hsm_v3": wrap_agent_cls(
        HsmV3Agent,
        allow_multiple_actions=True,
        use_orbot_dom=False,
        orbot_dom_options={
            "compact": True,
            "skip_visibility_check": False,
        },
        max_html_tokens=26000,
        action_subsets=["bid", "chat", "infeas"],
        bid_to_coordinate_conversion=False,
    ),
    "hsm_v3_subtask": wrap_agent_cls(
        HsmV3Agent,
        allow_multiple_actions=True,
        use_orbot_dom=False,
        orbot_dom_options={
            "compact": True,
            "skip_visibility_check": False,
        },
        max_html_tokens=60000,
        action_subsets=["bid", "chat", "infeas", "coord", "nav"],
        bid_to_coordinate_conversion=False,
    ),
    "unified_v1": wrap_agent_cls(UnifiedV1FMAgent, use_orbot_dom=False),
    "unified_v2": wrap_agent_cls(UnifiedV2FMAgent, use_orbot_dom=False),
    "hsm_v4": wrap_agent_cls(
        HsmV4Agent,
        allow_multiple_actions=True,
        use_orbot_dom=False,
        orbot_dom_options={
            "compact": True,
            "skip_visibility_check": False,
        },
        max_html_tokens=26000,
        action_subsets=["chat", "infeas", "bid", "coord"],
        vision_only_action_subsets=["chat", "infeas", "coord"],
        bid_to_coordinate_conversion=False,
    ),
    "hsm_v4_miniwob": wrap_agent_cls(
        HsmV4Agent,
        allow_multiple_actions=True,
        use_orbot_dom=True,
        orbot_dom_options={
            "compact": False,
            "skip_visibility_check": True,
            "keep_all_attributes": True,
        },
        max_html_tokens=26000,
        action_subsets=["chat", "infeas", "bid", "coord"],
        vision_only_action_subsets=["chat", "infeas", "coord"],
        bid_to_coordinate_conversion=False,
    ),
    "hsm_v3_bid_to_coord": wrap_agent_cls(
        HsmV3Agent,
        allow_multiple_actions=True,
        use_orbot_dom=False,
        orbot_dom_options={
            "compact": True,
            "skip_visibility_check": False,
        },
        max_html_tokens=26000,
        action_subsets=["bid", "chat", "infeas", "coord"],
        bid_to_coordinate_conversion=True,
    ),
    "action_crawler": wrap_agent_cls(
        ActionCrawlAgent,
        use_orbot_dom=True,
        action_subsets=["chat", "infeas", "bid", "coord", "nav", "tab"],
    ),
    "subtask_vision_agent_v1": wrap_agent_cls(
        SubtaskVisionAgentV1,
        action_subsets=["chat", "infeas", "coord"],
    ),
    "subtask_hybrid_agent_v1": wrap_agent_cls(
        SubtaskHybridAgentV1,
        allow_multiple_actions=True,
        use_orbot_dom=False,
        orbot_dom_options={
            "compact": True,
            "skip_visibility_check": False,
        },
        max_html_tokens=60000,
        action_subsets=["chat", "infeas", "bid", "coord"],
        bid_to_coordinate_conversion=False,
    ),
    "sva_v2": wrap_agent_cls(
        SvaV2,
        action_subsets=["chat", "infeas", "coord"],
        allow_multiple_actions=True,
    ),
    "sva_v3": wrap_agent_cls(
        SvaV3,
        action_subsets=["chat", "infeas", "coord"],
        allow_multiple_actions=True,
        use_orbot_dom=False,
        # mac_screenshot_size_reduction=True,
    ),
    "replay_sva_v3": wrap_agent_cls(
        ReplaySvaV3,
        action_subsets=["chat", "infeas", "coord"],
        allow_multiple_actions=True,
    ),
    "claude_cua": wrap_agent_cls(
        ClaudeComputerUseAgent,
        action_subsets=["chat", "infeas", "coord"],
        allow_multiple_actions=True,
    ),
    "replay_and_generate_sva_v3": wrap_agent_cls(
        ReplayAndGenerateSvaV3,
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
