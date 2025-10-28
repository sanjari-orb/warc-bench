# Compared to 20241007, added previous screenshot to final_grounding_prompt


def final_planning_prompt(
    goal_images,
    current_screenshot,
    prev_screenshot=None,
    plan_history=[],
    original_screenshot=None,
):
    prompt = """You are a powerful and precise web agent, executing the following goal: {goal}.
Here is the set of actions you can take, which you can call as python functions supplying the html backend id (the bid attribute) or any relevant field as specified. It is a documentation of all the functions, and it's important that you read it well and carefully: {actions}.
The user will provide the webpage and html, which you must operate on using the actions to perform your goal. Your outputs should be a list of natural language instructions for a human to follow in order to achieve this goal. Each step should be a separate line, and should be clear and concise.
You will also be given a set of past actions and errors, use these to correct your trajectory intelligently."""
    prompt += "\n\nHuman: "
    images = {}

    if len(goal_images) > 0:
        prompt += """Here are the images associated with the goal of the task:"""
        for i, image in enumerate(goal_images):
            images[f"goal_image_{i}"] = image
            prompt += f"<image_goal_image_{i}>"

    prompt += """Here is the screenshot of the webpage. Based on the goal, describe the next few steps of actions you would take to achieve the goal in order.

Here's the reference HTML content of the webpage:
{html}

{trace_string}Provide your plan in succinct natural language.<image_screenshot>"""
    images["screenshot"] = current_screenshot

    if len(plan_history) > 0:
        prompt += """
For reference, here is the original plan you provided:
{original_plan}

This was based on the original screenshot of the webpage below: <image_original_screenshot>"""
        images["original_screenshot"] = original_screenshot

    return prompt, images


def final_grounding_prompt(goal_images, current_screenshot, prev_screenshot=None):
    prompt = """You are a powerful and precise web agent, executing the following goal: {goal}.
Here is the set of actions you can take, which you can call as python functions supplying the html backend id (the bid attribute) or any relevant field as specified. It is a documentation of all the functions, and it's important that you read it well and carefully: {actions}.
The user will provide the webpage and html, which you must operate on using the actions to perform your goal. Your outputs should be single python function calls, without any additional text, and should follow the correct formatting \
given in the python function dump. Importantly, some functions operate on the backend id (bid) attribute which will be found in the html dump, and is a number passed as a string object. Others, particularly mouse operations, use coordinates if applicable. \
Refer to the documentation to determine appropriate args. You will also be given a set of past actions and errors, use these to correct your trajectory intelligently. DO NOT PROVIDE ANY MORE THAN A FUNCTION CALL AT EACH TURN!"""
    prompt += "\n\nHuman: "
    images = {}

    if len(goal_images) > 0:
        prompt += """Here are the images associated with the goal of the task:"""
        for i, image in enumerate(goal_images):
            images[f"goal_image_{i}"] = image
            prompt += f"<image_goal_image_{i}>"

    prompt += """Please help me! Here is the current image of the webpage, which you can interact with using the actions and which you should remember coordinates for elements:<image_screenshot>"""
    images["screenshot"] = current_screenshot

    prompt += """Next, here is the HTML content of the webpage. Cache the bids for retrieval for action call:
{html}

{trace_string}"""

    if prev_screenshot is not None:
        prompt += (
            "For reference, this is the screenshot before the previous action was taken. "
            "Carefully compare this with the current screenshot to understand if the previous action achieved the intended effect. <image_prev_screenshot>"
        )
        images["prev_screenshot"] = prev_screenshot

    prompt += "Closely analyze the HTML to see if the element can be interacted with through its bid (in square brackets), if so, prefer using the bid. If an action could not be performed with bid, consider using coordinates. "

    if current_screenshot is not None:
        # Add dimensions of the screenshot
        prompt += "For reference, the width of the screenshot is {screenshot_width} pixels and the height is {screenshot_height} pixels. "

    prompt += "What should be the next action call, as a python function call without any additional text and extremely concise? Answer: "

    return prompt, images
