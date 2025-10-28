from orby.digitalagent.prompts.hierarchical_stateless.prompts_20241007 import (
    final_grounding_prompt,
    final_planning_prompt,
)


def final_grounding_verifier_prompt(current_screenshot, prev_screenshot):
    prompt = """You are a powerful and precise web agent, executing the following goal: {goal}.
Another web agent has performed operations to achieve this goal, and your task is to verify whether the goal has been achieved. The user will provide the webpage and html, which the agent must operate on using the actions to perform your goal. Your final output should be concisely either "Yes" or "No"."""
    prompt += "\n\nHuman: "
    images = {}

    prompt += (
        "This is the screenshot before the previous action was taken by the agent. "
        "Carefully compare this with the current screenshot to understand if the previous action achieved the intended effect. <image_prev_screenshot>"
    )
    images["prev_screenshot"] = prev_screenshot

    prompt += """Here is the current image of the webpage:<image_screenshot>"""
    images["screenshot"] = current_screenshot

    prompt += """Next, here is the HTML content of the webpage.
{html}"""

    prompt += """Has the goal been successfully achieved? Answer "Yes" or "No"."""

    return prompt, images
