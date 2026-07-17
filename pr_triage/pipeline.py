from pr_triage.diff import cap_diff
from pr_triage.models import AssessedPR
from pr_triage.prescreen import bot_assessment, is_bot_pr
from pr_triage.screen import screened_out_assessment


def triage_pr(number, title, *, enrich, get_diff, repo_context, analyze,
              max_diff_chars=40000):
    """Run the per-PR pipeline: enrich -> fetch+cap diff -> analyze -> AssessedPR.

    Collaborators are injected so this composition is testable without I/O:
    ``enrich(number)`` returns an EnrichedPullRequest, ``get_diff(number)`` returns
    the raw diff text, and ``analyze(enriched, diff, repo_context)`` returns a
    PRAssessment.
    """
    enriched = enrich(number)
    diff = cap_diff(get_diff(number), max_diff_chars)
    assessment = analyze(enriched, diff, repo_context)
    return AssessedPR(number=number, title=title, assessment=assessment)


def triage_pr_tiered(number, title, *, enrich, get_diff, repo_context, screen, analyze,
                     max_diff_chars=40000):
    """Cost-tiered per-PR triage.

    Tier 0 (free): bot-authored PRs get a canned verdict — no LLM, no diff.
    Tier 1 (cheap): a metadata-only screen decides whether deep review is worth it;
      PRs it skips get a canned verdict — no diff, no expensive model.
    Tier 2 (expensive): only survivors get the diff fetched + capped and the full
      five-field analysis.

    ``screen(enriched) -> ScreenResult`` and ``analyze(enriched, diff, repo_context)
    -> PRAssessment`` are injected, as are ``enrich`` and ``get_diff``.
    """
    enriched = enrich(number)

    if is_bot_pr(enriched):
        return AssessedPR(number=number, title=title, assessment=bot_assessment(enriched))

    result = screen(enriched)
    if not result.worth_review:
        return AssessedPR(number=number, title=title,
                          assessment=screened_out_assessment(result))

    diff = cap_diff(get_diff(number), max_diff_chars)
    assessment = analyze(enriched, diff, repo_context)
    return AssessedPR(number=number, title=title, assessment=assessment)
