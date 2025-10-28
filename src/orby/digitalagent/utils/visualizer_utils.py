"""
Utilities for visualizer tool. These are very specific to the 
tool's use case, so please do not use these generally.
"""

from bs4 import BeautifulSoup
import copy
import io
import json
from PIL import Image, ImageDraw
import re
import streamlit as st

from orby.digitalagent.utils import dom_utils
from browsergym.utils.obs import flatten_axtree_to_str, flatten_dom_to_str

from orby.protos.fm.trajectory_data_pb2 import TrajectoryData
from orby.protos.fm import action_data_pb2


BID_ACTIONS = [
    "fill",
    "select_option",
    "click",
    "dblclick",
    "hover",
    "press",
    "focus",
    "clear",
    "drag_and_drop",
    "upload_file",
]


def find_axtree_representation(web_state: action_data_pb2.WebState) -> str:
    """
    Axtree to be used as observation for re-running an agent step.
    """
    if web_state.browser_gym_observation:
        return flatten_axtree_to_str(
            read_browsergym_json(web_state.browser_gym_observation.axtree)
        )

    print("Did not find the axtree in browsergym observation..")
    # Else this might be a TC or labelled trajectory,
    # which only populates the dom_tree
    if web_state.root_element:
        return dom_utils.html_to_string(web_state.root_element)

    return "Debugger is using the wrong HTML!! Please check!"


def _result(trajectory: TrajectoryData):
    """
    Simple conversion to find whether a trajectory failed/succeeded.
    """
    if trajectory.success.answer:
        return "succeeded", trajectory.success.answer
    else:
        return "failed!", f"Failure code: {trajectory.failure.failure_message}"


def viewport_to_image(
    viewport: action_data_pb2.Viewport,
    action_data: action_data_pb2.ActionData | None = None,
) -> Image:
    """
    Util method to take an input Viewport object and
    return a PIL.Image object corresponding to it.

    In case action_data is provided, we also try to visualize
    where the click occured on the viewport.
    """
    if not action_data:
        return Image.open(io.BytesIO(viewport.screenshot.content))

    # If action data is given, you can visualize click as well
    image = Image.open(io.BytesIO(viewport.screenshot.content))
    width, height = image.size
    for ui_event in action_data.action.raw_events:
        if ui_event.mouse:
            x = (
                ui_event.mouse.viewport_x
                / action_data.action.before_state.viewport_width
                * width
            )
            y = (
                ui_event.mouse.viewport_y
                / action_data.action.before_state.viewport_height
                * height
            )
            draw = ImageDraw.Draw(im=image)
            draw.rectangle((x - 20, y - 20, x + 20, y + 20), width=5, outline="red")

    # TODO: If UI event is not found, can we visualize the browsergym click?
    # Tried this, but the bbox information is rarely contained in the dom
    # dom = read_browsergym_json(action_data.before_state.browser_gym_observation.dom)
    # bid = extract_action_bid(find_action_string(action_data))
    # if bid in dom['documents'][0]['nodes']['backendNodeId']:
    #     node_idx = dom['documents'][0]['nodes']['backendNodeId'].index(bid)
    #     if node_idx in dom['documents'][0]['layout']['nodeIndex']:
    #         bbox_idx = dom['documents'][0]['layout']['nodeIndex'].index(node_idx)
    #         bbox = dom['documents'][0]['layout']['bounds'][bbox_idx]
    #         draw = ImageDraw.Draw(im=image)
    #         draw.rectangle(bbox, width=5, outline='red')
    return image


def find_action_string(action_data: action_data_pb2.ActionData) -> str:
    """
    Util to extract action description from ActionData object.
    """
    if action_data.browser_gym_action.action_string:
        return action_data.browser_gym_action.action_string

    # Else try to find the orbot action's description itself
    return action_data.action.description


def find_html_element_of_action(action_data: action_data_pb2.ActionData):
    """
    Util to find HTML element on which an action was performed.
    """
    before_state = action_data.before_state
    html = flatten_dom_to_str(
        read_browsergym_json(before_state.browser_gym_observation.dom)
    )
    soup = BeautifulSoup(html, "html.parser")
    try:
        action_bid = extract_action_bid_from_action_string(
            find_action_string(action_data)
        )
        st.text(f"extracting for bid {action_bid}...")
        element = soup.find_all(attrs={"bid": str(action_bid)})[0]

        return element

    except Exception as e:
        print(e)
        return "Could not locate element by BID."


def extract_action_bid_from_action_string(string: str):
    """
    Util method to extract the numerical bid from the browsergym action
    string.
    """
    find_bid_action = False
    for bid_action in BID_ACTIONS:
        if string.startswith(bid_action):
            find_bid_action = True
            break
    if not find_bid_action:
        raise ValueError("No bid action is found.")
    candidates = re.findall(r"\d+", string)
    return candidates[0]


def read_browsergym_json(bytes):
    """
    Read browsergym environment serialized json fields.
    """
    return json.loads(bytes)
