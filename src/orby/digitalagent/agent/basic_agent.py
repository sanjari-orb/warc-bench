from copy import deepcopy

from orby.digitalagent.agent import Agent, LoggingMetaWrapper
from orby.digitalagent.agent.utils import prepare_image_input, screenshots_differ
from orby.digitalagent.model import FoundationModel
from orby.digitalagent.utils.image_utils import download_image_as_numpy_array
from orby.digitalagent.prompts.basic.prompts_20241007 import (
    SYSTEM_PROMPT,
    GROUNDING_PROMPT_BEFORE_IMG,
    GOAL_IMAGES_PROMPT,
    ANSWER_PROMPT,
    grounding_prompt_after_img,
)


class BasicFMAgent(Agent):
    def __init__(self, model_configs: dict, actions: str, limit_to_ctx: bool = True):
        Agent.__init__(self)
        self.model_configs = model_configs
        self.model = FoundationModel(**model_configs) if model_configs else None
        self.actions = actions
        self.messages = []
        self.limit_to_ctx = limit_to_ctx

    def reset(self, goal, html, screenshot, goal_image_urls=[]):
        self.goal_images = [
            download_image_as_numpy_array(url) for url in goal_image_urls
        ]
        self.goal = goal
        image_dict = prepare_image_input(screenshot)
        if len(self.goal_images) > 0:
            goal_image_msgs = [
                {"type": "text", "text": GOAL_IMAGES_PROMPT},
                *[prepare_image_input(image) for image in self.goal_images],
            ]
        else:
            goal_image_msgs = []
        self.messages = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT.format(
                            goal=self.goal, actions=self.actions
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    *goal_image_msgs,
                    {
                        "type": "text",
                        "text": GROUNDING_PROMPT_BEFORE_IMG,
                    },
                    image_dict,  # TODO make multimodal optional
                    {
                        "type": "text",
                        "text": grounding_prompt_after_img(
                            html=html, trace_string="", screenshot=screenshot
                        ),
                    },
                ],
            },
        ]
        self.html_history = [html]
        self.screenshot_history = [screenshot]

    def update(self, html, screenshot, trace):
        contents = []
        self.trace = trace
        if html != self.html_history[-1]:
            self.cached_html = html
            contents.append(
                {
                    "type": "text",
                    "text": f"Please update your bid caching. The HTML has changed to: {html}\n",
                }
            )

        if screenshots_differ(screenshot, self.screenshot_history[-1]):
            image_dict = prepare_image_input(screenshot)
            contents.append(
                {
                    "type": "text",
                    "text": "The screenshot has changed. Here is the new image of the webpage, please use it to locate elements and cache coordinates:\n",
                }
            )
            contents.append(image_dict)

        self.html_history.append(html)
        self.screenshot_history.append(screenshot)

        if len(contents) == 0:
            contents.append(
                {
                    "type": "text",
                    "text": f"Nothing has changed. Please verify your bid caching now. The HTML is still {html}.",
                }
            )

        contents.append(
            {
                "type": "text",
                "text": f"Here is the trace of previous actions, of the form (action, error): {trace}\n My goal is again: {self.goal}\nIf a previous action failed, please avoid repeating the same mistakes.",
            }
        )
        contents.append({"type": "text", "text": ANSWER_PROMPT})

        self.messages.append({"role": "user", "content": contents})

    def act(self, **kwargs):
        successful = False
        while not successful:
            try:
                action, response = self.model.generate(
                    messages=self.messages, return_raw=True, **kwargs
                )
                successful = True
            except Exception as e:
                print("Got this exception: ", e)
                self.messages.pop(1)

        # Create metadata of the action
        meta = {
            "llm_interactions": [
                {
                    "model_family": self.model.model_provider,
                    "model_name": self.model.model_name,
                    "prompts": self.messages,
                    "response": action,
                }
            ],
            "memory": {
                "trace": self.trace,
            },
        }

        self.messages.append({"role": "assistant", "content": action})
        return action, meta

    def get_state_dict(self):
        state_dict = super().get_state_dict()

        state_dict["messages"] = deepcopy(self.messages)

        return state_dict

    def load_state_dict(self, state_dict):
        self.messages = state_dict["messages"]

        super().load_state_dict(state_dict)
