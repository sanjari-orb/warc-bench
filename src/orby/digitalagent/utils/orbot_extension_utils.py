"""Utilities for interacting with Orbot Chrome extension content script.
"""

import dotenv
from typing import Optional
from playwright.sync_api import BrowserContext, Page, Error
from pb.v1alpha1 import element_pb2
import base64

dotenv.load_dotenv()


def get_web_state_element(
    context: BrowserContext, page: Optional[Page] = None
) -> element_pb2.Element:
    if page:
        page.bring_to_front()

    try:
        element_base64 = page.evaluate(
            "() => window.default.snapshoter.getDomTreeBase64()"
        )
        element = element_pb2.Element()
        element.ParseFromString(base64.b64decode(element_base64))
    except Exception as e:
        raise Error(
            f"get_web_state_element encountered an error {e}. possible load incomplete or Frame was detached."
        )

    return element
