import json
import logging
from abc import ABC, abstractmethod
from playwright.sync_api import sync_playwright
from typing import override

from orby.subtask_benchmark.utils import WebReplayServerSessionHandler

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("subtask_benchmark.synthetic_data_gen.dom_extractor")


class DOMExtractor(ABC):
    """
    Abstract base class for extracting DOM from various sources.
    Subclasses should implement the extract_dom method for specific source types.
    """

    @classmethod
    @abstractmethod
    def extract_dom(cls, url: str, *args, **kwargs) -> str:
        """
        Abstract method to extract DOM from a source.
        Must be implemented by subclasses.

        Args:
            url: URL of the web page to extract DOM from

        Returns:
            str: The extracted DOM content

        Raises:
            NotImplementedError: If subclass doesn't implement this method
        """
        raise NotImplementedError("Subclasses must implement extract_dom method")


class WaczDOMExtractor(DOMExtractor):

    @override
    @classmethod
    def extract_dom(cls, url: str, web_archive_path: str) -> str:
        """
        Launches a browser context that serves network requests
        from the given HAR file, navigates to `url`, waits for idle,
        and returns the HTML DOM.
        """
        # serve the wacz file from the local directory
        browser_args = {
            "disable-web-security": True,  # Disable CORS for testing
            "user-agent": "Mozilla/5.0 WebReplay Test Agent",  # Custom user agent
            "v": True,  # Verbose logging
        }

        logger.info(
            f"Starting WebReplay server for web archive file: {web_archive_path}"
        )

        # Initialize the WebReplay server handler
        handler = WebReplayServerSessionHandler(
            None,
            web_archive_path,
            url,
            browser_args=browser_args,
        )

        # Start the WebReplay server
        handler.setup_webreplay_server(run_headless=True)

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.new_context(proxy={"server": url})
            page = context.new_page()
            try:
                page.goto(url)
                page.wait_for_load_state("networkidle")
                dom = page.content()
                return dom
            except Exception as e:
                print(f"Error navigating to {url}: {e}")
                raise e
            finally:
                page.close()
                browser.close()
                handler.cleanup()


class OnlineDOMExtractor(DOMExtractor):

    @override
    @classmethod
    def extract_dom(cls, url: str) -> tuple[str, bytes]:
        """
        Launch a browser context that navigates to `url`, waits for idle,
        and returns the HTML DOM.
        """
        logger.info(f"Starting browser for {url}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url)
            try:
                page.wait_for_load_state("networkidle")
                dom = page.content()
                screenshot = page.screenshot(full_page=True)
                return dom, screenshot
            except Exception as e:
                print(f"Error navigating to {url}: {e}")
                raise e
            finally:
                page.close()
                browser.close()
