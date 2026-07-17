import requests


class GraphQLError(RuntimeError):
    """Raised when the GitHub GraphQL API returns an ``errors`` array."""


class GraphQLClient:
    """Thin GitHub GraphQL client: POST a query, unwrap ``data``, raise on errors.

    The HTTP session is injectable so ``execute`` can be tested without the network.
    """

    ENDPOINT = "https://api.github.com/graphql"

    def __init__(self, token, session=None):
        self._token = token
        self._session = session or requests.Session()

    def execute(self, query, variables):
        response = self._session.post(
            self.ENDPOINT,
            json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {self._token}"},
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            raise GraphQLError(payload["errors"])
        return payload["data"]
