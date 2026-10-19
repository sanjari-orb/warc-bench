"""Load each benchmark task, screenshot its start page, and run its evaluator on
the untouched page.

Flags tasks whose page fails to load, comes up blank, or whose evaluator
already reports success before the agent does anything. Run it after changing
archives, the replay server, or evaluators.

Example (test split, 8 tasks at a time):
    SUBTASK_BENCHMARK_FILE=benchmark_test.json python debug_script/check_envs.py --out env_check --workers 8
"""

import argparse
import collections
import io
import json
import multiprocessing
import os
import time

from PIL import Image
from playwright.sync_api import sync_playwright

from orby.subtask_benchmark.config import get_config
from orby.subtask_benchmark.evaluator.evaluator import EvaluatorRegistry
from orby.subtask_benchmark.utils import WebReplayServerSessionHandler

BLANK_SHARE = 0.97  # a screenshot is "blank" if one color covers this share of it


def blankness(png: bytes) -> tuple[float, int]:
    small = Image.open(io.BytesIO(png)).convert("RGB").resize((160, 90))
    counts = collections.Counter(small.getdata())
    return counts.most_common(1)[0][1] / (160 * 90), len(counts)


def check_task(task: dict, port: int, wait_s: float, shots_dir: str) -> dict:
    row = {"task_id": task["task_id"], "eval_type": task["eval"]["eval_type"]}
    handler = WebReplayServerSessionHandler(task_id=task["task_id"], debugging_port=port,
                                            viewport_width=1280, viewport_height=720)
    try:
        handler.setup_webreplay_server(run_headless=True)
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(f"http://localhost:{port}")
            page = next((pg for c in browser.contexts for pg in c.pages if pg.url != "about:blank"), None)
            if page is None:
                row["error"] = "no page opened"
                return row
            time.sleep(wait_s)
            png = page.screenshot()
            with open(os.path.join(shots_dir, f"{task['task_id']}.png"), "wb") as f:
                f.write(png)
            top_share, colors = blankness(png)
            row.update(url=page.url, top_color_share=round(top_share, 2), colors=colors, blank=top_share > BLANK_SHARE)
            if row["eval_type"] == "js_matcher":
                evaluator = EvaluatorRegistry.create(
                    eval_type="js_matcher", evaluation_script=task["eval"]["evaluate_scripts"][0]["script"])
                row["reward_untouched"] = evaluator.evaluate("", page)
    except Exception as e:  # report and move on to the next task
        row["error"] = f"{type(e).__name__}: {e}"[:300]
    finally:
        handler.cleanup()
    return row


def run_shard(args):
    tasks, port, wait_s, out_dir = args
    shots_dir = os.path.join(out_dir, "screenshots")
    return [check_task(t, port, wait_s, shots_dir) for t in tasks]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True, help="Output directory for results.jsonl and screenshots/")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--wait", type=float, default=12, help="Seconds to let each page load")
    parser.add_argument("--tasks", nargs="*", help="Only these task ids (default: all)")
    parser.add_argument("--base-port", type=int, default=9800)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    seen, tasks = set(), []
    for t in get_config():
        if t["task_id"] not in seen and (not args.tasks or t["task_id"] in args.tasks):
            seen.add(t["task_id"])
            tasks.append(t)
    if not tasks:
        raise SystemExit("No matching tasks")
    os.makedirs(os.path.join(args.out, "screenshots"), exist_ok=True)

    shards = [(tasks[i::args.workers], args.base_port + i, args.wait, args.out) for i in range(args.workers)]
    with multiprocessing.Pool(args.workers) as pool:
        rows = [r for shard in pool.map(run_shard, shards) for r in shard]

    with open(os.path.join(args.out, "results.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    errors = [r for r in rows if "error" in r]
    blank = [r["task_id"] for r in rows if r.get("blank")]
    trivial = [r["task_id"] for r in rows if r.get("reward_untouched")]
    print(f"checked {len(rows)} tasks: {len(errors)} errors, {len(blank)} blank, {len(trivial)} pass untouched")
    for r in errors:
        print("  error", r["task_id"], r["error"])
    if blank:
        print("  blank:", " ".join(blank))
    if trivial:
        print("  evaluator passes untouched page:", " ".join(trivial))


if __name__ == "__main__":
    main()
