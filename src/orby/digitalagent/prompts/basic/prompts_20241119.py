from orby.digitalagent.agent.utils import screenshots_differ

SYSTEM_PROMPT = """You are a powerful and precise web agent, executing the following goal: {goal}.
Here is the set of actions you can take, which you can call as python functions supplying the html backend id (the bid attribute) or any relevant field as specified. It is a documentation of all the functions, and it's important that you read it well and carefully: {actions}.
The user will provide the webpage and html, which you must operate on using the actions to perform your goal. Your outputs should be single python function calls, without any additional text, and should follow the correct formatting \
given in the python function dump. Importantly, some functions operate on the backend id (bid) attribute which will be found in the html dump, and is a number passed as a string object. Others, particularly mouse operations, use coordinates if applicable. \
Refer to the documentation to determine appropriate args. You will also be given a set of past actions and errors, use these to correct your trajectory intelligently. DO NOT PROVIDE MORE THAN ONE STEP AT EACH TURN!"""

GOAL_IMAGES_PROMPT = """Here are the images associated with the goal of the task:"""

GROUNDING_PROMPT_BEFORE_IMG = """Please help me! Here is the current image of the webpage, which you can interact with using the actions and which you should remember coordinates for elements:"""

ANSWER_PROMPT = """\
What should be the next action call and why?
Please answer this question in the following format:
<thinking>Your reasoning about what should be done next based on the current state of the webpage and your goal.</thinking>
<action description>A natural language description of the action you should perform.</action description>
<action>The python function call you should make.</action>

Answer:
"""

GROUNDING_PROMPT_AFTER_IMG_PART1 = """Next, here is the HTML content of the webpage. Cache the bids for retrieval for action call:
{html}

{trace_string}"""


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
