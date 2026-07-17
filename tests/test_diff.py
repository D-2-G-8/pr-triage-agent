from pr_triage.diff import cap_diff


def test_returns_diff_unchanged_when_within_limit():
    text = "diff --git a/x b/x\n+one line\n"

    assert cap_diff(text, max_chars=1000) == text


def test_truncates_and_marks_when_over_limit():
    text = "x" * 5000

    result = cap_diff(text, max_chars=1000)

    # kept content is bounded by max_chars; a marker discloses what was dropped
    assert result.startswith("x" * 1000)
    assert "truncated" in result.lower()
    assert "5000" in result  # original size disclosed
    assert result != text


def test_truncation_never_silently_drops_content():
    # A cap must announce itself — no silent loss.
    result = cap_diff("y" * 2000, max_chars=500)

    assert "truncated" in result.lower()
