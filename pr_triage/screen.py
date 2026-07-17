import json

from pr_triage.analysis import CATEGORIES
from pr_triage.models import PRAssessment, ScreenResult

SCREEN_MODEL = "claude-haiku-4-5"

_SYSTEM = """You are a fast, cheap pre-screener for a PR triage pipeline.
Based ONLY on a pull request's metadata (no code diff), decide whether it is worth
a full, expensive deep review. Keep anything that plausibly solves a real problem,
is tied to an engaged issue, or needs human judgement. Skip the obviously
low-value, stale, or duplicate. Return:
- worth_review — true to send it to the deep-review tier, false to skip it.
- reason — one short sentence justifying the decision.
- likely_category — your best guess, one of: {categories}.
Be decisive and lean toward skipping only when the metadata makes low value clear;
when unsure, keep it for deep review.""".format(categories=", ".join(CATEGORIES))

_SCHEMA = {
    "type": "object",
    "properties": {
        "worth_review": {"type": "boolean"},
        "reason": {"type": "string"},
        "likely_category": {"type": "string", "enum": CATEGORIES},
    },
    "required": ["worth_review", "reason", "likely_category"],
    "additionalProperties": False,
}


def build_screen_prompt(enriched):
    """Build (system, user) for the cheap metadata-only screen — no code sent."""
    if enriched.linked_issues:
        linked = "; ".join(
            f"#{i.number} [{i.state}] {i.thumbs_up} thumbs-up, {i.comments_count} comments"
            for i in enriched.linked_issues
        )
    else:
        linked = "none"

    files = ", ".join(f"{f.path} (+{f.additions}/-{f.deletions})"
                      for f in enriched.changed_files) or "none"
    ci = enriched.ci_status if enriched.ci_status is not None else "none (checks not run)"

    user = f"""PR #{enriched.number}: {enriched.title}
Author: {enriched.author}   State: {enriched.state}   Draft: {enriched.draft}
Labels: {", ".join(enriched.labels) or "none"}
CI status: {ci}
Linked issues (engagement): {linked}
Changed files: {files}

Description:
{enriched.body or "(empty)"}
"""
    return _SYSTEM, user


def screen_pr(enriched, client, model=SCREEN_MODEL, max_tokens=300):
    """Tier 1: cheaply decide whether a PR deserves the full deep review.

    Sends metadata only (no diff) to a cheap model. ``client`` is injected so the
    mapping is testable without a live call.
    """
    system, user = build_screen_prompt(enriched)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
        messages=[{"role": "user", "content": user}],
    )
    text = next(block.text for block in response.content if block.type == "text")
    return ScreenResult(**json.loads(text))


def screened_out_assessment(result):
    """A deterministic verdict for a PR the cheap screen judged not worth deep review."""
    return PRAssessment(
        summary="Screened out at the metadata tier — no deep review was run.",
        problem_statement=f"(not deeply analyzed) {result.reason}",
        dod_ac_status="Not evaluated — did not pass the cheap pre-screen.",
        reality_assessment=f"Not independently evaluated. Screen note: {result.reason}",
        recommended_category=result.likely_category,
    )
