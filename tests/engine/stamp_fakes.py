"""Ticket stamp backends for recovery tests."""

from __future__ import annotations

from typing import Any

from praetor.tickets.stamp import (
    StampBackendOutcome,
    StampBackendResult,
    StampTimeoutError,
)


class ResolveUnknownOnRetryBackend:
    """First call ambiguous; second resolves to a terminal outcome."""

    def __init__(self, *, resolve_to: StampBackendOutcome) -> None:
        self.resolve_to = resolve_to
        self.stamp_calls: list[str] = []

    def stamp(self, stamp_id: str, payload: dict[str, Any]) -> StampBackendResult:
        self.stamp_calls.append(stamp_id)
        if len(self.stamp_calls) == 1:
            raise StampTimeoutError("simulated timeout")
        return StampBackendResult(
            outcome=self.resolve_to,
            payload={"retry": len(self.stamp_calls)},
        )


class AlwaysFailedStampBackend:
    def stamp(self, stamp_id: str, payload: dict[str, Any]) -> StampBackendResult:
        _ = stamp_id, payload
        return StampBackendResult(outcome=StampBackendOutcome.FAILED, payload={})


class AlwaysTimeoutStampBackend:
    """Every call is ambiguous; the stamp can never resolve to terminal."""

    def __init__(self) -> None:
        self.stamp_calls: list[str] = []

    def stamp(self, stamp_id: str, payload: dict[str, Any]) -> StampBackendResult:
        self.stamp_calls.append(stamp_id)
        _ = payload
        raise StampTimeoutError("simulated persistent timeout")
