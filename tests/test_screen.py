import json
from types import SimpleNamespace

from pr_triage.analysis import CATEGORIES
from pr_triage.models import ChangedFile, EnrichedPullRequest, LinkedIssue, ScreenResult
from pr_triage.screen import SCREEN_MODEL, build_screen_prompt, screen_pr


def make_enriched(**over):
    base = dict(
        number=42, title="Fix retry logic", body="Bounds retries. Closes #100",
        author="daria", state="OPEN", draft=False, labels=["bug"], ci_status="FAILURE",
        linked_issues=[LinkedIssue(100, "Retries never stop", "OPEN", 12, 5)],
        changed_files=[ChangedFile("retry.py", 10, 2)], files_truncated=False,
    )
    base.update(over)
    return EnrichedPullRequest(**base)


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


def test_screen_prompt_uses_metadata_and_omits_the_diff():
    system, user = build_screen_prompt(make_enriched())

    assert "42" in user and "Fix retry logic" in user
    assert "FAILURE" in user and "retry.py" in user
    assert "#100" in user and "12" in user           # engagement signal
    assert "diff" not in user.lower()                 # no diff sent at screen time
    assert "worth" in system.lower()                  # decides worth of deep review


SCREEN_JSON = json.dumps({
    "worth_review": True,
    "reason": "Fixes a bug tied to an engaged issue.",
    "likely_category": "ready_for_review",
})


def test_screen_pr_maps_result():
    client = FakeClient(SCREEN_JSON)

    result = screen_pr(make_enriched(), client=client)

    assert result == ScreenResult(
        worth_review=True,
        reason="Fixes a bug tied to an engaged issue.",
        likely_category="ready_for_review",
    )


def test_screen_pr_uses_cheap_model_and_schema():
    client = FakeClient(SCREEN_JSON)

    screen_pr(make_enriched(), client=client)

    call = client.messages.calls[0]
    assert call["model"] == SCREEN_MODEL == "claude-haiku-4-5"
    schema = call["output_config"]["format"]["schema"]
    assert set(schema["required"]) == {"worth_review", "reason", "likely_category"}
    assert schema["properties"]["likely_category"]["enum"] == CATEGORIES
