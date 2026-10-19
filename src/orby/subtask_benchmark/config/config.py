import json
import os
from pathlib import Path
from typing import Dict, Any

# Which task file in environments/ to load. Set to "benchmark_test.json" to run
# the test split; the task ids in the two files overlap, so only one can be
# registered at a time.
TASK_FILE_ENV_VAR = "SUBTASK_BENCHMARK_FILE"
DEFAULT_TASK_FILE = "benchmark.json"


def get_config() -> Dict[str, Any]:
    """
    Load and cache configuration from a JSON file.

    Returns:
        Dict containing the configuration

    Raises:
        FileNotFoundError: If the config file doesn't exist
        json.JSONDecodeError: If the config file is not valid JSON
    """

    # First try to find in the package config directory
    top_level_config_dir = Path(__file__).parent.parent / "environments"
    task_file = os.environ.get(TASK_FILE_ENV_VAR) or DEFAULT_TASK_FILE
    # Only a plain file name inside environments/ is allowed.
    if Path(task_file).name != task_file or not task_file.endswith(".json"):
        raise ValueError(
            f"{TASK_FILE_ENV_VAR} must be a .json file name in {top_level_config_dir}, got {task_file!r}"
        )
    config_path = top_level_config_dir / task_file

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found {config_path}")

    with open(config_path, "r") as f:
        config = json.load(f)

    return config
