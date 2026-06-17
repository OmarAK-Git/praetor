"""Smoke benchmark for serialized SQLite revocation path (Task 11).

Measures automated revocation writes (critical_transaction + feed outbox)
against ``provisional_alert_rate_targets`` from the active org config.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from praetor.config.state import fetch_active_snapshot
from praetor.contracts.ledger import DirectiveRevocationRecord, RevocationReason
from praetor.state.store import StateStore, open_state_store


@dataclass(frozen=True)
class SmokeBenchmarkResult:
    operations: int
    elapsed_seconds: float
    sustained_alerts_per_minute: float
    burst_alerts_per_minute: float
    target_sustained: int
    target_burst: int
    meets_sustained_target: bool
    meets_burst_target: bool


def provisional_targets_from_conn(conn: sqlite3.Connection) -> tuple[int, int]:
    """Load Sprint 1 provisional targets from the active org config snapshot."""
    snapshot = fetch_active_snapshot(conn)
    if snapshot is None:
        msg = "smoke benchmark requires an active org config snapshot"
        raise ValueError(msg)
    targets = snapshot.provisional_alert_rate_targets
    return (
        targets.sustained_alerts_per_minute,
        targets.burst_alerts_per_minute,
    )


def _revocation_record(revocation_id: str) -> DirectiveRevocationRecord:
    now = datetime.now(UTC)
    return DirectiveRevocationRecord(
        revocation_id=revocation_id,
        directive_id="dir-bench",
        reason=RevocationReason.NEVER_CONTAIN_CONFLICT,
        reason_code="never_contain_conflict",
        triggered_by="benchmark",
        revoked_at=now,
        ledger_commit_at=now,
        idempotency_key_cleared=False,
    )


def _result_from_timing(
    *,
    operations: int,
    elapsed: float,
    target_sustained: int,
    target_burst: int,
) -> SmokeBenchmarkResult:
    if elapsed <= 0:
        elapsed = 1e-9
    rate_per_minute = (operations / elapsed) * 60.0
    return SmokeBenchmarkResult(
        operations=operations,
        elapsed_seconds=elapsed,
        sustained_alerts_per_minute=rate_per_minute,
        burst_alerts_per_minute=rate_per_minute,
        target_sustained=target_sustained,
        target_burst=target_burst,
        meets_sustained_target=rate_per_minute >= float(target_sustained),
        meets_burst_target=rate_per_minute >= float(target_burst),
    )


def run_smoke_serialized_path_benchmark(
    db_path: Path,
    *,
    operations: int = 30,
) -> SmokeBenchmarkResult:
    """Run revocation writes and compare rate to active config targets."""
    store = open_state_store(db_path)
    try:
        target_sustained, target_burst = provisional_targets_from_conn(store.conn)
        start = time.perf_counter()
        for index in range(operations):
            store.write_automated_revocation(
                _revocation_record(f"rev-bench-{index}")
            )
        elapsed = time.perf_counter() - start
    finally:
        store.close()
    return _result_from_timing(
        operations=operations,
        elapsed=elapsed,
        target_sustained=target_sustained,
        target_burst=target_burst,
    )


def run_smoke_for_store(
    store: StateStore,
    *,
    operations: int,
) -> SmokeBenchmarkResult:
    """Benchmark against an already-open store with active org config."""
    target_sustained, target_burst = provisional_targets_from_conn(store.conn)
    start = time.perf_counter()
    for index in range(operations):
        store.write_automated_revocation(
            _revocation_record(f"rev-bench-{index}")
        )
    elapsed = time.perf_counter() - start
    return _result_from_timing(
        operations=operations,
        elapsed=elapsed,
        target_sustained=target_sustained,
        target_burst=target_burst,
    )
