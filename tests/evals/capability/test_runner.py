from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from evals.capability.corpus import Anchor
from evals.capability.runner import (
    PATH_A,
    PATH_B,
    Observation,
    open_spike_store,
    run_anchor,
)

from praetor.contracts.disposition import Disposition
from praetor.judgment.fake_provider import FakeProvider

ANCHOR_TIME = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

ANCHOR = Anchor(
    anchor_id="mal-01",
    anchor_time=ANCHOR_TIME,
    expected_class="malicious",
    rationale="test anchor",
)


def _sysmon(record_id: str, event_id: int = 1) -> dict[str, object]:
    return {
        "EventID": event_id,
        "Channel": "Microsoft-Windows-Sysmon/Operational",
        "EventRecordID": record_id,
        "Computer": "ws-01",
        "UtcTime": "2026-01-01 12:00:00.000",
        "EventData": {
            "Image": r"C:\Windows\System32\powershell.exe",
            "CommandLine": "powershell -enc ZQBjAGgAbwA=",
            "ProcessGuid": "{guid-1}",
            "ParentProcessGuid": "{guid-0}",
            "ParentImage": r"C:\Program Files\Office\winword.exe",
            "User": "CORP\\alice",
            "ProcessId": "1234",
            "ParentProcessId": "1000",
        },
    }


def _security(record_id: str) -> dict[str, object]:
    return {
        "EventID": 4624,
        "Channel": "Security",
        "EventRecordID": record_id,
        "Computer": "ws-01",
        "UtcTime": "2026-01-01 12:00:30.000",
        "EventData": {
            "TargetUserName": "alice",
            "TargetDomainName": "CORP",
            "TargetUserSid": "S-1-5-21-1",
            "LogonType": "3",
        },
    }


def test_both_paths_produce_observations(tmp_path: Path) -> None:
    store = open_spike_store(tmp_path / "spike.db")
    try:
        observations = run_anchor(
            store,
            anchor=ANCHOR,
            events=[_sysmon("1"), _security("2")],
            provider=FakeProvider(proposed_disposition=Disposition.ESCALATE),
            runs=1,
        )
    finally:
        store.conn.close()

    assert len(observations) == 2
    paths = {obs.path for obs in observations}
    assert paths == {PATH_A, PATH_B}
    assert all(isinstance(obs, Observation) for obs in observations)
    assert all(obs.anchor_id == "mal-01" for obs in observations)
    assert all(obs.expected_class == "malicious" for obs in observations)


def test_path_b_sees_more_facts_than_path_a(tmp_path: Path) -> None:
    """EventID 3 is invisible to correlation but present in the Path B bundle."""
    events = [_sysmon("1"), _sysmon("3", event_id=3), _security("2")]
    store = open_spike_store(tmp_path / "spike.db")
    try:
        observations = run_anchor(
            store,
            anchor=ANCHOR,
            events=events,
            provider=FakeProvider(proposed_disposition=Disposition.ESCALATE),
            runs=1,
        )
    finally:
        store.conn.close()

    by_path = {obs.path: obs for obs in observations}
    assert by_path[PATH_B].bundle_fact_count > by_path[PATH_A].bundle_fact_count


def test_runs_parameter_repeats_each_path(tmp_path: Path) -> None:
    store = open_spike_store(tmp_path / "spike.db")
    try:
        observations = run_anchor(
            store,
            anchor=ANCHOR,
            events=[_sysmon("1"), _security("2")],
            provider=FakeProvider(proposed_disposition=Disposition.ESCALATE),
            runs=3,
        )
    finally:
        store.conn.close()

    assert len(observations) == 6
    assert sorted(obs.run_index for obs in observations) == [0, 0, 1, 1, 2, 2]


def test_path_a_correlates_in_window_events(tmp_path: Path) -> None:
    """Path A must pass anchor_time so correlation finds fixture events."""
    store = open_spike_store(tmp_path / "spike.db")
    disposition = Disposition.STANDARD_REVIEW
    try:
        observations = run_anchor(
            store,
            anchor=ANCHOR,
            events=[_sysmon("1"), _security("2")],
            provider=FakeProvider(proposed_disposition=disposition),
            runs=1,
        )
    finally:
        store.conn.close()

    path_a = next(obs for obs in observations if obs.path == PATH_A)
    assert "correlation_failure" not in path_a.fault_flags
    assert path_a.proposed_disposition == disposition.value


def test_proposed_disposition_is_recorded(tmp_path: Path) -> None:
    store = open_spike_store(tmp_path / "spike.db")
    try:
        observations = run_anchor(
            store,
            anchor=ANCHOR,
            events=[_sysmon("1"), _security("2")],
            provider=FakeProvider(proposed_disposition=Disposition.ESCALATE),
            runs=1,
        )
    finally:
        store.conn.close()

    assert all(obs.proposed_disposition == "escalate" for obs in observations)
