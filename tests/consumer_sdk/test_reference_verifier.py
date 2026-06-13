"""Tests for the reference consumer pre-actuation verifier (Task 21)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from consumer_sdk.reference_verifier import (
    ConsumerClockState,
    ConsumerFeedView,
    ConsumerVerifierConfig,
    FailedCheck,
    VerifierOutcome,
    verify_directive_pre_actuation,
)

from praetor.contracts.containment import (
    ContainmentDirective,
    DirectiveStatus,
    TargetType,
)
from praetor.contracts.feed import RevocationFeedRecord
from praetor.contracts.ledger import DirectiveRevocationRecord, RevocationReason
from praetor.hashing import compute_never_contain_entries_hash
from praetor.revocation.feed import build_feed_record

NOW = datetime(2026, 6, 12, 12, 0, 0, tzinfo=UTC)
DEFAULT_CONFIG = ConsumerVerifierConfig(
    max_consumer_clock_skew_seconds=30,
    max_revocation_feed_propagation_delay_seconds=60,
)
MAX_FEED_AGE_SECONDS = (
    DEFAULT_CONFIG.max_revocation_feed_propagation_delay_seconds
    + DEFAULT_CONFIG.max_consumer_clock_skew_seconds
)


def _directive(
    *,
    directive_id: str = "dir-1",
    target_id: str = "host-01",
    issued_at: datetime | None = None,
    lifetime_seconds: int = 120,
    minimum_feed_sequence: int = 0,
    supersedes_directive_id: str | None = None,
    tamper_hash: bool = False,
    embedded: list[dict[str, object]] | None = None,
) -> ContainmentDirective:
    issued = issued_at or NOW
    entries = [] if embedded is None else embedded
    live_hash = compute_never_contain_entries_hash(entries)
    if tamper_hash:
        live_hash = "sha256:tampered"
    return ContainmentDirective(
        directive_id=directive_id,
        decision_id="dec-1",
        target_type=TargetType.HOST,
        target_id=target_id,
        scope="host-isolation",
        evidence_refs=["ev-1"],
        issued_at=issued,
        expires_at=issued + timedelta(seconds=lifetime_seconds),
        idempotency_key="idem-1",
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.EMITTED,
        live_never_contain_hash=live_hash,
        embedded_never_contain_entries=entries,
        minimum_feed_sequence_at_issue=minimum_feed_sequence,
        supersedes_directive_id=supersedes_directive_id,
    )


def _feed_record(
    *,
    sequence_number: int,
    directive_id: str = "dir-other",
    reason_code: str = "manual_revocation",
) -> RevocationFeedRecord:
    record = DirectiveRevocationRecord(
        revocation_id=f"rev-{sequence_number}",
        directive_id=directive_id,
        reason=RevocationReason.MANUAL,
        reason_code=reason_code,
        triggered_by="soc-lead-1",
        revoked_at=NOW,
        ledger_commit_at=NOW,
        idempotency_key_cleared=True,
    )
    return build_feed_record(record, sequence_number=sequence_number)


def _fresh_feed(*, cursor: int = 0) -> ConsumerFeedView:
    records = tuple(_feed_record(sequence_number=n) for n in range(1, cursor + 1))
    return ConsumerFeedView(
        feed_cursor=cursor,
        feed_last_read_at=NOW,
        records=records,
    )


def _clock(
    at: datetime | None = None,
    *,
    uncertainty_seconds: float = 0.0,
) -> ConsumerClockState:
    return ConsumerClockState(
        consumer_clock_at_check=at or NOW,
        clock_sync_uncertainty_seconds=uncertainty_seconds,
    )


def _assert_required_result_fields(
    result: object,
    *,
    directive: ContainmentDirective,
    clock: ConsumerClockState,
    last_seen_sequence: int,
    failed_check: FailedCheck | None,
) -> None:
    from consumer_sdk.reference_verifier import ReferenceVerifierResult

    assert isinstance(result, ReferenceVerifierResult)
    assert result.directive_id == directive.directive_id
    assert result.target.target_type == "host"
    assert result.target.target_id == directive.target_id
    assert result.target.scope == directive.scope
    assert result.failed_check == failed_check
    assert result.last_seen_sequence == last_seen_sequence
    assert result.consumer_clock_at_check == clock.consumer_clock_at_check
    assert result.expires_at == directive.expires_at


def test_expired_directive_non_actionable() -> None:
    issued = NOW - timedelta(seconds=200)
    directive = _directive(issued_at=issued, lifetime_seconds=120)
    clock = _clock(NOW)
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=clock,
        feed=_fresh_feed(cursor=0),
    )
    assert result.outcome == VerifierOutcome.NON_ACTIONABLE
    assert result.failed_check == FailedCheck.DIRECTIVE_EXPIRED
    _assert_required_result_fields(
        result,
        directive=directive,
        clock=clock,
        last_seen_sequence=0,
        failed_check=FailedCheck.DIRECTIVE_EXPIRED,
    )


def test_expired_one_second_past_expires_at_non_actionable() -> None:
    expires_at = NOW - timedelta(seconds=1)
    directive = _directive(issued_at=expires_at - timedelta(seconds=120))
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=_clock(NOW),
        feed=_fresh_feed(cursor=0),
    )
    assert result.outcome == VerifierOutcome.NON_ACTIONABLE
    assert result.failed_check == FailedCheck.DIRECTIVE_EXPIRED


def test_expired_within_skew_window_before_nominal_expiry() -> None:
    directive = _directive(lifetime_seconds=10)
    clock = _clock(NOW + timedelta(seconds=5))
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=clock,
        feed=_fresh_feed(cursor=0),
    )
    assert result.outcome == VerifierOutcome.NON_ACTIONABLE
    assert result.failed_check == FailedCheck.DIRECTIVE_EXPIRED


def test_comfortably_live_directive_actionable() -> None:
    directive = _directive(lifetime_seconds=120)
    feed = _fresh_feed(cursor=0)
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=_clock(NOW),
        feed=feed,
    )
    assert result.outcome == VerifierOutcome.ACTIONABLE
    assert result.failed_check is None


def test_revoked_directive_non_actionable() -> None:
    directive = _directive(directive_id="dir-revoked", minimum_feed_sequence=1)
    feed = ConsumerFeedView(
        feed_cursor=1,
        feed_last_read_at=NOW,
        records=(_feed_record(sequence_number=1, directive_id="dir-revoked"),),
    )
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=_clock(),
        feed=feed,
    )
    assert result.outcome == VerifierOutcome.NON_ACTIONABLE
    assert result.failed_check == FailedCheck.DIRECTIVE_REVOKED


def test_revocation_beyond_cursor_in_hand_non_actionable() -> None:
    directive = _directive(directive_id="dir-revoked", minimum_feed_sequence=0)
    feed = ConsumerFeedView(
        feed_cursor=1,
        feed_last_read_at=NOW,
        records=(
            _feed_record(sequence_number=1, directive_id="dir-other"),
            _feed_record(sequence_number=2, directive_id="dir-revoked"),
        ),
    )
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=_clock(),
        feed=feed,
    )
    assert result.outcome == VerifierOutcome.NON_ACTIONABLE
    assert result.failed_check == FailedCheck.DIRECTIVE_REVOKED


def test_embedded_hash_mismatch_escalates() -> None:
    directive = _directive(tamper_hash=True)
    clock = _clock()
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=clock,
        feed=_fresh_feed(cursor=0),
    )
    assert result.outcome == VerifierOutcome.ESCALATE_HUMAN
    assert result.failed_check == FailedCheck.EMBEDDED_HASH_MISMATCH
    _assert_required_result_fields(
        result,
        directive=directive,
        clock=clock,
        last_seen_sequence=0,
        failed_check=FailedCheck.EMBEDDED_HASH_MISMATCH,
    )


def test_non_empty_embedded_entries_actionable() -> None:
    embedded = [
        {"target_type": "host", "target_id": "host-01", "source": "emergency"},
    ]
    directive = _directive(embedded=embedded, minimum_feed_sequence=1)
    feed = _fresh_feed(cursor=1)
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=_clock(),
        feed=feed,
    )
    assert result.outcome == VerifierOutcome.ACTIONABLE
    assert result.failed_check is None


def test_feed_cursor_below_floor_escalates() -> None:
    directive = _directive(minimum_feed_sequence=2)
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=_clock(),
        feed=_fresh_feed(cursor=1),
    )
    assert result.outcome == VerifierOutcome.ESCALATE_HUMAN
    assert result.failed_check == FailedCheck.FEED_CURSOR_BELOW_FLOOR


def test_feed_stale_escalates() -> None:
    directive = _directive(minimum_feed_sequence=0)
    stale_read = NOW - timedelta(seconds=MAX_FEED_AGE_SECONDS + 1)
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=_clock(),
        feed=ConsumerFeedView(
            feed_cursor=0,
            feed_last_read_at=stale_read,
            records=(),
        ),
    )
    assert result.outcome == VerifierOutcome.ESCALATE_HUMAN
    assert result.failed_check == FailedCheck.FEED_STALE


def test_feed_staleness_boundary_not_stale_at_exact_age() -> None:
    directive = _directive(minimum_feed_sequence=0)
    read_at = NOW - timedelta(seconds=MAX_FEED_AGE_SECONDS)
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=_clock(),
        feed=ConsumerFeedView(
            feed_cursor=0,
            feed_last_read_at=read_at,
            records=(),
        ),
    )
    assert result.outcome == VerifierOutcome.ACTIONABLE


def test_feed_staleness_boundary_stale_one_second_past() -> None:
    directive = _directive(minimum_feed_sequence=0)
    read_at = NOW - timedelta(seconds=MAX_FEED_AGE_SECONDS + 1)
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=_clock(),
        feed=ConsumerFeedView(
            feed_cursor=0,
            feed_last_read_at=read_at,
            records=(),
        ),
    )
    assert result.outcome == VerifierOutcome.ESCALATE_HUMAN
    assert result.failed_check == FailedCheck.FEED_STALE


def test_feed_checksum_mismatch_escalates() -> None:
    directive = _directive(minimum_feed_sequence=1)
    valid = _feed_record(sequence_number=1)
    corrupted = valid.model_copy(update={"record_checksum": "sha256:corrupt"})
    feed = ConsumerFeedView(
        feed_cursor=1,
        feed_last_read_at=NOW,
        records=(corrupted,),
    )
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=_clock(),
        feed=feed,
    )
    assert result.outcome == VerifierOutcome.ESCALATE_HUMAN
    assert result.failed_check == FailedCheck.FEED_CHECKSUM_MISMATCH


def test_sequence_gap_escalates() -> None:
    directive = _directive(minimum_feed_sequence=0)
    feed = ConsumerFeedView(
        feed_cursor=7,
        feed_last_read_at=NOW,
        records=(
            _feed_record(sequence_number=5),
            _feed_record(sequence_number=7),
        ),
    )
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=_clock(),
        feed=feed,
    )
    assert result.outcome == VerifierOutcome.ESCALATE_HUMAN
    assert result.failed_check == FailedCheck.FEED_SEQUENCE_GAP


def test_truncated_window_starting_above_one_passes() -> None:
    directive = _directive(minimum_feed_sequence=5)
    feed = ConsumerFeedView(
        feed_cursor=7,
        feed_last_read_at=NOW,
        records=(
            _feed_record(sequence_number=5),
            _feed_record(sequence_number=6),
            _feed_record(sequence_number=7),
        ),
    )
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=_clock(),
        feed=feed,
    )
    assert result.outcome == VerifierOutcome.ACTIONABLE


def test_cursor_beyond_retained_window_max_is_gap() -> None:
    directive = _directive(minimum_feed_sequence=5)
    feed = ConsumerFeedView(
        feed_cursor=10,
        feed_last_read_at=NOW,
        records=(
            _feed_record(sequence_number=5),
            _feed_record(sequence_number=6),
            _feed_record(sequence_number=7),
        ),
    )
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=_clock(),
        feed=feed,
    )
    assert result.outcome == VerifierOutcome.ESCALATE_HUMAN
    assert result.failed_check == FailedCheck.FEED_SEQUENCE_GAP


def test_clock_sync_uncertainty_escalates() -> None:
    directive = _directive()
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=_clock(uncertainty_seconds=45.0),
        feed=_fresh_feed(cursor=0),
    )
    assert result.outcome == VerifierOutcome.ESCALATE_HUMAN
    assert result.failed_check == FailedCheck.CLOCK_SYNC_UNCERTAIN


def test_lineage_conflict_escalates() -> None:
    directive = _directive(directive_id="dir-new", target_id="host-01")
    overlapping = _directive(directive_id="dir-old", target_id="host-01")
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=_clock(),
        feed=_fresh_feed(cursor=0),
        known_directives=(overlapping,),
    )
    assert result.outcome == VerifierOutcome.ESCALATE_HUMAN
    assert result.failed_check == FailedCheck.LINEAGE_CONFLICT


def test_superseded_old_directive_with_live_replacement_escalates() -> None:
    old = _directive(directive_id="dir-old", target_id="host-01")
    new = _directive(
        directive_id="dir-new",
        target_id="host-01",
        supersedes_directive_id="dir-old",
    )
    result = verify_directive_pre_actuation(
        old,
        config=DEFAULT_CONFIG,
        clock=_clock(),
        feed=_fresh_feed(cursor=0),
        known_directives=(new,),
    )
    assert result.outcome == VerifierOutcome.ESCALATE_HUMAN
    assert result.failed_check == FailedCheck.LINEAGE_CONFLICT


def test_valid_directive_actionable() -> None:
    directive = _directive(minimum_feed_sequence=1)
    feed = _fresh_feed(cursor=1)
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=_clock(),
        feed=feed,
    )
    assert result.outcome == VerifierOutcome.ACTIONABLE
    assert result.failed_check is None


def test_result_includes_required_fields() -> None:
    directive = _directive(minimum_feed_sequence=1)
    feed = _fresh_feed(cursor=1)
    clock = _clock()
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=clock,
        feed=feed,
    )
    _assert_required_result_fields(
        result,
        directive=directive,
        clock=clock,
        last_seen_sequence=1,
        failed_check=None,
    )


def test_supersession_feed_avoids_lineage_conflict() -> None:
    old = _directive(directive_id="dir-old", target_id="host-01")
    new = _directive(
        directive_id="dir-new",
        target_id="host-01",
        supersedes_directive_id="dir-old",
        minimum_feed_sequence=1,
    )
    feed = ConsumerFeedView(
        feed_cursor=1,
        feed_last_read_at=NOW,
        records=(
            _feed_record(
                sequence_number=1,
                directive_id="dir-old",
                reason_code="supersession",
            ),
        ),
    )
    result = verify_directive_pre_actuation(
        new,
        config=DEFAULT_CONFIG,
        clock=_clock(),
        feed=feed,
        known_directives=(old,),
    )
    assert result.outcome == VerifierOutcome.ACTIONABLE
    assert result.failed_check is None


@pytest.mark.parametrize(
    ("cursor", "minimum"),
    [
        (2, 2),
        (5, 3),
    ],
)
def test_feed_cursor_at_or_above_floor_passes(cursor: int, minimum: int) -> None:
    directive = _directive(minimum_feed_sequence=minimum)
    result = verify_directive_pre_actuation(
        directive,
        config=DEFAULT_CONFIG,
        clock=_clock(),
        feed=_fresh_feed(cursor=cursor),
    )
    assert result.outcome == VerifierOutcome.ACTIONABLE
