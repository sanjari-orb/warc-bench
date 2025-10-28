import time
import base64
import hmac
import hashlib
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

SECRET_KEY = "3r98pew6yfdsijfgh3or597t3g"


def add_query_param(url: str, param: str, value: str) -> str:
    """
    Adds a query parameter to a URL.

    :param url: The original URL
    :param param: The query parameter key
    :param value: The query parameter value
    :return: The modified URL with the added parameter
    """
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    query_params[param] = [value]  # Add or replace the parameter

    new_query_string = urlencode(query_params, doseq=True)
    new_url = urlunparse(parsed_url._replace(query=new_query_string))

    return new_url


def generate_token(
    user_id: str, user_group: str, only_current_hour: bool = False
) -> str:
    """
    Generate a stateless token that is valid for the current hour and the next hour.
    """
    # Use the current hour (UTC-based). E.g., if the time is 2025-02-12 10:15, current_hour = 561459 (10:15 // 3600).
    current_hour = int(time.time() // 3600)
    if only_current_hour:
        current_hour -= 1

    # The token data without the signature
    data = f"{user_id}:{user_group}:{current_hour}"

    # Compute an HMAC signature using SHA-256
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"), data.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    # Construct the token as: user_id:user_group:current_hour:signature
    token_str = f"{data}:{signature}"

    # Encode the entire token in Base64 (URL-safe to avoid issues in URLs)
    token_b64 = base64.urlsafe_b64encode(token_str.encode("utf-8")).decode("utf-8")
    return token_b64


def validate_token(token: str) -> tuple[str, str, int] | None:
    """Validates a token and returns user_id, user_group, and expire time."""
    try:
        # Decode the Base64 token
        token_bytes = base64.urlsafe_b64decode(token)
        token_str = token_bytes.decode("utf-8")

        # Expected format: user_id:user_group:hour:signature
        parts = token_str.split(":")
        if len(parts) != 4:
            return None

        token_user_id, token_user_group, token_hour_str, token_signature = parts

        # Recompute the expected signature
        data_without_signature = f"{token_user_id}:{token_user_group}:{token_hour_str}"
        expected_signature = hmac.new(
            SECRET_KEY.encode("utf-8"),
            data_without_signature.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # Check that the signature matches
        if not hmac.compare_digest(expected_signature, token_signature):
            return None

        # Check that the hour is valid (current hour or next hour)
        token_hour = int(token_hour_str)
        current_hour = int(time.time() // 3600)

        if token_hour == current_hour or token_hour == current_hour - 1:
            return token_user_id, token_user_group, (token_hour + 2) * 3600
        else:
            return None

    except Exception:
        # If anything fails in decoding/parsing, treat as invalid
        return None
