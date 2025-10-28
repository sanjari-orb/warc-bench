#!/usr/bin/env python
"""Setup script for orby-web-agent monorepo."""

import sys
import os
from setuptools import setup, find_packages

# Add the current directory to the Python path so custom_build can be imported
sys.path.insert(0, os.path.abspath("."))

if __name__ == "__main__":
    # The monorepo structure maintains:
    # - src/orby/ (top-level package namespace)
    #   - subtask_benchmark/ (benchmark runner with WARC server)
    #   - digitalagent/ (agent implementations, models, evaluation)
    #   - prompt_utils/ (prompt template utilities)
    #   - protos/ (protocol buffer definitions)
    setup(
        packages=find_packages(where="src"),
        package_dir={"": "src"},
        include_package_data=True,
    )
