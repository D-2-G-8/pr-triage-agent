from pr_triage.enrichment import fetch_pr_enrichment
from pr_triage.models import ChangedFile, EnrichedPullRequest, LinkedIssue


def make_data(
    number=42,
    title="Fix retry logic",
    body="Closes #100",
    state="OPEN",
    is_draft=False,
    author={"login": "daria"},
    labels=("bug", "enhancement"),
    rollup_state="FAILURE",
    linked=(
        {
            "number": 100,
            "title": "Retries never stop",
            "state": "OPEN",
            "reactions": {"totalCount": 12},
            "comments": {"totalCount": 5},
        },
    ),
    files=({"path": "retry.py", "additions": 10, "deletions": 2},),
    has_next_files=False,
):
    """A stand-in for the GraphQL `data` payload our execute() returns."""
    return {
        "repository": {
            "pullRequest": {
                "number": number,
                "title": title,
                "body": body,
                "state": state,
                "isDraft": is_draft,
                "author": author,
                "labels": {"nodes": [{"name": n} for n in labels]},
                "commits": {
                    "nodes": [
                        {"commit": {"statusCheckRollup": {"state": rollup_state}
                                    if rollup_state else None}}
                    ]
                },
                "closingIssuesReferences": {"nodes": list(linked)},
                "files": {
                    "nodes": list(files),
                    "pageInfo": {"hasNextPage": has_next_files},
                },
            }
        }
    }


def fake_execute(data):
    calls = {}

    def execute(query, variables):
        calls["query"] = query
        calls["variables"] = variables
        return data

    execute.calls = calls
    return execute


def test_maps_graphql_payload_to_enriched_pull_request():
    execute = fake_execute(make_data())

    result = fetch_pr_enrichment("anthropics/claude-cookbooks", 42, execute)

    assert result == EnrichedPullRequest(
        number=42,
        title="Fix retry logic",
        body="Closes #100",
        author="daria",
        state="OPEN",
        draft=False,
        labels=["bug", "enhancement"],
        ci_status="FAILURE",
        linked_issues=[
            LinkedIssue(
                number=100,
                title="Retries never stop",
                state="OPEN",
                thumbs_up=12,
                comments_count=5,
            )
        ],
        changed_files=[ChangedFile(path="retry.py", additions=10, deletions=2)],
        files_truncated=False,
    )


def test_author_is_none_when_account_deleted():
    execute = fake_execute(make_data(author=None))

    result = fetch_pr_enrichment("anthropics/claude-cookbooks", 42, execute)

    assert result.author is None


def test_ci_status_is_none_without_a_rollup():
    execute = fake_execute(make_data(rollup_state=None))

    result = fetch_pr_enrichment("anthropics/claude-cookbooks", 42, execute)

    assert result.ci_status is None


def test_ci_status_is_none_when_no_commits():
    data = make_data()
    data["repository"]["pullRequest"]["commits"]["nodes"] = []
    execute = fake_execute(data)

    result = fetch_pr_enrichment("anthropics/claude-cookbooks", 42, execute)

    assert result.ci_status is None


def test_no_linked_issues_and_no_files():
    execute = fake_execute(make_data(linked=(), files=()))

    result = fetch_pr_enrichment("anthropics/claude-cookbooks", 42, execute)

    assert result.linked_issues == []
    assert result.changed_files == []


def test_flags_truncated_file_list():
    execute = fake_execute(make_data(has_next_files=True))

    result = fetch_pr_enrichment("anthropics/claude-cookbooks", 42, execute)

    assert result.files_truncated is True


def test_passes_owner_name_number_as_variables():
    execute = fake_execute(make_data(number=7))

    fetch_pr_enrichment("anthropics/claude-cookbooks", 7, execute)

    assert execute.calls["variables"] == {
        "owner": "anthropics",
        "name": "claude-cookbooks",
        "number": 7,
    }
