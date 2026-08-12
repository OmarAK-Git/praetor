from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from evals.capability.corpus import (
    AnchorManifest,
    ManifestError,
    load_anchor_manifest,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_valid_manifest() -> None:
    manifest = load_anchor_manifest(FIXTURES / "manifest_valid.yaml")
    assert isinstance(manifest, AnchorManifest)
    assert manifest.capture_id == "test-capture"
    assert len(manifest.anchors) == 4
    first = manifest.anchors[0]
    assert first.anchor_id == "mal-01"
    assert first.expected_class == "malicious"
    assert first.anchor_time == datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    assert first.rationale


def test_naive_timestamps_are_coerced_to_utc() -> None:
    manifest = load_anchor_manifest(FIXTURES / "manifest_valid.yaml")
    assert all(a.anchor_time.tzinfo is not None for a in manifest.anchors)


def test_duplicate_anchor_ids_rejected(tmp_path: Path) -> None:
    path = tmp_path / "dupe.yaml"
    path.write_text(
        "capture_id: c\n"
        "anchors:\n"
        "  - {anchor_id: a, anchor_time: 2026-01-01T00:00:00Z,"
        " expected_class: malicious, rationale: r}\n"
        "  - {anchor_id: a, anchor_time: 2026-01-01T00:01:00Z,"
        " expected_class: benign, rationale: r}\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError, match="duplicate anchor_id"):
        load_anchor_manifest(path)


def test_unbalanced_classes_rejected(tmp_path: Path) -> None:
    path = tmp_path / "unbalanced.yaml"
    rows = [
        f"  - {{anchor_id: m{i}, anchor_time: 2026-01-01T00:0{i}:00Z,"
        f" expected_class: malicious, rationale: r}}"
        for i in range(3)
    ]
    rows.append(
        "  - {anchor_id: b0, anchor_time: 2026-01-01T01:00:00Z,"
        " expected_class: benign, rationale: r}"
    )
    path.write_text("capture_id: c\nanchors:\n" + "\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(ManifestError, match="unbalanced"):
        load_anchor_manifest(path)


def test_unknown_expected_class_rejected(tmp_path: Path) -> None:
    path = tmp_path / "badclass.yaml"
    path.write_text(
        "capture_id: c\n"
        "anchors:\n"
        "  - {anchor_id: a, anchor_time: 2026-01-01T00:00:00Z,"
        " expected_class: ambiguous, rationale: r}\n"
        "  - {anchor_id: b, anchor_time: 2026-01-01T00:01:00Z,"
        " expected_class: benign, rationale: r}\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError, match="expected_class"):
        load_anchor_manifest(path)


def test_missing_rationale_rejected(tmp_path: Path) -> None:
    path = tmp_path / "norationale.yaml"
    path.write_text(
        "capture_id: c\n"
        "anchors:\n"
        "  - {anchor_id: a, anchor_time: 2026-01-01T00:00:00Z,"
        " expected_class: malicious, rationale: ''}\n"
        "  - {anchor_id: b, anchor_time: 2026-01-01T00:01:00Z,"
        " expected_class: benign, rationale: r}\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError, match="rationale"):
        load_anchor_manifest(path)


def test_unresolved_allowed_and_excluded_from_balance(tmp_path: Path) -> None:
    path = tmp_path / "with_unresolved.yaml"
    path.write_text(
        "capture_id: c\n"
        "emulation_steps_total: 10\n"
        "unchained_steps: 2\n"
        "anchors:\n"
        "  - {anchor_id: m1, anchor_time: 2026-01-01T00:00:00Z,"
        " expected_class: malicious, rationale: step}\n"
        "  - {anchor_id: b1, anchor_time: 2026-01-01T01:00:00Z,"
        " expected_class: benign, rationale: quiet}\n"
        "  - {anchor_id: u1, anchor_time: 2026-01-01T00:30:00Z,"
        " expected_class: unresolved, rationale: fileless}\n"
        "  - {anchor_id: u2, anchor_time: 2026-01-01T00:45:00Z,"
        " expected_class: unresolved, rationale: registry}\n",
        encoding="utf-8",
    )
    manifest = load_anchor_manifest(path)
    assert len(manifest.malicious) == 1
    assert len(manifest.benign) == 1
    assert len(manifest.unresolved) == 2
    assert manifest.emulation_steps_total == 10
    assert manifest.unchained_steps == 2
    assert manifest.unchained_step_share == 0.2


def test_step_fields_must_be_paired(tmp_path: Path) -> None:
    path = tmp_path / "partial_steps.yaml"
    path.write_text(
        "capture_id: c\n"
        "emulation_steps_total: 10\n"
        "anchors:\n"
        "  - {anchor_id: m1, anchor_time: 2026-01-01T00:00:00Z,"
        " expected_class: malicious, rationale: r}\n"
        "  - {anchor_id: b1, anchor_time: 2026-01-01T01:00:00Z,"
        " expected_class: benign, rationale: r}\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError, match="both"):
        load_anchor_manifest(path)
