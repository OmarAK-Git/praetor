"""Build OrgConfigSnapshot and compute stable snapshot hashes."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from praetor.config.constants import ALLOWED_TOP_LEVEL_KEYS
from praetor.config.errors import PreflightError
from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.hashing import ORG_CONFIG_SNAPSHOT_HASH_KEYS, canonical_hash
from praetor.hashing.canonical import CanonicalSerializationError


def reject_unknown_top_level_keys(document: dict[str, Any]) -> None:
    unknown = set(document.keys()) - ALLOWED_TOP_LEVEL_KEYS
    if unknown:
        raise PreflightError(
            "unknown_top_level_key",
            f"unknown top-level org config keys: {sorted(unknown)}",
        )


def verbatim_character_count(verbatim_text: str) -> int:
    """Unicode code-point length of source file text (judgment render budget)."""
    return len(verbatim_text)


def snapshot_binding_body(snapshot: OrgConfigSnapshot) -> dict[str, Any]:
    payload = snapshot.model_dump(mode="json")
    payload.pop("snapshot_hash", None)
    return payload


def compute_snapshot_hash_from_binding(body: dict[str, Any]) -> str:
    try:
        return canonical_hash(body, allowed_keys=ORG_CONFIG_SNAPSHOT_HASH_KEYS)
    except CanonicalSerializationError as exc:
        raise PreflightError("invalid_binding_value", str(exc)) from exc


def compute_snapshot_hash(snapshot: OrgConfigSnapshot) -> str:
    return compute_snapshot_hash_from_binding(snapshot_binding_body(snapshot))


def verify_snapshot_hash(snapshot: OrgConfigSnapshot) -> None:
    expected = compute_snapshot_hash(snapshot)
    if snapshot.snapshot_hash != expected:
        raise PreflightError(
            "snapshot_hash_mismatch",
            "snapshot_hash does not match binding body",
        )


def build_org_config_snapshot(document: dict[str, Any]) -> OrgConfigSnapshot:
    reject_unknown_top_level_keys(document)
    try:
        snapshot = OrgConfigSnapshot.model_validate(
            {**document, "snapshot_hash": "pending"}
        )
    except ValidationError as exc:
        raise PreflightError("invalid_snapshot", str(exc)) from exc
    body = snapshot_binding_body(snapshot)
    snapshot_hash = compute_snapshot_hash_from_binding(body)
    return snapshot.model_copy(update={"snapshot_hash": snapshot_hash})
