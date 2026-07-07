"""Circuit breakers for external dependencies."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from app.config import settings


class CircuitOpenError(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Circuit '{name}' is open")


@dataclass
class CircuitSnapshot:
    name: str
    state: str
    failures: int
    failure_threshold: int
    recovery_seconds: float
    opened_seconds_ago: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "failures": self.failures,
            "failure_threshold": self.failure_threshold,
            "recovery_seconds": self.recovery_seconds,
            "opened_seconds_ago": self.opened_seconds_ago,
        }


class CircuitBreaker:
    def __init__(self, name: str, *, failure_threshold: int, recovery_seconds: float) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._failures = 0
        self._opened_at: float | None = None
        self._half_open_trial = False

    @property
    def state(self) -> str:
        if self._opened_at is None:
            return "closed"
        if time.monotonic() - self._opened_at >= self.recovery_seconds:
            return "half_open"
        return "open"

    def is_open(self) -> bool:
        return self.state == "open"

    def allow_request(self) -> bool:
        if not settings.circuit_breakers_enabled:
            return True
        current = self.state
        if current == "closed":
            return True
        if current == "half_open":
            if not self._half_open_trial:
                self._half_open_trial = True
                return True
            return False
        return False

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None
        self._half_open_trial = False

    def record_failure(self) -> None:
        self._half_open_trial = False
        if self.state == "half_open":
            self._opened_at = time.monotonic()
            self._failures = self.failure_threshold
            return
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._opened_at = time.monotonic()

    def snapshot(self) -> CircuitSnapshot:
        opened_ago = None
        if self._opened_at is not None and self.state == "open":
            opened_ago = round(time.monotonic() - self._opened_at, 2)
        return CircuitSnapshot(
            name=self.name,
            state=self.state,
            failures=self._failures,
            failure_threshold=self.failure_threshold,
            recovery_seconds=self.recovery_seconds,
            opened_seconds_ago=opened_ago,
        )


_registry: dict[str, CircuitBreaker] = {}


def get_breaker(name: str) -> CircuitBreaker:
    if name not in _registry:
        _registry[name] = CircuitBreaker(
            name,
            failure_threshold=settings.circuit_breaker_failure_threshold,
            recovery_seconds=settings.circuit_breaker_recovery_seconds,
        )
    return _registry[name]


def all_breaker_snapshots() -> list[dict[str, Any]]:
    if not _registry:
        for name in ("opensearch", "virustotal", "playbook_webhook", "oidc", "llm"):
            get_breaker(name)
    return [breaker.snapshot().to_dict() for breaker in _registry.values()]
