"""Hash derivations (docs/contracts.md §2–§7a, §8–§9)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from praetor.hashing.canonical import (
    canonical_hash,
    canonical_serialize,
    delimited,
    sha256_hex,
)

DOMAIN_DECISION_ID = "praetor:v1:decision_id"
DOMAIN_IDEMPOTENCY_KEY = "praetor:v1:idempotency_key"
DOMAIN_STAMP_ID = "praetor:v1:stamp_id"
DOMAIN_LEDGER_LINK = "praetor:v1:ledger_link"

# Genesis previous-hash token for delimited link preimages (docs/contracts.md §7a).
LEDGER_GENESIS_PREVIOUS_HASH = "null"

# OrgConfigSnapshot binding body keys (docs/contracts.md §3a); excludes snapshot_hash.
ORG_CONFIG_SNAPSHOT_HASH_KEYS: frozenset[str] = frozenset(
    {
        "schema_version",
        "version_metadata",
        "known_principals",
        "assets_and_asset_groups",
        "normal_admin_patterns",
        "containment_exclusions",
        "business_context",
        "containment_policy",
        "account_auto_contain_enabled",
        "directive_lifetime_policy",
        "emergency_never_contain_policy",
        "rate_limit_policy",
        "provider_health_circuit_breaker_policy",
        "containment_circuit_breaker_policy",
        "revocation_feed_policy",
        "consumer_clock_skew_policy",
        "latency_and_queue_aging_policy",
        "provisional_alert_rate_targets",
    }
)

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

        unknown_fields = sorted(unknown)
        msg = f"unknown feed record fields: {unknown_fields}"
        raise CanonicalSerializationError(msg)
    return canonical_hash(payload, allowed_keys=_FEED_RECORD_ALLOWED_KEYS)


def compute_never_contain_entries_hash(entries: list[dict[str, Any]]) -> str:
    """Embedded never-contain integrity hash per docs/contracts.md §9."""
    return canonical_hash(entries)


def compute_ledger_link_hash(
    *,
    previous_hash: str | None,
    record: Mapping[str, Any],
) -> str:
    """Hash-chain link over canonical record body (docs/contracts.md §7a)."""
    prev = previous_hash if previous_hash is not None else LEDGER_GENESIS_PREVIOUS_HASH
    body_bytes = canonical_serialize(record)
    return sha256_hex(delimited([DOMAIN_LEDGER_LINK, prev, body_bytes]))
