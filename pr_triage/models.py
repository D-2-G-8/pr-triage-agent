from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PullRequest:
    """A minimal, GitHub-agnostic view of an open pull request."""

    number: int
    title: str
    author: str
    state: str
    created_at: datetime
    updated_at: datetime
    html_url: str
    draft: bool
