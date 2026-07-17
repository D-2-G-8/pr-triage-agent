import json

from pr_triage.models import PRAssessment

CATEGORIES = ["ready_for_review", "likely_duplicate", "stale", "low_value"]

MODEL = "claude-opus-4-8"

_FIELDS = [
    "summary",
    "problem_statement",
    "dod_ac_status",
    "reality_assessment",
    "recommended_category",
]

_SCHEMA = {
    "type": "object",
    "properties": {
        field: ({"type": "string", "enum": CATEGORIES}
                if field == "recommended_category" else {"type": "string"})
        for field in _FIELDS
    },
    "required": _FIELDS,
    "additionalProperties": False,
}

_SYSTEM_TEMPLATE = """You are a PR triage analyst for an open-source repository.
For each pull request, return a structured assessment with exactly five fields,
none empty:
- summary — an unbiased summary of what the PR does.
- problem_statement — the problem the PR claims to solve.
- dod_ac_status — whether it meets the repo's Definition of Done / Acceptance
  Criteria. Ground this in the CI check status and the criteria text below. Note
  that a null/absent CI status means checks have not run (e.g. awaiting maintainer
  approval) — say that explicitly rather than treating it as passing or failing.
- reality_assessment — whether the stated problem is real. Ground it in any linked
  issue and its engagement (reactions/comments). If no issue is linked and the PR
  body offers no other evidence, state explicitly that no independent confirmation
  was found — do not invent engagement.
- recommended_category — exactly one of: {categories}.

Base every judgement on this repository's own criteria below, not generic ones,
and cite specific facts (a named CI check status, a quote from the PR, a line from
CONTRIBUTING) rather than general phrases.

--- CONTRIBUTING.md ---
{contributing}

--- PULL REQUEST TEMPLATE ---
{pr_template}
"""


def build_prompt(enriched, diff, repo_context):
    """Build (system, user) prompt strings for the triage of one PR.

    Pure and side-effect free so the grounding can be tested without the API.
    """
    system = _SYSTEM_TEMPLATE.format(
        categories=", ".join(CATEGORIES),
        contributing=repo_context.contributing or "(none provided)",
        pr_template=repo_context.pr_template or "(none provided)",
    )

    if enriched.linked_issues:
        linked = "\n".join(
            f"  - #{i.number} \"{i.title}\" [{i.state}] "
            f"— {i.thumbs_up} thumbs-up, {i.comments_count} comments"
            for i in enriched.linked_issues
        )
    else:
        linked = "  (no linked issue — no independent confirmation from an issue)"

    files = "\n".join(
        f"  - {f.path} (+{f.additions}/-{f.deletions})" for f in enriched.changed_files
    ) or "  (none)"

    ci = enriched.ci_status if enriched.ci_status is not None else "none (checks not run)"

    user = f"""PR #{enriched.number}: {enriched.title}
Author: {enriched.author}   State: {enriched.state}   Draft: {enriched.draft}
Labels: {", ".join(enriched.labels) or "(none)"}
CI status: {ci}

Description:
{enriched.body or "(empty)"}

Linked issues:
{linked}

Changed files{" (list truncated)" if enriched.files_truncated else ""}:
{files}

Unified diff:
{diff}
"""
    return system, user


def analyze_pr(enriched, diff, repo_context, client, model=MODEL, max_tokens=2000):
    """Call Claude to produce the five-field assessment for one PR.

    ``client`` (an Anthropic client) is injected so the mapping is testable
    without a live API call. Structured outputs constrain the response to the
    five required fields with a validated category enum.
    """
    system, user = build_prompt(enriched, diff, repo_context)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
        messages=[{"role": "user", "content": user}],
    )
    text = next(block.text for block in response.content if block.type == "text")
    return PRAssessment(**json.loads(text))
