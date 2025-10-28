from typing import Any, Dict, Optional, Union, List, Tuple, Callable
import random

from orby.protos.fm.trajectory_data_pb2 import TrajectoryData
from orby.digitalagent.utils import file_utils


def check_wa_traj_success(traj: TrajectoryData) -> bool:
    """
    Get the ground truth successful/failed status from a trajectory, for Webarena tasks.
    """
    return True if traj.success.answer else False


def load_traj_from_s3_path(s3_path: str):
    with file_utils.open(s3_path, "rb") as f:
        traj = TrajectoryData.FromString(f.read())
    return traj


def sample_traj_from_s3_folder(
    s3_folder: str,
    num_samples: Optional[int] = None,
    success_ratio: Optional[float] = None,
    success_check_func: Callable[[TrajectoryData], bool] = check_wa_traj_success,
    seed: int = 42,
) -> List[str]:
    """
    Sample trajectories from a given S3 folder, following the rules:
    (1) Sample all trajectories if num_samples is None;
    (2) Randomly sample num_samples trajectories if specified;
    (3) Randomly sample with a given success_ratio if specified.
    Returns a list of S3 paths.
    """
    objects = file_utils.list_files(s3_folder)
    protos = [o for o in objects if o.endswith(".pb")]
    print(f"Found {len(protos)} trajectory protos.")
    random.seed(seed)
    random.shuffle(protos)
    if not num_samples:  # no sampling
        print(f"No sampling required, get all {len(protos)} trajectories.")
        return protos
    if not success_ratio:  # randomly sampled
        num_protos = min(num_samples, len(protos))
        print(f"Sampled {num_protos}/{len(protos)} trajectories.")
        return protos[:num_protos]

    if not success_check_func:
        raise ValueError("No success check function provided.")
    # sample with a certain success ratio
    required_success_count = int(num_samples * success_ratio)
    required_failed_count = num_samples - required_success_count

    successful_protos, failed_protos = [], []
    for proto in protos:
        traj = load_traj_from_s3_path(proto)
        if success_check_func(traj) and len(successful_protos) < required_success_count:
            successful_protos.append(proto)
        elif (
            not success_check_func(traj) and len(failed_protos) < required_failed_count
        ):
            failed_protos.append(proto)
        # stop when reaching the desired counts for both
        if (
            len(successful_protos) == required_success_count
            and len(failed_protos) == required_failed_count
        ):
            break
    print(
        f"Sampled {len(successful_protos)} successful and {len(failed_protos)} failed trajectory protos."
    )
    return successful_protos + failed_protos
