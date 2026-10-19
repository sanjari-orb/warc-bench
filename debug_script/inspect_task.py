"""Load one task with the replay server and record what goes wrong.

Prints failed and 4xx/5xx requests, console errors and page errors, and saves
a screenshot after loading and after each optional click. Requests the archive
cannot answer come back as 404, so this shows which pages or scripts an
archive is missing.

Examples:
    python debug_script/inspect_task.py online.136
    # Replay clicks (viewport pixels at 1280x720) and see what each one requests:
    python debug_script/inspect_task.py online.204 --click 34,151 --click 974,226 --click 854,123
    # Load in a fresh tab so the log covers the page's very first request:
    python debug_script/inspect_task.py online.136 --fresh-tab
    # Try a fixed page clock (ms since epoch) or extra Chrome flags:
    python debug_script/inspect_task.py online.110 --timestamp 1757532296497 --browser-arg enable-features=SharedArrayBuffer
"""

import argparse
import os
import time

from playwright.sync_api import sync_playwright

from orby.subtask_benchmark.utils import WebReplayServerSessionHandler


def parse_click(text: str) -> tuple[float, float]:
    try:
        x, y = (float(v) for v in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected x,y, got {text!r}")
    return x, y


def parse_browser_arg(text: str) -> tuple[str, object]:
    key, sep, value = text.partition("=")
    return key, (value if sep else True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task_id")
    parser.add_argument("--wait", type=float, default=15, help="Seconds to let the page load")
    parser.add_argument("--click", type=parse_click, action="append", default=[], help="x,y to click, in order")
    parser.add_argument("--after-click-wait", type=float, default=6)
    parser.add_argument("--fresh-tab", action="store_true", help="Open the start URL in a new tab with logging on")
    parser.add_argument("--timestamp", type=int, help="Fixed page clock in ms since epoch")
    parser.add_argument("--browser-arg", type=parse_browser_arg, action="append", default=[], help="Chrome flag, e.g. key=value")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--port", type=int, default=9700)
    parser.add_argument("--out", default="inspect_output", help="Directory for screenshots")
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    handler = WebReplayServerSessionHandler(task_id=args.task_id, debugging_port=args.port,
                                            viewport_width=1280, viewport_height=720,
                                            browser_args=dict(args.browser_arg) or None)
    if args.timestamp:
        env = dict(handler.task_config["env"], timestamp={"seconds": args.timestamp // 1000,
                                                          "nanos": (args.timestamp % 1000) * 1_000_000})
        handler.task_config = dict(handler.task_config, env=env)

    events, phase = [], ["load"]

    def watch(page):
        page.on("response", lambda r: r.status >= 400 and events.append((phase[0], f"{r.status} {r.request.method} {r.url}")))
        page.on("requestfailed", lambda r: events.append((phase[0], f"FAILED {r.failure} {r.method} {r.url}")))
        page.on("console", lambda m: m.type == "error" and events.append((phase[0], f"console: {m.text}")))
        page.on("pageerror", lambda e: events.append((phase[0], f"page error: {e}")))

    try:
        handler.setup_webreplay_server(run_headless=not args.headed)
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(f"http://localhost:{args.port}")
            if args.fresh_tab:
                page = browser.contexts[0].new_page()
                watch(page)
                page.goto(handler.task_config["env"]["start_url"], wait_until="commit")
            else:
                page = next(pg for c in browser.contexts for pg in c.pages if pg.url != "about:blank")
                watch(page)
            time.sleep(args.wait)
            page.screenshot(path=os.path.join(args.out, f"{args.task_id}_0_load.png"))
            for n, (x, y) in enumerate(args.click, start=1):
                phase[0] = f"click {n} ({x:g},{y:g})"
                page.mouse.click(x, y)
                time.sleep(args.after_click_wait)
                page.screenshot(path=os.path.join(args.out, f"{args.task_id}_{n}_click.png"))
            print("final url:", page.url)
    finally:
        handler.cleanup()

    phases = ["load"] + [f"click {n} ({x:g},{y:g})" for n, (x, y) in enumerate(args.click, start=1)]
    for ph in phases:
        items = [e for p, e in events if p == ph]
        print(f"== {ph}: {len(items)} problems")
        for e in items:
            print("   ", e[:300])
    print(f"screenshots in {args.out}/")


if __name__ == "__main__":
    main()
