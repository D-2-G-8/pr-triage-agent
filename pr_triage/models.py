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
class AssessedPR:
    """A PR paired with its triage verdict — the unit the digest aggregates."""

    number: int
    title: str
    assessment: "PRAssessment"


@dataclass(frozen=True)
class Digest:
    """Aggregated triage summary over all assessed PRs."""

    total: int
    counts: dict[str, int]
    ready: list[AssessedPR]
    ready_count: int
    ready_truncated: bool


@dataclass(frozen=True)
class TriageFailure:
    """A backlog item that could not be processed after all retries."""

    item: object
    error: str


@dataclass(frozen=True)
class TriageRun:
    """Outcome of a backlog pass: successes and per-item failures."""

    results: list
    failures: list[TriageFailure]


@dataclass(frozen=True)
class ScreenResult:
    """Tier 1 cheap-screen verdict: is a PR worth a full, expensive review?"""

    worth_review: bool
    reason: str
    likely_category: str


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
    author_is_bot: bool = False
