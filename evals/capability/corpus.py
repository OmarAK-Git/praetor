"""Labeled anchor manifest for the judgment capability spike.

Labels are authored from capture ground truth and committed BEFORE any
provider call. Labeling after seeing engine output produces a tautology.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

MALICIOUS = "malicious"
BENIGN = "benign"
UNRESOLVED = "unresolved"
_VALID_CLASSES = frozenset({MALICIOUS, BENIGN, UNRESOLVED})
_SCORED_CLASSES = frozenset({MALICIOUS, BENIGN})


class ManifestError(Exception):
    """Raised when an anchor manifest is structurally invalid."""


@dataclass(frozen=True)
class Anchor:
    anchor_id: str
    anchor_time: datetime
    expected_class: str
    rationale: str
    # Optional seed metadata for Guard #2 confound features only.
    # Path A/B runtime uses anchor_time alone — never a seed record.
    seed_event_id: int | None = None
    seed_channel: str | None = None
    seed_event_record_id: str | None = None
    seed_host_id: str | None = None
    seed_subject_sid: str | None = None


@dataclass(frozen=True)
class AnchorManifest:
    capture_id: str
    anchors: tuple[Anchor, ...]
    emulation_steps_total: int | None = None
    unchained_steps: int | None = None

    @property
    def malicious(self) -> tuple[Anchor, ...]:
        return tuple(a for a in self.anchors if a.expected_class == MALICIOUS)

    @property
    def benign(self) -> tuple[Anchor, ...]:
        return tuple(a for a in self.anchors if a.expected_class == BENIGN)

    @property
    def unresolved(self) -> tuple[Anchor, ...]:
        return tuple(a for a in self.anchors if a.expected_class == UNRESOLVED)

    @property
    def unchained_step_share(self) -> float | None:
        if self.emulation_steps_total is None or self.unchained_steps is None:
            return None
        if self.emulation_steps_total <= 0:
            return None
        return self.unchained_steps / self.emulation_steps_total


def _coerce_time(value: Any, *, anchor_id: str) -> datetime:
    if isinstance(value, datetime):
        moment = value
    elif isinstance(value, str):
        try:
            moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as err:
            msg = f"anchor {anchor_id}: unparseable anchor_time {value!r}"
            raise ManifestError(msg) from err
    else:
        msg = f"anchor {anchor_id}: anchor_time must be a timestamp"
        raise ManifestError(msg)
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment


def _build_anchor(raw: Mapping[str, Any]) -> Anchor:
    anchor_id = str(raw.get("anchor_id", "")).strip()
    if not anchor_id:
        msg = "every anchor requires a non-empty anchor_id"
        raise ManifestError(msg)

    expected_class = str(raw.get("expected_class", "")).strip()
    if expected_class not in _VALID_CLASSES:
        msg = (
            f"anchor {anchor_id}: expected_class must be one of "
            f"{sorted(_VALID_CLASSES)}, got {expected_class!r}"
        )
        raise ManifestError(msg)

    rationale = str(raw.get("rationale", "")).strip()
    if not rationale:
        msg = f"anchor {anchor_id}: rationale is required and must be non-empty"
        raise ManifestError(msg)

    seed_event_id: int | None = None
    if "seed_event_id" in raw and raw["seed_event_id"] is not None:
        value = raw["seed_event_id"]
        if isinstance(value, bool) or not isinstance(value, int):
            msg = f"anchor {anchor_id}: seed_event_id must be an integer"
            raise ManifestError(msg)
        seed_event_id = value

    seed_channel: str | None = None
    if "seed_channel" in raw and raw["seed_channel"] is not None:
        seed_channel = str(raw["seed_channel"]).strip() or None

    seed_rid: str | None = None
    if "seed_event_record_id" in raw and raw["seed_event_record_id"] is not None:
        seed_rid = str(raw["seed_event_record_id"]).strip() or None

    seed_host: str | None = None
    if "seed_host_id" in raw and raw["seed_host_id"] is not None:
        seed_host = str(raw["seed_host_id"]).strip() or None

    seed_sid: str | None = None
    if "seed_subject_sid" in raw and raw["seed_subject_sid"] is not None:
        seed_sid = str(raw["seed_subject_sid"]).strip() or None

    return Anchor(
        anchor_id=anchor_id,
        anchor_time=_coerce_time(raw.get("anchor_time"), anchor_id=anchor_id),
        expected_class=expected_class,
        rationale=rationale,
        seed_event_id=seed_event_id,
        seed_channel=seed_channel,
        seed_event_record_id=seed_rid,
        seed_host_id=seed_host,
        seed_subject_sid=seed_sid,
    )


def _optional_nonneg_int(raw: Mapping[str, Any], key: str, *, path: Path) -> int | None:
    if key not in raw or raw[key] is None:
        return None
    value = raw[key]
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{path}: {key} must be a non-negative integer"
        raise ManifestError(msg)
    if value < 0:
        msg = f"{path}: {key} must be a non-negative integer"
        raise ManifestError(msg)
    return value


def load_anchor_manifest(path: Path) -> AnchorManifest:
    """Load and validate a labeled anchor manifest."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        msg = f"{path}: manifest must be a mapping"
        raise ManifestError(msg)

    capture_id = str(raw.get("capture_id", "")).strip()
    if not capture_id:
        msg = f"{path}: capture_id is required"
        raise ManifestError(msg)

    rows = raw.get("anchors")
    if not isinstance(rows, list) or not rows:
        msg = f"{path}: anchors must be a non-empty list"
        raise ManifestError(msg)

    anchors: list[Anchor] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            msg = f"{path}: each anchor must be a mapping"
            raise ManifestError(msg)
        anchor = _build_anchor(row)
        if anchor.anchor_id in seen:
            msg = f"{path}: duplicate anchor_id {anchor.anchor_id!r}"
            raise ManifestError(msg)
        seen.add(anchor.anchor_id)
        anchors.append(anchor)

    steps_total = _optional_nonneg_int(raw, "emulation_steps_total", path=path)
    unchained = _optional_nonneg_int(raw, "unchained_steps", path=path)
    if (steps_total is None) ^ (unchained is None):
        msg = (
            f"{path}: emulation_steps_total and unchained_steps must both be "
            "set or both omitted"
        )
        raise ManifestError(msg)
    if steps_total is not None and unchained is not None and unchained > steps_total:
        msg = f"{path}: unchained_steps cannot exceed emulation_steps_total"
        raise ManifestError(msg)

    manifest = AnchorManifest(
        capture_id=capture_id,
        anchors=tuple(anchors),
        emulation_steps_total=steps_total,
        unchained_steps=unchained,
    )
    n_mal = len(manifest.malicious)
    n_ben = len(manifest.benign)
    if n_mal != n_ben:
        msg = (
            f"{path}: unbalanced corpus — {n_mal} malicious vs {n_ben} benign. "
            "Shrink both sides together; an unbalanced corpus is not interpretable. "
            "unresolved anchors do not participate in the balance."
        )
        raise ManifestError(msg)

    return manifest
