"""Canonical serialization and domain-separated hash derivations."""

from praetor.hashing.canonical import (
    EMPTY_BUNDLE,
    EMPTY_BUNDLE_SENTINEL,
    CanonicalSerializationError,
    canonical_hash,
    canonical_serialize,
    delimited,
    sha256_hex,
)
from praetor.hashing.domains import (
    DOMAIN_DECISION_ID,
    DOMAIN_EVIDENCE_ID,
    DOMAIN_IDEMPOTENCY_KEY,
    DOMAIN_LEDGER_LINK,
    DOMAIN_STAMP_ID,
    LEDGER_GENESIS_PREVIOUS_HASH,
    ORG_CONFIG_SNAPSHOT_HASH_KEYS,
    compute_feed_record_checksum,
    compute_ledger_link_hash,
    compute_never_contain_entries_hash,
    derive_decision_id,
    derive_idempotency_key,
    derive_stamp_id,
)

__all__ = [
    "EMPTY_BUNDLE",
    "EMPTY_BUNDLE_SENTINEL",
    "CanonicalSerializationError",
    "DOMAIN_DECISION_ID",
    "DOMAIN_EVIDENCE_ID",
    "DOMAIN_IDEMPOTENCY_KEY",
    "DOMAIN_LEDGER_LINK",
    "DOMAIN_STAMP_ID",
    "LEDGER_GENESIS_PREVIOUS_HASH",
    "ORG_CONFIG_SNAPSHOT_HASH_KEYS",
    "canonical_hash",
    "canonical_serialize",
    "compute_feed_record_checksum",
    "compute_ledger_link_hash",
    "compute_never_contain_entries_hash",
    "delimited",
    "derive_decision_id",
    "derive_idempotency_key",
    "derive_stamp_id",
    "sha256_hex",
]
