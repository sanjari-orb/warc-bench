from typing import Any, Dict, Optional, Union, List, Tuple
from abc import ABCMeta, abstractmethod
import io
import json
from PIL import Image
import numpy as np
import random

from orby.protos.fm.trajectory_data_pb2 import TrajectoryData
from orby.digitalagent.utils import file_utils
from orby.digitalagent.rewards import trajectory_utils


class TrajectoryEvaluator:
    def __init__(self, **kwargs):
        self.model = None
        self.model_configs = kwargs.get("model_configs", {})
        self.prompt_template: str = ""

    @abstractmethod
    def evaluate(self, traj: TrajectoryData, **kwargs) -> Any:
        pass

    def batch_evaluate(
        self,
        s3_paths: List[str],
        run_id: str = "test",
    ) -> Tuple[List[Dict], Dict]:
        """
        Run the LLM evaluator on a batch of trajectories, get the results and calculate metrics.
        """
        # TODO: make it multi-thread
        results = []
        for path in s3_paths:
            traj = trajectory_utils.load_traj_from_s3_path(path)
            output = self.evaluate(traj)
            results.append(
                {
                    "s3_path": path,
                    **output,
                }
            )
        return results
