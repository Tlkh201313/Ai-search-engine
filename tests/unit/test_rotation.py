"""Test circuit breaker, backoff, and rotation logic."""

import pytest
import time
from core import rotation
from core.rotation import (
    CircuitBreaker,
    CircuitState,
    BackendMetrics,
    register,
    pick,
    mark_used,
    mark_failed,
    record_latency,
    get_stats,
    get_circuit_states,
    CIRCUIT_OPEN_THRESHOLD,
    CIRCUIT_HALF_OPEN_DELAY,
    BACKOFF_BASE,
    BACKOFF_MAX,
    BACKOFF_FACTOR,
)


@pytest.fixture(autouse=True)
def clean_registry():
    rotation.REGISTRY.clear()
    rotation.CIRCUITS.clear()
    rotation.METRICS.clear()
    yield


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker()
        for _ in range(CIRCUIT_OPEN_THRESHOLD):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_closes_on_success(self):
        cb = CircuitBreaker()
        cb.record_failure()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.consecutive_failures == 0

    def test_half_open_after_delay(self, monkeypatch):
        cb = CircuitBreaker()
        for _ in range(CIRCUIT_OPEN_THRESHOLD):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        monkeypatch.setattr(
            time, "time", lambda: cb.last_failure_time + CIRCUIT_HALF_OPEN_DELAY + 1
        )
        assert cb.can_execute() is True
        assert cb.state == CircuitState.HALF_OPEN

    def test_backoff_increases_with_failures(self):
        cb = CircuitBreaker()
        for _ in range(CIRCUIT_OPEN_THRESHOLD + 3):
            cb.record_failure()
        expected = min(BACKOFF_BASE * (BACKOFF_FACTOR**3), BACKOFF_MAX)
        assert cb.backoff_delay == expected

    def test_backoff_caps_at_max(self):
        cb = CircuitBreaker()
        for _ in range(CIRCUIT_OPEN_THRESHOLD + 20):
            cb.record_failure()
        assert cb.backoff_delay <= BACKOFF_MAX

    def test_backoff_resets_on_success(self):
        cb = CircuitBreaker()
        for _ in range(CIRCUIT_OPEN_THRESHOLD):
            cb.record_failure()
        cb.record_success()
        assert cb.backoff_delay == BACKOFF_BASE

    def test_remaining_cooldown_zero_when_closed(self):
        cb = CircuitBreaker()
        assert cb.remaining_cooldown() == 0.0


class TestBackendMetrics:
    def test_success_rate_all_success(self):
        m = BackendMetrics()
        m.uses = 10
        m.fails = 0
        assert m.success_rate() == 1.0

    def test_success_rate_mixed(self):
        m = BackendMetrics()
        m.uses = 7
        m.fails = 3
        assert m.success_rate() == 0.7

    def test_success_rate_no_data(self):
        m = BackendMetrics()
        assert m.success_rate() == 1.0

    def test_latency_percentiles(self):
        m = BackendMetrics()
        for i in range(100):
            m.record_latency(float(i))
        assert m.p50() == 50.0
        assert m.p95() == 95.0
        assert m.p99() == 99.0

    def test_latency_truncates_at_500(self):
        m = BackendMetrics()
        for i in range(1000):
            m.record_latency(float(i))
        assert len(m.latencies) == 500


class TestPick:
    def test_pick_lru(self):
        register("a", weight=1.0)(lambda q, n, c: [])
        register("b", weight=1.0)(lambda q, n, c: [])
        rotation.METRICS["a"].last_used = 0.0
        rotation.METRICS["b"].last_used = 1.0
        assert pick("lru") == "a"

    def test_pick_excludes(self):
        register("a", weight=1.0)(lambda q, n, c: [])
        register("b", weight=1.0)(lambda q, n, c: [])
        assert pick("lru", exclude=["a"]) == "b"

    def test_pick_returns_none_when_all_excluded(self):
        register("a", weight=1.0)(lambda q, n, c: [])
        assert pick("lru", exclude=["a"]) is None

    def test_pick_skips_open_circuits(self):
        register("a", weight=1.0)(lambda q, n, c: [])
        register("b", weight=1.0)(lambda q, n, c: [])
        rotation.CIRCUITS["a"].state = CircuitState.OPEN
        rotation.CIRCUITS["a"].record_failure()
        rotation.CIRCUITS["a"].record_failure()
        rotation.CIRCUITS["a"].record_failure()
        result = pick("lru")
        assert result != "a"

    def test_pick_random(self):
        register("a", weight=1.0)(lambda q, n, c: [])
        register("b", weight=1.0)(lambda q, n, c: [])
        result = pick("random")
        assert result in ("a", "b")

    def test_pick_round_robin(self):
        register("a", weight=1.0)(lambda q, n, c: [])
        register("b", weight=1.0)(lambda q, n, c: [])
        rotation.METRICS["a"].uses = 5
        rotation.METRICS["b"].uses = 2
        assert pick("round_robin") == "b"

    def test_pick_weighted(self):
        register("a", weight=1.0)(lambda q, n, c: [])
        register("b", weight=5.0)(lambda q, n, c: [])
        counts = {"a": 0, "b": 0}
        for _ in range(100):
            r = pick("weighted")
            counts[r] += 1
        assert counts["b"] > counts["a"]


class TestMarkFunctions:
    def test_mark_used_increments(self):
        register("x", weight=1.0)(lambda q, n, c: [])
        mark_used("x")
        assert rotation.METRICS["x"].uses == 1
        assert rotation.METRICS["x"].last_used > 0

    def test_mark_failed_increments(self):
        register("x", weight=1.0)(lambda q, n, c: [])
        mark_failed("x")
        assert rotation.METRICS["x"].fails == 1

    def test_record_latency_stores_value(self):
        register("x", weight=1.0)(lambda q, n, c: [])
        record_latency("x", 150.5)
        assert 150.5 in rotation.METRICS["x"].latencies


class TestGetStats:
    def test_stats_include_circuit_state(self):
        register("a", weight=1.0)(lambda q, n, c: [])
        stats = get_stats()
        assert "circuit_state" in stats["a"]
        assert stats["a"]["circuit_state"] == "closed"

    def test_stats_include_latency_percentiles(self):
        register("a", weight=1.0)(lambda q, n, c: [])
        for i in range(100):
            record_latency("a", float(i))
        stats = get_stats()
        assert stats["a"]["latency_p50"] is not None
        assert stats["a"]["latency_p95"] is not None

    def test_stats_exclude_fn(self):
        register("a", weight=1.0)(lambda q, n, c: [])
        stats = get_stats()
        assert "fn" not in stats["a"]


class TestGetCircuitStates:
    def test_returns_all_states(self):
        register("a", weight=1.0)(lambda q, n, c: [])
        register("b", weight=1.0)(lambda q, n, c: [])
        states = get_circuit_states()
        assert states == {"a": "closed", "b": "closed"}
