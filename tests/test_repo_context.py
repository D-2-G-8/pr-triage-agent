from pr_triage.models import RepoContext
from pr_triage.repo_context import fetch_repo_context


def fake_get_text(files):
    """A get_text(path) backed by a dict; returns None for missing paths."""
    return lambda path: files.get(path)


def test_maps_contributing_and_pr_template():
    get_text = fake_get_text({
        "CONTRIBUTING.md": "Follow the style guide.",
        ".github/PULL_REQUEST_TEMPLATE.md": "## Description",
    })

    assert fetch_repo_context(get_text) == RepoContext(
        contributing="Follow the style guide.",
        pr_template="## Description",
    )


def test_falls_back_to_dot_github_contributing_location():
    get_text = fake_get_text({".github/CONTRIBUTING.md": "in .github"})

    result = fetch_repo_context(get_text)

    assert result.contributing == "in .github"


def test_finds_lowercase_pr_template_variant():
    get_text = fake_get_text({".github/pull_request_template.md": "lower"})

    result = fetch_repo_context(get_text)

    assert result.pr_template == "lower"


def test_none_when_neither_present():
    result = fetch_repo_context(fake_get_text({}))

    assert result == RepoContext(contributing=None, pr_template=None)


def test_first_matching_location_wins():
    get_text = fake_get_text({
        "CONTRIBUTING.md": "root",
        ".github/CONTRIBUTING.md": "dot-github",
    })

    assert fetch_repo_context(get_text).contributing == "root"
