from orby.digitalagent.agent.utils import prepare_image_input, screenshots_differ
from orby.digitalagent.utils.image_utils import download_image_as_numpy_array
from orby.digitalagent.prompts.basic.prompts_20241119 import (
    SYSTEM_PROMPT,
    GROUNDING_PROMPT_BEFORE_IMG,
    GOAL_IMAGES_PROMPT,
    ANSWER_PROMPT,
    grounding_prompt_after_img,
)
from .basic_agent import BasicFMAgent
from orby.digitalagent.utils.action_parsing_utils import extract_content_by_tags


class BasicCoTFMAgent(BasicFMAgent):
    def __init__(
        self,
        model_configs: dict,
        actions: str,
        limit_to_ctx: bool = True,
        debug: bool = False,
    ):
        super().__init__(
            model_configs=model_configs, actions=actions, limit_to_ctx=limit_to_ctx
        )
        self.debug = debug

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
                    "text": f"Please update your bid caching. The HTML has changed to:\n{html}\n",
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
                "text": f"Here is the trace of previous actions, of the form (action, error): {trace}\nMy goal is again: {self.goal}\nIf a previous action failed, please avoid repeating the same mistakes.",
            }
        )
        contents.append({"type": "text", "text": ANSWER_PROMPT})

        self.messages.append({"role": "user", "content": contents})

        # pop out earlier messages
        while len(self.messages) > 10:
            # 10 corresponds to letting the model sees the previous 4 interactions
            self.messages.pop(
                1
            )  # pop out the second message because the first message is the system message

    def act(self, **kwargs):
        if self.debug:
            print("Current messages:")
            for message in self.messages:
                print(f"Role: {message['role']}")
                if isinstance(message["content"], str):
                    print(message["content"])
                else:
                    for content in message["content"]:
                        if isinstance(content, str):
                            print(content)
                        elif content["type"] == "image_url":
                            print("Image")
                        else:
                            print(content["text"])
        action, meta = super().act(**kwargs)
        if self.debug:
            print("Action: ", action)
        action = extract_content_by_tags(action, ["action"])["action"]
        return action, meta
