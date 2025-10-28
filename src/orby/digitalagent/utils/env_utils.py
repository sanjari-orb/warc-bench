import dotenv
from PIL import Image
import numpy as np
from typing import Any, Optional, Mapping
import gymnasium.envs.registration
import gymnasium as gym
from gymnasium import Env
import os
from gymnasium.spaces import Space
from browsergym.core.spaces import AnyDict
from playwright.sync_api import BrowserContext, Page
from orby.digitalagent.utils import orbot_extension_utils

dotenv.load_dotenv()

_INIT_SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "resources", "injected-agent.js"
)


def extra_obs(
    browser_context: Optional[BrowserContext] = None,
    page: Optional[Page] = None,
    **kwargs: Any,
):
    assert (
        browser_context is not None
    ), "Browser context is required for extra observations."
    obs = {}
    width = page.evaluate("()=> window.innerWidth")
    height = page.evaluate("()=> window.innerHeight")
    # obs["orby_root_element"] = orbot_extension_utils.get_web_state_element(
    #     browser_context, page
    # )
    obs["orby_viewport_size"] = {
        "width": width,
        "height": height,
    }
    return obs


def make(
    id: str | gymnasium.envs.registration.EnvSpec,
    max_episode_steps: int | None = None,
    disable_env_checker: bool | None = None,
    pw_chromium_kwargs: dict = {},
    **kwargs: Any,
) -> Env:
    """Creates a gymnasium environment with Orby init script installed and new observation space configured."""
    with open(_INIT_SCRIPT_PATH, "r") as f:
        init_script = f.read()
    pw_chromium_kwargs["args"] = pw_chromium_kwargs.get("args", []) + [
        "--force-device-scale-factor=1"
    ]
    env = gym.make(
        id,
        max_episode_steps=max_episode_steps,
        disable_env_checker=disable_env_checker,
        pw_chromium_kwargs=pw_chromium_kwargs,
        extra_obs_func=extra_obs,
        init_script=init_script,
        **kwargs,
    )
    # env.observation_space["orby_root_element"] = AnyDict()
    env.observation_space["orby_viewport_size"] = AnyDict()
    return env
