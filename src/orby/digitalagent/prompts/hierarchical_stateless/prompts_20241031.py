# Compared to 20241016, removed previous screenshot from planning and grounding prompts


def final_planning_prompt(
    goal_images,
    current_screenshot,
    prev_screenshot=None,
    plan_history=[],
    original_screenshot=None,
):
    prompt = """You are a powerful and precise web agent, executing the following goal: {goal}.
Here is the set of actions you can take, which you can call as python functions supplying the html backend id (the bid attribute) or any relevant field as specified. It is a documentation of all the functions, and it's important that you read it well and carefully: {actions}.
The user will provide the webpage and html, which you must operate on using the actions to perform your goal. Your outputs should be a list of natural language instructions in order to achieve this goal. Each step should be a separate line, and should be clear and concise.
If multiple functions can achieve the same result, choose the most efficient one with the least number of steps. Describe the steps in natural language, and do not provide any code.
You will also be given a set of past actions and errors, use these to correct your trajectory intelligently."""
    prompt += "\n\nHuman: "
    images = {}

    if len(goal_images) > 0:
        prompt += """Here are the images associated with the goal of the task:"""
        for i, image in enumerate(goal_images):
            images[f"goal_images.{i}"] = image
            prompt += f"<image_goal_images.{i}>"

    prompt += """Here is the screenshot of the webpage. Based on the goal, describe the next few steps of actions you would take to achieve the goal in order.

Here's the reference HTML content of the webpage:
{html}

{trace_string}Reflect about the current state and what the plan needs to achieve, and enclose your thought process in <thinking> </thinking> tags. Decompose or combine adjacent steps if there are alternative actions that can potentially achieve the same result. Limit your thought process to no more than 200 words. Then provide your plan to achieve the goal after the </thinking> tag, and present each step on a separate line. 
If there has been previous plans executed, summarize the feedback and present it in <feedback> </feedback> tags before the first step of the new plan.<image_screenshot>"""
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
            images[f"goal_images.{i}"] = image
            prompt += f"<image_goal_images.{i}>"

    prompt += """Please help me! Here is the current image of the webpage, which you can interact with using the actions and which you should remember coordinates for elements:<image_screenshot>"""
    images["screenshot"] = current_screenshot

    prompt += """Next, here is the HTML content of the webpage. Cache the bids for retrieval for action call:
{html}

{trace_string}"""

    prompt += "Closely analyze the HTML to see if the element can be interacted with through its bid (in square brackets), if so, prefer using the bid. If an action could not be performed with bid, consider using coordinates. "

    if current_screenshot is not None:
        # Add dimensions of the screenshot
        prompt += (
            "For reference, the width of the screenshot is {screenshot_width} pixels and the height is {screenshot_height} pixels. "
            "Pixel coordinates originate from the top left corner of the image, where the first coordinate refers to the horizontal/width axis and the second refers to the vertical/height axis. "
        )

    prompt += "What should be the SINGLE action call to achieve the goal? Think step by step for no more than 200 words, and wrap your thought process in <thinking> </thinking> tags. DO NOT plan to achieve the goal using multiple function calls. Provide a final answer in the form of a concise Python-like function call after </thinking>."

    return prompt, images
