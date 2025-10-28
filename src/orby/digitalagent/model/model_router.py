"""
This utility is for consuming the router file created by (multimodal) scripts/inference/report_endpoint.py.
"""

import os
import json
import hashlib
import time
from orby.digitalagent.utils import file_utils
import functools
import pandas as pd
import logging


logger = logging.getLogger(__name__)


def get_router_file_folder() -> str:
    folder = os.environ.get("MOSAIC_VLLM_MODEL_HOST_URL", "")
    if not folder:
        folder = "s3://orby-osu-va/model_router/"
    return folder


@functools.cache
def load_router_file(model_name: str) -> dict | None:
    if os.environ.get("MOSAIC_VLLM_MODEL_HOST_URL", "").startswith("http"):
        return None
    folder = get_router_file_folder()
    path = os.path.join(folder, hashlib.sha256(model_name.encode()).hexdigest())
    with file_utils.open(path) as f:
        return json.load(f)


def lookup_endpoint(host: str, model_name: str) -> tuple[str, str]:
    # This try/except block always fails now, commented it out for now.
    try:
        config = load_router_file(model_name)
        if config is None:
            return host, model_name
        host = config["host"]
        if not host.endswith("/v1"):
            host += "/v1"
        return host, config["model_name"]
    except Exception as e:
        logger.warning(f"Failed to lookup endpoint for {model_name}:{str(e)}")
    return host, model_name


def list_endpoints() -> pd.DataFrame:
    results = {
        "Name": [],
        "Host": [],
        "Run name": [],
        "Last reported": [],
        "Local model name": [],
        "Note": [],
    }
    for path in file_utils.list_files(get_router_file_folder()):
        with file_utils.open(path) as f:
            data = json.load(f)
        last_reported = data["timestamp"]
        note = ""
        # endpoint is supposed to report every 10 minutes.
        # 10 secs buffer time
        if int(time.time()) - last_reported > 10 * 60 + 10:
            file_utils.rm(path)
            note = "\tExpired"
        results["Name"].append(data["display_name"])
        results["Host"].append(data["host"])
        results["Run name"].append(data["run_name"])
        results["Last reported"].append(f"{int(time.time()) - last_reported} secs ago")
        results["Local model name"].append(data["model_name"])
        results["Note"].append(note)
    return pd.DataFrame(results)


if __name__ == "__main__":
    print(list_endpoints())
