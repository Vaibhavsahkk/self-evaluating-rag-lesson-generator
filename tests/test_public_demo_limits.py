"""Tests for public demo LLM usage limits."""

from ui.server import PublicRunLimiter


def test_limiter_allows_configured_runs_after_active_run_finishes():
    limiter = PublicRunLimiter(runs_per_hour=2)

    assert limiter.acquire("127.0.0.1") is True
    assert limiter.acquire("127.0.0.1") is False

    limiter.release("127.0.0.1")
    assert limiter.acquire("127.0.0.1") is True
    limiter.release("127.0.0.1")

    assert limiter.acquire("127.0.0.1") is False


def test_limiter_tracks_clients_independently():
    limiter = PublicRunLimiter(runs_per_hour=1)

    assert limiter.acquire("client-a") is True
    assert limiter.acquire("client-b") is True