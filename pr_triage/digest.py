from pr_triage.analysis import CATEGORIES
from pr_triage.models import Digest

_CATEGORY_LABELS = {
    "ready_for_review": "Ready for review",
    "likely_duplicate": "Likely duplicate",
    "stale": "Stale",
    "low_value": "Low value",
}


def build_digest(assessed, top_n=15):
    """Aggregate assessed PRs into a digest.

    Per the acceptance criteria, ``ready_for_review`` is the headline category and
    is capped at ``top_n`` (default 15) rather than dumping the whole backlog. The
    full count is preserved and truncation is flagged so nothing is silently lost.
    """
    counts = {category: 0 for category in CATEGORIES}
    for item in assessed:
        category = item.assessment.recommended_category
        counts[category] = counts.get(category, 0) + 1

    ready = [a for a in assessed if a.assessment.recommended_category == "ready_for_review"]
    return Digest(
        total=len(assessed),
        counts=counts,
        ready=ready[:top_n],
        ready_count=len(ready),
        ready_truncated=len(ready) > top_n,
    )


def _pr_link(item, repo_full_name):
    label = f"#{item.number} {item.title}"
    if repo_full_name:
        return f"[{label}](https://github.com/{repo_full_name}/pull/{item.number})"
    return label


def render_digest_markdown(digest, repo_full_name=None):
    """Render a Digest as a Markdown report — ready-for-review section first."""
    lines = ["# PR Triage Digest", ""]
    lines.append(f"**{digest.total} open PRs analyzed.**")
    lines.append("")

    shown = len(digest.ready)
    lines.append(f"## Ready for review ({digest.ready_count})")
    if digest.ready_truncated:
        lines.append(f"_Showing top {shown} of {digest.ready_count}._")
    if digest.ready:
        for item in digest.ready:
            lines.append(f"- {_pr_link(item, repo_full_name)}")
            lines.append(f"  - {item.assessment.summary}")
    else:
        lines.append("_None._")
    lines.append("")

    lines.append("## Category breakdown")
    for category in CATEGORIES:
        label = _CATEGORY_LABELS.get(category, category)
        lines.append(f"- {label} (`{category}`): {digest.counts.get(category, 0)}")

    return "\n".join(lines) + "\n"
