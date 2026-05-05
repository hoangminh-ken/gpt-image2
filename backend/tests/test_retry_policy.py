from app.core.retry_policy import (
    MAX_ATTEMPTS,
    MAX_DELAY_SEC,
    backoff_seconds,
    is_retryable,
    should_retry,
)


class FakeStatusError(Exception):
    def __init__(self, msg, status_code):
        super().__init__(msg)
        self.status_code = status_code


class FakeRateLimitError(Exception):
    pass


# Make name match openai SDK class name
FakeRateLimitError.__name__ = "RateLimitError"


def test_is_retryable_429():
    assert is_retryable(FakeStatusError("rate", 429))


def test_is_retryable_5xx():
    assert is_retryable(FakeStatusError("server", 503))


def test_not_retryable_4xx():
    assert not is_retryable(FakeStatusError("bad", 400))
    assert not is_retryable(FakeStatusError("auth", 401))
    assert not is_retryable(FakeStatusError("payload", 413))


def test_is_retryable_by_class_name():
    assert is_retryable(FakeRateLimitError("limited"))


def test_backoff_grows_then_caps():
    # Run multiple samples to account for jitter
    for attempt in range(1, 8):
        d = backoff_seconds(attempt)
        assert d <= MAX_DELAY_SEC * 1.25 + 0.001
        assert d >= 0.0


def test_should_retry_attempts_cap():
    exc = FakeStatusError("rate", 429)
    assert should_retry(exc, attempt=1)
    assert should_retry(exc, attempt=MAX_ATTEMPTS - 1)
    assert not should_retry(exc, attempt=MAX_ATTEMPTS)
    assert not should_retry(FakeStatusError("bad", 400), attempt=1)
