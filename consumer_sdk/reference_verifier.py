"""Reference consumer pre-actuation verifier (docs/contracts.md §10).

Lives outside ``src/praetor/`` so integrators can mirror the protocol without
shipping Praetor production modules in their actuation binary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from praetor.contracts.containment import ContainmentDirective, TargetType
from praetor.contracts.feed import RevocationFeedRecord
from praetor.hashing import (
    compute_feed_record_checksum,
    compute_never_contain_entries_hash,
)


class VerifierOutcome(StrEnum):
    ACTIONABLE = "actionable"
    NON_ACTIONABLE = "non_actionable"
    ESCALATE_HUMAN = "escalate_human"


class FailedCheck(StrEnum):
    DIRECTIVE_EXPIRED = "directive_expired"
    DIRECTIVE_REVOKED = "directive_revoked"
    EMBEDDED_HASH_MISMATCH = "embedded_hash_mismatch"
    FEED_CURSOR_BELOW_FLOOR = "feed_cursor_below_floor"
    FEED_STALE = "feed_stale"
    FEED_CHECKSUM_MISMATCH = "feed_checksum_mismatch"
    FEED_SEQUENCE_GAP = "feed_sequence_gap"
    CLOCK_SYNC_UNCERTAIN = "clock_sync_uncertain"
    LINEAGE_CONFLICT = "lineage_conflict"


@dataclass(frozen=True)
class ConsumerVerifierConfig:
    max_consumer_clock_skew_seconds: int = 30
    max_revocation_feed_propagation_delay_seconds: int = 60


@dataclass(frozen=True)
class ConsumerClockState:
    consumer_clock_at_check: datetime
    clock_sync_uncertainty_seconds: float = 0.0


@dataclass(frozen=True)
class ConsumerFeedView:
    feed_cursor: int
    feed_last_read_at: datetime
    records: tuple[RevocationFeedRecord, ...] = ()


@dataclass(frozen=True)
class TargetRef:
    target_type: str
    target_id: str
    scope: str


@dataclass(frozen=True)
class ReferenceVerifierResult:
    outcome: VerifierOutcome
    directive_id: str
    target: TargetRef
    failed_check: FailedCheck | None
    last_seen_sequence: int
    consumer_clock_at_check: datetime
    expires_at: datetime


def _target_ref(directive: ContainmentDirective) -> TargetRef:
    target_type = directive.target_type
    if isinstance(target_type, TargetType):
        target_type_value = target_type.value
    else:
        target_type_value = str(target_type)
    return TargetRef(
        target_type=target_type_value,
        target_id=directive.target_id,
        scope=directive.scope,
    )


def _result(
    directive: ContainmentDirective,
    *,
    outcome: VerifierOutcome,
    failed_check: FailedCheck | None,
    clock: ConsumerClockState,
    last_seen_sequence: int,
) -> ReferenceVerifierResult:
    return ReferenceVerifierResult(
        outcome=outcome,
        directive_id=directive.directive_id,
        target=_target_ref(directive),
        failed_check=failed_check,
        last_seen_sequence=last_seen_sequence,
        consumer_clock_at_check=clock.consumer_clock_at_check,
        expires_at=directive.expires_at,
    )


def _verify_embedded_hash(directive: ContainmentDirective) -> bool:
    recomputed = compute_never_contain_entries_hash(
        directive.embedded_never_contain_entries
    )
    return bool(recomputed == directive.live_never_contain_hash)


def _feed_is_stale(
    clock: ConsumerClockState,
    feed: ConsumerFeedView,
    config: ConsumerVerifierConfig,
) -> bool:
    max_age = timedelta(
        seconds=(
            config.max_revocation_feed_propagation_delay_seconds
            + config.max_consumer_clock_skew_seconds
        )
    )
    return clock.consumer_clock_at_check - feed.feed_last_read_at > max_age


def _feed_has_checksum_mismatch(feed: ConsumerFeedView) -> bool:
    for record in feed.records:
        payload: dict[str, Any] = record.model_dump(mode="python")
        expected = str(record.record_checksum)
        computed = compute_feed_record_checksum(payload)
        if computed != expected:
            return True
    return False


def _feed_has_sequence_gap(feed: ConsumerFeedView) -> bool:
    """Gap check on the retained feed window only (DEC-038).

    Truncated archives may start above sequence 1; only sequences at or below
    ``feed_cursor`` must form a contiguous window whose max equals the cursor.
    Read-ahead records above the cursor do not constitute a gap.
    """
    if feed.feed_cursor <= 0:
        return False
    retained = [
        record
        for record in feed.records
        if record.sequence_number <= feed.feed_cursor
    ]
    if not retained:
        return True
    sequences = sorted(record.sequence_number for record in retained)
    if sequences[-1] != feed.feed_cursor:
        return True
    for left, right in zip(sequences, sequences[1:], strict=False):
        if right - left != 1:
            return True
    return False


def _revoked_directive_ids(feed: ConsumerFeedView) -> set[str]:
    return {record.directive_id for record in feed.records}


def _directive_is_expired(
    directive: ContainmentDirective,
    clock: ConsumerClockState,
    config: ConsumerVerifierConfig,
) -> bool:
    skew = timedelta(seconds=config.max_consumer_clock_skew_seconds)
    return bool(clock.consumer_clock_at_check > directive.expires_at - skew)


def _directive_is_live(
    directive: ContainmentDirective,
    *,
    clock: ConsumerClockState,
    config: ConsumerVerifierConfig,
    revoked_ids: set[str],
) -> bool:
    if directive.directive_id in revoked_ids:
        return False
    return not _directive_is_expired(directive, clock, config)


def _supersession_feed_covers(
    superseded_directive_id: str,
    feed: ConsumerFeedView,
) -> bool:
    for record in feed.records:
        if record.directive_id != superseded_directive_id:
            continue
        if record.reason_code == "supersession":
            # v1 feed projection cannot prove WHICH replacement the supersession
            # record refers to (no superseded_by on the feed line).
            return True
    return False


def _has_lineage_conflict(
    directive: ContainmentDirective,
    *,
    known_directives: tuple[ContainmentDirective, ...],
    clock: ConsumerClockState,
    config: ConsumerVerifierConfig,
    feed: ConsumerFeedView,
    revoked_ids: set[str],
) -> bool:
    target_key = (
        _target_ref(directive).target_type,
        directive.target_id,
        directive.scope,
    )
    for other in known_directives:
        if other.directive_id == directive.directive_id:
            continue
        other_target = _target_ref(other)
        if (
            other_target.target_type,
            other.target_id,
            other_target.scope,
        ) != target_key:
            continue
        if not _directive_is_live(
            other,
            clock=clock,
            config=config,
            revoked_ids=revoked_ids,
        ):
            continue
        if directive.supersedes_directive_id == other.directive_id:
            if _supersession_feed_covers(other.directive_id, feed):
                continue
        return True
    return False


def verify_directive_pre_actuation(
    directive: ContainmentDirective,
    *,
    config: ConsumerVerifierConfig,
    clock: ConsumerClockState,
    feed: ConsumerFeedView,
    known_directives: tuple[ContainmentDirective, ...] = (),
) -> ReferenceVerifierResult:
    """Run the §10 consumer pre-actuation protocol checks in canonical order."""
    last_seen = feed.feed_cursor

    if clock.clock_sync_uncertainty_seconds > config.max_consumer_clock_skew_seconds:
        return _result(
            directive,
            outcome=VerifierOutcome.ESCALATE_HUMAN,
            failed_check=FailedCheck.CLOCK_SYNC_UNCERTAIN,
            clock=clock,
            last_seen_sequence=last_seen,
        )

    if _directive_is_expired(directive, clock, config):
        return _result(
            directive,
            outcome=VerifierOutcome.NON_ACTIONABLE,
            failed_check=FailedCheck.DIRECTIVE_EXPIRED,
            clock=clock,
            last_seen_sequence=last_seen,
        )

    if not _verify_embedded_hash(directive):
        return _result(
            directive,
            outcome=VerifierOutcome.ESCALATE_HUMAN,
            failed_check=FailedCheck.EMBEDDED_HASH_MISMATCH,
            clock=clock,
            last_seen_sequence=last_seen,
        )

    if feed.feed_cursor < directive.minimum_feed_sequence_at_issue:
        return _result(
            directive,
            outcome=VerifierOutcome.ESCALATE_HUMAN,
            failed_check=FailedCheck.FEED_CURSOR_BELOW_FLOOR,
            clock=clock,
            last_seen_sequence=last_seen,
        )

    if _feed_is_stale(clock, feed, config):
        return _result(
            directive,
            outcome=VerifierOutcome.ESCALATE_HUMAN,
            failed_check=FailedCheck.FEED_STALE,
            clock=clock,
            last_seen_sequence=last_seen,
        )

    if _feed_has_checksum_mismatch(feed):
        return _result(
            directive,
            outcome=VerifierOutcome.ESCALATE_HUMAN,
            failed_check=FailedCheck.FEED_CHECKSUM_MISMATCH,
            clock=clock,
            last_seen_sequence=last_seen,
        )

    if _feed_has_sequence_gap(feed):
        return _result(
            directive,
            outcome=VerifierOutcome.ESCALATE_HUMAN,
            failed_check=FailedCheck.FEED_SEQUENCE_GAP,
            clock=clock,
            last_seen_sequence=last_seen,
        )

    revoked_ids = _revoked_directive_ids(feed)
    if directive.directive_id in revoked_ids:
        return _result(
            directive,
            outcome=VerifierOutcome.NON_ACTIONABLE,
            failed_check=FailedCheck.DIRECTIVE_REVOKED,
            clock=clock,
            last_seen_sequence=last_seen,
        )

    if _has_lineage_conflict(
        directive,
        known_directives=known_directives,
        clock=clock,
        config=config,
        feed=feed,
        revoked_ids=revoked_ids,
    ):
        return _result(
            directive,
            outcome=VerifierOutcome.ESCALATE_HUMAN,
            failed_check=FailedCheck.LINEAGE_CONFLICT,
            clock=clock,
            last_seen_sequence=last_seen,
        )

    return _result(
        directive,
        outcome=VerifierOutcome.ACTIONABLE,
        failed_check=None,
        clock=clock,
        last_seen_sequence=last_seen,
    )
