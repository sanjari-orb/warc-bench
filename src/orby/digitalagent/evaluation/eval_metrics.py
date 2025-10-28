from orby.digitalagent.evaluation.eval_config import (
    AgentConfig,
    ModelConfig,
    RunnerConfig,
    BenchmarkConfig,
)

_wandb_started = False


def start_recording(
    name: str,
    agent_name: str,
    agent_config: AgentConfig,
    model_config: ModelConfig,
    runner_config: RunnerConfig,
    benchmarks: dict[str, BenchmarkConfig],
):
    """Starts recording an evaluation if wandb_project is specified in the runner_config.

    Args:
        name: Name of the eval run that will appear in wandb.
        agent_name: Name of the agent being evaluated.
        agent_config: Config of the agent being evaluated.
        model_config: Config of the model being evaluated.
        runner_config: Config of the eval runner.
        benchmarks: Benchmarks that will be used in this eval run."""
    if not runner_config.wandb_project:
        return
    import wandb

    wandb.init(
        entity="orby",
        project=runner_config.wandb_project,
        name=name,
        config={
            "random_seed": runner_config.seed,
            "agent": agent_name,
            "agent_name": agent_config.name,
            "model_provider": model_config.provider,
            "model_name": model_config.name,
            "model_config": model_config.model_dump(exclude_none=True),
            "benchmarks": {
                key: benchmarks[key].model_dump(exclude_none=True) for key in benchmarks
            },
            "output_dir": runner_config.output_dir,
            "threads": runner_config.threads,
            "timeout_secs": runner_config.timeout_secs,
        },
    )
    global _wandb_started
    _wandb_started = True


def report_metrics(metrics: dict[str, float]):
    """Records eval metrics."""
    if not _wandb_started:
        return
    import wandb

    wandb.log(metrics)


def finish_recording():
    """Finishes recording of an eval."""
    global _wandb_started
    if not _wandb_started:
        return
    import wandb

    wandb.finish()
    _wandb_started = False
