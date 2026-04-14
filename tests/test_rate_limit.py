from app.rate_limit import InMemoryRateLimiter


def test_rate_limiter_disabled_allows_all_requests() -> None:
    limiter = InMemoryRateLimiter(requests=0, window_seconds=60)
    for _ in range(100):
        assert limiter.is_allowed("127.0.0.1")


def test_rate_limiter_blocks_after_threshold() -> None:
    limiter = InMemoryRateLimiter(requests=2, window_seconds=60)
    key = "127.0.0.1"
    assert limiter.is_allowed(key)
    assert limiter.is_allowed(key)
    assert not limiter.is_allowed(key)


def test_rate_limiter_isolated_per_key() -> None:
    limiter = InMemoryRateLimiter(requests=1, window_seconds=60)
    assert limiter.is_allowed("ip-1")
    assert limiter.is_allowed("ip-2")
    assert not limiter.is_allowed("ip-1")


def test_rate_limiter_returns_retry_after_when_blocked() -> None:
    limiter = InMemoryRateLimiter(requests=1, window_seconds=60)
    key = "127.0.0.1"
    first = limiter.consume(key)
    assert first.allowed
    assert first.remaining == 0

    second = limiter.consume(key)
    assert not second.allowed
    assert second.retry_after_seconds >= 1
