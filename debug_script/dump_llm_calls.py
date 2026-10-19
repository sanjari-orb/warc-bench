"""Write every LLM call in an eval run to one text file: the prompt text
(images shown as placeholders) and the model's reply, task by task.

Example:
    python debug_script/dump_llm_calls.py --run-dir eval_outputs/<run>/subtaskbench_run1_<model> --out llm_calls.txt
    python debug_script/dump_llm_calls.py --run-dir ... --task online.84   # one task, printed
"""

import argparse
import glob
import json
import lzma
import os
import sys

from orby.protos.fm.trajectory_data_pb2 import TrajectoryData


def task_number(path: str) -> tuple:
    tail = path.rsplit(".", 1)[-1]
    return (0, int(tail)) if tail.isdigit() else (1, tail)


def write_task(out, task_dir: str, state: dict) -> None:
    res_path = os.path.join(task_dir, "results.json")
    res = json.load(open(res_path)) if os.path.exists(res_path) else {}
    traj = TrajectoryData()
    with lzma.open(os.path.join(task_dir, "trajectory.pb.xz"), "rb") as f:
        traj.ParseFromString(f.read())
    task_id = os.path.basename(task_dir).split("subtaskbench.")[-1]
    out.write("#" * 100 + f"\nTASK {task_id}  success={res.get('success')}  steps={len(traj.actions)}\n")
    out.write(f"GOAL: {res.get('goal', traj.goal)}\n\n")
    for i, action in enumerate(traj.actions):
        for j, call in enumerate(action.agent_state.llm_interactions):
            state["calls"] += 1
            out.write(f"===== step {i + 1}, call {j + 1}, model={call.model_name}\n")
            for msg in call.llm_messages:
                parts = []
                for c in msg.llm_contents:
                    if c.text:
                        parts.append(c.text)
                    elif c.image_url:
                        parts.append(f"[image: {len(c.image_url)} base64 chars]")
                text = "\n".join(parts)
                # The system prompt is the same for every call, so print it once.
                if msg.role == "system":
                    if state["system_printed"]:
                        out.write(f"--- system: (same {len(text)}-char system prompt as the first call)\n")
                        continue
                    state["system_printed"] = True
                out.write(f"--- {msg.role}:\n{text}\n")
            out.write(f"--- RESPONSE:\n{call.response}\n\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-dir", required=True, help="Directory containing browsergym/<task>/")
    parser.add_argument("--out", help="Output text file (default: print to stdout)")
    parser.add_argument("--task", help="Only this task id, e.g. online.84")
    args = parser.parse_args()

    task_dirs = [d for d in glob.glob(os.path.join(args.run_dir, "browsergym", "*"))
                 if os.path.exists(os.path.join(d, "trajectory.pb.xz"))]
    if args.task:
        task_dirs = [d for d in task_dirs if d.endswith("subtaskbench." + args.task)]
    if not task_dirs:
        raise SystemExit("No matching trajectories")
    task_dirs.sort(key=task_number)

    state = {"calls": 0, "system_printed": False}
    out = open(args.out, "w") if args.out else sys.stdout
    try:
        for d in task_dirs:
            write_task(out, d, state)
        out.write(f"Total LLM calls: {state['calls']}\n")
    finally:
        if args.out:
            out.close()
    if args.out:
        print(f"{args.out}: {len(task_dirs)} tasks, {state['calls']} calls")


if __name__ == "__main__":
    main()
