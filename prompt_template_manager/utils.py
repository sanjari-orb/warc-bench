"""
Utility functions for loading and rendering Jinja2 templates.

This module provides:
- `load_template`: Loads Jinja2 templates from a specified path.
- `create_template`: Creates a Jinja2 template from a string.
- `render_block`: Renders a specific block from a Jinja2 template.
"""

import os
import json
from jinja2 import Environment, StrictUndefined, Template as Jinja2Template


def load_template(template_path: str) -> str:
    """
    Load a Jinja2 template from the specified path within the installed package.
    
    :param template_path: Path to the Jinja2 template (relative to the package).
    :return: The template content as a string.
    """
    base_path = os.path.join(os.path.dirname(__file__), "templates")
    full_path = os.path.join(base_path, template_path)
    if not os.path.exists(full_path):
        available_templates = os.listdir(base_path)
        raise FileNotFoundError( \
            f"Template file not found: {full_path}. Available templates: {available_templates}")
    with open(full_path, "r", encoding="utf-8") as file:
        return file.read()

def create_template(template_str: str) -> Jinja2Template:
    """
    Create a Jinja2 template from the provided template string.
    
    :param template_str: The Jinja2 template content as a string.
    :return: A Jinja2 Template object.
    """
    env = Environment(undefined=StrictUndefined)
    env.filters['json_loads'] = json.loads
    return env.from_string(template_str)


def render_block(template:Jinja2Template, block_name:str, context:dict) -> str:
    """
    Render a specific block from a Jinja2 template.
    
    :param template: The Jinja2 Template object.
    :param block_name: The name of the block to render.
    :param context: The context to render the block with.
    :return: The rendered block as a string.
    """
    block = template.blocks[block_name]
    return "".join(block(template.new_context(context)))