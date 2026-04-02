"""
Backend rotation engine with circuit breaker and exponential backoff.

Register backends with @register("name", weight=1.0).
run_with_fallback() cycles through healthy backends before giving up.
Each backend has its own circuit breaker state and backoff schedule.
"""

import time
import random
import asyncio
import math
from typing import Callable, Optional
from enum import Enum
from dataclasses import dataclass, field

CIRCUIT_OPEN_THRESHOLD = 3
CIRCUIT_HALF_OPEN_DELAY = 60
BACKOFF_BASE = 0.5
BACKOFF_MAX = 8.0
BACKOFF_FACTOR = 2


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    consecutive_failures: int = 0
    last_failure_time: float = 0.0
    backoff_delay: float = BACKOFF_BASE
    state: CircuitState = CircuitState.CLOSED

    def record_success(self):
        self.consecutive_failures = 0
        self.backoff_delay = BACKOFF_BASE
        self.state = CircuitState.CLOSED

    def record_failure(self):
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        if self.consecutive_failures >= CIRCUIT_OPEN_THRESHOLD:
            self.state = CircuitState.OPEN
            self.backoff_delay = min(
                BACKOFF_BASE
                * (
                    BACKOFF_FACTOR
                    ** (self.consecutive_failures - CIRCUIT_OPEN_THRESHOLD)
                ),
                BACKOFF_MAX,
            )

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            elapsed = time.time() - self.last_failure_time
            if elapsed >= CIRCUIT_HALF_OPEN_DELAY:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True

    def remaining_cooldown(self) -> float:
        if self.state != CircuitState.OPEN:
            return 0.0
        elapsed = time.time() - self.last_failure_time
        return max(0.0, CIRCUIT_HALF_OPEN_DELAY - elapsed)


@dataclass
class BackendMetrics:
    uses: int = 0
    fails: int = 0
    last_used: float = 0.0
    weight: float = 1.0
    latencies: list = field(default_factory=list)

    def record_latency(self, ms: float):
        self.latencies.append(ms)
        if len(self.latencies) > 500:
            self.latencies = self.latencies[-500:]

    def p50(self) -> Optional[float]:
        if not self.latencies:
            return None
        s = sorted(self.latencies)
        return s[len(s) // 2]

    def p95(self) -> Optional[float]:
        if not self.latencies:
            return None
        s = sorted(self.latencies)
        idx = min(int(len(s) * 0.95), len(s) - 1)
        return s[idx]

    def p99(self) -> Optional[float]:
        if not self.latencies:
            return None
        s = sorted(self.latencies)
        idx = min(int(len(s) * 0.99), len(s) - 1)
        return s[idx]

    def success_rate(self) -> float:
        total = self.uses + self.fails
        if total == 0:
            return 1.0
        return self.uses / total


REGISTRY: dict[str, dict] = {}
CIRCUITS: dict[str, CircuitBreaker] = {}
METRICS: dict[str, BackendMetrics] = {}


def register(name: str, weight: float = 1.0):
    def decorator(fn: Callable):
        REGISTRY[name] = {"fn": fn, "weight": weight}
        CIRCUITS[name] = CircuitBreaker()
        METRICS[name] = BackendMetrics(weight=weight)
        return fn

    return decorator


def pick(strategy: str = "lru", exclude: list = None) -> Optional[str]:
    if exclude is None:
        exclude = []
    pool = {k: v for k, v in REGISTRY.items() if k not in exclude}
    if not pool:
        return None
    available = {
        k: v for k, v in pool.items() if CIRCUITS.get(k, CircuitBreaker()).can_execute()
    }
    if not available:
        return None
    if strategy == "random":
        return random.choice(list(available.keys()))
    if strategy == "round_robin":
        return min(available, key=lambda k: METRICS[k].uses if k in METRICS else 0)
    if strategy == "weighted":
        names = list(available.keys())
        weights = [METRICS[n].weight if n in METRICS else 1.0 for n in names]
        return random.choices(names, weights=weights, k=1)[0]
    return min(available, key=lambda k: METRICS[k].last_used if k in METRICS else 0)


def mark_used(name: str):
    if name in METRICS:
        METRICS[name].uses += 1
        METRICS[name].last_used = time.time()
    if name in CIRCUITS:
        CIRCUITS[name].record_success()


def mark_failed(name: str):
    if name in METRICS:
        METRICS[name].fails += 1
    if name in CIRCUITS:
        CIRCUITS[name].record_failure()


def record_latency(name: str, ms: float):
    if name in METRICS:
        METRICS[name].record_latency(ms)


def get_stats() -> dict:
    result = {}
    for name in REGISTRY:
        cb = CIRCUITS.get(name, CircuitBreaker())
        m = METRICS.get(name, BackendMetrics())
        result[name] = {
            "uses": m.uses,
            "fails": m.fails,
            "last_used": m.last_used,
            "weight": m.weight,
            "circuit_state": cb.state.value,
            "consecutive_failures": cb.consecutive_failures,
            "backoff_delay": round(cb.backoff_delay, 2),
            "success_rate": round(m.success_rate(), 3),
            "latency_p50": round(cb.backoff_delay, 2)
            if cb.state != CircuitState.CLOSED
            else (round(m.p50(), 1) if m.p50() else None),
            "latency_p95": round(m.p95(), 1) if m.p95() else None,
            "latency_p99": round(m.p99(), 1) if m.p99() else None,
        }
        if cb.state == CircuitState.CLOSED and m.p50() is not None:
            result[name]["latency_p50"] = round(m.p50(), 1)
    return result


def get_circuit_states() -> dict[str, str]:
    return {name: CIRCUITS[name].state.value for name in CIRCUITS}


async def run_with_fallback(
    query: str, max_results: int, strategy: str = "lru"
) -> dict:
    import httpx

    tried = []
    async with httpx.AsyncClient(follow_redirects=True) as client:
        while len(tried) < len(REGISTRY):
            name = pick(strategy, exclude=tried)
            if not name:
                for skipped_name in [k for k in REGISTRY if k not in tried]:
                    cb = CIRCUITS.get(skipped_name)
                    if cb and cb.state == CircuitState.OPEN:
                        tried.append(skipped_name)
                break
            tried.append(name)
            cb = CIRCUITS.get(name)
            if cb and not cb.can_execute():
                continue
            start = time.monotonic()
            mark_used(name)
            try:
                results = await asyncio.wait_for(
                    REGISTRY[name]["fn"](query, max_results, client), timeout=12
                )
                elapsed_ms = (time.monotonic() - start) * 1000
                record_latency(name, elapsed_ms)
                if results:
                    return {"results": results, "backend_used": name, "tried": tried}
                mark_failed(name)
            except asyncio.TimeoutError:
                elapsed_ms = (time.monotonic() - start) * 1000
                record_latency(name, elapsed_ms)
                mark_failed(name)
            except Exception:
                elapsed_ms = (time.monotonic() - start) * 1000
                record_latency(name, elapsed_ms)
                mark_failed(name)
    return {"results": [], "error": "All backends exhausted", "tried": tried}
