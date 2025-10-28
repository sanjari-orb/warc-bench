#!/usr/bin/env python3
"""
Minimal example script demonstrating how to use the WebReplayServerSessionHandler utility.
This script starts a WebReplay server for a specific task, connects to it,
and then cleans up resources properly.
"""

import sys
import time
import argparse
import json
import logging
from playwright.sync_api import sync_playwright

from orby.subtask_benchmark.utils import WebReplayServerSessionHandler
from orby.subtask_benchmark.evaluator.evaluator import EvaluatorRegistry

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("webreplay_server_check")


def main():
    """
    Run a minimal example of the WebReplayServerSessionHandler.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="WebReplay Server Test Script")
    parser.add_argument("--task-id", "-t", required=True, help="Task ID to replay")
    parser.add_argument(
        "--debugging-port", type=int, default=9222, help="Chrome debugging port"
    )
    parser.add_argument(
        "--headless", action="store_true", help="Run Chrome in headless mode"
    )
    parser.add_argument(
        "--timeout", type=int, default=10, help="Server timeout in seconds"
    )
    args = parser.parse_args()

    # Example browser arguments (customize as needed)
    browser_args = {
        "disable-web-security": True,  # Disable CORS for testing
        "user-agent": "Mozilla/5.0 WebReplay Test Agent",  # Custom user agent
        "v": True,  # Verbose logging
    }

    print(f"Starting WebReplay server for task: {args.task_id}")

    # Initialize the WebReplay server handler
    handler = WebReplayServerSessionHandler(
        task_id=args.task_id,
        debugging_port=args.debugging_port,
        browser_args=browser_args,
    )

    # Start the WebReplay server
    server_url = handler.setup_webreplay_server(run_headless=args.headless)

    print(f"WebReplay server started at {server_url}")
    print(f"Chrome debugging available at localhost:{args.debugging_port}")

    # Get task config from the handler (it loads it automatically)
    task_config = handler.task_config
    if not task_config:
        logger.error("Failed to load task configuration")
        return 1

    # Print the task goal clearly for the labeller
    print("\n" + "=" * 60)
    print("TASK GOAL:")
    print("=" * 60)
    print(f"{task_config.get('goal', 'No goal specified')}")
    print("=" * 60 + "\n")

    # Initialize evaluator
    try:
        eval_type = task_config["eval"]["eval_type"]
        evaluation_script = task_config["eval"]["evaluate_scripts"][0]["script"]
        evaluator = EvaluatorRegistry.create(
            eval_type=eval_type,
            evaluation_script=evaluation_script,
        )
        logger.info(f"Initialized evaluator of type: {eval_type}")
    except Exception as e:
        logger.error(f"Error initializing evaluator: {e}")
        return 1

    # Connect to the browser using Playwright
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(
                f"http://localhost:{args.debugging_port}"
            )
            page = (
                browser.contexts[0].pages[0]
                if browser.contexts and browser.contexts[0].pages
                else browser.contexts[0].new_page()
            )

            print("Browser connected successfully")
            print("You can now interact with the page...")

            # Wait for user input
            while True:
                user_input = (
                    input("Are you ready to check the reward now? (Y/n): ")
                    .strip()
                    .lower()
                )
                if user_input in ["y", "yes", ""]:
                    # Get answer (this might need to be customized based on your specific use case)
                    answer = input(
                        "Enter the answer to evaluate (or press Enter for empty): "
                    ).strip()

                    # Evaluate the task
                    try:
                        reward = evaluator.evaluate(answer, page)
                        logger.info(f"Reward: {reward}")
                        print(f"Reward: {reward}")
                    except Exception as e:
                        logger.error(f"Error during evaluation: {e}")
                        print(f"Error during evaluation: {e}")

                    break
                elif user_input in ["n", "no"]:
                    print("Evaluation cancelled.")
                    break
                else:
                    print("Please enter Y/yes or N/no")

            browser.close()

    except Exception as e:
        logger.error(f"Error connecting to browser: {e}")
        print(f"Error connecting to browser: {e}")

    # Always clean up resources
    if "handler" in locals():
        print("Cleaning up WebReplay server...")
        handler.cleanup()
    else:
        raise ValueError(
            "Do not remove the handler variable, else the clean up behaviour will get affected.."
        )

    print("WebReplay server test completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
