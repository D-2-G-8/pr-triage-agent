import json
from types import SimpleNamespace

from pr_triage.analysis import CATEGORIES, analyze_pr, build_prompt
from pr_triage.models import (
    ChangedFile,
    EnrichedPullRequest,
    LinkedIssue,
    PRAssessment,
    RepoContext,
)


class FakeMessages:
    def __init__(self, text):
        self._text = text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self._text)])


class FakeClient:
    def __init__(self, text):
        self.messages = FakeMessages(text)


def make_enriched(**over):
    base = dict(
        number=42,
        title="Fix retry logic",
        body="Retries never terminate; this bounds them. Closes #100",
        author="daria",
        state="OPEN",
        draft=False,
        labels=["bug"],
        ci_status="FAILURE",
        linked_issues=[
            LinkedIssue(number=100, title="Retries never stop", state="OPEN",
                        thumbs_up=12, comments_count=5)
        ],
        changed_files=[ChangedFile(path="retry.py", additions=10, deletions=2)],
        files_truncated=False,
    )
    base.update(over)
    return EnrichedPullRequest(**base)


CONTEXT = RepoContext(contributing="Every notebook must pass validation.",
                      pr_template="## Description\n## Testing")


def test_system_prompt_grounds_in_repo_context_and_five_fields():
    system, _ = build_prompt(make_enriched(), diff="diff text", repo_context=CONTEXT)

    assert "Every notebook must pass validation." in system  # CONTRIBUTING
    assert "## Description" in system                         # PR template
    for field in ("summary", "problem_statement", "dod_ac_status",
                  "reality_assessment", "recommended_category"):
        assert field in system
    for category in CATEGORIES:
        assert category in system


def test_user_prompt_carries_pr_facts_and_diff():
    _, user = build_prompt(make_enriched(), diff="UNIQUE_DIFF_MARKER", repo_context=CONTEXT)

    assert "42" in user and "Fix retry logic" in user
    assert "Retries never terminate" in user       # body
    assert "FAILURE" in user                        # CI status
    assert "retry.py" in user                       # changed file
    assert "UNIQUE_DIFF_MARKER" in user             # the diff
    # linked issue engagement is surfaced for the reality assessment
    assert "#100" in user and "12" in user and "5" in user


def test_user_prompt_flags_absence_of_linked_issue():
    enriched = make_enriched(linked_issues=[])

    _, user = build_prompt(enriched, diff="d", repo_context=CONTEXT)

    # AC: when nothing is linked, say so explicitly instead of implying engagement
    assert "no linked issue" in user.lower() or "none" in user.lower()


ASSESSMENT_JSON = json.dumps({
    "summary": "Bounds retry attempts to 3.",
    "problem_statement": "Retries never terminate.",
    "dod_ac_status": "CI check FAILURE — not met.",
    "reality_assessment": "Linked issue #100 has 12 thumbs-up; problem is real.",
    "recommended_category": "ready_for_review",
})


def test_analyze_pr_maps_json_response_to_assessment():
    client = FakeClient(ASSESSMENT_JSON)

    result = analyze_pr(make_enriched(), diff="d", repo_context=CONTEXT, client=client)

    assert result == PRAssessment(
        summary="Bounds retry attempts to 3.",
        problem_statement="Retries never terminate.",
        dod_ac_status="CI check FAILURE — not met.",
        reality_assessment="Linked issue #100 has 12 thumbs-up; problem is real.",
        recommended_category="ready_for_review",
    )


def test_analyze_pr_calls_claude_with_schema_and_prompt():
    client = FakeClient(ASSESSMENT_JSON)

    analyze_pr(make_enriched(), diff="d", repo_context=CONTEXT, client=client)

    call = client.messages.calls[0]
    assert call["model"] == "claude-opus-4-8"
    assert call["system"], "system prompt should be passed"
    assert call["messages"][0]["role"] == "user"
    schema = call["output_config"]["format"]["schema"]
    assert set(schema["required"]) == {
        "summary", "problem_statement", "dod_ac_status",
        "reality_assessment", "recommended_category",
    }
    assert schema["properties"]["recommended_category"]["enum"] == CATEGORIES
