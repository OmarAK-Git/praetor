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
    assert main([]) == 0
    assert "skipped" in capsys.readouterr().out.lower()


def test_bundles_only_runs_without_env_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv(SPIKE_ENV_FLAG, raising=False)

    manifest = tmp_path / "m.yaml"
    manifest.write_text(
        """
capture_id: test
anchors:
  - anchor_id: mal-01
    anchor_time: 2026-01-01T12:00:00Z
    expected_class: malicious
    seed_host_id: ws-01
    rationale: synthetic
  - anchor_id: ben-01
    anchor_time: 2026-01-01T12:00:00Z
    expected_class: benign
    seed_host_id: ws-01
    rationale: synthetic
""".strip()
        + "\n",
        encoding="utf-8",
    )
    capture = tmp_path / "c.jsonl"
    events = [
        {
            "EventID": 1,
            "Channel": "Microsoft-Windows-Sysmon/Operational",
            "EventRecordID": "1",
            "Computer": "ws-01",
            "UtcTime": "2026-01-01 12:00:00.000",
            "EventData": {"Image": r"C:\Windows\System32\cmd.exe"},
        },
        {
            "EventID": 4624,
            "Channel": "Security",
            "EventRecordID": "2",
            "Computer": "ws-01",
            "UtcTime": "2026-01-01 12:00:01.000",
            "EventData": {"TargetUserName": "alice"},
        },
    ]
    capture.write_text(
        "\n".join(json.dumps(row) for row in events) + "\n", encoding="utf-8"
    )
    assert (
        main(
            [
                "--bundles-only",
                "--manifest",
                str(manifest),
                "--capture",
                str(capture),
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "mode=bundles-only" in out
    assert "path_a_empty_by_class" in out
    assert "malicious" in out and "benign" in out
    assert "path_a_empty_by_class malicious=0/1 benign=0/1" in out


def test_enabled_without_key_still_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(SPIKE_ENV_FLAG, "1")
    monkeypatch.delenv("PRAETOR_GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCLOUD_PROJECT", raising=False)
    monkeypatch.delenv("PRAETOR_GCP_PROJECT", raising=False)
    assert spike_enabled() is True
    assert resolve_spike_provider() is None


def test_enabled_with_gcp_project_uses_spike_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(SPIKE_ENV_FLAG, "1")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.delenv("PRAETOR_GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    provider = resolve_spike_provider()
    assert provider is not None
    assert getattr(provider, "provider_name", None) == "vertex-spike"
    assert getattr(provider, "temperature", None) == 1.0
    assert getattr(provider, "project", None) == "test-project"


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
