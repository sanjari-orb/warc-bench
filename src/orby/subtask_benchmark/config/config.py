import json
from pathlib import Path
from typing import Dict, Any


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
    config_path = top_level_config_dir / "benchmark.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found {config_path}")

    with open(config_path, "r") as f:
        config = json.load(f)

    return config
