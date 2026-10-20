"""Rerun some tasks of a finished run and merge their results into it.

Use this only for tasks that never got a real attempt, such as a dropped
network connection, not to retry tasks the model failed.

The rerun goes to <run-dir>/rerun_<name>/ with its own config, usage log and
per-task CSV. The run's tasks CSV is then rewritten with those tasks' rows
replaced; the original is kept next to it as *_tasks.before_<name>.csv, and
<run-dir>/rerun_<name>/rerun_info.json records the tasks and the reason.

Example:
    python scripts/rerun_tasks.py --run-dir runs/gpt61sol/run1 --name conn \\
        --tasks online.144 --reason "openai.APIConnectionError, not retried"
"""

import argparse
import csv
import glob
import json
import os
import re
import subprocess
import sys
import time

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASK_RE = re.compile(r"^online\.[0-9]+$")
NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
PROXY_ENV_VARS = ["ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_CUSTOM_HEADERS", "OPENAI_BASE_URL"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-dir", required=True, help="A finished run, e.g. runs/gpt61sol/run1")
    parser.add_argument("--name", required=True, help="Short name for this rerun, used in paths")
    parser.add_argument("--tasks", nargs="+", required=True, help="Task ids, e.g. online.144")
    parser.add_argument("--reason", required=True, help="Why these tasks are rerun (recorded)")
    args = parser.parse_args()

    if not NAME_RE.match(args.name):
        raise SystemExit("--name may only use letters, digits, '_' and '-'")
    bad = [t for t in args.tasks if not TASK_RE.match(t)]
    if bad:
        raise SystemExit(f"not task ids: {bad}")
    tasks = sorted(set(args.tasks), key=lambda t: int(t.split(".")[1]))

    run_dir = os.path.abspath(args.run_dir)
    run_name = os.path.basename(os.path.dirname(run_dir)) + "_" + os.path.basename(run_dir)
    task_csv = os.path.join(run_dir, "report", f"{run_name}_tasks.csv")
    if not os.path.exists(task_csv):
        raise SystemExit(f"{task_csv} not found; is this a finished run?")
    with open(task_csv, newline="") as f:
        rows = list(csv.DictReader(f))
    known = {r["task_id"] for r in rows}
    missing = [t for t in tasks if t not in known]
    if missing:
        raise SystemExit(f"tasks not in {task_csv}: {missing}")

    rerun_dir = os.path.join(run_dir, f"rerun_{args.name}")
    if os.path.exists(rerun_dir):
        raise SystemExit(f"{rerun_dir} already exists; pick another --name")
    os.makedirs(rerun_dir)

    with open(os.path.join(run_dir, "config.yaml")) as f:
        config = yaml.safe_load(f)
    rerun_id = f"{run_name}_rerun_{args.name}"
    config["run_id"] = rerun_id
    config["runner"] = dict(config["runner"], output_dir=os.path.join(rerun_dir, "eval_outputs"),
                            threads=min(len(tasks), config["runner"].get("threads", 8)))
    for bench in config["benchmarks"].values():
        bench["example_ids"] = [f"browsergym/subtaskbench.{t}" for t in tasks]
    config_path = os.path.join(rerun_dir, "config.yaml")
    with open(config_path, "w") as f:
        yaml.safe_dump(config, f, sort_keys=False)

    usage_log = os.path.join(rerun_dir, "usage.jsonl")
    env = dict(os.environ, SUBTASK_BENCHMARK_FILE="benchmark_test.json", LLM_USAGE_LOG=usage_log)
    for var in PROXY_ENV_VARS:
        env.pop(var, None)
    start = time.time()
    with open(os.path.join(rerun_dir, "eval.log"), "w") as log:
        proc = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "run_eval.py"), config_path],
                              cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT)
    wall = round(time.time() - start, 1)
    if proc.returncode != 0:
        raise SystemExit(f"run_eval.py exited with {proc.returncode}; see {rerun_dir}/eval.log")

    out_dirs = glob.glob(os.path.join(rerun_dir, "eval_outputs", rerun_id, "*"))
    if len(out_dirs) != 1:
        raise SystemExit(f"expected one benchmark output dir, found {out_dirs}")
    report_dir = os.path.join(rerun_dir, "report")
    subprocess.run([sys.executable, os.path.join(REPO, "scripts", "usage_report.py"),
                    "--run-dir", out_dirs[0], "--usage-log", usage_log, "--wall-time", str(wall),
                    "--out-dir", report_dir, "--name", rerun_id], check=True)
    with open(os.path.join(report_dir, f"{rerun_id}_tasks.csv"), newline="") as f:
        new_rows = {r["task_id"]: r for r in csv.DictReader(f)}
    if set(new_rows) != set(tasks):
        raise SystemExit(f"rerun covered {sorted(new_rows)}, expected {tasks}; run CSV left unchanged")

    backup = task_csv.replace("_tasks.csv", f"_tasks.before_{args.name}.csv")
    if os.path.exists(backup):
        raise SystemExit(f"{backup} already exists; run CSV left unchanged")
    os.replace(task_csv, backup)
    merged = [new_rows.get(r["task_id"], r) for r in rows]
    with open(task_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(merged)

    old = {r["task_id"]: r for r in rows}
    info = {
        "run": run_name, "reason": args.reason, "wall_time_s": wall,
        "tasks": {t: {"before_success": int(old[t]["success"]), "after_success": int(new_rows[t]["success"])}
                  for t in tasks},
    }
    with open(os.path.join(rerun_dir, "rerun_info.json"), "w") as f:
        json.dump(info, f, indent=2)
    print(json.dumps(info))


if __name__ == "__main__":
    main()
