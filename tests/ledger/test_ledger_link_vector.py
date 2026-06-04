"""Task 10 — ledger link hash test vector (docs/contracts.md §7a)."""

from __future__ import annotations

from datetime import UTC, datetime

from praetor.hashing.domains import (
    DOMAIN_LEDGER_LINK,
    LEDGER_GENESIS_PREVIOUS_HASH,
    compute_ledger_link_hash,
)

TASK010_GENESIS_LINK_HASH = (
    "4a702d2467a6763bfb76a23016b46d7f30cdb245514e4c3183b5d643306074e0"
)


def test_domain_constants_match_contracts() -> None:
    assert DOMAIN_LEDGER_LINK == "praetor:v1:ledger_link"
    assert LEDGER_GENESIS_PREVIOUS_HASH == "null"


def test_genesis_link_test_vector_from_contracts() -> None:
    body = {
        "schema_version": "1",
        "record_type": "directive_revocation",
        "revocation_id": "rev-task010-vector",
        "directive_id": "dir-task010-vector",
        "reason": "manual",
        "reason_code": "manual_revocation",
        "triggered_by": "soc-lead-vector",
        "revoked_at": datetime(2026, 6, 4, 12, 0, 0, tzinfo=UTC),
        "ledger_commit_at": datetime(2026, 6, 4, 12, 0, 0, tzinfo=UTC),
        "idempotency_key_cleared": True,
        "superseded_by_directive_id": None,
    }
    assert (
        compute_ledger_link_hash(previous_hash=None, record=body)
        == TASK010_GENESIS_LINK_HASH
    )
