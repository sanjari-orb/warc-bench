# Gather prompts in a single file to make it easier to edit versions for experiments

import os

from orby.prompt_utils import Template

basic_stateless = Template(
    os.path.join(os.path.dirname(__file__), "basic_stateless", "20241031.jinja2")
)
hierarchical_stateless = Template(
    os.path.join(os.path.dirname(__file__), "hierarchical_stateless", "20241031.jinja2")
)
hierarchical_stateless_multi = Template(
    os.path.join(
        os.path.dirname(__file__), "hierarchical_stateless_multi", "20241031.jinja2"
    )
)
hsm_v2 = Template(os.path.join(os.path.dirname(__file__), "hsm_v2", "20241114.jinja2"))
pixel_coord_executor = Template(
    os.path.join(os.path.dirname(__file__), "hsm_v2", "pixel_coord_executor.jinja2")
)
hybrid_executor = Template(
    os.path.join(os.path.dirname(__file__), "hsm_v2", "hybrid_executor.jinja2")
)
unified_v1 = Template(
    os.path.join(os.path.dirname(__file__), "unified_v1", "20241120.jinja2")
)
hsm_v3 = Template(os.path.join(os.path.dirname(__file__), "hsm_v3", "20241219.jinja2"))
unified_v2 = Template(
    os.path.join(os.path.dirname(__file__), "unified_v2", "20241211.jinja2")
)
hsm_v4 = Template(os.path.join(os.path.dirname(__file__), "hsm_v4", "20250207.jinja2"))
action_crawler = Template(
    os.path.join(os.path.dirname(__file__), "action_crawler_v1", "20241220.jinja2")
)
subtask_vision_agent_v1 = Template(
    os.path.join(
        os.path.dirname(__file__), "subtask_vision_agent_v1", "20250423.jinja2"
    )
)
subtask_hybrid_agent_v1 = Template(
    os.path.join(
        os.path.dirname(__file__), "subtask_hybrid_agent_v1", "20250425.jinja2"
    )
)
sva_v2 = Template(os.path.join(os.path.dirname(__file__), "sva_v2", "20250428.jinja2"))
sva_v3 = Template(os.path.join(os.path.dirname(__file__), "sva_v3", "20250508.jinja2"))
sva_v4 = Template(os.path.join(os.path.dirname(__file__), "sva_v4", "20250814.jinja2"))
claude_cua = Template(os.path.join(os.path.dirname(__file__), "claude_cua", "20250807.jinja2"))
