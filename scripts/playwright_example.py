#!/usr/bin/env python3
"""
Example script showing how to connect to a browser instance launched by webreplay-standalone
using Python Playwright directly.

Usage:
1. Start webreplay-standalone with the --debugging-port option:
   node dist/index.js serve your-file.txtpb --debugging-port 9222

2. Run this script to connect to the browser and control it:
   python src/playwright_example.py
"""

import asyncio
import sys
import time
import logging
import os
from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("playwright_client")


def connect_to_browser(
    debugging_port: int = 9222, max_retries: int = 10, retry_interval: int = 2
) -> None:
    """
    Connect to a browser running with CDP debugging enabled and perform actions.

    Args:
        debugging_port: The port number where the browser's debugging interface is exposed
        max_retries: Maximum number of connection attempts
        retry_interval: Seconds to wait between retries
    """
    logger.info(f"Attempting to connect to browser on port {debugging_port}")

    retries = 0
    while retries < max_retries:
        try:
            with sync_playwright() as p:
                # Connect to the existing browser instance through CDP
                browser_url = f"http://localhost:{debugging_port}"
                logger.info(f"Connecting to: {browser_url}")

                browser = p.chromium.connect_over_cdp(browser_url)
                logger.info(f"Connected to browser: {browser}")

                # Get existing contexts or create a new one
                contexts = browser.contexts
                if contexts:
                    logger.info(f"Found {len(contexts)} existing browser contexts")
                    context = contexts[0]  # Use the first available context
                else:
                    logger.info("No existing context found, creating a new one")
                    context = browser.new_context()

                # Create a new page
                page = context.new_page()

                # Example: Navigate to a website
                logger.info("Navigating to example.com...")
                page.goto("https://www.mercuryinsurance.com")

                # Example: Get page title
                title = page.title()
                logger.info(f"Page title: {title}")

                # Example: Get all links on the page
                links = page.evaluate(
                    """
                    Array.from(document.querySelectorAll('a')).map(a => ({
                        text: a.textContent.trim(),
                        href: a.href
                    }))
                """
                )
                import pdb

                pdb.set_trace()
                logger.info(f"Found {len(links)} links on the page:")
                for link in links:
                    logger.info(f"  - {link['text']}: {link['href']}")

                # Example: Take a screenshot
                screenshots_dir = Path("screenshots")
                screenshots_dir.mkdir(exist_ok=True)

                screenshot_path = screenshots_dir / f"example_{int(time.time())}.png"
                page.screenshot(path=str(screenshot_path))
                logger.info(f"Saved screenshot to {screenshot_path}")

                # Example: Execute a more complex browser automation task
                logger.info("Demonstrating more complex automation...")

                # Click on the "More information" link
                try:
                    more_info = page.get_by_text("More information")
                    if more_info:
                        logger.info("Clicking 'More information' link")
                        more_info.click()

                        # Wait for navigation
                        page.wait_for_load_state("networkidle")

                        # Get the new page title
                        new_title = page.title()
                        logger.info(f"Navigated to new page: {new_title}")

                        # Take another screenshot
                        screenshot_path = (
                            screenshots_dir / f"more_info_{int(time.time())}.png"
                        )
                        page.screenshot(path=str(screenshot_path))
                        logger.info(f"Saved screenshot to {screenshot_path}")
                except Exception as e:
                    logger.warning(f"Could not click 'More information': {e}")

                # You can leave the page open, as the browser was started by webreplay-standalone
                # and will continue running even if we disconnect
                logger.info(
                    "Disconnecting from the browser (browser will continue running)"
                )
                browser.close()
                return

        except Exception as e:
            logger.error(f"Attempt {retries + 1}/{max_retries} failed: {e}")
            retries += 1
            if retries < max_retries:
                logger.info(f"Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)

    logger.error(f"Failed to connect after {max_retries} attempts")
    sys.exit(1)


if __name__ == "__main__":
    # Default debugging port, should match what you used with webreplay-standalone
    debugging_port = 4222

    # You can override the port from command line
    if len(sys.argv) > 1:
        try:
            debugging_port = int(sys.argv[1])
        except ValueError:
            logger.error(f"Invalid port number: {sys.argv[1]}")
            sys.exit(1)

    connect_to_browser(debugging_port)
