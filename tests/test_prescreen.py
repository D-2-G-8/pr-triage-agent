from pr_triage.models import ChangedFile, EnrichedPullRequest, PRAssessment
from pr_triage.prescreen import bot_assessment, is_bot_pr


def enriched(author="daria", author_is_bot=False):
    return EnrichedPullRequest(
        number=1, title="t", body="b", author=author, state="OPEN", draft=False,
        labels=[], ci_status=None, linked_issues=[],
        changed_files=[ChangedFile("f", 1, 0)], files_truncated=False,
        author_is_bot=author_is_bot,
    )


def test_bot_flag_from_typename_is_detected():
    assert is_bot_pr(enriched(author="whatever", author_is_bot=True)) is True


def test_bot_suffix_login_is_detected():
    assert is_bot_pr(enriched(author="some-app[bot]")) is True


def test_known_bot_names_are_detected():
    assert is_bot_pr(enriched(author="dependabot")) is True
    assert is_bot_pr(enriched(author="renovate[bot]")) is True


def test_human_author_is_not_a_bot():
    assert is_bot_pr(enriched(author="daria")) is False


def test_missing_author_is_not_a_bot():
    assert is_bot_pr(enriched(author=None)) is False


def test_bot_assessment_is_low_value_with_no_empty_fields():
    a = bot_assessment(enriched(author="dependabot"))

    assert isinstance(a, PRAssessment)
    assert a.recommended_category == "low_value"
    assert "dependabot" in a.summary
    assert all(getattr(a, f) for f in
               ("summary", "problem_statement", "dod_ac_status",
                "reality_assessment", "recommended_category"))
