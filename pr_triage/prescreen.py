from pr_triage.models import PRAssessment

# Substrings that mark well-known automation accounts, checked case-insensitively.
_BOT_LOGIN_MARKERS = ("dependabot", "renovate", "greenkeeper", "snyk-bot", "github-actions")


def is_bot_pr(enriched):
    """Tier 0 (free): is this PR from an automated account?

    Uses GitHub's authoritative bot flag (``author_is_bot`` from GraphQL
    ``__typename``) plus login heuristics, so obvious bot spam is routed out
    before any LLM call.
    """
    if enriched.author_is_bot:
        return True
    login = (enriched.author or "").lower()
    if login.endswith("[bot]"):
        return True
    return any(marker in login for marker in _BOT_LOGIN_MARKERS)


def bot_assessment(enriched):
    """A deterministic, LLM-free verdict for a bot-authored PR."""
    author = enriched.author or "unknown"
    return PRAssessment(
        summary=f"Automated PR from bot account '{author}' — not independently reviewed.",
        problem_statement="Bot-generated change (e.g. dependency bump or automated maintenance).",
        dod_ac_status="Not evaluated — filtered as bot-authored before deep review.",
        reality_assessment="No human-reported issue or engagement; bot-authored automation.",
        recommended_category="low_value",
    )
