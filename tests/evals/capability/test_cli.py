from __future__ import annotations

import json
from pathlib import Path

import pytest
from evals.capability_spike import (
    SPIKE_ENV_FLAG,
    load_capture_events,
    main,
    resolve_spike_provider,
    spike_enabled,
)


def test_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(SPIKE_ENV_FLAG, raising=False)
    assert spike_enabled() is False
    assert resolve_spike_provider() is None


def test_main_exits_zero_when_disabled(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv(SPIKE_ENV_FLAG, raising=False)
    assert main() == 0
    assert "skipped" in capsys.readouterr().out.lower()


def test_enabled_without_key_still_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(SPIKE_ENV_FLAG, "1")
    monkeypatch.delenv("PRAETOR_GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert spike_enabled() is True
    assert resolve_spike_provider() is None


def test_load_capture_events_reads_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "capture.jsonl"
    rows = [
        {"EventID": 1, "Channel": "Sysmon", "EventRecordID": "1", "Computer": "ws-01"},
        {"EventID": 3, "Channel": "Sysmon", "EventRecordID": "2", "Computer": "ws-01"},
    ]
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    events = load_capture_events(path)
    assert len(events) == 2
    assert events[1]["EventID"] == 3


def test_load_capture_events_skips_blank_and_malformed_lines(tmp_path: Path) -> None:
    path = tmp_path / "capture.jsonl"
    path.write_text(
        '{"EventID": 1, "EventRecordID": "1"}\n'
        "\n"
        "not json at all\n"
        '{"EventID": 3, "EventRecordID": "2"}\n',
        encoding="utf-8",
    )
    events = load_capture_events(path)
    assert len(events) == 2


def test_harness_does_not_import_the_spike() -> None:
    """The gating suite must never become network-dependent."""
    harness_source = (
        Path(__file__).resolve().parents[3] / "evals" / "harness.py"
    ).read_text(encoding="utf-8")
    assert "capability_spike" not in harness_source
    assert "evals.capability" not in harness_source
