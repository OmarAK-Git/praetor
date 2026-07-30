"""Live never-contain evaluation helpers."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

from praetor.config.errors import PreflightError
from praetor.contracts.containment import ContainmentDirective
from praetor.contracts.ledger import EmergencyNeverContainRecord
from praetor.contracts.org_config_sections import NeverContainEntry

_logger = logging.getLogger(__name__)

_SID_PATTERN = re.compile(r"^S-1-5(?:-\d+)+$", re.IGNORECASE)


def canonical_target_specification(spec: dict[str, Any]) -> dict[str, str]:
    """Single canonical emergency/never-contain target form."""
    keys = set(spec.keys())
    if keys == {"target_type", "target_id"}:
        target_type = spec["target_type"]
        target_id = spec["target_id"]
    else:
        raise PreflightError(
            "invalid_target_specification",
            "target_specification must contain only target_type and target_id",
        )
    if target_type not in ("host", "account"):
        raise PreflightError("invalid_target_specification", f"invalid target_type: {target_type!r}")
    if not isinstance(target_id, str) or not target_id.strip():
        raise PreflightError("invalid_target_specification", "target_id must be a non-empty string")
    if target_type == "account" and not _SID_PATTERN.match(target_id):
        raise PreflightError(
            "invalid_target_specification",
            "account target_id must be a Windows SID",
        )
    return {"target_type": str(target_type), "target_id": str(target_id)}


def validate_never_contain_entries(entries: list[dict[str, Any]]) -> list[NeverContainEntry]:
    if not entries:
        raise PreflightError(
            "missing_never_contain",
            "containment_exclusions.never_contain must be non-empty",
        )
    validated: list[NeverContainEntry] = []
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise PreflightError("invalid_never_contain", f"entry {idx} must be a mapping")
        canonical = canonical_target_specification(entry)
        try:
            validated.append(NeverContainEntry.model_validate(canonical))
        except Exception as exc:
            raise PreflightError("invalid_never_contain", f"entry {idx}: {exc}") from exc
    return validated


def permanent_never_contain_entries(containment_exclusions: Any) -> list[dict[str, Any]]:
    if not isinstance(containment_exclusions, dict):
        raise PreflightError("invalid_section", "containment_exclusions must be a mapping")
    raw = containment_exclusions.get("never_contain", [])
    if not isinstance(raw, list):
        raise PreflightError("invalid_never_contain", "never_contain must be a list")
    entries: list[dict[str, Any]] = []
    for idx, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise PreflightError("invalid_never_contain", f"entry {idx} must be a mapping")
        entries.append(entry)
    validated = validate_never_contain_entries(entries)
    return [entry.model_dump(mode="json") for entry in validated]


def emergency_entry_as_never_contain(record: EmergencyNeverContainRecord) -> dict[str, Any]:
    canonical = canonical_target_specification(record.target_specification)
    return {**canonical, "source": "emergency"}


def directive_matches_entry(directive: ContainmentDirective, entry: dict[str, Any]) -> bool:
    try:
        canonical = canonical_target_specification(
            {k: v for k, v in entry.items() if k in ("target_type", "target_id")}
        )
    except PreflightError as exc:
        _logger.warning(
            "malformed never-contain entry skipped during directive match: %s", exc
        )
        return False
    return (
        directive.target_type.value == canonical["target_type"]
        and directive.target_id == canonical["target_id"]
    )


def combined_live_never_contain_entries(
    permanent: list[dict[str, Any]],
    active_emergencies: list[EmergencyNeverContainRecord],
    *,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    moment = now or datetime.now(UTC)
    combined = list(permanent)
    for record in active_emergencies:
        if record.expires_at <= moment:
            continue
        combined.append(emergency_entry_as_never_contain(record))
    return combined


def target_in_never_contain_list(
    target_type: str,
    target_id: str,
    entries: list[dict[str, Any]],
) -> bool:
    for entry in entries:
        try:
            canonical = canonical_target_specification(
                {k: v for k, v in entry.items() if k in ("target_type", "target_id")}
            )
        except PreflightError as exc:
            _logger.warning(
                "malformed never-contain entry skipped during target match: %s", exc
            )
            continue
        if canonical["target_type"] == target_type and canonical["target_id"] == target_id:
            return True
    return False


def reconciliation_never_contain_entries(
    permanent: list[dict[str, Any]],
    active_emergencies: list[EmergencyNeverContainRecord],
) -> list[dict[str, Any]]:
    return combined_live_never_contain_entries(permanent, active_emergencies)
