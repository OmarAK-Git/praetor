"""Queue aging policy for alert processing attempts."""

from __future__ import annotations

from datetime import UTC, datetime

from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.state.attempts import ProcessingAttempt


def max_queue_age_seconds(snapshot: OrgConfigSnapshot) -> int:
    return snapshot.latency_and_queue_aging_policy.max_queue_age_seconds


def attempt_queue_age_seconds(
    attempt: ProcessingAttempt,
    *,
    now: datetime | None = None,
) -> float:
    moment = now or datetime.now(UTC)
    return (moment - attempt.created_at).total_seconds()


def queue_aging_exceeded(
    attempt: ProcessingAttempt,
    *,
    max_age_seconds: int,
    now: datetime | None = None,
) -> bool:
    return attempt_queue_age_seconds(attempt, now=now) > max_age_seconds


def queue_aging_exceeded_for_snapshot(
    attempt: ProcessingAttempt,
    snapshot: OrgConfigSnapshot,
    *,
    now: datetime | None = None,
) -> bool:
    return queue_aging_exceeded(
        attempt,
        max_age_seconds=max_queue_age_seconds(snapshot),
        now=now,
    )
