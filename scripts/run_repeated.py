"""Run the test split k times for one model, report each run, and upload it.

For each run this starts scripts/run_eval.py with its own usage log, writes
the per-task CSV with scripts/usage_report.py, and copies the run's outputs to
<s3-prefix>/<label>/run<i>/. After the last run it writes the avg@k summary
with scripts/aggregate_runs.py and uploads that too.

API keys and AWS credentials come from the environment.

Example:
    python scripts/run_repeated.py --label opus55 \\
        --config scripts/eval_configs/test_split_opus55.yaml \\
        --runs 3 --s3-prefix s3://warc-bench-results/test_split_20261019
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABEL_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
PROXY_ENV_VARS = ["ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_CUSTOM_HEADERS", "OPENAI_BASE_URL"]


def s3_copy(src, dest, recursive=False, profile=None):
    """Copy to S3. Returns False on failure so a long batch of runs is not lost
    to an expired login; the files stay on disk and can be copied later."""
    cmd = ["aws", "s3", "cp", src, dest, "--only-show-errors"]
    if recursive:
        cmd.append("--recursive")
    if profile:
        cmd += ["--profile", profile]
    if subprocess.run(cmd).returncode != 0:
        print(f"WARNING: upload of {src} to {dest} failed; copy it again later", flush=True)
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", required=True, help="Short model label used in paths")
    parser.add_argument("--config", required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--start-run", type=int, default=1, help="First run number, to resume")
    parser.add_argument("--s3-prefix", required=True, help="s3://bucket/prefix")
    parser.add_argument("--work-dir", default=os.path.join(REPO, "runs"))
    parser.add_argument("--rate-card", default=os.path.join(REPO, "scripts", "rate_card.json"))
    parser.add_argument("--aws-profile")
    args = parser.parse_args()

    if not LABEL_RE.match(args.label):
        raise SystemExit("--label may only use letters, digits, '.', '_' and '-'")
    if not args.s3_prefix.startswith("s3://"):
        raise SystemExit("--s3-prefix must start with s3://")
    if args.runs < 1 or args.start_run < 1 or args.start_run > args.runs:
        raise SystemExit("need 1 <= --start-run <= --runs")
    s3_base = f"{args.s3_prefix.rstrip('/')}/{args.label}"

    with open(args.config) as f:
        base_config = yaml.safe_load(f)
    model_dir = os.path.join(args.work_dir, args.label)
    os.makedirs(model_dir, exist_ok=True)

    task_csvs = []
    for i in range(1, args.runs + 1):
        run_name = f"{args.label}_run{i}"
        run_dir = os.path.join(model_dir, f"run{i}")
        task_csv = os.path.join(run_dir, "report", f"{run_name}_tasks.csv")
        task_csvs.append(task_csv)
        if i < args.start_run:
            if not os.path.exists(task_csv):
                raise SystemExit(f"cannot resume: {task_csv} is missing")
            continue

        if os.path.exists(run_dir) and os.listdir(run_dir):
            raise SystemExit(f"{run_dir} already has files; move it away before rerunning")
        os.makedirs(run_dir, exist_ok=True)
        config = dict(base_config, run_id=run_name)
        config["runner"] = dict(base_config["runner"], output_dir=os.path.join(run_dir, "eval_outputs"))
        config_path = os.path.join(run_dir, "config.yaml")
        with open(config_path, "w") as f:
            yaml.safe_dump(config, f, sort_keys=False)
        usage_log = os.path.join(run_dir, "usage.jsonl")

        env = dict(os.environ, SUBTASK_BENCHMARK_FILE="benchmark_test.json", LLM_USAGE_LOG=usage_log)
        # A shell set up for another tool (such as Claude Code) can point the
        # Anthropic SDK at a proxy with its own token. Send requests straight to
        # the provider with ANTHROPIC_API_KEY instead.
        for var in PROXY_ENV_VARS:
            env.pop(var, None)
        print(f"[{run_name}] starting", flush=True)
        start = time.time()
        with open(os.path.join(run_dir, "eval.log"), "w") as log:
            proc = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "run_eval.py"), config_path],
                                  cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT)
        wall = round(time.time() - start, 1)
        if proc.returncode != 0:
            raise SystemExit(f"[{run_name}] run_eval.py exited with {proc.returncode}; see {run_dir}/eval.log")

        results_dirs = glob.glob(os.path.join(run_dir, "eval_outputs", run_name, "*"))
        if len(results_dirs) != 1:
            raise SystemExit(f"[{run_name}] expected one benchmark output dir, found {results_dirs}")
        subprocess.run([sys.executable, os.path.join(REPO, "scripts", "usage_report.py"),
                        "--run-dir", results_dirs[0], "--usage-log", usage_log,
                        "--wall-time", str(wall), "--out-dir", os.path.join(run_dir, "report"),
                        "--name", run_name], check=True)
        with open(os.path.join(run_dir, "run_info.json"), "w") as f:
            json.dump({"run": run_name, "wall_time_s": wall, "config": args.config}, f, indent=2)

        uploaded = s3_copy(run_dir, f"{s3_base}/run{i}/", recursive=True, profile=args.aws_profile)
        print(f"[{run_name}] done in {wall}s" + (f", uploaded to {s3_base}/run{i}/" if uploaded else ", NOT uploaded"), flush=True)

    agg = os.path.join(model_dir, f"{args.label}_aggregate.json")
    cmd = [sys.executable, os.path.join(REPO, "scripts", "aggregate_runs.py"),
           "--label", args.label, "--task-csvs", *task_csvs, "--out", agg]
    if os.path.exists(args.rate_card):
        cmd += ["--rate-card", args.rate_card]
    subprocess.run(cmd, check=True)
    s3_copy(agg, f"{s3_base}/{args.label}_aggregate.json", profile=args.aws_profile)


if __name__ == "__main__":
    main()
