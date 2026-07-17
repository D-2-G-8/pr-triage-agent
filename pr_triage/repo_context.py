from pr_triage.models import RepoContext

_CONTRIBUTING_PATHS = (
    "CONTRIBUTING.md",
    ".github/CONTRIBUTING.md",
    "docs/CONTRIBUTING.md",
)

_PR_TEMPLATE_PATHS = (
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/pull_request_template.md",
    "PULL_REQUEST_TEMPLATE.md",
    "docs/PULL_REQUEST_TEMPLATE.md",
)


def _first_present(get_text, paths):
    for path in paths:
        text = get_text(path)
        if text is not None:
            return text
    return None


def fetch_repo_context(get_text):
    """Collect the repo's DoD/AC reference material (CONTRIBUTING + PR template).

    ``get_text(path)`` is injected and returns the file's text, or None if absent,
    so path resolution is testable without the network. The first matching
    location for each document wins.
    """
    return RepoContext(
        contributing=_first_present(get_text, _CONTRIBUTING_PATHS),
        pr_template=_first_present(get_text, _PR_TEMPLATE_PATHS),
    )
