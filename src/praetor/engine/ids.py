"""Decision identifiers for the walking skeleton (docs/contracts.md §3, §7)."""

from __future__ import annotations

from typing import Any

from praetor.hashing import EMPTY_BUNDLE, canonical_hash, derive_decision_id


def evidence_bundle_hash(bundle: dict[str, Any]) -> str:
    """Canonical hash of a correlated evidence bundle."""
    return canonical_hash(bundle)


def resolved_evidence_bundle_hash(
    evidence_bundle_hash_value: str,
    *,
    correlation_failure: bool = False,
) -> str:
    """The single EMPTY_BUNDLE substitution site (docs/contracts.md §3.3).

    Every consumer that needs the evidence-bundle-hash position — ``decision_id``,
    ``stamp_id``, and the stored ``DecisionEdict.evidence_bundle_hash`` field —
    must read the value returned here rather than re-deriving the substitution.
    """
    return EMPTY_BUNDLE if correlation_failure else evidence_bundle_hash_value


def decision_id_for_attempt(
    *,
    alert_identity: str,
    evidence_bundle_hash_value: str,
    org_config_snapshot_hash: str,
    processing_attempt_identity: str,
    correlation_failure: bool = False,
) -> str:
    """Derive decision_id; bundle-hash substitution via the single site (§3.3)."""
    bundle_hash = resolved_evidence_bundle_hash(
        evidence_bundle_hash_value,
        correlation_failure=correlation_failure,
    )
    return derive_decision_id(
        alert_identity,
        bundle_hash,
        org_config_snapshot_hash,
        processing_attempt_identity,
    )


def stamp_evidence_hash(
    *,
    evidence_bundle_hash_value: str,
    correlation_failure: bool = False,
) -> str:
    """Evidence hash input for stamp_id (§5); same single-site substitution rule."""
    return resolved_evidence_bundle_hash(
        evidence_bundle_hash_value,
        correlation_failure=correlation_failure,
    )
