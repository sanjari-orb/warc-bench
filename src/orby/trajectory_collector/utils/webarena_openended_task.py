import playwright.sync_api

from typing import Tuple
from browsergym.core.task import AbstractBrowserTask
from browsergym.webarena.instance import WebArenaInstance


# TODO: Replace with env var based matching
def find_task_type(url: str) -> str:
    if ":7780" in url:
        return "shopping_admin"
    elif ":7770" in url:
        return "shopping"
    elif ":9999" in url:
        return "reddit"
    elif ":8023" in url:
        return "gitlab"
    elif ":3000" in url:
        return "map"
    elif ":8888" in url:
        return "wikipedia"
    return url


class WebArenaOpenEndedTask(AbstractBrowserTask):
    @classmethod
    def get_task_id(cls):
        return "wa_openended"

    def __init__(self, seed: int, start_url: str, goal: str = None) -> None:
        """
        Args:
            seed: random seed.
            start_url: str, the url for the starting page.
            goal: str, the initial goal.

        """
        super().__init__(seed)
        self.start_url = start_url
        self.goal = goal
        self.task_type = find_task_type(start_url)

        self.webarena_instance = WebArenaInstance()
        # Replace start URL with correct start URL
        self.start_url = self.webarena_instance.urls[self.task_type]

    def setup(self, page: playwright.sync_api.Page) -> tuple[str, dict]:
        self.webarena_instance.ui_login(site=self.task_type, page=page)

        page.goto(self.start_url, timeout=0)
        return self.goal, {}

    def teardown(self) -> None:
        pass

    def validate(
        self, page: playwright.sync_api.Page, chat_messages: list[str]
    ) -> Tuple[float, bool, str, dict]:
        reward, done, msg, info = 0, False, "", {}

        for message in chat_messages:
            if message["role"] == "user" and message["message"] == "exit":
                done = True
                break

        return reward, done, msg, info


# register the open-ended task
from browsergym.core.registration import register_task

register_task(WebArenaOpenEndedTask.get_task_id(), WebArenaOpenEndedTask)
