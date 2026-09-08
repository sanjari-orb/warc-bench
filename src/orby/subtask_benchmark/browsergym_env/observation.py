"""Screenshot capture for WARC-Bench.

Replaces ``browsergym.core.observation.extract_screenshot``, which grabs the
page over a fresh CDP session using ``Page.captureScreenshot`` with
``captureBeyondViewport``. That path does not work against the WARC replay
server: the environment attaches to a browser started by the replay server, and
opening a second CDP session on the same page returns a frame sized to the
document rather than the viewport, so screenshots do not line up with the
coordinates the agent acts on.

Playwright's own ``page.screenshot()`` captures the viewport as rendered, which
is what the agent sees and what the recorded results were produced with.
"""

import io

import numpy as np
import PIL.Image
import playwright.sync_api


def extract_screenshot(page: playwright.sync_api.Page) -> np.ndarray:
    """Extract the screenshot of a page using Playwright.

    Appends a "cheap" version of the screenshot to the observation, as a
    ``uint8`` array of shape (height, width, 3) in RGB order.

    Args:
        page: the playwright page of which to extract the screenshot.

    Returns:
        A screenshot of the page, in the form of a 3D array (height, width, rgb).
    """
    screenshot_bytes = page.screenshot()
    with io.BytesIO(screenshot_bytes) as f:
        # load png as a PIL image
        img = PIL.Image.open(f)
        # convert to RGB (3 channels)
        img = img.convert(mode="RGB")
        # convert to a numpy array
        img = np.array(img)

    return img
