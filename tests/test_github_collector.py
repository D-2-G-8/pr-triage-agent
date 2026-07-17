from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from pr_triage.github_collector import fetch_open_pull_requests
from pr_triage.models import PullRequest


def make_raw_pr(
    number=1,
    title="Add example",
    login="octocat",
    state="open",
    created_at=datetime(2026, 7, 1, 12, 0, 0),
    updated_at=datetime(2026, 7, 2, 12, 0, 0),
    html_url="https://github.com/anthropics/claude-cookbooks/pull/1",
    draft=False,
):
    """A stand-in for a PyGithub PullRequest object (only the attrs we read)."""
    return SimpleNamespace(
        number=number,
        title=title,
        user=SimpleNamespace(login=login),
        state=state,
        created_at=created_at,
        updated_at=updated_at,
        html_url=html_url,
        draft=draft,
    )


def make_client(raw_pulls):
    client = MagicMock()
    client.get_repo.return_value.get_pulls.return_value = raw_pulls
    return client


def test_maps_raw_pr_fields_to_pull_request():
    raw = make_raw_pr(
        number=42,
        title="Fix retry logic",
        login="daria",
        created_at=datetime(2026, 6, 1, 9, 0, 0),
        updated_at=datetime(2026, 6, 3, 9, 0, 0),
        html_url="https://github.com/anthropics/claude-cookbooks/pull/42",
        draft=True,
    )
    client = make_client([raw])

    result = fetch_open_pull_requests("anthropics/claude-cookbooks", client)

    assert result == [
        PullRequest(
            number=42,
            title="Fix retry logic",
            author="daria",
            state="open",
            created_at=datetime(2026, 6, 1, 9, 0, 0),
            updated_at=datetime(2026, 6, 3, 9, 0, 0),
            html_url="https://github.com/anthropics/claude-cookbooks/pull/42",
            draft=True,
        )
    ]


def test_returns_empty_list_when_no_open_pulls():
    client = make_client([])

    assert fetch_open_pull_requests("anthropics/claude-cookbooks", client) == []


def test_maps_every_pr_across_pages():
    raws = [make_raw_pr(number=n) for n in range(1, 6)]
    client = make_client(raws)

    result = fetch_open_pull_requests("anthropics/claude-cookbooks", client)

    assert [pr.number for pr in result] == [1, 2, 3, 4, 5]


def test_requests_only_open_pulls_from_the_repo():
    client = make_client([make_raw_pr()])

    fetch_open_pull_requests("anthropics/claude-cookbooks", client)

    client.get_repo.assert_called_once_with("anthropics/claude-cookbooks")
    client.get_repo.return_value.get_pulls.assert_called_once_with(state="open")
