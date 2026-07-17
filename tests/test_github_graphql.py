import pytest

from pr_triage.github_graphql import GraphQLClient, GraphQLError


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def post(self, url, json, headers):
        self.calls.append({"url": url, "json": json, "headers": headers})
        return self._response


def test_execute_returns_unwrapped_data():
    session = FakeSession(FakeResponse({"data": {"repository": {"pullRequest": {"number": 5}}}}))
    client = GraphQLClient(token="ghp_x", session=session)

    data = client.execute("query { x }", {"number": 5})

    assert data == {"repository": {"pullRequest": {"number": 5}}}


def test_execute_posts_query_variables_and_auth_header():
    session = FakeSession(FakeResponse({"data": {}}))
    client = GraphQLClient(token="ghp_secret", session=session)

    client.execute("query($n: Int!) { x }", {"n": 7})

    call = session.calls[0]
    assert call["url"] == "https://api.github.com/graphql"
    assert call["json"] == {"query": "query($n: Int!) { x }", "variables": {"n": 7}}
    assert call["headers"]["Authorization"] == "Bearer ghp_secret"


def test_execute_raises_on_graphql_errors():
    session = FakeSession(
        FakeResponse({"data": None, "errors": [{"message": "Could not resolve to a Repository"}]})
    )
    client = GraphQLClient(token="ghp_x", session=session)

    with pytest.raises(GraphQLError, match="Could not resolve"):
        client.execute("query { x }", {})
