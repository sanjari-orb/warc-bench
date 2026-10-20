"""Write a per-task CSV and a summary row for one eval run.

Inputs are the run's output directory (with one results.json per task) and the
usage log written when the run was started with LLM_USAGE_LOG set.

Example:
    LLM_USAGE_LOG=usage.jsonl python scripts/run_eval.py scripts/eval_configs/test_split.yaml
    python scripts/usage_report.py \\
        --run-dir eval_outputs/<run>/subtaskbench_run1_<model> \\
        --usage-log usage.jsonl --wall-time 1252 --out-dir reports
"""

import argparse
import csv
import glob
import json
import os

TOKEN_FIELDS = ["input_uncached", "input_cache_read", "input_cache_write", "output", "reasoning"]


def load_usage(path):
    calls, task_ends = [], {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            task_id = (rec.get("task") or "").split("subtaskbench.")[-1]
            if rec.get("event") == "llm_call":
                calls.append((task_id, rec))
            elif rec.get("event") == "task_end":
                task_ends[task_id] = rec
    return calls, task_ends


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-dir", required=True, help="Directory containing browsergym/<task>/results.json")
    parser.add_argument("--usage-log", required=True, help="JSONL file written via LLM_USAGE_LOG")
    parser.add_argument("--wall-time", type=float, required=True, help="Wall-clock seconds the whole run took")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--name", help="Run name used in file names (default: the run directory name)")
    args = parser.parse_args()

    task_dirs = glob.glob(os.path.join(args.run_dir, "browsergym", "*"))
    if not task_dirs:
        raise SystemExit(f"No task directories under {args.run_dir}/browsergym")
    calls, task_ends = load_usage(args.usage_log)
    name = args.name or os.path.basename(os.path.normpath(args.run_dir))
    os.makedirs(args.out_dir, exist_ok=True)

    rows = []
    for d in task_dirs:
        task_id = os.path.basename(d).split("subtaskbench.")[-1]
        results_path = os.path.join(d, "results.json")
        res = json.load(open(results_path)) if os.path.exists(results_path) else {}
        steps = res.get("steps")
        task_calls = [c for t, c in calls if t == task_id]
        row = {
            "task_id": task_id,
            "success": int(bool(res.get("success"))),
            "steps": steps if isinstance(steps, int) else len(steps or []),
            "task_time_s": task_ends.get(task_id, {}).get("elapsed_s"),
            "llm_calls": len(task_calls),
            "model": task_calls[0]["model"] if task_calls else "",
        }
        for field in TOKEN_FIELDS:
            values = [c.get(field) for c in task_calls]
            # Left empty when no call reported the field (older Anthropic models
            # count thinking inside output tokens without a separate figure).
            row[field] = "" if values and all(v is None for v in values) else sum(v or 0 for v in values)
        row["refusals"] = sum(1 for c in task_calls if c.get("stop_reason") == "refusal")
        row["truncated_calls"] = sum(1 for c in task_calls if c.get("stop_reason") in ("max_tokens", "length"))
        rows.append(row)
    rows.sort(key=lambda r: (len(r["task_id"]), r["task_id"]))

    with open(os.path.join(args.out_dir, f"{name}_tasks.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    n = len(rows)
    passed = sum(r["success"] for r in rows)
    times = [r["task_time_s"] for r in rows if r["task_time_s"] is not None]
    summary = {
        "run": name,
        "model": next((r["model"] for r in rows if r["model"]), ""),
        "tasks": n,
        "passed": passed,
        "score": round(passed / n, 4),
        "wall_time_s": args.wall_time,
        "avg_task_time_s": round(sum(times) / len(times), 1) if times else "",
        "avg_steps": round(sum(r["steps"] for r in rows) / n, 2),
        "llm_calls": sum(r["llm_calls"] for r in rows),
    }
    for field in TOKEN_FIELDS:
        values = [r[field] for r in rows if r[field] != ""]
        summary[field] = sum(values) if values else ""
    summary["refusals"] = sum(r["refusals"] for r in rows)
    summary["truncated_calls"] = sum(r["truncated_calls"] for r in rows)

    summary_path = os.path.join(args.out_dir, "summary.csv")
    write_header = not os.path.exists(summary_path)
    with open(summary_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary))
        if write_header:
            writer.writeheader()
        writer.writerow(summary)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
