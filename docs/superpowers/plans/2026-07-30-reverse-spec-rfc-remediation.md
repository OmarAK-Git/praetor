# Reverse-Spec RFC Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the observability and test-coverage gaps confirmed real during manual verification of `5570cfdd-02d7-4a8f-8867-31d8bacc829b-rfcs.md` (a reverse-spec review over `AS_BUILT.md` / `DEBT_LEDGER.md`), without touching the parts of that review that were wrong.

**Architecture:** Six small, independent, additive changes. None alter disposition/authorization logic (PolicyGate, stamp/ledger ordering, never-contain matching semantics all stay exactly as they are). Each task adds either a log line, a metric, a health alert, or a test that was missing.

**Tech Stack:** Python 3.11+, pydantic 2, SQLite (stdlib `sqlite3`), pytest.

## Global Constraints

- No task may change `evaluate_policy_gate` authorization outcomes, disposition semantics, or the stamp-before-critical_transaction ordering (DEC-053) — verified deliberate, see Verification Notes.
- No task may add a new `OutcomeMatrixFaultFlag` enum member — that triggers the Outcome Matrix completeness gate (4 wiring sites + a mandatory `evals/` harness scenario) and none of this work changes any disposition outcome, so none of it qualifies as an Outcome Matrix fault flag.
- No task may implement revocation-feed rotation/segmentation — `tests/docs/test_docs.py::test_contracts_documents_feed_v2_boundaries` and `test_operator_runbook_required_topics` pin the phrases "no rotation machinery" and "segmented rotation is deferred" as *required* doc content. Rotation is a contractually-frozen v1 non-goal (DEBT-082, INFO), not a bug.
- `MetricsCollector` is documented single-writer/thread-unsafe (`src/praetor/metrics/collector.py:32`) — new counters follow the same simple-increment style as existing ones, no locking.
- Run `ruff check .` and `mypy .` after each task; run the full task's test file (not the whole suite) after each Step, and the whole suite once at the end of the plan.

## Verification Notes (why RFC-001 and the raw RFC-002 framing are excluded)

- **RFC-001** (invert stamp/critical_transaction order) is **rejected, not implemented**. `docs/spec.md:149` ("Stamping precedes ledger write"), `docs/architecture.md:56/74`, `docs/contracts.md:312/644`, and `docs/operator_runbook.md:49-52` all independently pin the current order as **DEC-053**, and `docs/decisions.md:169-172` records it was refined again in DEC-060. V2-008 already closed a "DEC-053 fidelity gap." Inverting the order would recreate the exact hazard DEC-053 exists to prevent: a committed ledger/directive record that has to be revoked after the fact if the external ticket call fails. The RFC also conflates the ticket "stamp" (`execute_stamp` in `src/praetor/tickets/stamp.py`) with actual containment actuation; per `AS_BUILT.md` §0, Praetor never calls SOAR/EDR directly, so there is no "SOAR flagged as AUTO_CONTAIN" state to desync. This rejection should be treated as final unless a project owner overturns DEC-053 explicitly (that would be a `docs/decisions.md` change, not a code change).
- **RFC-002**'s "health alerts get silently suppressed by JSONL exhaustion" claim is false — `src/praetor/alerts/system_health.py` and `src/praetor/revocation/{feed,exporter}.py` are already fully separate sinks/tables, and `_transition_feed_unhealthy` (`src/praetor/revocation/exporter.py:107-112`) already emits a durable `SystemHealthAlert`. Only the real kernel (DEBT-042, no size bound on the feed file) is carried into Task 5, scoped to an operator warning, not rotation.
- **RFC-003**'s "halt on malformed never-contain" is downgraded further than the review's own WEAKEN: `permanent_never_contain_entries`/`emergency_entry_as_never_contain` already validate every entry before it reaches `target_in_never_contain_list`/`directive_matches_entry` on the production read path (`read_live_never_contain_entries`, `src/praetor/config/state.py:410-418`), so the `except PreflightError` skip branches in `src/praetor/config/live.py` are defensive dead code on the happy path, not a live security gap. Task 1 makes that dead-code path observable instead of adding a new global-halt failure mode (which would itself be a self-inflicted denial of automated containment).
- **RFC-005**'s S1 severity is rejected: exemplars are advisory-only prompt text (`judgment/excerpt.py`); PolicyGate re-authorizes every containment decision independent of what the LLM proposes (AS_BUILT invariant #21), so a poisoned precedent cannot itself authorize unauthorized `auto_contain`. The real sharp edge (compromised annotation tokens) is DEBT-041 (no production `TokenVerifier`), already tracked separately. Task 4 keeps only the real, narrow fix: log instead of silently drop on a malformed ledger edict during precedent fetch.
- **RFC-006** overstates DEBT-072: `src/praetor/engine/citations.py` is a 15-line pass-through to `src/praetor/evidence/citations.py`, which already has direct tests (`tests/evidence/test_citation_validation.py`). The 822-LOC orchestrator does not contain citation business logic. Task 3 adds the one missing thing: a direct test of the adapter itself.

---

### Task 1: Log visibility on never-contain matcher skip branches (RFC-003, rescoped)

**Files:**
- Modify: `src/praetor/config/live.py:78-88` (`directive_matches_entry`), `src/praetor/config/live.py:106-120` (`target_in_never_contain_list`)
- Test: `tests/config/test_live_never_contain_matching.py` (new)

**Interfaces:**
- Consumes: nothing new.
- Produces: no signature changes — both functions keep their existing return types and skip-and-continue behavior. Only a module-level `logging.Logger` named `_logger` is added to `config/live.py`.

- [ ] **Step 1: Write the failing test**

```python
"""Regression coverage for config.live never-contain matcher skip visibility."""

from __future__ import annotations

import logging

from praetor.config.live import directive_matches_entry, target_in_never_contain_list
from praetor.contracts.containment import ContainmentDirective, ContainmentTargetType


def _directive() -> ContainmentDirective:
    return ContainmentDirective.model_construct(
        target_type=ContainmentTargetType.HOST,
        target_id="host-1",
    )


def test_target_in_never_contain_list_skips_malformed_entry_and_logs(
    caplog: "logging.LogCaptureFixture",
) -> None:
    malformed = {"target_type": "host"}  # missing target_id: fails canonicalization
    valid = {"target_type": "host", "target_id": "host-1"}

    with caplog.at_level(logging.WARNING, logger="praetor.config.live"):
        result = target_in_never_contain_list("host", "host-1", [malformed, valid])

    assert result is True
    assert any(
        "malformed never-contain entry" in record.message for record in caplog.records
    )


def test_target_in_never_contain_list_no_log_when_all_entries_valid(
    caplog: "logging.LogCaptureFixture",
) -> None:
    valid = {"target_type": "host", "target_id": "host-1"}

    with caplog.at_level(logging.WARNING, logger="praetor.config.live"):
        result = target_in_never_contain_list("host", "host-2", [valid])

    assert result is False
    assert caplog.records == []


def test_directive_matches_entry_returns_false_and_logs_on_malformed_entry(
    caplog: "logging.LogCaptureFixture",
) -> None:
    malformed = {"target_type": "host"}

    with caplog.at_level(logging.WARNING, logger="praetor.config.live"):
        result = directive_matches_entry(_directive(), malformed)

    assert result is False
    assert any(
        "malformed never-contain entry" in record.message for record in caplog.records
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/config/test_live_never_contain_matching.py -v`
Expected: FAIL — no `_logger`/warning is emitted yet, so `caplog.records` is empty in the first and third tests.

- [ ] **Step 3: Add the logger and warning calls**

In `src/praetor/config/live.py`, add near the top (after the existing imports, before `_SID_PATTERN`):

```python
import logging

_logger = logging.getLogger(__name__)
```

Update `directive_matches_entry`:

```python
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
```

Update `target_in_never_contain_list`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/config/test_live_never_contain_matching.py -v`
Expected: PASS (3/3)

- [ ] **Step 5: Commit**

```bash
git add src/praetor/config/live.py tests/config/test_live_never_contain_matching.py
git commit -m "config: log skipped malformed never-contain entries instead of silently dropping them"
```

---

### Task 2: Correlation unsupported-EventID metric (RFC-004)

**Files:**
- Modify: `src/praetor/metrics/events.py` (add `correlation_unsupported_event_id_total` field)
- Modify: `src/praetor/metrics/collector.py` (add counter + `record_correlation_unsupported_event_id`)
- Modify: `src/praetor/correlation/__init__.py` (thread optional `metrics` param through `correlate_telemetry`)
- Modify: `src/praetor/engine/orchestrator.py` (thread `metrics_collector` through `_resolve_intake_evidence_bundle` into `correlate_telemetry`)
- Test: `tests/metrics/test_metrics.py` (extend), `tests/correlation/test_correlation_metrics.py` (new)

**Interfaces:**
- Produces: `MetricsCollector.record_correlation_unsupported_event_id(self) -> None`; `MetricsSnapshot.correlation_unsupported_event_id_total: int`; `correlate_telemetry(..., metrics: MetricsCollector | None = None) -> CorrelationResult` (new keyword-only, defaulted — existing callers unaffected).

- [ ] **Step 1: Write the failing metrics-layer test**

Add to `tests/metrics/test_metrics.py` (open the file first to match its existing import/fixture style, then append):

```python
def test_record_correlation_unsupported_event_id_increments_snapshot() -> None:
    from praetor.metrics.collector import MetricsCollector

    collector = MetricsCollector()
    collector.record_correlation_unsupported_event_id()
    collector.record_correlation_unsupported_event_id()

    snap = collector.snapshot()
    assert snap.correlation_unsupported_event_id_total == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/metrics/test_metrics.py::test_record_correlation_unsupported_event_id_increments_snapshot -v`
Expected: FAIL with `AttributeError: 'MetricsCollector' object has no attribute 'record_correlation_unsupported_event_id'`

- [ ] **Step 3: Add the field, counter, and method**

In `src/praetor/metrics/events.py`, add the field to `MetricsSnapshot` (after `revocation_feed_unhealthy_transitions: int`):

```python
    revocation_feed_unhealthy_transitions: int
    correlation_unsupported_event_id_total: int
```

In `src/praetor/metrics/collector.py`, add to `__init__` (after `self._revocation_feed_unhealthy_transitions = 0`):

```python
        self._revocation_feed_unhealthy_transitions = 0
        self._correlation_unsupported_event_id_total = 0
```

Add the recorder method (after `record_revocation_feed_unhealthy_transition`):

```python
    def record_revocation_feed_unhealthy_transition(self) -> None:
        self._revocation_feed_unhealthy_transitions += 1

    def record_correlation_unsupported_event_id(self) -> None:
        """Record a telemetry event skipped because its EventID is unsupported.

        Distinguishes a schema-mismatch cause of an empty/short EvidenceBundle
        from genuinely empty telemetry, since both currently downgrade to the
        same ``correlation_failure`` disposition path.
        """
        self._correlation_unsupported_event_id_total += 1
```

Update `snapshot()` to include the new field (after `revocation_feed_unhealthy_transitions=...`):

```python
            revocation_feed_unhealthy_transitions=(
                self._revocation_feed_unhealthy_transitions
            ),
            correlation_unsupported_event_id_total=(
                self._correlation_unsupported_event_id_total
            ),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/metrics/test_metrics.py::test_record_correlation_unsupported_event_id_increments_snapshot -v`
Expected: PASS

- [ ] **Step 5: Write the failing correlation-wiring test**

Create `tests/correlation/test_correlation_metrics.py`:

```python
"""Coverage for the correlation-layer unsupported-EventID metric (RFC-004)."""

from __future__ import annotations

from datetime import UTC, datetime

from praetor.correlation import correlate_telemetry
from praetor.metrics.collector import MetricsCollector

ANCHOR = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)


def _sysmon_process_create(record_id: int) -> dict[str, object]:
    return {
        "EventID": 1,
        "System": {"EventRecordID": record_id, "Computer": "HOST-1"},
        "EventData": {
            "UtcTime": ANCHOR.isoformat(sep=" ", timespec="seconds"),
            "Image": r"C:\Windows\System32\cmd.exe",
            "CommandLine": "cmd.exe /c whoami",
        },
    }


def _sysmon_unsupported(record_id: int) -> dict[str, object]:
    event = _sysmon_process_create(record_id)
    event["EventID"] = 99  # not in SUPPORTED_SYSMON_EVENT_IDS
    return event


def test_correlate_telemetry_records_metric_for_unsupported_sysmon_event_id() -> None:
    metrics = MetricsCollector()

    result = correlate_telemetry(
        sysmon_events=[_sysmon_process_create(1), _sysmon_unsupported(2)],
        security_events=[],
        anchor_time=ANCHOR,
        metrics=metrics,
    )

    assert len(result.bundle.facts) == 1
    assert metrics.snapshot().correlation_unsupported_event_id_total == 1


def test_correlate_telemetry_without_metrics_collector_does_not_raise() -> None:
    result = correlate_telemetry(
        sysmon_events=[_sysmon_unsupported(1)],
        security_events=[],
        anchor_time=ANCHOR,
    )

    assert result.bundle.facts == []
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/correlation/test_correlation_metrics.py -v`
Expected: FAIL with `TypeError: correlate_telemetry() got an unexpected keyword argument 'metrics'`

- [ ] **Step 7: Thread `metrics` through `correlate_telemetry`**

In `src/praetor/correlation/__init__.py`, add the import (after the existing `from praetor.judgment.excerpt import PromptExcerptSet` line):

```python
from praetor.judgment.excerpt import PromptExcerptSet
from praetor.metrics.collector import MetricsCollector
```

Update the signature and skip loops:

```python
def correlate_telemetry(
    *,
    sysmon_events: Sequence[Mapping[str, Any]],
    security_events: Sequence[Mapping[str, Any]],
    anchor_time: datetime,
    window_seconds: int = DEFAULT_CORRELATION_WINDOW_SECONDS,
    anchor_host_id: str | None = None,
    metrics: MetricsCollector | None = None,
) -> CorrelationResult:
    """Normalize and window-filter telemetry into bundle + prompt excerpts."""
    filtered_sysmon = filter_events_in_window(
        list(sysmon_events),
        anchor_time=anchor_time,
        window_seconds=window_seconds,
        timestamp_of=event_timestamp,
    )
    filtered_security = filter_events_in_window(
        list(security_events),
        anchor_time=anchor_time,
        window_seconds=window_seconds,
        timestamp_of=event_timestamp,
    )

    resolved_anchor_host = resolve_anchor_host_id(
        sysmon_events=filtered_sysmon,
        security_events=filtered_security,
        anchor_host_id=anchor_host_id,
        anchor_time=anchor_time,
    )
    if resolved_anchor_host is not None:
        filtered_sysmon = filter_events_to_anchor_host(
            filtered_sysmon,
            anchor_host_id=resolved_anchor_host,
        )
        filtered_security = filter_events_to_anchor_host(
            filtered_security,
            anchor_host_id=resolved_anchor_host,
        )

    facts: list[EvidenceFact] = []
    for event in filtered_sysmon:
        if not supports_sysmon_event(event):
            if metrics is not None:
                metrics.record_correlation_unsupported_event_id()
            continue
        facts.append(normalize_sysmon_event(event))
    for event in filtered_security:
        if not supports_security_event(event):
            if metrics is not None:
                metrics.record_correlation_unsupported_event_id()
            continue
        facts.append(normalize_security_event(event))

    facts.sort(key=lambda fact: fact.timestamp)
    bundle = EvidenceBundle(facts=facts)
    return CorrelationResult(
        bundle=bundle,
        prompt_excerpt_set=build_correlation_prompt_excerpts(bundle),
    )
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/correlation/test_correlation_metrics.py -v`
Expected: PASS (2/2)

- [ ] **Step 9: Wire the orchestrator's intake path so production callers get the metric too**

In `src/praetor/engine/orchestrator.py`, update `_resolve_intake_evidence_bundle` (around line 106):

```python
def _resolve_intake_evidence_bundle(
    *,
    correlate: bool,
    evidence_bundle: EvidenceBundle | None,
    sysmon_events: Sequence[Mapping[str, Any]] | None,
    security_events: Sequence[Mapping[str, Any]] | None,
    anchor_time: datetime | None,
    metrics_collector: MetricsCollector | None = None,
) -> tuple[EvidenceBundle | None, bool]:
    if not correlate:
        return None, True
    if evidence_bundle is not None:
        return evidence_bundle, False
    if sysmon_events is not None or security_events is not None:
        from praetor.correlation import correlate_telemetry

        moment = anchor_time or datetime.now(UTC)
        correlated = correlate_telemetry(
            sysmon_events=list(sysmon_events or ()),
            security_events=list(security_events or ()),
            anchor_time=moment,
            metrics=metrics_collector,
        )
        if not correlated.bundle.facts:
            return None, True
        return correlated.bundle, False
    return SKELETON_EVIDENCE_BUNDLE, False
```

Update the single call site inside `process_alert_intake` (around line 275):

```python
    resolved_bundle, correlation_failed = _resolve_intake_evidence_bundle(
        correlate=correlate,
        evidence_bundle=evidence_bundle,
        sysmon_events=sysmon_events,
        security_events=security_events,
        anchor_time=anchor_time,
        metrics_collector=metrics_collector,
    )
```

- [ ] **Step 10: Run the full engine intake suite to confirm no regression**

Run: `pytest tests/engine/ -v`
Expected: PASS, no regressions (the new keyword argument is defaulted, so existing calls without `metrics_collector` still work).

- [ ] **Step 11: Commit**

```bash
git add src/praetor/metrics/events.py src/praetor/metrics/collector.py src/praetor/correlation/__init__.py src/praetor/engine/orchestrator.py tests/metrics/test_metrics.py tests/correlation/test_correlation_metrics.py
git commit -m "correlation: add distinct metric for unsupported-EventID schema mismatches"
```

---

### Task 3: Direct unit test for the `engine.citations` adapter (RFC-006, rescoped)

**Files:**
- Test: `tests/engine/test_citations.py` (new)

**Interfaces:**
- Consumes: `validate_skeleton_citations(judgment: ModelJudgment, evidence_bundle: EvidenceBundle) -> bool` from `src/praetor/engine/citations.py` (unchanged, no production code touched in this task).

- [ ] **Step 1: Write the test**

Create `tests/engine/test_citations.py`:

```python
"""Direct unit coverage for the engine.citations adapter (DEBT-072).

evidence/citations.py already has full branch coverage in
tests/evidence/test_citation_validation.py; this file only pins that the
engine-facing adapter forwards to it correctly, since engine/citations.py
was previously exercised only indirectly through orchestrator integration
tests.
"""

from __future__ import annotations

from datetime import UTC, datetime

from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.contracts.judgment import CitedEvidenceRef, ModelJudgment
from praetor.engine.citations import validate_skeleton_citations

NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)


def _fact(evidence_id: str = "ev-1") -> EvidenceFact:
    return EvidenceFact(
        evidence_id=evidence_id,
        normalized_fields={"process_name": "cmd.exe"},
        source_event_reference="sysmon:1",
        raw_source="raw",
        provenance_path="sysmon_event_log",
        ambiguity_flag=False,
        timestamp=NOW,
    )


def _judgment(refs: list[CitedEvidenceRef]) -> ModelJudgment:
    return ModelJudgment(
        proposed_disposition=Disposition.ESCALATE,
        cited_evidence_refs=refs,
        key_tells=["tell"],
        org_config_refs=[],
        benign_alternatives=[],
        benign_alternatives_ruled_out=[],
        convergence_reasoning="reasoning",
        narrative="narrative",
        model_name="fake-model",
        provider_name="fake-provider",
    )


def test_validate_skeleton_citations_true_for_resolvable_citation() -> None:
    bundle = EvidenceBundle(facts=[_fact()])
    judgment = _judgment(
        [CitedEvidenceRef(evidence_id="ev-1", field_path="normalized_fields.process_name")]
    )

    assert validate_skeleton_citations(judgment, bundle) is True


def test_validate_skeleton_citations_false_for_unresolvable_evidence_id() -> None:
    bundle = EvidenceBundle(facts=[_fact()])
    judgment = _judgment(
        [CitedEvidenceRef(evidence_id="ev-missing", field_path="normalized_fields.process_name")]
    )

    assert validate_skeleton_citations(judgment, bundle) is False


def test_validate_skeleton_citations_false_for_unresolvable_field_path() -> None:
    bundle = EvidenceBundle(facts=[_fact()])
    judgment = _judgment(
        [CitedEvidenceRef(evidence_id="ev-1", field_path="normalized_fields.no_such_field")]
    )

    assert validate_skeleton_citations(judgment, bundle) is False
```

- [ ] **Step 2: Run test to verify it fails or passes correctly**

Run: `pytest tests/engine/test_citations.py -v`
Expected: PASS (3/3) — this task adds coverage for existing correct behavior; it should not fail. If any assertion fails, re-read `src/praetor/evidence/citations.py:50-91` (`validate_evidence_citations`) and correct the test's expectations to match actual resolution semantics — do not change production code for this task.

- [ ] **Step 3: Commit**

```bash
git add tests/engine/test_citations.py
git commit -m "test: add direct unit coverage for the engine.citations adapter"
```

---

### Task 4: Log visibility for malformed ledger edicts in precedent fetch (RFC-005, rescoped)

**Files:**
- Modify: `src/praetor/annotations/precedent.py:69-88` (`_fetch_decision_edict`)
- Test: `tests/annotations/test_precedent.py` (new)

**Interfaces:**
- Produces: no signature change to `_fetch_decision_edict` or `fetch_human_confirmed_precedents`; only adds a module-level `_logger` and a warning call on the existing `except ValidationError: return None` branch.

**Note:** `tests/judgment/test_similar_case_retrieval.py` already directly exercises `fetch_human_confirmed_precedents`, `rank_precedents_by_similarity`, and `retrieve_similar_case_exemplars` end-to-end — DEBT-074 ("no `tests/retrieval/` package tree") is a filing-location gap, not a coverage gap, so this task does not duplicate that suite. It only covers the one real behavioral gap: a corrupt ledger edict is currently dropped with zero visibility.

- [ ] **Step 1: Write the failing test**

Create `tests/annotations/test_precedent.py`:

```python
"""Coverage for annotations.precedent malformed-edict visibility (DEBT-022)."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from praetor.annotations.precedent import fetch_human_confirmed_precedents
from praetor.annotations.store import init_annotation_schema, submit_annotation
from praetor.auth import Principal, PrincipalMapVerifier
from praetor.ledger.hash_chain import DECISION_EDICT_RECORD_TYPE
from praetor.state.sqlite_guard import create_guarded_connection, critical_transaction
from praetor.state.store import init_state_schema

NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)
ANALYST_TOKEN = "token-analyst"


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[Any]:
    from praetor.alerts.outbox import init_health_alert_outbox_schema
    from praetor.state.sqlite_guard import init_state_dir
    from praetor.tickets.outbox import init_stamp_outbox_schema

    db_path = tmp_path / "state.db"
    init_state_dir(db_path)
    connection = create_guarded_connection(db_path)
    import sqlite3

    connection.row_factory = sqlite3.Row
    init_state_schema(connection)
    init_stamp_outbox_schema(connection)
    init_health_alert_outbox_schema(connection)
    init_annotation_schema(connection)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ledger_chain (
            sequence_number INTEGER PRIMARY KEY AUTOINCREMENT,
            record_type TEXT NOT NULL,
            record_json TEXT NOT NULL
        )
        """
    )
    connection.commit()
    yield connection
    connection.close()


@pytest.fixture
def verifier() -> PrincipalMapVerifier:
    return PrincipalMapVerifier(
        {ANALYST_TOKEN: Principal(identity="analyst@example.com", role="analyst")}
    )


def test_fetch_human_confirmed_precedents_logs_and_skips_malformed_edict(
    conn: Any, verifier: PrincipalMapVerifier, caplog: "logging.LogCaptureFixture"
) -> None:
    decision_id = "dec-corrupt"
    conn.execute(
        "INSERT INTO ledger_chain (record_type, record_json) VALUES (?, ?)",
        (DECISION_EDICT_RECORD_TYPE, '{"decision_id": "dec-corrupt", "not_a_valid": "edict"}'),
    )
    conn.commit()
    with critical_transaction(conn):
        submit_annotation(
            conn,
            token=ANALYST_TOKEN,
            verifier=verifier,
            decision_id=decision_id,
            disposition_correct=True,
            corrected_disposition=None,
            comment="looks right",
            timestamp=NOW,
        )
    conn.commit()

    with caplog.at_level(logging.WARNING, logger="praetor.annotations.precedent"):
        precedents = fetch_human_confirmed_precedents(conn)

    assert precedents == []
    assert any(
        "malformed ledger edict" in record.message and decision_id in record.message
        for record in caplog.records
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/annotations/test_precedent.py -v`
Expected: FAIL — `caplog.records` is empty (no warning emitted yet).

- [ ] **Step 3: Add the logger and warning call**

In `src/praetor/annotations/precedent.py`, add near the top (after the existing imports):

```python
import logging

from pydantic import ValidationError

from praetor.contracts.edict import DecisionEdict
from praetor.ledger.hash_chain import DECISION_EDICT_RECORD_TYPE

_logger = logging.getLogger(__name__)
```

Update `_fetch_decision_edict`:

```python
def _fetch_decision_edict(
    conn: sqlite3.Connection,
    decision_id: str,
) -> DecisionEdict | None:
    row = conn.execute(
        """
        SELECT record_json
        FROM ledger_chain
        WHERE record_type = ?
          AND json_extract(record_json, '$.decision_id') = ?
        LIMIT 1
        """,
        (DECISION_EDICT_RECORD_TYPE, decision_id),
    ).fetchone()
    if row is None:
        return None
    try:
        return DecisionEdict.model_validate_json(str(row["record_json"]))
    except ValidationError:
        _logger.warning(
            "malformed ledger edict for decision_id=%s skipped in precedent fetch",
            decision_id,
        )
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/annotations/test_precedent.py -v`
Expected: PASS

- [ ] **Step 5: Run the existing similar-case retrieval suite to confirm no regression**

Run: `pytest tests/judgment/test_similar_case_retrieval.py -v`
Expected: PASS, unchanged (this suite never hits the malformed-edict branch).

- [ ] **Step 6: Commit**

```bash
git add src/praetor/annotations/precedent.py tests/annotations/test_precedent.py
git commit -m "annotations: log malformed ledger edicts skipped during precedent fetch"
```

---

### Task 5: Revocation feed file-size operator warning (RFC-002, rescoped — no rotation)

**Files:**
- Modify: `src/praetor/config/constants.py` (add `DEFAULT_FEED_FILE_SIZE_WARNING_BYTES`)
- Modify: `src/praetor/revocation/exporter.py` (add size-check helper, call it from `run_feed_startup_hook`)
- Test: `tests/revocation/test_feed_exporter.py` (extend)

**Interfaces:**
- Produces: `check_feed_file_size_warning(conn: sqlite3.Connection, feed_path: Path, *, warning_bytes: int) -> bool` (returns whether a warning alert was (re)confirmed necessary) in `src/praetor/revocation/exporter.py`. Emits `SystemHealthAlert(alert_code="revocation_feed_file_size_warning", ...)` via the existing `write_pending_health_alert` outbox — same durability/delivery path as `_emit_feed_unhealthy_alert`, not a new mechanism.
- This does **not** touch `FileFeedJsonlSink.append_line`, the JSONL format, sequence numbering, or `validate_feed_file_prefix` — no consumer-facing contract changes, consistent with the frozen "no rotation machinery" pin in `docs/operator_runbook.md` / `docs/contracts.md`.

- [ ] **Step 1: Write the failing test**

Add to `tests/revocation/test_feed_exporter.py` (append; reuse the file's existing `_revocation` helper and `store`/`tmp_path` fixtures already defined earlier in the file):

```python
def test_run_feed_startup_hook_emits_size_warning_when_threshold_exceeded(
    tmp_path: Path,
) -> None:
    from praetor.revocation.exporter import (
        check_feed_file_size_warning,
        default_feed_jsonl_path,
    )
    from praetor.state.store import open_state_store

    db_path = tmp_path / "state.db"
    store = open_state_store(db_path)
    feed_path = default_feed_jsonl_path(db_path)
    feed_path.parent.mkdir(parents=True, exist_ok=True)
    feed_path.write_bytes(b"x" * 2048)

    warned = check_feed_file_size_warning(
        store.conn, feed_path, warning_bytes=1024
    )
    store.conn.commit()

    assert warned is True
    rows = store.conn.execute(
        "SELECT alert_code FROM system_health_alert_outbox"
    ).fetchall()
    assert any(row["alert_code"] == "revocation_feed_file_size_warning" for row in rows)
    store.close()


def test_check_feed_file_size_warning_no_alert_below_threshold(
    tmp_path: Path,
) -> None:
    from praetor.revocation.exporter import (
        check_feed_file_size_warning,
        default_feed_jsonl_path,
    )
    from praetor.state.store import open_state_store

    db_path = tmp_path / "state.db"
    store = open_state_store(db_path)
    feed_path = default_feed_jsonl_path(db_path)
    feed_path.parent.mkdir(parents=True, exist_ok=True)
    feed_path.write_bytes(b"x" * 100)

    warned = check_feed_file_size_warning(
        store.conn, feed_path, warning_bytes=1024
    )
    store.conn.commit()

    assert warned is False
    rows = store.conn.execute(
        "SELECT alert_code FROM system_health_alert_outbox"
    ).fetchall()
    assert not any(
        row["alert_code"] == "revocation_feed_file_size_warning" for row in rows
    )
    store.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/revocation/test_feed_exporter.py -k size_warning -v`
Expected: FAIL with `ImportError: cannot import name 'check_feed_file_size_warning'`

- [ ] **Step 3: Add the constant**

In `src/praetor/config/constants.py`, add after `DEFAULT_FEED_PROPAGATION_SECONDS`:

```python
DEFAULT_FEED_PROPAGATION_SECONDS = 60
DEFAULT_CLOCK_SKEW_SECONDS = 30

# Operator visibility only — not a rotation trigger. Feed rotation remains a
# deferred v1 non-goal (docs/operator_runbook.md "no rotation machinery").
# Provisional threshold pending owner-set org-config value.
DEFAULT_FEED_FILE_SIZE_WARNING_BYTES = 500_000_000
```

- [ ] **Step 4: Add `check_feed_file_size_warning` and wire it into startup**

In `src/praetor/revocation/exporter.py`, add the import (with the existing `from praetor.contracts.health import SystemHealthAlert` line already present) and the new function after `_emit_feed_unhealthy_alert`:

```python
FEED_FILE_SIZE_WARNING_CODE = "revocation_feed_file_size_warning"


def check_feed_file_size_warning(
    conn: sqlite3.Connection,
    feed_path: Path,
    *,
    warning_bytes: int,
) -> bool:
    """Emit an operator health alert when the (unrotated) feed file crosses a size threshold.

    Purely observational: does not rotate, truncate, or otherwise modify the
    feed file, and does not affect ``is_feed_actuation_blocked``.
    """
    if not feed_path.exists():
        return False
    if feed_path.stat().st_size <= warning_bytes:
        return False
    alert = SystemHealthAlert(
        alert_code=FEED_FILE_SIZE_WARNING_CODE,
        emitted_at=datetime.now(UTC),
    )
    write_pending_health_alert(conn, alert)
    return True
```

Wire it into `run_feed_startup_hook` — update the signature and the end of the function body:

```python
def run_feed_startup_hook(
    conn: sqlite3.Connection,
    *,
    feed_path: Path,
    max_feed_export_retries: int,
    propagation_delay_seconds: int,
    now: datetime | None = None,
    metrics: MetricsCollector | None = None,
    feed_file_size_warning_bytes: int | None = None,
) -> FeedExportResult:
    """Recover pending feed rows before actuation; set degraded if SLO missed."""
    init_revocation_feed_export_schema(conn)
    if not reconcile_feed_metadata_against_jsonl(conn, feed_path):
        unhealthy = is_feed_unhealthy(conn)
        degraded = is_feed_actuation_blocked(
            conn,
            propagation_delay_seconds=propagation_delay_seconds,
            now=now,
        )
        return FeedExportResult(
            exported_count=0,
            feed_unhealthy=unhealthy,
            degraded_actuation=degraded,
        )
    sink = FileFeedJsonlSink(feed_path)
    result = export_pending_feed_rows(
        conn,
        sink=sink,
        max_feed_export_retries=max_feed_export_retries,
        propagation_delay_seconds=propagation_delay_seconds,
        now=now,
        metrics=metrics,
    )
    if is_feed_actuation_blocked(
        conn,
        propagation_delay_seconds=propagation_delay_seconds,
        now=now,
    ):
        if not is_feed_unhealthy(conn):
            _transition_feed_unhealthy(conn)
        result = FeedExportResult(
            exported_count=result.exported_count,
            feed_unhealthy=True,
            degraded_actuation=True,
        )
    if feed_file_size_warning_bytes is not None:
        check_feed_file_size_warning(
            conn, feed_path, warning_bytes=feed_file_size_warning_bytes
        )
        conn.commit()
    return result
```

Update `run_feed_startup_hook_for_db` to pass the default through:

```python
def run_feed_startup_hook_for_db(
    conn: sqlite3.Connection,
    db_path: Path,
    *,
    max_feed_export_retries: int = 3,
    propagation_delay_seconds: int = 60,
    metrics: MetricsCollector | None = None,
    feed_file_size_warning_bytes: int = DEFAULT_FEED_FILE_SIZE_WARNING_BYTES,
) -> FeedExportResult:
    """Default hook using feed path adjacent to the state database."""
    return run_feed_startup_hook(
        conn,
        feed_path=default_feed_jsonl_path(db_path),
        max_feed_export_retries=max_feed_export_retries,
        propagation_delay_seconds=propagation_delay_seconds,
        metrics=metrics,
        feed_file_size_warning_bytes=feed_file_size_warning_bytes,
    )
```

Add the constant import at the top of `exporter.py` (alongside the existing `praetor.alerts.outbox` import):

```python
from praetor.alerts.outbox import write_pending_health_alert
from praetor.config.constants import DEFAULT_FEED_FILE_SIZE_WARNING_BYTES
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/revocation/test_feed_exporter.py -k size_warning -v`
Expected: PASS (2/2)

- [ ] **Step 6: Run the full exporter suite to confirm no regression**

Run: `pytest tests/revocation/test_feed_exporter.py -v`
Expected: PASS, all existing tests unaffected (`feed_file_size_warning_bytes` is optional/defaulted on `run_feed_startup_hook`, and `run_feed_startup_hook_for_db` keeps working with its new defaulted parameter).

- [ ] **Step 7: Commit**

```bash
git add src/praetor/config/constants.py src/praetor/revocation/exporter.py tests/revocation/test_feed_exporter.py
git commit -m "revocation: add operator size-warning health alert for the unrotated feed file"
```

---

### Task 6: Record the reverse-spec RFC disposition

**Files:**
- Create: `docs/proposals/reverse_spec_rfc_disposition.md`

**Interfaces:** none — documentation only.

- [ ] **Step 1: Write the disposition record**

Create `docs/proposals/reverse_spec_rfc_disposition.md`:

```markdown
# Reverse-Spec RFC Disposition (2026-07-30)

Source: `5570cfdd-02d7-4a8f-8867-31d8bacc829b-rfcs.md`, a reverse-spec review
generated from `AS_BUILT.md` and `DEBT_LEDGER.md`. Each RFC's cited evidence
was checked against current source and against `docs/decisions.md`, which the
generating tool did not appear to cross-reference. Full rationale for each
verdict is in `docs/superpowers/plans/2026-07-30-reverse-spec-rfc-remediation.md`
("Verification Notes").

| RFC | Original severity | Verdict | Disposition |
|---|---|---|---|
| RFC-001 (invert stamp/ledger order) | S1, tool CONCEDEd | **Rejected** | Contradicts DEC-053 (docs/decisions.md, docs/spec.md:149, docs/architecture.md:56/74, docs/contracts.md:312/644). Do not implement without an explicit DEC-053 supersession decided by a project owner. |
| RFC-002 (JSONL sink limits/isolation) | S1 | **Rejected framing; narrow fix shipped** | "Health alerts silently suppressed" is false — separate sink, already durable (`alerts/system_health.py`). Real kernel (DEBT-042, no size bound) closed via an operator size-warning alert only; rotation stays out of scope (frozen v1 non-goal, `tests/docs/test_docs.py`). |
| RFC-003 (halt on malformed never-contain) | S1, tool WEAKENed | **Accepted, rescoped tighter than the tool's own WEAKEN** | Skip branches are defensive dead code on the production read path (entries are pre-validated by `read_live_never_contain_entries`). Made observable via logging rather than a system-wide halt, which would itself be a denial-of-automation vector. |
| RFC-004 (correlation schema-mismatch metric) | S2, tool WEAKENed | **Accepted as scoped** | Real, low-risk observability gap. Implemented as-is. |
| RFC-005 (precedent poisoning) | S1, tool CONCEDEd | **Rejected S1 severity; narrow fix shipped** | Exemplars are advisory-only; PolicyGate independently re-authorizes every containment decision (AS_BUILT invariant #21), so poisoning cannot itself authorize unauthorized `auto_contain`. Real annotation-auth gap is DEBT-041, tracked separately. Only the malformed-edict silent-drop (DEBT-022) was fixed. |
| RFC-006 (citations unit tests) | S2, tool WEAKENed | **Accepted, rescoped tighter than the tool's own WEAKEN** | `engine/citations.py` is a 15-line adapter; the actual citation logic already has direct tests in `tests/evidence/test_citation_validation.py`. Added one direct test file for the adapter itself; no orchestrator extraction needed. |

**Process note:** this reverse-spec tool's automated rebuttal pass reached
CONCEDE on two S1 findings (RFC-001, RFC-005) that manual verification against
`docs/decisions.md` and the actual authorization flow rejected outright. Future
runs of this tool should be checked against `docs/decisions.md` before any S1
finding is acted on.
```

- [ ] **Step 2: Verify the file renders as intended**

Run: `pytest tests/docs/test_docs.py -v`
Expected: PASS, unchanged — this new file is not referenced by any existing doc-drift assertion, so it cannot break `tests/docs/test_docs.py`.

- [ ] **Step 3: Commit**

```bash
git add docs/proposals/reverse_spec_rfc_disposition.md
git commit -m "docs: record verified disposition of the reverse-spec RFC review"
```

---

## Final Verification

- [ ] Run `ruff check .` — expect no new violations.
- [ ] Run `mypy .` — expect no new errors.
- [ ] Run `pytest` (full suite) — expect all green, including the six new/extended test files above.
- [ ] Confirm `git log --oneline -7` shows the six commits from this plan in order.
