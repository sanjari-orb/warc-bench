import boto3
import os
import io
import pandas as pd
from botocore.exceptions import ClientError
from urllib.parse import urlparse
from functools import lru_cache
from orby.protos.fm.trajectory_data_pb2 import TrajectoryData

# TODO: look into xz compression for the trajectory data based on https://github.com/orby-ai-engineering/digital-agent/pull/160

def load_s3_object_as_bytes(s3_uri: str) -> bytes:
    """
    Load an S3 object as bytes.

    Args:
        s3_uri (str): The S3 URI of the object to load.

    Returns:
        bytes: The object as bytes.
    """
    s3_client = boto3.client("s3")
    bucket, key = get_s3_bucket_and_key_from_uri(s3_uri)
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def upload_bytes_to_s3(data_bytes: bytes, s3_uri: str) -> None:
    """
    Upload bytes data to an S3 location.

    Args:
        data_bytes (bytes): The bytes data to upload
        s3_uri (str): The S3 URI destination
    """
    s3_client = boto3.client("s3")
    bucket, key = get_s3_bucket_and_key_from_uri(s3_uri)
    s3_client.put_object(Bucket=bucket, Key=key, Body=data_bytes)


def load_trajectory_data_from_s3(td_s3_path: str) -> TrajectoryData:
    td_bytes = load_s3_object_as_bytes(td_s3_path)
    td = TrajectoryData()
    td.ParseFromString(td_bytes)
    return td


def upload_trajectory_data_to_s3(td: TrajectoryData, td_s3_path: str) -> None:
    """
    Upload a TrajectoryData object to an S3 location.
    """
    td_bytes = td.SerializeToString()
    upload_bytes_to_s3(td_bytes, td_s3_path)


def get_or_cache_s3_object(s3_uri: str, local_cache_dir: str = ".cache") -> str:
    """
    Get the S3 object, cache it locally if not already cached, and return the local file path.
    """
    # Parse the S3 URI
    bucket, key = get_s3_bucket_and_key_from_uri(s3_uri)

    # Create a filename for the local cache
    cache_filename = f"{bucket}_{key.replace('/', '_')}"
    local_cache_path = os.path.join(local_cache_dir, cache_filename)

    # If the file doesn't exist locally, download it from S3
    if not os.path.exists(local_cache_path):
        print(f"Downloading {s3_uri} to local cache...")

        # Create the cache directory if it doesn't exist
        os.makedirs(local_cache_dir, exist_ok=True)

        session = boto3.Session()
        s3 = session.client("s3")

        # Get the object from S3
        obj = s3.get_object(Bucket=bucket, Key=key)

        # Write the content to the local file
        with open(local_cache_path, "wb") as f:
            f.write(obj["Body"].read())

        print(f"Downloaded and cached at {local_cache_path}")
    else:
        print(f"Using cached file at {local_cache_path}")

    return local_cache_path


def load_pandas_from_s3_or_cache(s3_uri: str) -> pd.DataFrame:
    """
    Load a Parquet table from S3 or local cache into a pandas DataFrame.
    """
    local_file_path = get_or_cache_s3_object(s3_uri)
    table = pd.read_parquet(local_file_path)
    return table


def get_s3_bucket_and_key_from_uri(s3_uri: str) -> tuple[str, str]:
    """
    Get the bucket and key from an S3 URI.

    Args:
        s3_uri (str): The S3 URI.

    Returns:
        tuple[str, str]: The bucket and key.
    """
    bucket, key = s3_uri.replace("s3://", "").strip().split("/", 1)
    return bucket, key


@lru_cache
def get_bucket_region(bucket_name: str) -> str:
    s3_client = boto3.client("s3")
    response = s3_client.get_bucket_location(Bucket=bucket_name)
    region = response.get("LocationConstraint")

    # Handle default region (e.g., us-east-1)
    if region is None:
        return "us-east-1"
    return region


def list_s3_uris(s3_client, s3_uri: str) -> list[str]:
    """
    List all S3 URIs under the given S3 URI, original URI excluded.

    Args:
        s3_client (boto3.client): The S3 client.
        s3_uri (str): The S3 URI.

    Returns:
        list[str]: A list of S3 URIs.
    """
    bucket, prefix = get_s3_bucket_and_key_from_uri(s3_uri)
    s3_uris = []

    # Fetching all objects within the given prefix
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            # Constructing the full S3 URI
            s3_uris.append(f"s3://{bucket}/{obj['Key']}")

    if s3_uri in s3_uris:
        s3_uris.remove(s3_uri)  # Remove the input URI from the list
    return s3_uris


def check_s3_file_exists(s3_uri: str) -> bool:
    """
    Check if an S3 object exists.

    Args:
        s3_uri (str): The S3 URI of the object to check

    Returns:
        bool: True if the file exists, False otherwise.
    """
    # Parse the S3 URI
    parsed_uri = urlparse(s3_uri)
    bucket = parsed_uri.netloc
    key = parsed_uri.path.lstrip("/")  # Remove leading slash

    # Create an S3 client
    s3 = boto3.client("s3")

    try:
        # Attempt to get metadata for the object
        s3.head_object(Bucket=bucket, Key=key)
        return True  # File exists
    except ClientError as e:
        # If a 404 error code is returned, the object does not exist
        if e.response["Error"]["Code"] == "404":
            return False
        # If another error is raised, re-raise it
        else:
            raise e


def upload_df_to_s3_as_parquet(
    df: pd.DataFrame,
    s3_uri: str,
    s3_client=boto3.client("s3"),
) -> None:
    """
    Upload a pandas DataFrame to S3 as a Parquet file.

    Args:
        df (pd.DataFrame): The DataFrame to upload.
        s3_uri (str): The S3 URI to upload the DataFrame to.
    """
    buffer = io.BytesIO()
    bucket, key = get_s3_bucket_and_key_from_uri(s3_uri)
    df.to_parquet(buffer, engine="pyarrow", index=False)
    buffer.seek(0)

    # Upload buffer to S3
    s3_client.put_object(Bucket=bucket, Key=key, Body=buffer)
