def final_prompt(goal_images, current_screenshot, prev_screenshot=None):
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

    prompt += (
        "If an action could not be performed with bid, consider using coordinates. "
    )

    if current_screenshot is not None:
        # Add dimensions of the screenshot
        prompt += "For reference, the width of the screenshot is {screenshot_width} pixels and the height is {screenshot_height} pixels. "

    prompt += "What should be the next action call, as a python function call without any additional text and extremely concise? Answer: "

    return prompt, images
