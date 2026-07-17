def cap_diff(text, max_chars):
    """Bound a diff to ``max_chars`` for cost/rate-limit control.

    Returns the text unchanged when it fits. Otherwise keeps the first
    ``max_chars`` characters and appends a marker disclosing the original size —
    a cap must never silently drop content.
    """
    if len(text) <= max_chars:
        return text
    return (
        text[:max_chars]
        + f"\n\n[diff truncated: showing {max_chars} of {len(text)} chars]"
    )
