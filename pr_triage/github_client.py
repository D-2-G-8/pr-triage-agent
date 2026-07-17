import os

from github import Auth, Github


def build_client(token=None):
    """Return a PyGithub client authenticated with a personal access token.

    The token is taken from the ``token`` argument, or from the ``GITHUB_TOKEN``
    environment variable when not provided. Raises RuntimeError if neither is set.
    """
    token = token or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN is not set; add it to your environment or .env file"
        )
    return Github(auth=Auth.Token(token))
