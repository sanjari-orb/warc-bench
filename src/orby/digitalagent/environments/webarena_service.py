import boto3
import os
import time
import requests
from requests_aws4auth import AWS4Auth
from retry import retry


API_ENDPOINT = "https://webarena.orbyapi.com"
REGION = "us-east-1"


def get_aws_auth():
    """Get AWS authentication for requests."""
    session = boto3.Session()
    credentials = session.get_credentials()
    return AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        REGION,
        "execute-api",
        session_token=credentials.token,
    )


def request_instance(
    instance_type=None, ttl_hours=None, experiment=""
) -> tuple[str, dict]:
    """Requests an EC2 instance and returns the instance ID."""
    url = f"{API_ENDPOINT}/environments/request"

    # Prepare request body with optional instance type
    body = {}
    if instance_type:
        body["instance_type"] = instance_type
    if ttl_hours:
        body["ttl_hours"] = ttl_hours
    if experiment:
        body["experiment"] = experiment

    response = requests.post(url, json=body, auth=get_aws_auth())
    return response.json().get("instance_id"), response.json()


def get_instance(instance_id) -> tuple[bool, str]:
    """Checks the status of a requested instance and returns a readiness flag and public IP address of the instance."""
    url = f"{API_ENDPOINT}/environments/{instance_id}/status"

    response = requests.get(url, auth=get_aws_auth())
    return response.json().get("status") == "available", response.json().get(
        "public_ip", ""
    )


def release_instance(instance_id):
    """Terminates an EC2 instance."""
    url = f"{API_ENDPOINT}/environments/{instance_id}/release"

    requests.post(url, json={}, auth=get_aws_auth())


@retry(ValueError, tries=10, delay=30, backoff=2)
def create_instance(
    instance_type=None, verbose=False, ttl_hours=None, experiment=""
) -> tuple[str, str]:
    """Creates a ready-to-use instance and returns its instance ID and public IP."""
    if not experiment and "RUN_NAME" in os.environ:
        experiment = os.environ["RUN_NAME"]
    instance_id, response_json = request_instance(
        instance_type=instance_type,
        ttl_hours=ttl_hours,
        experiment=experiment,
    )
    if not instance_id:
        raise ValueError("Failed to request an instance: {}".format(str(response_json)))
    if verbose:
        print("Requested an instance:", instance_id)

    # Wait for the instance to become available
    while True:
        ready, public_ip = get_instance(instance_id)
        if ready:
            if verbose:
                print("Instance is ready to use, public IP:", public_ip)
            return instance_id, public_ip
        if verbose:
            print("Waiting for the instance to become available...")
        time.sleep(30)


def app(instance_type=None, ttl_hours=None, experiment=""):
    start = time.time()
    create_instance(
        instance_type=instance_type,
        ttl_hours=ttl_hours,
        experiment=experiment,
        verbose=True,
    )
    print("Time spent:", time.time() - start)


if __name__ == "__main__":
    import fire

    fire.Fire(app)
