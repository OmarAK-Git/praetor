"""Host bundle presence corroboration (DEC-066)."""

from __future__ import annotations

from datetime import UTC, datetime

from praetor.contracts.evidence import EvidenceFact
from praetor.evidence.provenance import (
    LEDGER_HISTORY,
    SYSMON_EVENT_LOG,
    WINDOWS_SECURITY_LOG,
    is_attacker_controllable_provenance,
    meets_host_bundle_corroboration,
)

NOW = datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC)
TARGET_HOST = "ws-01"


def _fact(
    evidence_id: str,
    provenance_path: str,
    *,
    host_id: str | None = TARGET_HOST,
    source_event_reference: str | None = None,
) -> EvidenceFact:
    return EvidenceFact(
        evidence_id=evidence_id,
        normalized_fields={"host_id": host_id} if host_id is not None else {},
        source_event_reference=source_event_reference or f"syn:{evidence_id}",
        raw_source="{}",
        provenance_path=provenance_path,
        ambiguity_flag=False,
        timestamp=NOW,
    )


def _check(*facts: EvidenceFact) -> bool:
    return meets_host_bundle_corroboration(facts, target_host_id=TARGET_HOST)


def test_windows_security_log_not_attacker_controllable() -> None:
    assert is_attacker_controllable_provenance(WINDOWS_SECURITY_LOG) is False


def test_sysmon_is_attacker_controllable() -> None:
    assert is_attacker_controllable_provenance(SYSMON_EVENT_LOG) is True


def test_unknown_provenance_defaults_attacker_controllable() -> None:
    assert is_attacker_controllable_provenance("future_normalizer") is True


def test_two_eligible_paths_in_host_scoped_bundle_pass() -> None:
    sysmon = _fact("a", SYSMON_EVENT_LOG)
    security = _fact("b", WINDOWS_SECURITY_LOG)
    assert _check(sysmon, security) is True


def test_single_path_bundle_fails_even_if_cited() -> None:
    sysmon = _fact("a", SYSMON_EVENT_LOG)
    assert _check(sysmon) is False


def test_cross_host_second_path_does_not_count() -> None:
    sysmon = _fact("a", SYSMON_EVENT_LOG, host_id=TARGET_HOST)
    other_host = _fact("b", WINDOWS_SECURITY_LOG, host_id="ws-other")
    assert _check(sysmon, other_host) is False


def test_ledger_history_path_not_corroboration_eligible() -> None:
    ledger = _fact("a", LEDGER_HISTORY)
    sysmon = _fact("b", SYSMON_EVENT_LOG)
    assert _check(ledger, sysmon) is False
