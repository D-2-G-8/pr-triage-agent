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


@dataclass(frozen=True)
class LinkedIssue:
    """An issue a PR closes, with the engagement signal used to gauge realness."""

    number: int
    title: str
    state: str
    thumbs_up: int
    comments_count: int


@dataclass(frozen=True)
class ChangedFile:
    """One file touched by a PR (path and line counts, not the patch text)."""

    path: str
    additions: int
    deletions: int


@dataclass(frozen=True)
class PRAssessment:
    """The five-field triage verdict for one PR (no field may be empty)."""

    summary: str
    problem_statement: str
    dod_ac_status: str
    reality_assessment: str
    recommended_category: str


@dataclass(frozen=True)
class RepoContext:
    """The repository's own DoD/AC reference material for grounding assessments."""

    contributing: str | None
    pr_template: str | None


@dataclass(frozen=True)
class EnrichedPullRequest:
    """Structured per-PR context gathered from GitHub GraphQL (no diff text)."""

    number: int
    title: str
    body: str
    author: str
    state: str
    draft: bool
    labels: list[str]
    ci_status: str | None
    linked_issues: list[LinkedIssue]
    changed_files: list[ChangedFile]
    files_truncated: bool
