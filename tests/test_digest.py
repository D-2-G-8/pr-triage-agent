from pr_triage.digest import build_digest, render_digest_markdown
from pr_triage.models import AssessedPR, Digest, PRAssessment


def assessed(category, number=1, title="t"):
    return AssessedPR(
        number=number,
        title=title,
        assessment=PRAssessment(
            summary="s",
            problem_statement="p",
            dod_ac_status="d",
            reality_assessment="r",
            recommended_category=category,
        ),
    )


def test_counts_all_categories_and_total():
    items = [
        assessed("ready_for_review", 1),
        assessed("ready_for_review", 2),
        assessed("likely_duplicate", 3),
        assessed("stale", 4),
    ]

    d = build_digest(items)

    assert d.total == 4
    assert d.counts == {
        "ready_for_review": 2,
        "likely_duplicate": 1,
        "stale": 1,
        "low_value": 0,
    }


def test_ready_list_holds_only_ready_and_is_capped():
    items = [assessed("ready_for_review", i) for i in range(20)]

    d = build_digest(items, top_n=15)

    assert len(d.ready) == 15
    assert d.ready_count == 20
    assert d.ready_truncated is True
    assert all(x.assessment.recommended_category == "ready_for_review" for x in d.ready)


def test_ready_not_truncated_when_within_top_n():
    d = build_digest([assessed("ready_for_review", 1)], top_n=15)

    assert d.ready_count == 1
    assert d.ready_truncated is False


def test_returns_digest_type():
    assert isinstance(build_digest([]), Digest)


def test_markdown_puts_ready_section_first_with_counts():
    d = build_digest([
        assessed("ready_for_review", 42, "Fix retry logic"),
        assessed("likely_duplicate", 7, "Dup change"),
    ])

    md = render_digest_markdown(d)

    ready_pos = md.index("Ready for review")
    breakdown_pos = md.index("Category breakdown")
    assert ready_pos < breakdown_pos          # ready section comes first
    assert "#42" in md and "Fix retry logic" in md
    assert "ready_for_review" in md and "likely_duplicate" in md
    assert "2" in md                           # total analyzed


def test_markdown_notes_truncation():
    d = build_digest([assessed("ready_for_review", i) for i in range(20)], top_n=15)

    md = render_digest_markdown(d)

    assert "15" in md and "20" in md           # showing 15 of 20


def test_markdown_links_prs_when_repo_given():
    d = build_digest([assessed("ready_for_review", 42, "Fix retry logic")])

    md = render_digest_markdown(d, repo_full_name="anthropics/claude-cookbooks")

    assert "https://github.com/anthropics/claude-cookbooks/pull/42" in md
