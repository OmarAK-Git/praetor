"""Domain-separation constants and hash derivations (docs/contracts.md §2–§9)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from praetor.hashing.canonical import canonical_hash, delimited, sha256_hex

DOMAIN_DECISION_ID = "praetor:v1:decision_id"
DOMAIN_IDEMPOTENCY_KEY = "praetor:v1:idempotency_key"
DOMAIN_STAMP_ID = "praetor:v1:stamp_id"

_FEED_RECORD_ALLOWED_KEYS = frozenset(
    {
        "schema_version",
        "sequence_number",
        "directive_id",
        "revocation_id",
        "reason_code",
        "revoked_at",
        "ledger_commit_at",
        "public_detail",
    }
)


def derive_decision_id(
    alert_identity: str,
    evidence_bundle_hash: str,
    org_config_snapshot_hash: str,
    processing_attempt_identity: str,
) -> str:
    """Five-part SHA-256 per docs/contracts.md §3."""
    return sha256_hex(
        delimited(
            [
                DOMAIN_DECISION_ID,
                alert_identity,
                evidence_bundle_hash,
                org_config_snapshot_hash,
                processing_attempt_identity,
            ]
        )
    )


def derive_idempotency_key(
    alert_identity: str,
    target_type: str,
    target_id: str,
    scope: str,
) -> str:
    """Five-part SHA-256 per docs/contracts.md §4."""
    return sha256_hex(
        delimited(
            [
                DOMAIN_IDEMPOTENCY_KEY,
                alert_identity,
                target_type,
                target_id,
                scope,
            ]
        )
    )


def derive_stamp_id(
    alert_identity: str,
    evidence_bundle_hash: str,
    org_config_snapshot_hash: str,
) -> str:
    """Four-part SHA-256 per docs/contracts.md §5 (completed-edict three-tuple)."""
    return sha256_hex(
        delimited(
            [
                DOMAIN_STAMP_ID,
                alert_identity,
                evidence_bundle_hash,
                org_config_snapshot_hash,
            ]
        )
    )


def compute_feed_record_checksum(record: Mapping[str, Any]) -> str:
    """Corruption detection checksum per docs/contracts.md §8.1."""
    payload = {key: record[key] for key in record if key != "record_checksum"}
    unknown = set(payload.keys()) - _FEED_RECORD_ALLOWED_KEYS
    if unknown:
        from praetor.hashing.canonical import CanonicalSerializationError

        raise CanonicalSerializationError(f"unknown feed record fields: {sorted(unknown)}")
    return canonical_hash(payload, allowed_keys=_FEED_RECORD_ALLOWED_KEYS)


def compute_never_contain_entries_hash(entries: list[dict[str, Any]]) -> str:
    """Embedded never-contain integrity hash per docs/contracts.md §9."""
    return canonical_hash(entries)
