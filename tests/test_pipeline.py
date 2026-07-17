from pr_triage.models import (
    AssessedPR,
    ChangedFile,
    EnrichedPullRequest,
    PRAssessment,
    RepoContext,
)
from pr_triage.pipeline import triage_pr


def make_enriched(number=42):
    return EnrichedPullRequest(
        number=number, title="t", body="b", author="a", state="OPEN", draft=False,
        labels=[], ci_status=None, linked_issues=[],
        changed_files=[ChangedFile("f.py", 1, 0)], files_truncated=False,
    )


CTX = RepoContext(contributing="c", pr_template="t")


def test_triage_pr_composes_enrichment_diff_and_analysis():
    seen = {}

    def analyze(enriched, diff, repo_context):
        seen["enriched"] = enriched
        seen["diff"] = diff
        seen["ctx"] = repo_context
        return PRAssessment("s", "p", "d", "r", "ready_for_review")

    result = triage_pr(
        42, "My title",
        enrich=lambda n: make_enriched(n),
        get_diff=lambda n: "x" * 100,
        repo_context=CTX,
        analyze=analyze,
        max_diff_chars=50,
    )

    assert result == AssessedPR(
        number=42, title="My title",
        assessment=PRAssessment("s", "p", "d", "r", "ready_for_review"),
    )
    assert seen["enriched"].number == 42
    assert seen["ctx"] is CTX
    # the diff is capped before analysis
    assert "truncated" in seen["diff"].lower()
    assert seen["diff"].startswith("x" * 50)
