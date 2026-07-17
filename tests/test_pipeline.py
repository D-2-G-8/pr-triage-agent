from pr_triage.models import (
    AssessedPR,
    ChangedFile,
    EnrichedPullRequest,
    PRAssessment,
    RepoContext,
    ScreenResult,
)
from pr_triage.pipeline import triage_pr, triage_pr_tiered


def make_enriched(number=42, author="a", author_is_bot=False):
    return EnrichedPullRequest(
        number=number, title="t", body="b", author=author, state="OPEN", draft=False,
        labels=[], ci_status=None, linked_issues=[],
        changed_files=[ChangedFile("f.py", 1, 0)], files_truncated=False,
        author_is_bot=author_is_bot,
    )


def counting(store, key, value):
    store[key] = store.get(key, 0) + 1
    return value


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


READY = PRAssessment("s", "p", "d", "r", "ready_for_review")


def test_tiered_bot_pr_uses_canned_verdict_without_screen_or_analysis():
    calls = {}

    result = triage_pr_tiered(
        1, "T",
        enrich=lambda n: make_enriched(author="dependabot", author_is_bot=True),
        get_diff=lambda n: counting(calls, "diff", "d"),
        repo_context=CTX,
        screen=lambda e: counting(calls, "screen", ScreenResult(True, "r", "ready_for_review")),
        analyze=lambda e, d, c: counting(calls, "analyze", READY),
    )

    assert result.assessment.recommended_category == "low_value"
    assert calls == {}  # no screen, no diff fetch, no Opus analysis


def test_tiered_screen_skip_avoids_diff_and_deep_analysis():
    calls = {}

    result = triage_pr_tiered(
        2, "T",
        enrich=lambda n: make_enriched(author="human"),
        get_diff=lambda n: counting(calls, "diff", "d"),
        repo_context=CTX,
        screen=lambda e: ScreenResult(worth_review=False, reason="trivial",
                                      likely_category="low_value"),
        analyze=lambda e, d, c: counting(calls, "analyze", READY),
    )

    assert result.assessment.recommended_category == "low_value"
    assert "diff" not in calls and "analyze" not in calls


def test_tiered_keep_runs_diff_and_full_analysis():
    seen = {}

    def analyze(enriched, diff, ctx):
        seen["diff"] = diff
        return READY

    result = triage_pr_tiered(
        3, "T",
        enrich=lambda n: make_enriched(author="human"),
        get_diff=lambda n: "x" * 100,
        repo_context=CTX,
        screen=lambda e: ScreenResult(True, "looks real", "ready_for_review"),
        analyze=analyze,
        max_diff_chars=50,
    )

    assert result.assessment.recommended_category == "ready_for_review"
    assert "truncated" in seen["diff"].lower()   # diff fetched and capped
