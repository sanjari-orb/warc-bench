"""Check a finished eval run for signs of broken environments.

For every task it reports: blank screenshots (and whether the page stayed blank
for the whole run), model notes that mention a blank, loading or error page
(for agents that write a <note> or <thinking> per step), errors logged by the
eval loop, and runs that hit the step limit.

Example:
    SUBTASK_BENCHMARK_FILE=benchmark_test.json python debug_script/check_run.py \\
        --run-dir eval_outputs/<run>/subtaskbench_run1_<model> --log run.log --out check.json
"""

import argparse
import collections
import glob
import io
import json
import lzma
import os
import re

from PIL import Image

from orby.protos.fm.trajectory_data_pb2 import TrajectoryData
from orby.subtask_benchmark.config import get_config

BLANK_SHARE = 0.97
BROKEN_PAGE_WORDS = re.compile(
    r"\b(blank|still loading|not loaded|skeleton|spinner|error page|not found|404|no connection|"
    r"failed to load|empty page|white page|did not render|not rendering|splash)\b", re.I)
TASK_ERROR = re.compile(r"Exception occurred when running task 'browsergym/subtaskbench\.([^']+)': ([^\n]{0,200})")


def task_number(path: str) -> tuple:
    tail = path.rsplit(".", 1)[-1]
    return (0, int(tail)) if tail.isdigit() else (1, tail)


def is_blank(png: bytes) -> bool:
    small = Image.open(io.BytesIO(png)).convert("RGB").resize((160, 90))
    return collections.Counter(small.getdata()).most_common(1)[0][1] / (160 * 90) > BLANK_SHARE


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-dir", required=True, help="Directory containing browsergym/<task>/")
    parser.add_argument("--log", help="Console log of the run, to pick up task errors")
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--out", help="Write per-task details to this JSON file")
    args = parser.parse_args()

    archives = {t["task_id"]: t["env"]["data_path"].split("web_archives/")[-1] for t in get_config()}
    task_errors = dict(TASK_ERROR.findall(open(args.log, errors="replace").read())) if args.log else {}
    task_dirs = sorted(glob.glob(os.path.join(args.run_dir, "browsergym", "*")), key=task_number)
    if not task_dirs:
        raise SystemExit(f"No task directories under {args.run_dir}/browsergym")

    rows = []
    for d in task_dirs:
        task_id = os.path.basename(d).split("subtaskbench.")[-1]
        row = {"task_id": task_id, "archive": archives.get(task_id, "?")}
        if not os.path.exists(os.path.join(d, "trajectory.pb.xz")):
            row["missing_trajectory"] = True
            rows.append(row)
            continue
        res = json.load(open(os.path.join(d, "results.json"))) if os.path.exists(os.path.join(d, "results.json")) else {}
        traj = TrajectoryData()
        with lzma.open(os.path.join(d, "trajectory.pb.xz"), "rb") as f:
            traj.ParseFromString(f.read())
        shots = []
        for i, action in enumerate(traj.actions):
            if i == 0 and action.before_state.viewport.screenshot.content:
                shots.append(action.before_state.viewport.screenshot.content)
            if action.after_state.viewport.screenshot.content:
                shots.append(action.after_state.viewport.screenshot.content)
        blank = [i for i, s in enumerate(shots) if is_blank(s)]
        notes = []
        for action in traj.actions:
            for call in action.agent_state.llm_interactions:
                m = re.search(r"<(note|thinking)>(.*?)</\1>", call.response or "", re.S)
                text = (m.group(2) if m else "").strip().replace("\n", " ")
                if text and BROKEN_PAGE_WORDS.search(text):
                    notes.append(text[:200])
        row.update(success=bool(res.get("success")), steps=len(traj.actions), screenshots=len(shots),
                   blank_screenshots=blank, blank_whole_run=bool(shots) and len(blank) == len(shots),
                   broken_page_notes=notes, error=task_errors.get(task_id),
                   hit_step_limit=len(traj.actions) >= args.max_steps)
        rows.append(row)

    ok = [r for r in rows if not r.get("missing_trajectory")]
    print(f"tasks: {len(rows)}  passed: {sum(r['success'] for r in ok)}  missing trajectories: {len(rows) - len(ok)}")
    print("errors:", {r["task_id"]: r["error"] for r in ok if r["error"]} or "none")
    print("blank for the whole run:", [r["task_id"] for r in ok if r["blank_whole_run"]] or "none")
    print("started blank, then loaded:", [r["task_id"] for r in ok if r["blank_screenshots"][:1] == [0] and not r["blank_whole_run"]] or "none")
    print("hit step limit:", [r["task_id"] for r in ok if r["hit_step_limit"]] or "none")
    by_archive = collections.defaultdict(list)
    for r in ok:
        by_archive[r["archive"]].append(r)
    print("\nper archive: passed/total, tasks whose notes mention a broken page")
    for archive, rs in sorted(by_archive.items()):
        print(f"  {archive:55s} {sum(r['success'] for r in rs):3d}/{len(rs):<3d} {sum(bool(r['broken_page_notes']) for r in rs)}")
    if args.out:
        with open(args.out, "w") as f:
            json.dump(rows, f, indent=1)


if __name__ == "__main__":
    main()
