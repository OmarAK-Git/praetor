"""Unit tests for provenance trust classification (DEC-059, DEC-064)."""

from __future__ import annotations

from praetor.evidence.provenance import (
    LEDGER_HISTORY,
    SYSMON_EVENT_LOG,
    WINDOWS_SECURITY_LOG,
    is_attacker_controllable_provenance,
)


def test_ledger_history_is_attacker_controllable() -> None:
    assert is_attacker_controllable_provenance(LEDGER_HISTORY) is True


def test_existing_classifications_unchanged() -> None:
    assert is_attacker_controllable_provenance(WINDOWS_SECURITY_LOG) is False
    assert is_attacker_controllable_provenance(SYSMON_EVENT_LOG) is True


def test_unknown_provenance_path_defaults_attacker_controllable() -> None:
    assert is_attacker_controllable_provenance("some_new_source") is True
