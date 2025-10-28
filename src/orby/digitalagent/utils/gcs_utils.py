import urllib
from typing import Tuple
from google.cloud import storage


def decode_gcs_uri(uri: str) -> Tuple[str, str]:
    p = urllib.parse.urlparse(uri)
    bucket_name = p.netloc
    object_path = p.path.lstrip("/")
    if p.query:
        object_path += "?" + p.query
    if p.fragment:
        object_path += "#" + p.fragment
    return bucket_name, object_path


def upload_file_to_gcs(
    file_path: str,
    storage_client: storage.Client,
    bucket_name: str,
    destination_blob_name: str,
) -> str:
    """
    Upload a file to Google Cloud Storage.

    Args:
        file_path (str): Path to the file to upload
        storage_client (storage.Client): Google Cloud Storage client
        bucket_name (str): Name of the bucket
        destination_blob_name (str): Name of the destination

    Returns:
        str: The URI of the uploaded file
    """
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(file_path)

    return f"gs://{bucket_name}/{destination_blob_name}"


def download_file_from_gcs_as_bytes(
    storage_client: storage.Client,
    bucket_name: str,
    source_blob_name: str,
) -> bytes:
    """
    Download a file from Google Cloud Storage as bytes.

    Args:
        storage_client (storage.Client): Google Cloud Storage client
        bucket_name (str): Name of the bucket
        source_blob_name (str): Name of the source blob

    Returns:
        bytes: The content of the file as bytes
    """
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    return blob.download_as_bytes()
