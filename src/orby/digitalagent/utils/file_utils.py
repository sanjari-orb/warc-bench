import io
import os
import boto3
from contextlib import contextmanager
import lzma
import smart_open


# Support for xz files, which shows ~100x compression ratio over the original protobuf files.
def _handle_xz(file_obj, mode):
    return lzma.LZMAFile(filename=file_obj, mode=mode, format=lzma.FORMAT_XZ)


# Register the xz compressor with smart_open.
smart_open.register_compressor('.xz', _handle_xz)


_OPEN = smart_open.open


def makedirs(name: str, mode=0o777, exist_ok: bool = False):
    if name.startswith("s3://"):
        return
    os.makedirs(name, mode=mode, exist_ok=exist_ok)


def rm(file_path: str):
    if file_path.startswith("s3"):
        s3 = boto3.client("s3")
        bucket_name, file_key = parse_s3_path(file_path)
        try:
            s3.delete_object(Bucket=bucket_name, Key=file_key)
        except Exception as e:
            print(f"Error deleting file '{file_key}' from bucket '{bucket_name}':  {e}")
        return
    try:
        os.remove(file_path)
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
    except Exception as e:
        print(f"Error deleting file '{file_path}': {e}")


@contextmanager
def open(path, mode="r", **kwargs):
    """
    Utility function to open files locally or on S3, depending on the provided path.
    Supports 'r', 'w', 'rb', 'wb' modes.
    """
    if path.startswith("s3://"):
        if "r" in mode:
            # Read from S3
            file_obj = smart_open.open(path, mode)
            if "b" not in mode:
                yield io.TextIOWrapper(file_obj)
            else:
                yield file_obj
        elif "w" in mode:
            # Write to S3
            file_obj = io.BytesIO()
            try:
                if "b" not in mode:
                    wrapper = io.TextIOWrapper(file_obj, **kwargs)
                    yield wrapper
                    wrapper.flush()
                else:
                    yield file_obj
            finally:
                # Upload to S3
                file_obj.seek(0)
                if 'b' not in mode:
                    content = wrapper.read()
                else:
                    content = file_obj.getvalue()
                with _OPEN(path, mode) as fout:
                    fout.write(content)
        else:
            raise ValueError("Unsupported mode for S3: {}".format(mode))
    else:
        # Fallback to local file operations
        with open_local(path, mode, **kwargs) as f:
            yield f


def parse_s3_path(s3_path):
    """Parses an S3 path into bucket and key."""
    assert s3_path.startswith("s3://"), "Invalid S3 path: {}".format(s3_path)
    _, _, bucket, *key_parts = s3_path.split("/")
    key = "/".join(key_parts)
    return bucket, key


@contextmanager
def open_local(path, mode="r", **kwargs):
    """Context manager for opening local files."""
    with _OPEN(path, mode, **kwargs) as f:
        yield f


def list_files(path):
    """
    Utility function to list all files under a folder recursively.
    Supports both local paths and S3 paths.
    """
    if path.startswith("s3://"):
        s3_client = boto3.client("s3")
        bucket, prefix = parse_s3_path(path)
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            if "Contents" in page:
                for obj in page["Contents"]:
                    yield "s3://{}/{}".format(bucket, obj["Key"])
    else:
        for root, _, files in os.walk(path):
            for file in files:
                yield os.path.join(root, file)


if __name__ == "__main__":
    import json

    with open("s3://orby-llm/test", "w") as f:
        f.write("Hello")
    with open("s3://orby-llm/test", "r") as f:
        print(f.read())
    with open(
        "s3://orby-llm/browsergym-eval/miniwob_hsm_v2_openai_gpt-4o-mini-2024-07-18_2024-11-14_20-10-51/browsergym/miniwob.drag-box/results.json"
    ) as f:
        print(json.load(f))
    for path in list_files("s3://orby-llm/browsergym-eval/"):
        print(path)
