"""V2-020 metrics production completeness integration tests."""

from __future__ import annotations

import inspect
import threading
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from praetor.contracts.ledger import DirectiveRevocationRecord, RevocationReason
from praetor.engine.orchestrator import _record_intake_metrics_bypass_gate
from praetor.metrics.collector import MetricsCollector
from praetor.metrics.events import LLM_FAILURE_FAULT_FLAGS, OutcomeMatrixFaultFlag
from praetor.revocation.exporter import FileFeedJsonlSink, export_pending_feed_rows
from praetor.state.store import StateStore, open_state_store


def _revocation(
    *,
    revocation_id: str,
    ledger_commit_at: datetime,
) -> DirectiveRevocationRecord:
    return DirectiveRevocationRecord(
        revocation_id=revocation_id,
        directive_id="dir-1",
        reason=RevocationReason.NEVER_CONTAIN_CONFLICT,
        reason_code="never_contain_conflict",
        triggered_by="test",
        revoked_at=ledger_commit_at,
        ledger_commit_at=ledger_commit_at,
        idempotency_key_cleared=False,
    )


@pytest.fixture
def store(tmp_path: Path) -> Iterator[StateStore]:
    db = tmp_path / "state.db"
    s = open_state_store(db)
    yield s
    s.close()


def test_feed_export_records_lag_on_completion(
    store: StateStore, tmp_path: Path
) -> None:
    commit_at = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)
    export_at = commit_at + timedelta(seconds=25)
    store.write_automated_revocation(
        _revocation(revocation_id="rev-lag", ledger_commit_at=commit_at)
    )
    metrics = MetricsCollector()
    sink = FileFeedJsonlSink(tmp_path / "revocation_feed.jsonl")

    result = export_pending_feed_rows(
        store.conn,
        sink=sink,
        max_feed_export_retries=3,
        propagation_delay_seconds=60,
        now=export_at,
        metrics=metrics,
    )

    assert result.exported_count == 1
    snap = metrics.snapshot()
    assert snap.feed_export_lag_samples == (25.0,)
    assert snap.feed_export_lag_warning_threshold_seconds == 60.0


def test_record_llm_failure_production_wiring_uses_llm_flags_only() -> None:
    source = inspect.getsource(_record_intake_metrics_bypass_gate)
    assert "is_llm_failure_fault_flag" in source
    assert "record_llm_failure" in source


def test_bypass_gate_skips_non_llm_fault_flags() -> None:
    from praetor.contracts.disposition import Disposition

    metrics = MetricsCollector()
    _record_intake_metrics_bypass_gate(
        metrics,
        disposition=Disposition.ESCALATE,
        fault_flag=OutcomeMatrixFaultFlag.CORRELATION_FAILURE.value,
    )
    snap = metrics.snapshot()
    assert snap.disposition_counts[Disposition.ESCALATE.value] == 1
    assert snap.llm_failure_by_fault_flag == {}


def test_bypass_gate_records_llm_failure_for_provider_flags() -> None:
    from praetor.contracts.disposition import Disposition

    metrics = MetricsCollector()
    flag = OutcomeMatrixFaultFlag.PROVIDER_UNAVAILABLE.value
    assert flag in {member.value for member in LLM_FAILURE_FAULT_FLAGS}
    _record_intake_metrics_bypass_gate(
        metrics,
        disposition=Disposition.ESCALATE,
        fault_flag=flag,
    )
    snap = metrics.snapshot()
    assert snap.llm_failure_by_fault_flag == {flag: 1}


def test_metrics_collector_documents_single_writer_assumption() -> None:
    doc = MetricsCollector.__doc__ or ""
    assert "single-writer" in doc.lower() or "thread-unsafe" in doc.lower()


def test_metrics_collector_concurrent_writes_are_undefined_but_do_not_crash() -> None:
    """Document v1 assumption: concurrent mutation is unsupported but must not raise."""
    collector = MetricsCollector()
    errors: list[BaseException] = []

    def writer() -> None:
        try:
            for _ in range(50):
                collector.record_disposition("escalate")
        except BaseException as exc:  # pragma: no cover - documents undefined behavior
            errors.append(exc)

    threads = [threading.Thread(target=writer) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    assert collector.snapshot().disposition_counts["escalate"] == 200
