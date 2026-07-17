import pytest

from pr_triage.github_rest import RestClient


class FakeResponse:
    def __init__(self, text, status=200):
        self.text = text
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def get(self, url, headers):
        self.calls.append({"url": url, "headers": headers})
        return self._response


DIFF = "diff --git a/retry.py b/retry.py\n@@ -1 +1 @@\n-old\n+new\n"


def test_fetch_pr_diff_returns_unified_diff_text():
    session = FakeSession(FakeResponse(DIFF))
    client = RestClient(token="ghp_x", session=session)

    assert client.fetch_pr_diff("anthropics/claude-cookbooks", 42) == DIFF


def test_fetch_pr_diff_requests_the_diff_media_type_with_auth():
    session = FakeSession(FakeResponse(DIFF))
    client = RestClient(token="ghp_secret", session=session)

    client.fetch_pr_diff("anthropics/claude-cookbooks", 42)

    call = session.calls[0]
    assert call["url"] == "https://api.github.com/repos/anthropics/claude-cookbooks/pulls/42"
    assert call["headers"]["Accept"] == "application/vnd.github.v3.diff"
    assert call["headers"]["Authorization"] == "Bearer ghp_secret"


def test_fetch_pr_diff_raises_on_http_error():
    session = FakeSession(FakeResponse("", status=404))
    client = RestClient(token="ghp_x", session=session)

    with pytest.raises(RuntimeError, match="HTTP 404"):
        client.fetch_pr_diff("anthropics/claude-cookbooks", 999)
