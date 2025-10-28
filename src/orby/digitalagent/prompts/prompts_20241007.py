from orby.digitalagent.agent.utils import screenshots_differ

SYSTEM_PROMPT = """You are a powerful and precise web agent, executing the following goal: {goal}.
Here is the set of actions you can take, which you can call as python functions supplying the html backend id (the bid attribute) or any relevant field as specified. It is a documentation of all the functions, and it's important that you read it well and carefully: {actions}.
The user will provide the webpage and html, which you must operate on using the actions to perform your goal. Your outputs should be single python function calls, without any additional text, and should follow the correct formatting \
given in the python function dump. Importantly, some functions operate on the backend id (bid) attribute which will be found in the html dump, and is a number passed as a string object. Others, particularly mouse operations, use coordinates if applicable. \
Refer to the documentation to determine appropriate args. You will also be given a set of past actions and errors, use these to correct your trajectory intelligently. DO NOT PROVIDE ANY MORE THAN A FUNCTION CALL AT EACH TURN!"""

GOAL_IMAGES_PROMPT = """Here are the images associated with the goal of the task:"""

GROUNDING_PROMPT_BEFORE_IMG = """Please help me! Here is the current image of the webpage, which you can interact with using the actions and which you should remember coordinates for elements:"""

ANSWER_PROMPT = "What should be the next action call, as a python function call without any additional text and extremely concise? Answer: "

GROUNDING_PROMPT_AFTER_IMG_PART1 = """Next, here is the HTML content of the webpage. Cache the bids for retrieval for action call:
{html}

{trace_string}"""

GROUNDING_PROMT_AFTER_IMG_PART2 = (
    "If an action could not be performed with bid, consider using coordinates. "
    + ANSWER_PROMPT
)

TRACE_PROMPT = """Here is the trace of previous actions, of the form (action, error, screenshot changed?, HTML changed?):
{trace}
If a previous action failed or has been repeated multiple times without a positive outcome, please avoid repeating the same mistakes.

"""

PLANNING_PROMPT = """Here is the screenshot of the webpage. Based on the goal, describe the next few steps of actions you would take to achieve the goal in order.

Here's the reference HTML content of the webpage:
{html}

{trace_string}Provide your plan in succinct natural language."""

PLANNING_PROMPT_ORIGINAL = """For reference, here is the original plan you provided:
{plan}

This was based on the original screenshot of the webpage below:
"""

PLAN_TRACE_PROMPT = """Here is the trace of previous planned actions, of the form (action, whether it succeeded):
{executed_plan}
If a previous action failed or has been repeated multiple times without a positive outcome, please avoid repeating the same mistakes. Only provide the next step plans after these actions have been performed, do not repeat them.

"""

SCREENSHOT_CHANGE_PROMPT = (
    "No change in screenshot",
    "Screenshot changed from this action",
)
HTML_CHANGE_PROMPT = ("No change in HTML", "HTML changed from this action")


def _trace_string(self):
    if len(self.trace) > 0:
        # previous action, error, screenshot changed, HTML changed
        trace = "\n".join(
            str(
                (
                    t[0],
                    t[1],
                    SCREENSHOT_CHANGE_PROMPT[
                        int(
                            screenshots_differ(
                                self.screenshot_history[i],
                                self.screenshot_history[i + 1],
                            )
                        )
                    ],
                    HTML_CHANGE_PROMPT[
                        int(self.html_history[i] != self.html_history[i + 1])
                    ],
                )
            )
            for i, t in enumerate(self.trace)
        )
        trace_string = TRACE_PROMPT.format(trace=trace)
    else:
        trace_string = ""

    return trace_string


def grounding_prompt_after_img(html, trace_string, plan=None, screenshot=None):
    res = GROUNDING_PROMPT_AFTER_IMG_PART1.format(html=html, trace_string=trace_string)
    if plan is not None:
        res += f"""Here's a rough plan to achieve this goal from this point on:
{plan}

Pay close attention to the first step in the plan above."""
    res += "If an action could not be performed with bid, consider using coordinates. "

    if screenshot is not None:
        # Add dimensions of the screenshot
        res += f"For reference, the width of the screenshot is {screenshot.shape[1]} pixels and the height is {screenshot.shape[0]} pixels. "

    res += ANSWER_PROMPT

    return res
