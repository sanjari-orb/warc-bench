from orby.digitalagent.agent.task_executors.pixel_coord_executor_agent import (
    PixelCoordExecutorAgent,
)
from orby.digitalagent.prompts.default import hybrid_executor


class HybridExecutorAgent(PixelCoordExecutorAgent):
    """
    An executor that produces both bid and pixel coordinate actions.
    """

    def __init__(
        self, model_configs: dict, actions: str, limit_to_ctx: bool = True, **kwargs
    ):
        PixelCoordExecutorAgent.__init__(
            self,
            model_configs=model_configs,
            actions=actions,
            limit_to_ctx=limit_to_ctx,
            **kwargs
        )
        self.template = hybrid_executor
