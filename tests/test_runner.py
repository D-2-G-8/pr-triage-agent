from pr_triage.runner import run_backlog


def test_collects_results_in_order():
    run = run_backlog([1, 2, 3], process=lambda x: x * 10, sleep=lambda s: None)

    assert run.results == [10, 20, 30]
    assert run.failures == []


def test_retries_transient_failure_then_succeeds():
    attempts = {"n": 0}

    def process(x):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise RuntimeError("rate limited")
        return x

    slept = []
    run = run_backlog([5], process=process, max_attempts=3, sleep=slept.append)

    assert run.results == [5]
    assert run.failures == []
    assert len(slept) == 1  # one backoff between the two attempts


def test_records_failure_and_keeps_processing_the_rest():
    def process(x):
        if x == 2:
            raise RuntimeError("boom on 2")
        return x

    run = run_backlog([1, 2, 3], process=process, max_attempts=2, sleep=lambda s: None)

    assert run.results == [1, 3]  # a bad PR does not abort the run
    assert len(run.failures) == 1
    assert run.failures[0].item == 2
    assert "boom on 2" in run.failures[0].error


def test_backoff_grows_between_attempts():
    slept = []

    def always_fail(x):
        raise RuntimeError("nope")

    run_backlog([1], process=always_fail, max_attempts=3, sleep=slept.append)

    assert len(slept) == 2         # 3 attempts -> 2 backoff sleeps
    assert slept[1] > slept[0]     # increasing backoff


def test_respects_should_retry_predicate():
    def process(x):
        raise ValueError("permanent")

    slept = []
    run = run_backlog(
        [1], process=process, max_attempts=5,
        sleep=slept.append, should_retry=lambda e: not isinstance(e, ValueError),
    )

    assert len(run.failures) == 1
    assert slept == []  # not retried — predicate said no
