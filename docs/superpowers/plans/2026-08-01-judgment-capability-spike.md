# Judgment Capability Spike Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an offline-testable eval that measures whether Praetor's single-shot judgment layer separates malicious from benign telemetry, and how much of any failure is caused by correlation's two-event-type coverage limit.

**Architecture:** A new `evals/capability/` package runs each labeled anchor through `process_alert_intake` twice — Path A via real `correlate_telemetry` (Sysmon EventID 1 + Security 4624 only), Path B via a harness-built bundle from a generic flattener covering all event types. Only `ModelJudgment.proposed_disposition` is scored; PolicyGate output is recorded but not scored. The A/B delta attributes failures to evidence coverage versus judgment quality.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, PyYAML, `praetor.judgment.vertex_provider.VertexProvider` (Gemini).

## Amendment 2026-08-02 (post Task 1–6 drain)

Design addendum in `docs/superpowers/specs/2026-08-01-capability-spike-design.md`. Implement before any APT29 manifest authoring (schema change).

### A2 — `unresolved` label + label-quality counters

- Extend `expected_class` to `{malicious, benign, unresolved}`.
- Balance check remains **malicious count == benign count**; `unresolved` unrestricted.
- Manifest fields `emulation_steps_total` and `unchained_steps` (both required together or both absent for unit fixtures; required for live APT29 manifests).
- `score_path` / `ab_delta` exclude `unresolved` (and still exclude empty judgment).
- CLI **always** prints `n_unresolved` and `unchained_step_share` (use `n/a` only when step fields absent on fixtures).

### A3 — Citation-mix join key + A≈B read

- Path B flattener pins `EventID` and `Channel` into `normalized_fields`.
- `Observation` records `cited_event_ids` from resolved `cited_evidence_refs` joined through the path's bundle facts.
- Pre-registered constants (do not change after seeing a live tie):
  - `AB_TIE_SEPARATION_EPSILON = 0.05`
  - `PATH_A_VISIBLE_EVENT_IDS = {1, 4624}`
  - `PATH_A_CITATION_CONCENTRATION_THRESHOLD = 0.80`
- CLI always prints Path B concentration and tie interpretation (`not_a_tie` | `prompt_constrained` | `coverage_not_bottleneck` | `citations_unavailable`).

### A4 — Commit gate for this amendment

- [x] `pytest tests/evals/capability -q` (45 passed)
- [x] `ruff check evals/capability evals/capability_spike.py tests/evals/capability`
- [x] `mypy evals/capability evals/capability_spike.py`
- [ ] Do **not** author the APT29 manifest until A2/A3 are green (schema landed; authoring still operator-owned).

## Amendment 2026-08-02b (ATLAS corpus + confound wiring)

Prefer ATLASv2 over APT29 when local. Design corpus section updated.

### A5 — ATLAS same-file labeling + residue semantics

- Scored benign/malicious from **attack-day** `msft-security-h*-*.xml` + `groundtruth/` only (not `data/benign/`).
- Path A does **not** consume GT; empty-bundle rate is the measurement.
- Malicious = distinct attack-action GT times (not every GT row / `_MEI*` handle noise).
- Benign = same file, outside GT, spread across full file time range.
- `emulation_steps_total = 10`; `unchained_steps` = scenarios with **no usable Path B anchor** (label quality), not Path A visibility.

### A6 — Wire Guard #2 + graded separation

- `confound_report` / `confound_graded_separation` beside boolean `confound_check`.
- `CONFOUND_GRADED_WARN_THRESHOLD = 0.90`.
- CLI builds capture-derived features and prints confound **before** provider calls and again in the summary.

## Global Constraints

- **No changes to `src/praetor/`.** This spike is measurement only. If a task appears to require a `src/` change, stop and report.
- **No changes to `evals/harness.py` or `evals/scenarios/`.** The 33 mandatory scenarios must stay untouched.
- **Nothing in this package may be imported by `evals/harness.py`,** or the gating suite becomes network-dependent.
- **All committed tests must pass offline with no API key**, using `FakeProvider`. Live-provider runs are opt-in via env var only.
- **Judgment path under test is the single-shot GenAI wrapper only.** Never construct or import from `praetor.judgment.agentic`.
- Every task ends green under `pytest -q`, `mypy .`, and `ruff check .`.
- Python version floor: **3.11+**.

---

### Task 1: Corpus manifest schema and loader

**Files:**
- Create: `evals/capability/__init__.py`
- Create: `evals/capability/corpus.py`
- Create: `tests/evals/capability/__init__.py`
- Test: `tests/evals/capability/test_corpus.py`
- Create: `tests/evals/capability/fixtures/manifest_valid.yaml`

**Interfaces:**
- Consumes: nothing.
- Produces: `Anchor` (frozen dataclass with fields `anchor_id: str`, `anchor_time: datetime`, `expected_class: str`, `rationale: str`); `AnchorManifest` (frozen dataclass with `capture_id: str`, `anchors: tuple[Anchor, ...]`); `load_anchor_manifest(path: Path) -> AnchorManifest`; `ManifestError(Exception)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/evals/capability/test_corpus.py
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
        "  - {anchor_id: m%d, anchor_time: 2026-01-01T00:0%d:00Z,"
        " expected_class: malicious, rationale: r}" % (i, i)
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
```

Also create the fixture:

```yaml
# tests/evals/capability/fixtures/manifest_valid.yaml
capture_id: test-capture
anchors:
  - anchor_id: mal-01
    anchor_time: 2026-01-01T12:00:00Z
    expected_class: malicious
    rationale: Encoded PowerShell spawned by Office process per capture technique notes.
  - anchor_id: mal-02
    anchor_time: 2026-01-01T12:05:00Z
    expected_class: malicious
    rationale: Credential access tooling executed on the same host.
  - anchor_id: ben-01
    anchor_time: 2026-01-01T08:00:00Z
    expected_class: benign
    rationale: Scheduled inventory script, same host, hours before the attack window.
  - anchor_id: ben-02
    anchor_time: 2026-01-01T08:30:00Z
    expected_class: benign
    rationale: Routine administrator logon, same host, outside the attack window.
```

Create empty `tests/evals/capability/__init__.py`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/evals/capability/test_corpus.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'evals.capability'`

- [ ] **Step 3: Write minimal implementation**

Create empty `evals/capability/__init__.py`, then:

```python
# evals/capability/corpus.py
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
_VALID_CLASSES = frozenset({MALICIOUS, BENIGN})


class ManifestError(Exception):
    """Raised when an anchor manifest is structurally invalid."""


@dataclass(frozen=True)
class Anchor:
    anchor_id: str
    anchor_time: datetime
    expected_class: str
    rationale: str


@dataclass(frozen=True)
class AnchorManifest:
    capture_id: str
    anchors: tuple[Anchor, ...]

    @property
    def malicious(self) -> tuple[Anchor, ...]:
        return tuple(a for a in self.anchors if a.expected_class == MALICIOUS)

    @property
    def benign(self) -> tuple[Anchor, ...]:
        return tuple(a for a in self.anchors if a.expected_class == BENIGN)


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

    return Anchor(
        anchor_id=anchor_id,
        anchor_time=_coerce_time(raw.get("anchor_time"), anchor_id=anchor_id),
        expected_class=expected_class,
        rationale=rationale,
    )


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

    manifest = AnchorManifest(capture_id=capture_id, anchors=tuple(anchors))
    n_mal = len(manifest.malicious)
    n_ben = len(manifest.benign)
    if n_mal != n_ben:
        msg = (
            f"{path}: unbalanced corpus — {n_mal} malicious vs {n_ben} benign. "
            "Shrink both sides together; an unbalanced corpus is not interpretable."
        )
        raise ManifestError(msg)

    return manifest
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/evals/capability/test_corpus.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Verify quality gates**

Run: `mypy . && ruff check .`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add evals/capability/__init__.py evals/capability/corpus.py tests/evals/capability/
git commit -m "Add labeled anchor manifest loader for capability spike."
```

---

### Task 2: Generic event flattener

**Files:**
- Create: `evals/capability/flatten.py`
- Test: `tests/evals/capability/test_flatten.py`

**Interfaces:**
- Consumes: `evals.capability.corpus` (nothing directly; independent module).
- Produces: `flatten_event_to_fact(event: Mapping[str, Any], *, provenance_path: str) -> EvidenceFact`; `resolve_provenance_path(event: Mapping[str, Any]) -> str`; `SPIKE_UNKNOWN_SOURCE: str`.

**Why this exists:** `_build_prompt_fact` (`src/praetor/judgment/excerpt.py:149-159`) emits one excerpt per `normalized_fields` key with arbitrary key names, so the model needs no per-event-type schema. This flattener must stay dumb and mechanical — no hand-tuned per-event-type extraction — or a good Path B result measures the flattener rather than Praetor.

- [ ] **Step 1: Write the failing test**

```python
# tests/evals/capability/test_flatten.py
from __future__ import annotations

from datetime import UTC, datetime

from praetor.evidence.provenance import SYSMON_EVENT_LOG, WINDOWS_SECURITY_LOG

from evals.capability.flatten import (
    SPIKE_UNKNOWN_SOURCE,
    flatten_event_to_fact,
    resolve_provenance_path,
)

SYSMON_NETWORK_EVENT = {
    "EventID": 3,
    "Channel": "Microsoft-Windows-Sysmon/Operational",
    "EventRecordID": "9001",
    "Computer": "ws-01",
    "UtcTime": "2026-01-01 12:00:00.000",
    "EventData": {
        "Image": r"C:\Windows\System32\powershell.exe",
        "DestinationIp": "203.0.113.10",
        "DestinationPort": "443",
    },
}


def test_unsupported_event_id_still_produces_a_fact() -> None:
    """EventID 3 is rejected by correlation but must flatten cleanly here."""
    fact = flatten_event_to_fact(
        SYSMON_NETWORK_EVENT, provenance_path=SYSMON_EVENT_LOG
    )
    assert fact.provenance_path == SYSMON_EVENT_LOG
    assert fact.evidence_id.startswith("ev-")
    assert fact.timestamp == datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def test_event_data_is_flattened_into_normalized_fields() -> None:
    fact = flatten_event_to_fact(
        SYSMON_NETWORK_EVENT, provenance_path=SYSMON_EVENT_LOG
    )
    assert fact.normalized_fields["DestinationIp"] == "203.0.113.10"
    assert fact.normalized_fields["DestinationPort"] == "443"
    assert fact.normalized_fields["Image"].endswith("powershell.exe")


def test_host_id_key_is_set_for_targeting() -> None:
    """host_id is the silent contract with containment_policy consumers."""
    fact = flatten_event_to_fact(
        SYSMON_NETWORK_EVENT, provenance_path=SYSMON_EVENT_LOG
    )
    assert fact.normalized_fields["host_id"] == "ws-01"


def test_raw_source_key_excluded_from_normalized_fields() -> None:
    """excerpt.py skips a normalized_fields['raw_source'] key; never emit one."""
    event = dict(SYSMON_NETWORK_EVENT)
    event["raw_source"] = "must not appear in normalized_fields"
    fact = flatten_event_to_fact(event, provenance_path=SYSMON_EVENT_LOG)
    assert "raw_source" not in fact.normalized_fields
    assert "must not appear" in fact.raw_source


def test_source_event_reference_includes_record_id() -> None:
    """Enrichment counts distinct source_event_reference, so record_id matters."""
    fact = flatten_event_to_fact(
        SYSMON_NETWORK_EVENT, provenance_path=SYSMON_EVENT_LOG
    )
    assert fact.source_event_reference.endswith(":3:9001")


def test_two_records_of_same_event_id_are_distinct_source_events() -> None:
    second = dict(SYSMON_NETWORK_EVENT)
    second["EventRecordID"] = "9002"
    a = flatten_event_to_fact(SYSMON_NETWORK_EVENT, provenance_path=SYSMON_EVENT_LOG)
    b = flatten_event_to_fact(second, provenance_path=SYSMON_EVENT_LOG)
    assert a.source_event_reference != b.source_event_reference
    assert a.evidence_id != b.evidence_id


def test_resolve_provenance_path_by_channel() -> None:
    assert resolve_provenance_path(SYSMON_NETWORK_EVENT) == SYSMON_EVENT_LOG
    assert (
        resolve_provenance_path({"Channel": "Security", "EventID": 4688})
        == WINDOWS_SECURITY_LOG
    )
    assert (
        resolve_provenance_path({"Channel": "SomeVendor/EDR", "EventID": 7})
        == SPIKE_UNKNOWN_SOURCE
    )


def test_ambiguity_flag_defaults_false() -> None:
    fact = flatten_event_to_fact(
        SYSMON_NETWORK_EVENT, provenance_path=SYSMON_EVENT_LOG
    )
    assert fact.ambiguity_flag is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/evals/capability/test_flatten.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'evals.capability.flatten'`

- [ ] **Step 3: Write minimal implementation**

```python
# evals/capability/flatten.py
"""Generic Windows-event flattener for capability-spike Path B.

Correlation normalizes only Sysmon EventID 1 and Security 4624
(``correlation/sysmon.py:23``, ``correlation/security_log.py:19``). This
module produces an ``EvidenceFact`` from ANY event so Path B can measure
what judgment does with full evidence coverage.

Deliberately dumb: it flattens whatever fields are present and adds no
per-event-type interpretation. Hand-tuned extraction here would mean a good
Path B score measures this file rather than Praetor.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from praetor.contracts.evidence import EvidenceFact
from praetor.correlation._event_fields import (
    canonical_raw_source,
    event_field,
    event_record_id,
    event_timestamp,
)
from praetor.correlation.host_isolation import event_host_id
from praetor.correlation.ids import derive_evidence_id, source_event_reference
from praetor.evidence.provenance import SYSMON_EVENT_LOG, WINDOWS_SECURITY_LOG

SPIKE_UNKNOWN_SOURCE = "spike_unknown_source"
_RAW_SOURCE_KEY = "raw_source"
_STRUCTURAL_KEYS = frozenset({"EventData", _RAW_SOURCE_KEY})


def resolve_provenance_path(event: Mapping[str, Any]) -> str:
    """Map an event to a provenance path by SOURCE, not by event type.

    Corroboration counts distinct provenance paths, so every Sysmon EventID
    collapses to one path by design.
    """
    channel = str(event_field(event, "Channel") or "")
    lowered = channel.lower()
    if "sysmon" in lowered:
        return SYSMON_EVENT_LOG
    if lowered.startswith("security"):
        return WINDOWS_SECURITY_LOG
    return SPIKE_UNKNOWN_SOURCE


def _flatten_fields(event: Mapping[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in event.items():
        if key in _STRUCTURAL_KEYS:
            continue
        flattened[str(key)] = value
    nested = event.get("EventData")
    if isinstance(nested, Mapping):
        for key, value in nested.items():
            if key == _RAW_SOURCE_KEY:
                continue
            flattened[str(key)] = value
    return flattened


def flatten_event_to_fact(
    event: Mapping[str, Any],
    *,
    provenance_path: str,
) -> EvidenceFact:
    """Build an ``EvidenceFact`` from any Windows event dict."""
    record_id = event_record_id(event)
    event_id = event_field(event, "EventID") or 0
    channel = str(event_field(event, "Channel") or "unknown")
    source_ref = source_event_reference(
        channel=channel,
        event_id=event_id,
        record_id=record_id,
    )

    normalized_fields = _flatten_fields(event)
    normalized_fields["host_id"] = event_host_id(event) or ""

    return EvidenceFact(
        evidence_id=derive_evidence_id(
            provenance_path=provenance_path,
            source_event_reference=source_ref,
        ),
        normalized_fields=normalized_fields,
        source_event_reference=source_ref,
        raw_source=canonical_raw_source(event),
        provenance_path=provenance_path,
        ambiguity_flag=False,
        timestamp=event_timestamp(event),
        entity_references=None,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/evals/capability/test_flatten.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Verify quality gates**

Run: `mypy . && ruff check .`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add evals/capability/flatten.py tests/evals/capability/test_flatten.py
git commit -m "Add generic event flattener for capability spike Path B."
```

---

### Task 3: Path B bundle builder

**Files:**
- Create: `evals/capability/bundle.py`
- Test: `tests/evals/capability/test_bundle.py`

**Interfaces:**
- Consumes: `flatten_event_to_fact`, `resolve_provenance_path` from Task 2.
- Produces: `build_spike_bundle(events: Sequence[Mapping[str, Any]], *, anchor_time: datetime, anchor_host_id: str | None = None, window_seconds: int = DEFAULT_CORRELATION_WINDOW_SECONDS) -> EvidenceBundle`.

**Critical constraint:** this MUST call `filter_events_in_window` and `filter_events_to_anchor_host` from `praetor.correlation` rather than reimplementing them. If windowing or host filtering drifts from Path A, part of the A/B delta becomes filtering differences masquerading as coverage differences — and that failure would be invisible in the results.

- [ ] **Step 1: Write the failing test**

```python
# tests/evals/capability/test_bundle.py
from __future__ import annotations

from datetime import UTC, datetime

from evals.capability.bundle import build_spike_bundle

ANCHOR = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def _event(
    *,
    record_id: str,
    event_id: int,
    host: str = "ws-01",
    utc: str = "2026-01-01 12:00:00.000",
    channel: str = "Microsoft-Windows-Sysmon/Operational",
) -> dict[str, object]:
    return {
        "EventID": event_id,
        "Channel": channel,
        "EventRecordID": record_id,
        "Computer": host,
        "UtcTime": utc,
        "EventData": {"Image": r"C:\Windows\System32\cmd.exe"},
    }


def test_includes_event_types_correlation_rejects() -> None:
    events = [
        _event(record_id="1", event_id=3),
        _event(record_id="2", event_id=11),
        _event(record_id="3", event_id=13),
    ]
    bundle = build_spike_bundle(events, anchor_time=ANCHOR)
    assert len(bundle.facts) == 3


def test_events_outside_window_excluded() -> None:
    events = [
        _event(record_id="1", event_id=1),
        _event(record_id="2", event_id=1, utc="2026-01-01 13:00:00.000"),
    ]
    bundle = build_spike_bundle(events, anchor_time=ANCHOR, window_seconds=300)
    assert len(bundle.facts) == 1
    assert bundle.facts[0].source_event_reference.endswith(":1:1")


def test_events_from_other_hosts_excluded() -> None:
    events = [
        _event(record_id="1", event_id=1, host="ws-01"),
        _event(record_id="2", event_id=1, host="ws-02"),
    ]
    bundle = build_spike_bundle(events, anchor_time=ANCHOR, anchor_host_id="ws-01")
    assert len(bundle.facts) == 1
    assert bundle.facts[0].normalized_fields["host_id"] == "ws-01"


def test_provenance_paths_derived_per_source() -> None:
    events = [
        _event(record_id="1", event_id=3),
        _event(record_id="2", event_id=4624, channel="Security"),
    ]
    bundle = build_spike_bundle(events, anchor_time=ANCHOR)
    paths = {fact.provenance_path for fact in bundle.facts}
    assert paths == {"sysmon_event_log", "windows_security_log"}


def test_empty_input_produces_empty_bundle() -> None:
    bundle = build_spike_bundle([], anchor_time=ANCHOR)
    assert bundle.facts == []


def test_undatable_events_are_skipped_not_fatal() -> None:
    events = [
        _event(record_id="1", event_id=1),
        {"EventID": 1, "Channel": "X", "EventRecordID": "2", "Computer": "ws-01"},
    ]
    bundle = build_spike_bundle(events, anchor_time=ANCHOR)
    assert len(bundle.facts) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/evals/capability/test_bundle.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'evals.capability.bundle'`

- [ ] **Step 3: Write minimal implementation**

```python
# evals/capability/bundle.py
"""Path B bundle assembly for the capability spike.

Windowing and anchor-host filtering reuse the real correlation helpers so the
ONLY difference between Path A and Path B is event-type coverage. Do not
reimplement either filter here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.correlation._event_fields import event_timestamp
from praetor.correlation.host_isolation import filter_events_to_anchor_host
from praetor.correlation.window import (
    DEFAULT_CORRELATION_WINDOW_SECONDS,
    filter_events_in_window,
)

from evals.capability.flatten import flatten_event_to_fact, resolve_provenance_path


def _datable(events: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Drop events without a parseable timestamp or record id."""
    usable: list[Mapping[str, Any]] = []
    for event in events:
        try:
            event_timestamp(event)
        except (ValueError, TypeError):
            continue
        usable.append(event)
    return usable


def build_spike_bundle(
    events: Sequence[Mapping[str, Any]],
    *,
    anchor_time: datetime,
    anchor_host_id: str | None = None,
    window_seconds: int = DEFAULT_CORRELATION_WINDOW_SECONDS,
) -> EvidenceBundle:
    """Build an all-event-type bundle scoped exactly as correlation would."""
    windowed = filter_events_in_window(
        _datable(events),
        anchor_time=anchor_time,
        window_seconds=window_seconds,
        timestamp_of=event_timestamp,
    )
    if anchor_host_id is not None:
        windowed = filter_events_to_anchor_host(
            windowed, anchor_host_id=anchor_host_id
        )

    facts: list[EvidenceFact] = []
    for event in windowed:
        try:
            facts.append(
                flatten_event_to_fact(
                    event, provenance_path=resolve_provenance_path(event)
                )
            )
        except (ValueError, TypeError):
            continue
    return EvidenceBundle(facts=facts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/evals/capability/test_bundle.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Verify quality gates**

Run: `mypy . && ruff check .`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add evals/capability/bundle.py tests/evals/capability/test_bundle.py
git commit -m "Add Path B bundle builder reusing correlation window and host filters."
```

---

### Task 4: Observation record and two-path runner

**Files:**
- Create: `evals/capability/runner.py`
- Test: `tests/evals/capability/test_runner.py`

**Interfaces:**
- Consumes: `Anchor` (Task 1), `build_spike_bundle` (Task 3).
- Produces: `Observation` (frozen dataclass: `anchor_id: str`, `expected_class: str`, `path: str`, `run_index: int`, `proposed_disposition: str | None`, `final_disposition: str | None`, `fault_flags: tuple[str, ...]`, `citation_count: int`, `bundle_fact_count: int`, `citations_resolved: bool`, `error: str | None`); `PATH_A: str`; `PATH_B: str`; `run_anchor(...) -> list[Observation]`; `open_spike_store(db_path: Path) -> StateStore`.

**Note on reading the judgment:** `IntakeResult` does not expose `ModelJudgment` directly. It is reached via `result.edict.model_judgment` (`src/praetor/contracts/edict.py:27`). `result.edict` is `None` when the attempt aborted or correlation failed, so every access must be guarded.

- [ ] **Step 1: Write the failing test**

```python
# tests/evals/capability/test_runner.py
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from praetor.contracts.disposition import Disposition
from praetor.judgment.fake_provider import FakeProvider

from evals.capability.corpus import Anchor
from evals.capability.runner import (
    PATH_A,
    PATH_B,
    Observation,
    open_spike_store,
    run_anchor,
)

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/evals/capability/test_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'evals.capability.runner'`

- [ ] **Step 3: Write minimal implementation**

```python
# evals/capability/runner.py
"""Two-path anchor execution for the capability spike.

Path A uses real ``correlate_telemetry`` (Sysmon EventID 1 + Security 4624
only). Path B uses a harness-built all-event-type bundle. Everything
downstream runs for real on both paths.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from praetor.auth.principal import Principal
from praetor.auth.verifier import PrincipalMapVerifier
from praetor.config.activation import activate_org_config
from praetor.correlation.host_isolation import resolve_anchor_host_id
from praetor.engine.orchestrator import (
    SucceedingStampBackend,
    process_alert_intake,
)
from praetor.judgment.provider import JudgmentProvider
from praetor.metrics.events import OutcomeMatrixFaultFlag
from praetor.state.store import StateStore, open_state_store

from evals.capability.bundle import build_spike_bundle
from evals.capability.corpus import Anchor

PATH_A = "correlation"
PATH_B = "flattened"

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLE_CONFIG = _REPO_ROOT / "configs" / "example_org.yaml"
_SOC_LEAD_TOKEN = "soc-lead-token"


@dataclass(frozen=True)
class Observation:
    anchor_id: str
    expected_class: str
    path: str
    run_index: int
    proposed_disposition: str | None
    final_disposition: str | None
    fault_flags: tuple[str, ...]
    citation_count: int
    bundle_fact_count: int
    citations_resolved: bool
    error: str | None = None


def open_spike_store(db_path: Path) -> StateStore:
    """Open a state store with the example org config activated."""
    store = open_state_store(db_path)
    activate_org_config(
        store,
        _EXAMPLE_CONFIG,
        token=_SOC_LEAD_TOKEN,
        verifier=PrincipalMapVerifier(
            {_SOC_LEAD_TOKEN: Principal(identity="spike-soc-lead", role="soc_lead")}
        ),
    )
    return store


def _split_events(
    events: Sequence[Mapping[str, Any]],
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    sysmon: list[Mapping[str, Any]] = []
    security: list[Mapping[str, Any]] = []
    for event in events:
        channel = str(event.get("Channel", "")).lower()
        if "sysmon" in channel:
            sysmon.append(event)
        elif channel.startswith("security"):
            security.append(event)
    return sysmon, security


def _observe(
    *,
    anchor: Anchor,
    path: str,
    run_index: int,
    result: Any,
    bundle_fact_count: int,
) -> Observation:
    edict = getattr(result, "edict", None)
    fault_flags = tuple(str(flag) for flag in getattr(result, "fault_flags", ()))
    proposed: str | None = None
    citation_count = 0
    if edict is not None:
        proposed = edict.model_judgment.proposed_disposition.value
        citation_count = len(edict.model_judgment.cited_evidence_refs)
    final = getattr(result, "disposition", None)
    return Observation(
        anchor_id=anchor.anchor_id,
        expected_class=anchor.expected_class,
        path=path,
        run_index=run_index,
        proposed_disposition=proposed,
        final_disposition=final.value if final is not None else None,
        fault_flags=fault_flags,
        citation_count=citation_count,
        bundle_fact_count=bundle_fact_count,
        citations_resolved=(
            OutcomeMatrixFaultFlag.INVALID_MODEL_CITATION.value not in fault_flags
        ),
    )


def run_anchor(
    store: StateStore,
    *,
    anchor: Anchor,
    events: Sequence[Mapping[str, Any]],
    provider: JudgmentProvider,
    runs: int = 3,
    window_seconds: int | None = None,
) -> list[Observation]:
    """Run one anchor through both paths ``runs`` times each."""
    sysmon, security = _split_events(events)
    anchor_host = resolve_anchor_host_id(
        sysmon_events=sysmon,
        security_events=security,
        anchor_time=anchor.anchor_time,
    )
    bundle_kwargs: dict[str, Any] = {
        "anchor_time": anchor.anchor_time,
        "anchor_host_id": anchor_host,
    }
    if window_seconds is not None:
        bundle_kwargs["window_seconds"] = window_seconds
    spike_bundle = build_spike_bundle(events, **bundle_kwargs)

    # Both counts are deterministic given (events, anchor), so compute once.
    fact_counts = {
        PATH_A: _path_a_fact_count(sysmon, security, anchor, anchor_host),
        PATH_B: len(spike_bundle.facts),
    }

    observations: list[Observation] = []
    stamp_backend = SucceedingStampBackend()

    for run_index in range(runs):
        for path in (PATH_A, PATH_B):
            # Unique identity per (anchor, path, run) so idempotency never
            # collapses two observations into one decision.
            alert_identity = (
                f"spike-{anchor.anchor_id}-{path}-{run_index}-{uuid.uuid4().hex[:8]}"
            )
            intake_kwargs: dict[str, Any] = {
                "judgment_provider": provider,
                "stamp_backend": stamp_backend,
                "alert_identity": alert_identity,
                # Required for Path A: without this, orchestrator defaults to
                # datetime.now(UTC) and historical capture events miss the window.
                "anchor_time": anchor.anchor_time,
            }
            if path == PATH_A:
                intake_kwargs["sysmon_events"] = sysmon
                intake_kwargs["security_events"] = security
            else:
                intake_kwargs["evidence_bundle"] = spike_bundle
            bundle_fact_count = fact_counts[path]

            try:
                result = process_alert_intake(store, **intake_kwargs)
            except (RuntimeError, ValueError) as exc:
                observations.append(
                    Observation(
                        anchor_id=anchor.anchor_id,
                        expected_class=anchor.expected_class,
                        path=path,
                        run_index=run_index,
                        proposed_disposition=None,
                        final_disposition=None,
                        fault_flags=(),
                        citation_count=0,
                        bundle_fact_count=bundle_fact_count,
                        citations_resolved=False,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
                continue

            observations.append(
                _observe(
                    anchor=anchor,
                    path=path,
                    run_index=run_index,
                    result=result,
                    bundle_fact_count=bundle_fact_count,
                )
            )

    return observations


def _path_a_fact_count(
    sysmon: Sequence[Mapping[str, Any]],
    security: Sequence[Mapping[str, Any]],
    anchor: Anchor,
    anchor_host: str | None,
) -> int:
    """Count facts correlation would build, for A/B coverage comparison."""
    from praetor.correlation import correlate_telemetry

    correlated = correlate_telemetry(
        sysmon_events=list(sysmon),
        security_events=list(security),
        anchor_time=anchor.anchor_time,
        anchor_host_id=anchor_host,
    )
    return len(correlated.bundle.facts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/evals/capability/test_runner.py -v`
Expected: PASS (4 tests)

If `test_proposed_disposition_is_recorded` fails with `proposed_disposition is None`, the attempt aborted before an edict was written — print `result.attempt_aborted` and `result.fault_flags` to see why. `FakeProvider`'s skeleton citations may not resolve against the spike bundle, which yields `invalid_model_citation` and an `escalate` **final** disposition, but `model_judgment.proposed_disposition` is still recorded on the edict. That is the intended split and is exactly what the spike measures.

- [ ] **Step 5: Verify quality gates**

Run: `mypy . && ruff check .`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add evals/capability/runner.py tests/evals/capability/test_runner.py
git commit -m "Add two-path anchor runner recording model judgment and gate outcome."
```

---

### Task 5: Scoring, A/B delta, and confound check

**Files:**
- Create: `evals/capability/score.py`
- Test: `tests/evals/capability/test_score.py`

**Interfaces:**
- Consumes: `Observation`, `PATH_A`, `PATH_B` (Task 4).
- Produces: `PathScore` (frozen dataclass: `path: str`, `scored: int`, `correct: int`, `excluded_empty_bundle: int`, `citation_resolution_rate: float | None`, `unstable_anchors: tuple[str, ...]`); `score_path(observations, *, path) -> PathScore`; `ab_delta(observations) -> dict[str, tuple[str, str]]`; `confound_check(anchor_events) -> dict[str, bool]`.

**Scoring rule:** malicious is correct when `proposed_disposition` is `escalate` or `auto_contain`; benign is correct when it is `standard_review`. Observations with no `proposed_disposition` (empty bundle, aborted attempt, provider error) are **excluded from scoring and counted separately** — they are correlation findings, not judgment findings.

- [ ] **Step 1: Write the failing test**

```python
# tests/evals/capability/test_score.py
from __future__ import annotations

from evals.capability.runner import PATH_A, PATH_B, Observation
from evals.capability.score import ab_delta, confound_check, score_path


def _obs(
    anchor_id: str,
    expected_class: str,
    path: str,
    proposed: str | None,
    *,
    run_index: int = 0,
    citations_resolved: bool = True,
    facts: int = 3,
) -> Observation:
    return Observation(
        anchor_id=anchor_id,
        expected_class=expected_class,
        path=path,
        run_index=run_index,
        proposed_disposition=proposed,
        final_disposition="escalate",
        fault_flags=(),
        citation_count=2,
        bundle_fact_count=facts,
        citations_resolved=citations_resolved,
    )


def test_malicious_correct_on_escalate_or_auto_contain() -> None:
    observations = [
        _obs("m1", "malicious", PATH_B, "escalate"),
        _obs("m2", "malicious", PATH_B, "auto_contain"),
    ]
    score = score_path(observations, path=PATH_B)
    assert score.scored == 2
    assert score.correct == 2


def test_malicious_incorrect_on_standard_review() -> None:
    observations = [_obs("m1", "malicious", PATH_B, "standard_review")]
    score = score_path(observations, path=PATH_B)
    assert score.scored == 1
    assert score.correct == 0


def test_benign_correct_only_on_standard_review() -> None:
    observations = [
        _obs("b1", "benign", PATH_B, "standard_review"),
        _obs("b2", "benign", PATH_B, "escalate"),
    ]
    score = score_path(observations, path=PATH_B)
    assert score.scored == 2
    assert score.correct == 1


def test_missing_judgment_excluded_not_counted_wrong() -> None:
    observations = [
        _obs("m1", "malicious", PATH_A, None),
        _obs("m2", "malicious", PATH_A, "escalate"),
    ]
    score = score_path(observations, path=PATH_A)
    assert score.scored == 1
    assert score.correct == 1
    assert score.excluded_empty_bundle == 1


def test_other_paths_are_ignored() -> None:
    observations = [
        _obs("m1", "malicious", PATH_A, "standard_review"),
        _obs("m1", "malicious", PATH_B, "escalate"),
    ]
    assert score_path(observations, path=PATH_B).correct == 1
    assert score_path(observations, path=PATH_A).correct == 0


def test_unstable_anchor_detected_across_runs() -> None:
    observations = [
        _obs("m1", "malicious", PATH_B, "escalate", run_index=0),
        _obs("m1", "malicious", PATH_B, "standard_review", run_index=1),
        _obs("m2", "malicious", PATH_B, "escalate", run_index=0),
        _obs("m2", "malicious", PATH_B, "escalate", run_index=1),
    ]
    score = score_path(observations, path=PATH_B)
    assert score.unstable_anchors == ("m1",)


def test_citation_resolution_rate() -> None:
    observations = [
        _obs("m1", "malicious", PATH_B, "escalate", citations_resolved=True),
        _obs("m2", "malicious", PATH_B, "escalate", citations_resolved=False),
    ]
    score = score_path(observations, path=PATH_B)
    assert score.citation_resolution_rate == 0.5


def test_ab_delta_classifies_each_anchor() -> None:
    observations = [
        _obs("m1", "malicious", PATH_A, "standard_review"),
        _obs("m1", "malicious", PATH_B, "escalate"),
        _obs("m2", "malicious", PATH_A, "escalate"),
        _obs("m2", "malicious", PATH_B, "escalate"),
        _obs("m3", "malicious", PATH_A, "standard_review"),
        _obs("m3", "malicious", PATH_B, "standard_review"),
        _obs("m4", "malicious", PATH_A, "escalate"),
        _obs("m4", "malicious", PATH_B, "standard_review"),
    ]
    delta = ab_delta(observations)
    assert delta["m1"] == ("wrong", "right")
    assert delta["m2"] == ("right", "right")
    assert delta["m3"] == ("wrong", "wrong")
    assert delta["m4"] == ("right", "wrong")


def test_confound_check_flags_perfectly_separating_host() -> None:
    anchor_events = {
        "m1": ("malicious", {"host_id": "attacker-box", "event_count": 5}),
        "m2": ("malicious", {"host_id": "attacker-box", "event_count": 6}),
        "b1": ("benign", {"host_id": "clean-box", "event_count": 5}),
        "b2": ("benign", {"host_id": "clean-box", "event_count": 6}),
    }
    flags = confound_check(anchor_events)
    assert flags["host_id"] is True
    assert flags["event_count"] is False


def test_confound_check_passes_on_shared_hosts() -> None:
    anchor_events = {
        "m1": ("malicious", {"host_id": "ws-01"}),
        "b1": ("benign", {"host_id": "ws-01"}),
    }
    assert confound_check(anchor_events)["host_id"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/evals/capability/test_score.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'evals.capability.score'`

- [ ] **Step 3: Write minimal implementation**

```python
# evals/capability/score.py
"""Scoring for the capability spike.

Scores ``ModelJudgment.proposed_disposition`` only. PolicyGate output is
recorded elsewhere but never folded into the capability number: the gate
controls authority, not judgment quality.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from evals.capability.corpus import BENIGN, MALICIOUS
from evals.capability.runner import PATH_A, PATH_B, Observation

_MALICIOUS_CORRECT = frozenset({"escalate", "auto_contain"})
_BENIGN_CORRECT = frozenset({"standard_review"})


@dataclass(frozen=True)
class PathScore:
    path: str
    scored: int
    correct: int
    excluded_empty_bundle: int
    citation_resolution_rate: float | None
    unstable_anchors: tuple[str, ...]

    @property
    def separation_rate(self) -> float | None:
        if self.scored == 0:
            return None
        return self.correct / self.scored


def _is_correct(expected_class: str, proposed: str) -> bool:
    if expected_class == MALICIOUS:
        return proposed in _MALICIOUS_CORRECT
    if expected_class == BENIGN:
        return proposed in _BENIGN_CORRECT
    return False


def score_path(observations: Sequence[Observation], *, path: str) -> PathScore:
    """Score one path's observations against their labels."""
    subset = [obs for obs in observations if obs.path == path]
    scorable = [obs for obs in subset if obs.proposed_disposition is not None]
    excluded = len(subset) - len(scorable)

    correct = sum(
        1
        for obs in scorable
        if _is_correct(obs.expected_class, str(obs.proposed_disposition))
    )

    resolution_rate: float | None = None
    if scorable:
        resolution_rate = sum(
            1 for obs in scorable if obs.citations_resolved
        ) / len(scorable)

    by_anchor: dict[str, set[str]] = defaultdict(set)
    for obs in scorable:
        by_anchor[obs.anchor_id].add(str(obs.proposed_disposition))
    unstable = tuple(
        sorted(anchor for anchor, values in by_anchor.items() if len(values) > 1)
    )

    return PathScore(
        path=path,
        scored=len(scorable),
        correct=correct,
        excluded_empty_bundle=excluded,
        citation_resolution_rate=resolution_rate,
        unstable_anchors=unstable,
    )


def _majority_correct(observations: Sequence[Observation]) -> str:
    """Return 'right', 'wrong', or 'excluded' for one anchor on one path."""
    scorable = [obs for obs in observations if obs.proposed_disposition is not None]
    if not scorable:
        return "excluded"
    hits = sum(
        1
        for obs in scorable
        if _is_correct(obs.expected_class, str(obs.proposed_disposition))
    )
    return "right" if hits * 2 > len(scorable) else "wrong"


def ab_delta(observations: Sequence[Observation]) -> dict[str, tuple[str, str]]:
    """Map anchor_id to (path_a_outcome, path_b_outcome).

    ('wrong', 'right') means the model can judge but correlation starved it —
    fix coverage. ('wrong', 'wrong') means judgment failed with full evidence —
    fix prompt, config, or model.
    """
    grouped: dict[str, dict[str, list[Observation]]] = defaultdict(
        lambda: {PATH_A: [], PATH_B: []}
    )
    for obs in observations:
        if obs.path in (PATH_A, PATH_B):
            grouped[obs.anchor_id][obs.path].append(obs)

    return {
        anchor_id: (
            _majority_correct(paths[PATH_A]),
            _majority_correct(paths[PATH_B]),
        )
        for anchor_id, paths in sorted(grouped.items())
    }


def confound_check(
    anchor_features: Mapping[str, tuple[str, Mapping[str, Any]]],
) -> dict[str, bool]:
    """Flag features that perfectly separate malicious from benign anchors.

    A True value means the corpus is contaminated: a trivial heuristic could
    score well without judging anything.
    """
    by_feature: dict[str, dict[str, set[Any]]] = defaultdict(
        lambda: {MALICIOUS: set(), BENIGN: set()}
    )
    for expected_class, features in anchor_features.values():
        if expected_class not in (MALICIOUS, BENIGN):
            continue
        for name, value in features.items():
            by_feature[name][expected_class].add(value)

    flags: dict[str, bool] = {}
    for name, classes in by_feature.items():
        malicious_values = classes[MALICIOUS]
        benign_values = classes[BENIGN]
        both_present = bool(malicious_values) and bool(benign_values)
        flags[name] = both_present and not (malicious_values & benign_values)
    return flags
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/evals/capability/test_score.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Verify quality gates**

Run: `mypy . && ruff check .`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add evals/capability/score.py tests/evals/capability/test_score.py
git commit -m "Add capability spike scoring, A/B delta, and confound check."
```

---

### Task 6: CLI entry point with offline default

**Files:**
- Create: `evals/capability_spike.py`
- Test: `tests/evals/capability/test_cli.py`
- Modify: `docs/eval_gates.md` (append a non-gating section)

**Interfaces:**
- Consumes: everything from Tasks 1–5.
- Produces: `SPIKE_ENV_FLAG: str`; `spike_enabled() -> bool`; `resolve_spike_provider() -> JudgmentProvider | None`; `load_capture_events(path: Path) -> list[Mapping[str, Any]]`; `main() -> int`.

**Safety requirement:** with no env flag and no API key, `main()` must exit 0 with a clear skip message and make zero network calls. This file must never be imported by `evals/harness.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/evals/capability/test_cli.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/evals/capability/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'evals.capability_spike'`

- [ ] **Step 3: Write minimal implementation**

```python
# evals/capability_spike.py
"""Judgment capability spike CLI (non-gating, opt-in, network-using).

Measures whether the single-shot judgment layer separates malicious from
benign telemetry, and how much of any failure is caused by correlation's
two-event-type coverage limit.

NOT a CI gate. Never import this from ``evals/harness.py``.

Enable a live run::

    set PRAETOR_CAPABILITY_SPIKE=1
    set PRAETOR_GEMINI_API_KEY=<key>
    python -m evals.capability_spike --manifest <manifest.yaml> \
        --capture <capture.jsonl> --out <results.jsonl>
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from praetor.judgment.provider import JudgmentProvider
from praetor.judgment.vertex_provider import DEFAULT_GEMINI_MODEL, VertexProvider

from evals.capability.corpus import load_anchor_manifest
from evals.capability.runner import (
    PATH_A,
    PATH_B,
    Observation,
    open_spike_store,
    run_anchor,
)
from evals.capability.score import ab_delta, score_path

SPIKE_ENV_FLAG = "PRAETOR_CAPABILITY_SPIKE"
GEMINI_API_KEY_ENV = "PRAETOR_GEMINI_API_KEY"
GOOGLE_API_KEY_ENV = "GOOGLE_API_KEY"
GEMINI_MODEL_ENV = "PRAETOR_GEMINI_MODEL"


def spike_enabled() -> bool:
    return os.environ.get(SPIKE_ENV_FLAG, "").strip().lower() in {"1", "true", "yes"}


def _resolve_api_key() -> str | None:
    for env_name in (GEMINI_API_KEY_ENV, GOOGLE_API_KEY_ENV):
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    return None


def resolve_spike_provider() -> JudgmentProvider | None:
    """Return a live provider only when explicitly enabled and configured."""
    if not spike_enabled():
        return None
    api_key = _resolve_api_key()
    if api_key is None:
        return None
    model_name = os.environ.get(GEMINI_MODEL_ENV, DEFAULT_GEMINI_MODEL).strip()
    return VertexProvider(
        api_key=api_key, model_name=model_name or DEFAULT_GEMINI_MODEL
    )


def load_capture_events(path: Path) -> list[Mapping[str, Any]]:
    """Read a JSON-lines telemetry capture, skipping blank/malformed lines."""
    events: list[Mapping[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, Mapping):
                events.append(parsed)
    return events


def _summarize(observations: Sequence[Observation]) -> str:
    lines: list[str] = ["", "=== capability spike summary ==="]
    for path in (PATH_A, PATH_B):
        score = score_path(observations, path=path)
        rate = score.separation_rate
        rate_text = "n/a" if rate is None else f"{rate:.2%}"
        resolution = score.citation_resolution_rate
        resolution_text = "n/a" if resolution is None else f"{resolution:.2%}"
        lines.append(
            f"path={path} scored={score.scored} correct={score.correct} "
            f"separation={rate_text} citations_resolved={resolution_text} "
            f"excluded_no_judgment={score.excluded_empty_bundle} "
            f"unstable={len(score.unstable_anchors)}"
        )

    lines.append("")
    lines.append("--- A/B delta (path_a, path_b) ---")
    buckets: dict[tuple[str, str], list[str]] = {}
    for anchor_id, pair in ab_delta(observations).items():
        buckets.setdefault(pair, []).append(anchor_id)
    for pair, anchors in sorted(buckets.items()):
        lines.append(f"{pair[0]:>8} / {pair[1]:<8} n={len(anchors):<3} {', '.join(anchors)}")

    lines.append("")
    lines.append(
        "Read ('wrong','right') as coverage-limited; ('wrong','wrong') as "
        "judgment-limited. Gate columns in the JSONL are recorded, not scored."
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Praetor judgment capability spike")
    parser.add_argument("--manifest", type=Path, help="labeled anchor manifest YAML")
    parser.add_argument("--capture", type=Path, help="JSON-lines telemetry capture")
    parser.add_argument("--out", type=Path, help="JSONL output path")
    parser.add_argument("--runs", type=int, default=3, help="runs per anchor per path")
    args = parser.parse_args(argv)

    provider = resolve_spike_provider()
    if provider is None:
        if not spike_enabled():
            print(f"capability spike skipped: {SPIKE_ENV_FLAG} not enabled")
        else:
            print(
                "capability spike skipped: no API key in "
                f"{GEMINI_API_KEY_ENV} or {GOOGLE_API_KEY_ENV}"
            )
        return 0

    if args.manifest is None or args.capture is None:
        print("capability spike skipped: --manifest and --capture are required")
        return 0

    manifest = load_anchor_manifest(args.manifest)
    events = load_capture_events(args.capture)
    print(
        f"capture={manifest.capture_id} anchors={len(manifest.anchors)} "
        f"events={len(events)} runs={args.runs}"
    )

    observations: list[Observation] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        store = open_spike_store(Path(tmpdir) / "spike.db")
        try:
            for anchor in manifest.anchors:
                observations.extend(
                    run_anchor(
                        store,
                        anchor=anchor,
                        events=events,
                        provider=provider,
                        runs=args.runs,
                    )
                )
                print(f"  ran anchor={anchor.anchor_id}")
        finally:
            store.conn.close()

    if args.out is not None:
        with args.out.open("w", encoding="utf-8") as handle:
            for obs in observations:
                handle.write(json.dumps(asdict(obs), sort_keys=True) + "\n")
        print(f"wrote {len(observations)} observations to {args.out}")

    print(_summarize(observations))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Then append to `docs/eval_gates.md`:

```markdown
## Non-gating: judgment capability spike

`python -m evals.capability_spike --manifest <m.yaml> --capture <c.jsonl> --out <r.jsonl>`

Measures whether the single-shot judgment layer separates malicious from benign
telemetry, and how much of any failure is caused by correlation's two-event-type
coverage limit (Path A vs Path B).

**Not a CI gate.** Requires `PRAETOR_CAPABILITY_SPIKE=1` and a Gemini API key;
exits 0 with a skip message otherwise. Scores `ModelJudgment.proposed_disposition`
only — PolicyGate output is recorded but never scored, because the gate controls
authority rather than judgment quality.

Design: `docs/superpowers/specs/2026-08-01-capability-spike-design.md`
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/evals/capability/test_cli.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Verify the whole suite and gates are unaffected**

Run: `python -m pytest -q && mypy . && ruff check . && python -m evals.harness`
Expected: full suite passes (note: `tests/runtime/test_startup_guard.py::TestSingletonLock::test_two_subprocesses_race_only_one_wins` is a known pre-existing flake unrelated to this work — if it fails, re-run it alone to confirm), `evals.harness` still reports 33 scenarios green.

Run: `python -m evals.capability_spike`
Expected: exits 0 printing `capability spike skipped: PRAETOR_CAPABILITY_SPIKE not enabled`, with no network call.

- [ ] **Step 6: Commit**

```bash
git add evals/capability_spike.py tests/evals/capability/test_cli.py docs/eval_gates.md
git commit -m "Add capability spike CLI with offline-safe default."
```

---

## After the plan

The spike is then **run**, not built. That is a separate activity requiring:

1. A chosen OTRF capture (APT29 Day 1 host recommended), verified for attack steps + same-host benign density.
2. A committed anchor manifest — **after** amendment A2/A3 schema lands — labels from plan-step ancestry; `unresolved` for unchained steps; `emulation_steps_total` / `unchained_steps` set; committed **before** the first provider call.
3. `PRAETOR_CAPABILITY_SPIKE=1` and a working Gemini API key.

Both items 1 and 2 are the user's, by agreement. The confound check from Task 5 should be run against the finished manifest before any live run. Read A≈B ties via the pre-registered citation-mix thresholds, not post-hoc.

**Interpreting results:** a clean negative is a successful spike. If Path B is no better than Path A, use citation mix to choose prompt vs "coverage not bottleneck." If Path B is materially better, the generic flattener is a validated prototype for a production generic normalizer — which is then a `docs/decisions.md` decision, not a quiet promotion. Strong scores on APT29 are a floor test under thin lab benign.
