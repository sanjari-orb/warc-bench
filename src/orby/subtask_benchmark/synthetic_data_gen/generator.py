"""Example usage: python generator.py --config data_gen_config.json"""

from dataclasses import dataclass, field, fields, is_dataclass
from typing import List
from string import Template
from tqdm import tqdm
import argparse
import csv
import json
import os
import base64
from concurrent.futures import ProcessPoolExecutor
from openai import OpenAI
import instructor
import copy

from orby.subtask_benchmark.synthetic_data_gen.dom_extractor import (
    WaczDOMExtractor,
    OnlineDOMExtractor,
)
from orby.subtask_benchmark.synthetic_data_gen.synthetic_data_template import (
    SyntheticDataTemplate,
)


@dataclass
class SyntheticDataConfig:
    output_file_path: str
    headers: List[str] = field(
        default_factory=lambda: [
            "data_path",
            "subtask_type",
            "subtask_goal",
            "start_url",
            "eval_type",
            "evaluation",
        ]
    )
    output_format: str = "csv"
    num_data_points: int = 10


@dataclass
class WebArchiveSources:
    """Data class containing web archive file name and list of URLs"""

    web_archive_file: str
    urls: List[str] = field(default_factory=list)


@dataclass
class SyntheticDataGeneratorConfig:
    prompt_file_path: str
    dom_extractor_type: str
    synthetic_data_config: SyntheticDataConfig
    num_processes: int = 1
    web_archives: List[WebArchiveSources] = field(default_factory=list)
    online_urls: List[str] = field(default_factory=list)


class SyntheticDataGenerator:

    def __init__(self, generator_config: SyntheticDataGeneratorConfig):
        self.generator_config = generator_config
        self.synthetic_data_config = generator_config.synthetic_data_config
        self.prompt_file = generator_config.prompt_file_path
        self.dom_extractor_type = generator_config.dom_extractor_type
        self.output_file_path = generator_config.synthetic_data_config.output_file_path
        self.output_format = generator_config.synthetic_data_config.output_format
        self.num_data_points = generator_config.synthetic_data_config.num_data_points
        self.client = instructor.patch(OpenAI())
        self.initialize_dom_extractor()
        self._load_prompt()

    def initialize_dom_extractor(self):
        """Initialize DOM extractor based on config"""
        if self.dom_extractor_type == "wacz":
            self.dom_extractor = WaczDOMExtractor
        elif self.dom_extractor_type == "online":
            self.dom_extractor = OnlineDOMExtractor
        else:
            raise ValueError(
                f"Unsupported DOM extractor type: {self.dom_extractor_type}"
            )

    def _load_prompt(self):
        """Load prompt from file"""
        try:
            with open(self.prompt_file, "r") as f:
                self.prompt_template = Template(f.read())
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found at {self.prompt_file}")

    def generate_synthetic_data(self):
        if self.dom_extractor_type == "wacz":
            self._generate_synthetic_data_wacz()
        elif self.dom_extractor_type == "online":
            self._generate_synthetic_data_online()
        else:
            raise ValueError(
                f"Unsupported DOM extractor type: {self.dom_extractor_type}"
            )

    def _generate_synthetic_data_wacz(self):
        """Generate synthetic data based on prompt and DOM for all web pages which are a part of the web app"""
        # Extract DOM from web archive
        for source in self.generator_config.web_archives:
            for url in source.urls:
                try:
                    dom_content = self.dom_extractor.extract_dom(
                        url, source.web_archive_file
                    )

                    # Generate synthetic data
                    synthetic_data = self.client.chat.completions.create(
                        model="gpt-4.1",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": self.prompt_template.substitute(
                                            num_data_points=self.num_data_points,
                                            html_dom=dom_content,
                                            web_archive_name="/".join(
                                                source.web_archive_file.split("/")[-2:]
                                            ),
                                        ),
                                    }
                                ],
                            }
                        ],
                        response_model=List[SyntheticDataTemplate],
                    )

                    # Save synthetic data to file
                    self.save_synthetic_data(synthetic_data)
                except Exception as e:
                    print(f"Error generating synthetic data for {url}: {e}")

    def _generate_synthetic_data_online(self):
        """Generate synthetic data based on prompt and DOM for all online URLs"""
        for url in tqdm(self.generator_config.online_urls):
            try:
                dom_content, screenshot = self.dom_extractor.extract_dom(url)
                base64_screenshot = base64.b64encode(screenshot).decode("utf-8")

                # Generate synthetic data
                synthetic_data = self.client.chat.completions.create(
                    model="gpt-4.1",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": self.prompt_template.substitute(
                                        num_data_points=self.num_data_points,
                                        html_dom=dom_content,
                                    ),
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{base64_screenshot}"
                                    },
                                },
                                {"type": "text", "text": "Answer: "},
                            ],
                        }
                    ],
                    response_model=List[SyntheticDataTemplate],
                )

                # Save synthetic data to file
                self.save_synthetic_data(synthetic_data)
            except Exception as e:
                print(f"Error generating synthetic data for {url}: {e}")

    def save_synthetic_data(self, synthetic_data):
        """Save synthetic data to file"""
        if self.output_format == "csv":
            self.save_synthetic_data_csv(synthetic_data)
        else:
            raise ValueError(f"Unsupported output format: {self.output_format}")

    def save_synthetic_data_csv(self, synthetic_data):
        """Save synthetic data to CSV file"""
        if not os.path.exists(self.output_file_path):
            # create a csv file with headers
            with open(self.output_file_path, "w") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(self.synthetic_data_config.headers)

        with open(self.output_file_path, "a") as csv_file:
            writer = csv.writer(csv_file)
            # clean and reformat synthetic data
            for sample in synthetic_data:
                # Convert subtask_type list to comma-separated string
                subtask_types = ",".join(sample.subtask_type)
                # Convert evaluation to string if it's a dict/list
                eval_str = (
                    json.dumps(sample.evaluation)
                    if isinstance(sample.evaluation, (dict, list))
                    else sample.evaluation
                )
                writer.writerow(
                    [
                        sample.data_path,
                        subtask_types,
                        sample.subtask_goal,
                        sample.start_url,
                        sample.eval_type,
                        eval_str,
                    ]
                )


def from_json(dataclass_type, data):
    """Recursively instantiate a dataclass from a dict."""
    if not is_dataclass(dataclass_type):
        # Handle List types specially
        if hasattr(dataclass_type, "__origin__") and dataclass_type.__origin__ is list:
            # Get the type of list elements
            element_type = dataclass_type.__args__[0]
            # Recursively convert each element if it's a dataclass
            return [from_json(element_type, item) for item in data]
        return data  # Base case: if not a dataclass or list, return the data directly

    fieldtypes = {f.name: f.type for f in fields(dataclass_type)}
    return dataclass_type(**{f: from_json(fieldtypes[f], data[f]) for f in data})


def split_config(
    generator_config: SyntheticDataGeneratorConfig,
) -> List[SyntheticDataGeneratorConfig]:
    """
    Split the config for parallel processing.
    Make changes in:
    - synthetic_data_config.output_file_path:  change this to include the process number
    - online_urls or web_archives: split this into num_processes lists to put into different configs
    Keep other fields the same across all configs
    """
    configs = []
    num_processes = generator_config.num_processes
    base_output_path = generator_config.synthetic_data_config.output_file_path

    # Split web archives across processes
    archives_per_process = [[] for _ in range(num_processes)]
    if generator_config.web_archives:
        for i, archive in enumerate(generator_config.web_archives):
            archives_per_process[i % num_processes].append(archive)

    # Or, split online URLs across processes
    urls_per_process = [[] for _ in range(num_processes)]
    if generator_config.online_urls:
        for i, url in enumerate(generator_config.online_urls):
            urls_per_process[i % num_processes].append(url)

    # Create separate config for each process
    for i in range(num_processes):
        config_copy = copy.deepcopy(generator_config)
        path_parts = os.path.splitext(base_output_path)
        config_copy.synthetic_data_config.output_file_path = (
            f"{path_parts[0]}_part{i}{path_parts[1]}"
        )
        config_copy.web_archives = archives_per_process[i]
        config_copy.online_urls = urls_per_process[i]
        configs.append(config_copy)

    return configs


def run_generator(config):
    """
    Function to run a synthetic data generator with a given config.
    This is needed for multiprocessing instead of using a lambda.
    """
    generator = SyntheticDataGenerator(config)
    generator.generate_synthetic_data()
    return True


def merge_results(part_files: List[str], output_file: str, headers: List[str]):
    """
    Merge multiple part CSV files into a single output file.

    Args:
        part_files: List of part file paths to merge
        output_file: Final output file path
        headers: CSV headers to write at the top of the merged file
    """
    # Create the output file with headers
    with open(output_file, "w", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(headers)

        # Append data from each part file
        for part_file in part_files:
            if os.path.exists(part_file):
                with open(part_file, "r", newline="") as infile:
                    reader = csv.reader(infile)
                    next(reader, None)  # Skip the header row
                    for row in reader:
                        writer.writerow(row)

                # Remove the part file after merging
                os.remove(part_file)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", type=str, required=True)
    args = parser.parse_args()

    """Run synthetic data generation"""
    with open(args.config, "r") as f:
        config_data = json.load(f)

    # Instantiate Generator's config
    generator_config = from_json(SyntheticDataGeneratorConfig, config_data)

    if generator_config.num_processes > 1:
        configs = split_config(generator_config)
        with ProcessPoolExecutor(
            max_workers=generator_config.num_processes
        ) as executor:
            # Use a named function instead of lambda for multiprocessing
            list(executor.map(run_generator, configs))

        # Merge the part files into the final output
        part_files = [
            config.synthetic_data_config.output_file_path for config in configs
        ]
        merge_results(
            part_files,
            generator_config.synthetic_data_config.output_file_path,
            generator_config.synthetic_data_config.headers,
        )
    else:
        run_generator(generator_config)


if __name__ == "__main__":
    main()
