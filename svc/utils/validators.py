import os


def initial_validation():
    """
    Validate that the environment is set and the Sentinel Hub credentials are set.
    """
    check_if_environment_is_set()
    check_if_sentinel_hub_credentials_are_set()


def check_if_sentinel_hub_credentials_are_set():
    """
    Validate that the Sentinel Hub credentials are set. (Not empty)
    """
    if not os.getenv("SENTINEL_HUB_CLIENT_ID") or not os.getenv(
        "SENTINEL_HUB_CLIENT_SECRET"
    ):
        raise ValueError("Sentinel Hub credentials are not set")
    return True


def check_if_environment_is_set():
    """
    Validate that the Sentinel Hub credentials are set. (Not empty)
    """
    if not os.getenv("ENV"):
        raise ValueError("Environment is not set")
    return True
