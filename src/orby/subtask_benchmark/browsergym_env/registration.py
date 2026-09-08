"""Task registration for WARC-Bench.

Mirrors ``browsergym.core.registration.register_task``, which hardcodes
``browsergym.core.env.BrowserEnv`` as the gym entry point. WARC-Bench needs the
vendored environment in :mod:`.env` instead, so registration is reimplemented
here.

Derived from BrowserGym (https://github.com/ServiceNow/BrowserGym) version
0.13.3. Copyright 2024 ServiceNow, licensed under the Apache License,
Version 2.0. See LICENSE-BrowserGym in the repository root.
"""

from functools import partial
from typing import Type

import gymnasium as gym
from browsergym.core.registration import frozen_partial
from browsergym.core.task import AbstractBrowserTask

from .env import BrowserEnv


def register_task(
    id: str,
    task_class: Type[AbstractBrowserTask],
    task_kwargs: dict = {},
    default_task_kwargs: dict = {},
    nondeterministic: bool = True,
    *args,
    **kwargs,
):
    """Register a browser task as a gym environment under its unique id.

    Args:
        id: the id of the task to register (will be prepended by "browsergym/").
        task_class: the task class to register.
        task_kwargs: frozen task arguments (cannot be overloaded at environment
            creation time).
        default_task_kwargs: default task arguments (can be overloaded at
            environment creation time).
        nondeterministic: whether the task cannot be guaranteed deterministic
            transitions.
        *args: additional sequential arguments for the gym or browsergym environment.
        **kwargs: additional keyword arguments for the gym or browsergym environment.

    Raises:
        ValueError: if the same parameter is given both a frozen and a default value.
    """
    if task_kwargs and default_task_kwargs:
        # check overlap between frozen and default task_kwargs
        clashing_kwargs = set(task_kwargs) & set(default_task_kwargs)  # key set intersection
        if clashing_kwargs:
            raise ValueError(
                f"Illegal attempt to register Browsergym environment {id} with both "
                f"frozen and default values for task parameters {clashing_kwargs}."
            )

    # freeze task_kwargs (cannot be overriden at environment creation)
    task_entrypoint = frozen_partial(task_class, **task_kwargs)

    # pre-set default_task_kwargs (can be overriden at environment creation)
    task_entrypoint = partial(task_entrypoint, **default_task_kwargs)

    gym.register(
        id=f"browsergym/{id}",
        entry_point=lambda *env_args, **env_kwargs: BrowserEnv(
            task_entrypoint, *env_args, **env_kwargs
        ),
        nondeterministic=nondeterministic,
        *args,
        **kwargs,
    )
