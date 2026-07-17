import time

from pr_triage.models import TriageFailure, TriageRun


def run_backlog(items, process, max_attempts=3, sleep=time.sleep, should_retry=None):
    """Run ``process(item)`` over every item with retries and per-item isolation.

    Resilience for a 200+ PR backlog: transient errors (e.g. GitHub rate limits)
    are retried with exponential backoff, and an item that ultimately fails is
    recorded as a failure rather than aborting the whole run.

    ``sleep`` is injected for testability. ``should_retry(exc) -> bool`` decides
    whether an error is worth retrying (default: retry everything).
    """
    if should_retry is None:
        should_retry = lambda _exc: True  # noqa: E731

    results, failures = [], []
    for item in items:
        for attempt in range(1, max_attempts + 1):
            try:
                results.append(process(item))
                break
            except Exception as exc:  # noqa: BLE001 — isolate a bad item, keep going
                last = attempt == max_attempts
                if last or not should_retry(exc):
                    failures.append(TriageFailure(item=item, error=str(exc)))
                    break
                sleep(2 ** (attempt - 1))  # 1s, 2s, 4s, ...
    return TriageRun(results=results, failures=failures)
