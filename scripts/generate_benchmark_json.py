#!/usr/bin/env python3
"""
Example usage:
python3.11 scripts/generate_benchmark_json.py scripts/csvs/tasks_04242025.csv src/subtask_benchmark/environments/benchmark_2.json --force
"""
import argparse
import csv
import json
import os
import sys


def resolve_path(path):
    """Resolve a potentially relative path to an absolute path"""
    if os.path.isabs(path):
        return path
    return os.path.abspath(path)


def get_task_list_from_csv(input_csv_path):
    input_csv_path = resolve_path(input_csv_path)
    task_list = []

    try:
        with open(input_csv_path, "r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            # Define mapping from CSV column names to JSON fields
            field_mapping = {
                "task id": "task_id",
                "website": "website",
                "serving type": "serving_type",
                "data path": "data_path",
                "goal": "goal",
                "eval type": "eval_type",
                "start url": "start_url",
                "evaluation": "evaluate_script",
                "timestamp": "timestamp_seconds",
                "n steps": "n_steps",
                "comment": "comment",
            }

            # Print the field mapping for debugging
            print("Field Mapping:")
            for csv_field, expected_field in field_mapping.items():
                print(f"  {csv_field} -> {expected_field}")

            for row_index, row in enumerate(reader, 1):
                # Extract needed fields using the mapping
                mapped_fields = {}
                for csv_field, json_field in field_mapping.items():
                    if csv_field in row:
                        mapped_fields[json_field] = row[csv_field].strip()

                # Create task ID by combining serving type and task ID
                task_id = mapped_fields.get("task_id", "")
                serving_type = mapped_fields.get("serving_type", "").lower()
                final_task_id = (
                    f"{serving_type}.{task_id}" if serving_type and task_id else task_id
                )

                data_path_prepend = (
                    "environments/static_web_apps"
                    if serving_type == "static"
                    else "environments/web_archives"
                )
                data_path = os.path.join(
                    data_path_prepend, mapped_fields.get("data_path", "")
                )

                # Initialize the basic task structure
                task_obj = {
                    "task_id": final_task_id,
                    "env": {
                        # Prepend environments/web_archives/ to the WARC file path
                        "data_path": data_path,
                        "start_url": mapped_fields.get("start_url", ""),
                    },
                    "goal": mapped_fields.get("goal", ""),
                    "eval": {
                        "eval_type": mapped_fields.get("eval_type", ""),
                        "evaluate_scripts": [],
                    },
                }

                # Add the evaluate script if it exists
                if (
                    "evaluate_script" in mapped_fields
                    and mapped_fields["evaluate_script"]
                ):
                    task_obj["eval"]["evaluate_scripts"].append(
                        {"script": mapped_fields["evaluate_script"]}
                    )

                # Handle timestamp if present
                if (
                    "timestamp_seconds" in mapped_fields
                    and mapped_fields["timestamp_seconds"]
                ):
                    try:
                        seconds = int(mapped_fields["timestamp_seconds"])
                        task_obj["env"]["timestamp"] = {"seconds": seconds, "nanos": 0}
                    except ValueError:
                        print(
                            f"Warning: Invalid timestamp value in row {row_index}: {mapped_fields['timestamp_seconds']}",
                            file=sys.stderr,
                        )

                # Add additional evaluate scripts if they exist in the CSV
                script_idx = 2
                script_key = f"evaluate_script_{script_idx}"
                while script_key in row and row[script_key].strip():
                    task_obj["eval"]["evaluate_scripts"].append(
                        {"script": row[script_key].strip()}
                    )
                    script_idx += 1
                    script_key = f"evaluate_script_{script_idx}"

                # Skip tasks with missing required fields
                if (
                    not task_obj["task_id"]
                    or not task_obj["env"]["data_path"]
                    or not task_obj["env"]["start_url"]
                    or not task_obj["goal"]
                    or not task_obj["eval"]["eval_type"]
                    or not task_obj["eval"]["evaluate_scripts"]
                ):
                    print(
                        f"Warning: Skipping row {row_index} due to missing required fields",
                        file=sys.stderr,
                    )
                    continue

                task_list.append(task_obj)

        if not task_list:
            print("Error: No valid tasks found in the CSV", file=sys.stderr)

    except FileNotFoundError:
        print(f"Error: Input file {input_csv_path} not found", file=sys.stderr)

    except Exception as e:
        print(f"Error during conversion: {str(e)}", file=sys.stderr)
        import traceback

        traceback.print_exc()

    return task_list


def write_task_list_benchmark_json(task_list, output_json_path):
    """
    Convert a CSV file to a JSON file in the format of benchmark.json

    Args:
        input_csv_path (str): Path to the input CSV file
        output_json_path (str): Path to the output JSON file

    Returns:
        bool: Whether the conversion was successful
    """
    try:
        # Resolve paths to absolute paths
        output_json_path = resolve_path(output_json_path)

        # Create the output directory if it doesn't exist
        output_dir = os.path.dirname(output_json_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Write the JSON to the output file
        with open(output_json_path, "w", encoding="utf-8") as jsonfile:
            json.dump(task_list, jsonfile, indent=2, ensure_ascii=False)

    except FileNotFoundError:
        print(
            f"Error: Output file {output_json_path} could not be created",
            file=sys.stderr,
        )
        return False

    except TypeError as e:
        print(f"Serialization error: {e}")
        return False

    except Exception as e:
        print(f"Error writing JSON file: {str(e)}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return False

    print(f"Wrote {len(task_list)} tasks to {output_json_path}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Convert a CSV file to a benchmark JSON file"
    )
    parser.add_argument(
        "--online_input_csv",
        required=True,
        help="Path to the online (dev) input CSV file",
    )
    parser.add_argument(
        "--online_train_csv",
        required=False,
        help="Path to the online (train) input CSV file",
    )
    parser.add_argument("--output_json", help="Path to the output JSON file")
    parser.add_argument(
        "--force", action="store_true", help="Overwrite output file if it exists"
    )

    args = parser.parse_args()

    # Check if the output file already exists
    resolved_output = resolve_path(args.output_json)
    if os.path.exists(resolved_output) and not args.force:
        print(
            f"Error: Output file {resolved_output} already exists. Use --force to overwrite.",
            file=sys.stderr,
        )
        return 1

    task_list = []
    for input_csv in [args.online_input_csv]:
        tasks = get_task_list_from_csv(input_csv)
        if not tasks:
            return 1
        task_list.extend(tasks)
    if args.online_train_csv:
        tasks = get_task_list_from_csv(args.online_train_csv)
        if not tasks:
            return 1
        task_list.extend(tasks)

    success = write_task_list_benchmark_json(task_list, args.output_json)
    if not success:
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
