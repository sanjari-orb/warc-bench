import json
import os
import re

from .utils import create_template, load_template, render_block

class Template:
    SUPPORTED_IMAGE_PREFIXES = ["image:"]
    SUPPORTED_IMAGE_ITERABLE_PREFIXES = ["images:"]

    def __init__(self, template_str_or_file_name: str):
        """
        Initialize a Template object from a Jinja2 template string or file.
        
        :param template_str_or_file_name: The Jinja2 template content as a string or the path to a template file.
        """
        if os.path.exists(template_str_or_file_name):
            self.template_str = load_template(template_str_or_file_name)
        else:
            self.template_str = template_str_or_file_name
        self.template = create_template(self.template_str)

    def render(self, *, replace_image_placeholders_as : str | None = None, block : str | None = None, **kwargs):
        """
        Render the template with the given keyword arguments.

        :param replace_image_placeholders_as: If provided, replace the image placeholders with the given string and return the images as a list.
        :param block: If provided, render the specified block from the template.
        :param kwargs: The keyword arguments to be passed to the template, including any image objects.

        :return:
            A string, rendered prompt with image placeholders
            A list or dictionary of images, depending on the value of replace_image_placeholders_as
        """

        if block:
            rendered_prompt = render_block(self.template, block, kwargs)
        else:
            rendered_prompt = self.template.render(**kwargs)

        image_pattern = re.compile(rf"<({'|'.join(self.SUPPORTED_IMAGE_PREFIXES + self.SUPPORTED_IMAGE_ITERABLE_PREFIXES)})([^>]*)>")
        image_dict = {}

        new_prompt = ""
        last_index = 0
        for image_tag in image_pattern.finditer(rendered_prompt):
            image_prefix = image_tag.group(1)
            new_prompt += rendered_prompt[last_index:image_tag.start()]
            if image_prefix in self.SUPPORTED_IMAGE_ITERABLE_PREFIXES:
                # Expand the iterable into individual images
                iterable_name = image_tag.group(2)
                images = kwargs[iterable_name]
                for i, image in enumerate(images):
                    image_dict[f"{iterable_name}.{i}"] = image
                    new_prompt += f"<{self.SUPPORTED_IMAGE_PREFIXES[0]}{iterable_name}.{i}>"
            else:
                image_name = image_tag.group(2)
                new_prompt += image_tag.group(0)

                image_dict[image_name] = kwargs[image_name]

            last_index = image_tag.end()

        new_prompt += rendered_prompt[last_index:]

        if replace_image_placeholders_as:
            image_list = []
            for image_tag in image_pattern.finditer(new_prompt):
                image_name = image_tag.group(2)
                image_list.append(image_dict[image_name])
            new_prompt = re.sub(image_pattern, replace_image_placeholders_as, new_prompt)

            return new_prompt, image_list
        else:
            return new_prompt, image_dict