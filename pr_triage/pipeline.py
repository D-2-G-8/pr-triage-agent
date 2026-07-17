from pr_triage.diff import cap_diff
from pr_triage.models import AssessedPR


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
