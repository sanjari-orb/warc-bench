"""Combine the per-model aggregate JSONs from aggregate_runs.py into one table.

Writes results.csv (one row per model, every metric) and results.md (a
readable table) to --out-dir. Models are listed in the order given by
--labels, or by label name if --labels is not set.

Example:
    python scripts/summarize_results.py --runs-dir runs --out-dir runs/results
"""

import argparse
import csv
import glob
import json
import os

TOKEN_FIELDS = ["input_uncached", "input_cache_read", "input_cache_write", "output", "reasoning"]


def row_for(agg):
    dur = agg.get("duration_s_per_task") or {}
    tok = agg.get("tokens_per_task") or {}
    ci = agg.get("ci95") or [None, None]
    row = {
        "label": agg["label"],
        "model": agg["model"],
        "runs": agg["runs"],
        "tasks": agg["tasks"],
        "score_avg_at_k": agg["score_avg_at_k"],
        "run_scores": " ".join(str(s) for s in agg["run_scores"]),
        "run_se": agg["run_se"],
        "task_se": agg["task_se"],
        "ci95_low": ci[0],
        "ci95_high": ci[1],
        "cost_usd_per_task": agg["cost_usd_per_task"],
        "duration_mean_s": dur.get("mean"),
        "duration_median_s": dur.get("median"),
        "duration_p90_s": dur.get("p90"),
        "tasks_without_time": dur.get("tasks_without_time"),
    }
    for field in TOKEN_FIELDS:
        row[f"{field}_per_task"] = tok.get(field)
    row["truncated_calls"] = agg["truncated_calls"]
    row["refusals"] = agg["refusals"]
    rates = agg.get("rate_card") or {}
    row["rate_card_date"] = rates.get("date")
    return row


def pct(x):
    return "" if x is None else f"{x * 100:.2f}%"


def num(x, nd=0):
    return "" if x is None else f"{x:,.{nd}f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs-dir", required=True, help="Directory with <label>/<label>_aggregate.json files")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--labels", nargs="+", help="Model labels, in table order")
    args = parser.parse_args()

    paths = glob.glob(os.path.join(args.runs_dir, "*", "*_aggregate.json"))
    aggs = {}
    for p in paths:
        with open(p) as f:
            agg = json.load(f)
        if agg["label"] in aggs:
            raise SystemExit(f"two aggregate files for label {agg['label']}")
        aggs[agg["label"]] = agg
    if not aggs:
        raise SystemExit(f"no *_aggregate.json files under {args.runs_dir}")
    order = [l for l in (args.labels or sorted(aggs)) if l in aggs]
    rows = [row_for(aggs[l]) for l in order]

    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "results.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "| Model | Score (avg@k) | 95% CI | Task SE | Run SE | Cost / task | "
        "Duration mean / median / p90 (s) | Uncached in / task | Cached in / task | "
        "Cache write / task | Output / task | Reasoning / task | Cut-off calls | Refusals |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        cost = "" if r["cost_usd_per_task"] is None else f"${r['cost_usd_per_task']:.4f}"
        lines.append(
            f"| {r['model']} | {pct(r['score_avg_at_k'])} (runs: {r['run_scores']}) | "
            f"{pct(r['ci95_low'])} to {pct(r['ci95_high'])} | {pct(r['task_se'])} | {pct(r['run_se'])} | {cost} | "
            f"{num(r['duration_mean_s'], 1)} / {num(r['duration_median_s'], 1)} / {num(r['duration_p90_s'], 1)} | "
            f"{num(r['input_uncached_per_task'])} | {num(r['input_cache_read_per_task'])} | "
            f"{num(r['input_cache_write_per_task'])} | {num(r['output_per_task'])} | "
            f"{num(r['reasoning_per_task'])} | {r['truncated_calls']} | {r['refusals']} |"
        )
    dates = sorted({r["rate_card_date"] for r in rows if r["rate_card_date"]})
    lines += ["", f"Cost uses list prices from scripts/rate_card.json (dated {', '.join(dates) or 'n/a'})."]
    with open(os.path.join(args.out_dir, "results.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
