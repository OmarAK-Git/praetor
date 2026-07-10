"""V2-022: Windows normalizer conformance helpers (PE-0024)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from praetor.correlation import load_fixture_events
from praetor.correlation.normalizer_conformance import (
    malformed_domain_separator_ambiguity,
    require_domain_separator_ambiguity_flag,
)
from praetor.correlation.security_log import normalize_security_event
from praetor.correlation.sysmon import normalize_sysmon_event

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SYSMON_FIXTURES = FIXTURES / "sysmon"
SECURITY_FIXTURES = FIXTURES / "security"


def _load_json_fixture(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return load_fixture_events(payload)


@pytest.mark.parametrize(
    ("account_repr", "expected"),
    [
        ("CORP\\jdoe", False),
        ("", False),
        ("jdoe", True),
        ("jdoe@corp.example", True),
    ],
)
def test_malformed_domain_separator_ambiguity_vectors(
    account_repr: str,
    expected: bool,
) -> None:
    assert malformed_domain_separator_ambiguity(account_repr) is expected


def test_require_domain_separator_ambiguity_flag_passes_well_formed() -> None:
    require_domain_separator_ambiguity_flag(
        account_repr="CORP\\jdoe",
        ambiguity_flag=False,
    )


def test_require_domain_separator_ambiguity_flag_raises_on_malformed() -> None:
    with pytest.raises(AssertionError, match="ambiguity_flag must be true"):
        require_domain_separator_ambiguity_flag(
            account_repr="jdoe",
            ambiguity_flag=False,
        )


def test_sysmon_well_formed_user_passes_conformance_helper() -> None:
    events = _load_json_fixture(SYSMON_FIXTURES / "process_chain.json")
    fact = normalize_sysmon_event(events[0])
    user = str(fact.normalized_fields["user"])

    require_domain_separator_ambiguity_flag(
        account_repr=user,
        ambiguity_flag=fact.ambiguity_flag,
    )
    assert fact.ambiguity_flag is False


def test_sysmon_malformed_user_passes_conformance_helper() -> None:
    events = _load_json_fixture(SYSMON_FIXTURES / "ambiguous_user.json")
    fact = normalize_sysmon_event(events[0])
    user = str(fact.normalized_fields["user"])

    require_domain_separator_ambiguity_flag(
        account_repr=user,
        ambiguity_flag=fact.ambiguity_flag,
    )
    assert fact.ambiguity_flag is True


def test_security_logon_behavior_unchanged() -> None:
    events = _load_json_fixture(SECURITY_FIXTURES / "successful_logon_4624.json")
    fact = normalize_security_event(events[0])

    assert fact.ambiguity_flag is False
    assert fact.normalized_fields["account_name"] == "jdoe"
    assert fact.normalized_fields["domain"] == "CORP"
    assert str(fact.normalized_fields["target_sid"]).startswith("S-1-5-21-")
