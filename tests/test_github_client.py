import pytest
from github import Github

from pr_triage.github_client import build_client


def test_build_client_returns_github_instance_with_explicit_token():
    client = build_client(token="ghp_explicit")

    assert isinstance(client, Github)


def test_build_client_reads_token_from_environment(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_from_env")

    client = build_client()

    assert isinstance(client, Github)


def test_build_client_without_token_raises_runtime_error(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
        build_client()
