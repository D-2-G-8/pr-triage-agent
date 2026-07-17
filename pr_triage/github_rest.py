import requests


class RestClient:
    """Thin GitHub REST client for what PyGithub/GraphQL don't cover cleanly.

    Currently: the raw unified diff of a PR (needs a custom Accept media type).
    The HTTP session is injectable so requests can be tested without the network.
    """

    API = "https://api.github.com"

    def __init__(self, token, session=None):
        self._token = token
        self._session = session or requests.Session()

    def fetch_pr_diff(self, repo_full_name, number):
        owner, name = repo_full_name.split("/", 1)
        response = self._session.get(
            f"{self.API}/repos/{owner}/{name}/pulls/{number}",
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github.v3.diff",
            },
        )
        response.raise_for_status()
        return response.text
