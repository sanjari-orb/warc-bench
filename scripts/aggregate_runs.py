"""Combine repeated runs of one model into avg@k score, tokens, cost and time.

Inputs are the per-task CSVs written by scripts/usage_report.py, one per run.
All runs must cover the same task ids; the script stops if they do not, since
avg@k over different task sets is not meaningful.

Score uncertainty is reported two ways:
  - run_se: standard error of the k run scores (spread between runs).
  - task_se: standard error over tasks of each task's mean success across
    runs. This is the usual error bar for an eval, and the 95% CI uses it.

Cost uses a rate card JSON of USD per million tokens, keyed by model name:
    {"claude-opus-5-5": {"input": 5, "cache_read": 0.5, "cache_write": 6.25,
                         "output": 25, "source": "...", "date": "2026-10-19"}}
Without a rate card entry for the model, cost columns are left empty.

Example:
    python scripts/aggregate_runs.py --label opus55 \\
        --task-csvs reports/opus55_run1_tasks.csv reports/opus55_run2_tasks.csv \\
                    reports/opus55_run3_tasks.csv \\
        --rate-card scripts/rate_card.json --out reports/opus55_aggregate.json
"""

import argparse
import csv
import json
import math
import os
import statistics

TOKEN_FIELDS = ["input_uncached", "input_cache_read", "input_cache_write", "output", "reasoning"]
RATE_KEYS = {"input_uncached": "input", "input_cache_read": "cache_read",
             "input_cache_write": "cache_write", "output": "output"}


def read_tasks(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit(f"{path} has no task rows")
    by_task = {}
    for r in rows:
        if r["task_id"] in by_task:
            raise SystemExit(f"{path} lists task {r['task_id']} twice")
        by_task[r["task_id"]] = r
    return by_task


def num(value):
    """CSV cell to float; empty means the provider did not report it."""
    return None if value in ("", None) else float(value)


def percentile(values, p):
    """Linear-interpolated percentile, p in [0, 100]. values must be non-empty."""
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    pos = (len(s) - 1) * p / 100
    lo = math.floor(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def sem(values):
    return statistics.stdev(values) / math.sqrt(len(values)) if len(values) > 1 else None


def run_cost_per_task(tasks, rates):
    """Mean USD per task for one run, or None if any billed field is unknown."""
    if not rates:
        return None
    total = 0.0
    for field, rate_key in RATE_KEYS.items():
        if rate_key not in rates:
            raise SystemExit(f"rate card entry is missing '{rate_key}'")
        values = [num(t[field]) for t in tasks.values()]
        if field == "input_cache_write" and all(v is None for v in values):
            continue  # provider does not bill cache writes separately
        if any(v is None for v in values):
            return None
        total += sum(values) * float(rates[rate_key]) / 1e6
    return total / len(tasks)


def r(x, nd=4):
    return None if x is None else round(x, nd)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", required=True)
    parser.add_argument("--task-csvs", nargs="+", required=True, help="One usage_report.py tasks CSV per run")
    parser.add_argument("--rate-card", help="JSON of USD per 1M tokens, keyed by model name")
    parser.add_argument("--time-limit-s", type=float,
                        help="Per-task time limit of the runs. A task with no recorded time was killed at "
                             "this limit (it scores 0), so its duration counts as this value. Without it, "
                             "such tasks are left out of the duration figures.")
    parser.add_argument("--out", required=True, help="Output JSON path")
    args = parser.parse_args()

    runs = [read_tasks(p) for p in args.task_csvs]
    task_ids = set(runs[0])
    for path, run in zip(args.task_csvs, runs):
        if set(run) != task_ids:
            diff = sorted(task_ids ^ set(run))
            raise SystemExit(f"{path} covers different tasks than {args.task_csvs[0]}: {diff[:10]}")
    n_tasks, k = len(task_ids), len(runs)

    models = {t["model"] for run in runs for t in run.values() if t["model"]}
    if len(models) > 1:
        raise SystemExit(f"runs mix models: {sorted(models)}")
    model = models.pop() if models else ""

    rates = None
    if args.rate_card:
        with open(args.rate_card) as f:
            rates = json.load(f).get(model)

    run_scores = [sum(int(t["success"]) for t in run.values()) / n_tasks for run in runs]
    task_means = [sum(int(run[tid]["success"]) for run in runs) / k for tid in sorted(task_ids)]
    score = statistics.mean(run_scores)
    task_se = sem(task_means)

    per_run = []
    for path, run in zip(args.task_csvs, runs):
        entry = {"csv": os.path.basename(path),
                 "score": r(sum(int(t["success"]) for t in run.values()) / n_tasks)}
        for field in TOKEN_FIELDS:
            values = [num(t[field]) for t in run.values()]
            entry[f"{field}_per_task"] = None if any(v is None for v in values) else r(sum(values) / n_tasks, 1)
        entry["cost_usd_per_task"] = r(run_cost_per_task(run, rates), 5)
        per_run.append(entry)

    if args.time_limit_s is not None and args.time_limit_s <= 0:
        raise SystemExit("--time-limit-s must be positive")
    times = [num(t["task_time_s"]) for run in runs for t in run.values()]
    missing_times = sum(v is None for v in times)
    if args.time_limit_s is not None:
        times = [args.time_limit_s if v is None else v for v in times]
    else:
        times = [v for v in times if v is not None]

    def mean_over_runs(key):
        values = [p[key] for p in per_run]
        return None if any(v is None for v in values) else statistics.mean(values)

    out = {
        "label": args.label,
        "model": model,
        "runs": k,
        "tasks": n_tasks,
        "score_avg_at_k": r(score),
        "run_scores": [r(s) for s in run_scores],
        "run_se": r(sem(run_scores)),
        "task_se": r(task_se),
        "ci95": None if task_se is None else [r(score - 1.96 * task_se), r(score + 1.96 * task_se)],
        "duration_s_per_task": {
            "mean": r(statistics.mean(times), 2) if times else None,
            "median": r(statistics.median(times), 2) if times else None,
            "p90": r(percentile(times, 90), 2) if times else None,
            "tasks_without_time": missing_times,
            # The value those tasks were counted at, or None if they were left out.
            "missing_time_counted_as_s": args.time_limit_s,
        },
        "tokens_per_task": {f: r(mean_over_runs(f"{f}_per_task"), 1) for f in TOKEN_FIELDS},
        "cost_usd_per_task": r(mean_over_runs("cost_usd_per_task"), 5),
        "rate_card": rates,
        "per_run": per_run,
        "refusals": sum(int(t["refusals"]) for run in runs for t in run.values()),
        "truncated_calls": sum(int(t["truncated_calls"]) for run in runs for t in run.values()),
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({k_: out[k_] for k_ in ("label", "model", "score_avg_at_k", "task_se", "cost_usd_per_task")}))


if __name__ == "__main__":
    main()
