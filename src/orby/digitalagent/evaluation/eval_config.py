from pydantic import BaseModel
from typing import ForwardRef, Optional

ModelConfig = ForwardRef("ModelConfig")


class ModelConfig(BaseModel):
    provider: str
    name: str
    temperature: float = 0
    max_tokens: int = 512
    frequency_penalty: float = 0
    grounder: Optional[ModelConfig] = None
    executor: Optional[ModelConfig] = None
    planner: Optional[ModelConfig] = None


class AgentConfig(BaseModel):
    name: str
    model: Optional[ModelConfig] = None
    model_config_name: Optional[str] = None
    model_config_names: Optional[list[str]] = None


class ViewportSize(BaseModel):
    width: float
    height: float


# TODO: add additional support for rerunning the same benchmark
# by supporting an optional num_runs parameter
class BenchmarkConfig(BaseModel):
    name: str = None
    dataset: str
    # Pool of URLs for action crawling agent.
    # This is a str path to a python list
    # of URLs.
    # It gets used only for openended environments (ie dataset which has
    # env_prefix containing "openended")
    url_pool: Optional[str] = None
    max_examples: int = 0
    max_steps: int = 20
    tasks_per_batch: int = -1
    example_ids: list[str] = []
    example_ids_to_skip: list[str] = []
    viewport_size: Optional[ViewportSize] = None
    headless: bool = True
    reset_env: bool = True


class RunnerConfig(BaseModel):
    threads: int = 8
    batch_size: int = 1  # defines how many examples share the same browser instance
    output_dir: str
    # Per example timeout
    timeout_secs: int = 10 * 60
    wandb_project: Optional[str] = None
    seed: Optional[int] = None
    environment_ttl_hours: Optional[int] = 10  # Default to 10 hours.


class EvalConfig(BaseModel):
    run_name: Optional[str] = None
    run_id: Optional[str] = (
        None  # unique run_id, based on run_name, random id, and timestamp
    )
    runner: RunnerConfig
    benchmarks: dict[str, BenchmarkConfig]
    agents: dict[str, AgentConfig]
    model_configs: dict[str, ModelConfig] = {}


def list_models(config: ModelConfig) -> list[ModelConfig]:
    models = []
    models.append(config)
    for field in config.model_fields_set:
        value = getattr(config, field)
        if isinstance(value, ModelConfig):
            models.extend(list_models(value))
    return models
