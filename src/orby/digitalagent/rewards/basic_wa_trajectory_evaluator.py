from typing import Any, Dict, Optional, Union, List, Tuple, Callable
from abc import ABCMeta, abstractmethod
import io
import json
from PIL import Image
import numpy as np
import pandas as pd
import random
import jinja2

from orby.digitalagent.model.fm import FoundationModel
from orby.digitalagent.agent.utils import prompt_to_messages
from orby.protos.fm.trajectory_data_pb2 import TrajectoryData
from orby.digitalagent.rewards import prompts, trajectory_utils
from orby.digitalagent.rewards import TrajectoryEvaluator


class BasicWATrajectoryEvaluator(TrajectoryEvaluator):
    def __init__(
        self,
        model_configs: dict,
        prompt_template: str,
        image_sequence_idx: List[int],
        check_gt_success: Callable[
            TrajectoryData, bool
        ] = trajectory_utils.check_wa_traj_success,
    ):
        TrajectoryEvaluator.__init__(self)
        self.model_configs = model_configs
        self.model = FoundationModel(**model_configs) if model_configs else None
        self.prompt_template = prompt_template
        self.image_sequence_idx = image_sequence_idx
        self.check_gt_success = check_gt_success

    def evaluate(
        self,
        traj: TrajectoryData,
        **kwargs,
    ):
        """
        Evaluate a single trajectory using one LLM call.
        """
        messages = self._construct_llm_messages(traj, **kwargs)
        try:
            response = self.model.generate(messages=messages)
            success, answer = self._parse_llm_response(response)
        except Exception as e:
            response = "Error: " + str(e)
            success = False
            answer = {}
        return {
            "llm_request_prompt": messages,
            "llm_response": response,
            "gt_success": self.check_gt_success(traj),
            "llm_pred_success": success,
            "llm_pred_answer": answer,
        }

    def _construct_llm_messages(
        self,
        traj: TrajectoryData,
        **kwargs,
    ) -> List:
        """
        Construct the messages for the LLM call by rendering the jinja2 template and get the image sequence.
        """
        prompt_text = jinja2.Template(self.prompt_template).render(traj=traj, **kwargs)
        images = self._extract_screenshot_sequence_from_traj(
            traj=traj, sequence_idx=self.image_sequence_idx
        )
        messages = prompt_to_messages(prompt_text, images=images)
        return messages

    def _parse_llm_response(
        self,
        response: str,
    ) -> tuple[bool, str]:
        """
        Parse the response from the model output of task completion verifier.

        Args:
            response (str): The response from the task completion verifier.

        Returns:
            tuple[bool, str]: A tuple containing the success status and the answer, if any.
        """
        response = response.strip("`").strip("json").strip().replace("\n", " ")
        try:
            response_dict = json.loads(response)
        except json.JSONDecodeError:
            response_dict = json.loads(response.strip("`").strip("json").strip())
        success = "yes" in response_dict.get("success", "").lower()
        answer = response_dict.get("answer", {})
        return success, answer

    def _extract_screenshot_sequence_from_traj(
        self,
        traj: TrajectoryData,
        sequence_idx: List[int] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Extract screenshots from a trajectory based on the sequence type.

        Args:
            traj (TrajectoryData): Trajectory data with actions and states.
            sequence_type (str): Type of sequence to extract.
                - "first_last": Returns the first and last screenshots.
        Returns:
            Dict[str, np.ndarray]:
        """
        all_states = [
            traj.actions[i].before_state for i in range(len(traj.actions))
        ] + [traj.actions[-1].after_state]
        screenshots = {
            str(i): all_states[i].viewport.screenshot.content for i in sequence_idx
        }
        screenshots = {
            k: np.array(Image.open(io.BytesIO(s))) for k, s in screenshots.items()
        }
        return screenshots
