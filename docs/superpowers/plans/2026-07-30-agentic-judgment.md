# Agentic Judgment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Praetor's LLM judgment phase from a single-shot, fixed-context call into a bounded, tool-using agentic pipeline (source fan-out → hypothesis debate → lead reconciliation), while `PolicyGate` remains the sole deterministic authority.

**Architecture:** A new package, `praetor.judgment.agentic`, implements `AgenticJudgmentProvider` — a drop-in `JudgmentProvider` (same Protocol `VertexProvider`/`FakeProvider` already satisfy). Internally it runs three phases per `generate_judgment` call: Phase 1 fans four source investigators out concurrently (ledger history, org-config sections, similar cases, untruncated telemetry) against a bounded per-source tool-call budget, recording every call into a `SessionEvidenceRegistry`; Phase 2 runs two reasoning-only hypothesis debaters (malicious case / benign case) over the registry; Phase 3 runs one lead-reconciliation call with its own protected budget (never eaten by Phase 1/2 overrun) that produces the final `ModelJudgment`. No orchestrator branching is required for provider selection — `process_alert_intake` already calls `judgment_provider.generate_judgment(request)` through the plain Protocol. Full spec: `docs/superpowers/specs/2026-07-30-agentic-judgment-design.md`.

**Tech Stack:** Python 3.12+ (repo standard), Pydantic v2 contracts, `sqlite3`, `concurrent.futures.ThreadPoolExecutor` for phase concurrency, `pytest` for tests.

## Global Constraints

- Single-shot mode (`VertexProvider`, `FakeProvider`, the 32-scenario deterministic eval harness) is **untouched** by this plan — every change here is additive.
- `PolicyGate` evaluation logic (`meets_host_cited_corroboration`, `meets_account_corroboration`, never-contain, rate/breaker, rule precedence) is **not modified** — only `praetor.evidence.provenance`'s trust classification table gains one new entry (`ledger_history`).
- Real LLM wire integration (a Gemini-function-calling-backed `SourceInvestigatorModel`/`HypothesisModel`/`LeadModel`) is **out of scope** for this plan. Every phase depends on narrow Protocols (`model.py`); this plan builds the orchestration layer and deterministic `Fake*` implementations of those Protocols only. A real backend is follow-on work that implements the same Protocols — nothing in this plan needs to change for that to happen later.
- `raw_source` isolation (DEC-047): every tool that produces `EvidenceFact`s must never let `raw_source` content leak into anything a `SourceInvestigatorModel`/`HypothesisModel`/`LeadModel` treats as prompt text. In this plan (no real LLM wire integration), that guarantee is enforced structurally — the Fakes never read `.raw_source` — and by a dedicated isolation test in Task 6.
- New corroboration-eligible provenance path: `ledger_history` only (see spec correction — `org_config_section` is explicitly **not** corroboration-eligible; it populates `ModelJudgment.org_config_refs`, a field structurally separate from `cited_evidence_refs`).
- `WiderTelemetryTool` provides **untruncated re-fetch of the already-correlated bundle's own facts**, not a wider time window (see spec correction — raw telemetry re-correlation needs a `JudgmentRequest` field this plan does not add).
- No changes to `docs/spec.md` (frozen this phase). New decisions go in `docs/decisions.md` (DEC-064) per the existing pattern.

---

## Task 1: Provenance trust classification — `ledger_history`

**Files:**
- Modify: `src/praetor/evidence/provenance.py`
- Test: Create `tests/evidence/test_provenance.py`

**Interfaces:**
- Produces: `LEDGER_HISTORY: str` constant, extends `is_attacker_controllable_provenance` so `is_attacker_controllable_provenance(LEDGER_HISTORY) is False`. Every later task that constructs `EvidenceFact`s from `LedgerHistoryTool` uses this constant as `provenance_path`.

- [ ] **Step 1: Write the failing test**

```python
# tests/evidence/test_provenance.py
"""Unit tests for provenance trust classification (DEC-059, DEC-064)."""

from __future__ import annotations

from praetor.evidence.provenance import (
    LEDGER_HISTORY,
    SYSMON_EVENT_LOG,
    WINDOWS_SECURITY_LOG,
    is_attacker_controllable_provenance,
)


def test_ledger_history_is_non_attacker_controllable() -> None:
    assert is_attacker_controllable_provenance(LEDGER_HISTORY) is False


def test_existing_classifications_unchanged() -> None:
    assert is_attacker_controllable_provenance(WINDOWS_SECURITY_LOG) is False
    assert is_attacker_controllable_provenance(SYSMON_EVENT_LOG) is True


def test_unknown_provenance_path_defaults_attacker_controllable() -> None:
    assert is_attacker_controllable_provenance("some_new_source") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/evidence/test_provenance.py -v`
Expected: FAIL — `ImportError: cannot import name 'LEDGER_HISTORY'`

- [ ] **Step 3: Add the constant and extend the trust set**

In `src/praetor/evidence/provenance.py`, add after `HOST_ID_FIELD`:

```python
LEDGER_HISTORY = "ledger_history"
```

Change:

```python
_NON_ATTACKER_CONTROLLABLE_PATHS = frozenset({WINDOWS_SECURITY_LOG})
```

to:

```python
_NON_ATTACKER_CONTROLLABLE_PATHS = frozenset({WINDOWS_SECURITY_LOG, LEDGER_HISTORY})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/evidence/test_provenance.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/praetor/evidence/provenance.py tests/evidence/test_provenance.py
git commit -m "feat(evidence): classify ledger_history as non-attacker-controllable provenance"
```

---

## Task 2: Session evidence registry and hash domain

**Files:**
- Modify: `src/praetor/hashing/domains.py`
- Create: `src/praetor/judgment/agentic/__init__.py`
- Create: `src/praetor/judgment/agentic/registry.py`
- Test: Create `tests/hashing/test_domains.py`
- Test: Create `tests/judgment/agentic/__init__.py`
- Test: Create `tests/judgment/agentic/test_registry.py`

**Interfaces:**
- Produces: `compute_session_trace_hash(evidence_entries, org_config_entries, exemplar_entries) -> str` in `praetor.hashing.domains`.
- Produces: `ToolCallRecord`, `OrgConfigCallRecord`, `ExemplarCallRecord`, `SessionEvidenceRegistry` in `praetor.judgment.agentic.registry`. `SessionEvidenceRegistry` has methods `record_evidence(ToolCallRecord)`, `record_org_config(OrgConfigCallRecord)`, `record_exemplars(ExemplarCallRecord)`, properties `facts -> tuple[EvidenceFact, ...]`, `exemplars -> tuple[dict[str, Any], ...]`, `org_config_findings -> tuple[OrgConfigCallRecord, ...]`, and `session_trace_hash() -> str`. Task 11 (phases.py) and Task 12 (provider.py) consume this exact surface.

- [ ] **Step 1: Write the failing hash-domain test**

```python
# tests/hashing/test_domains.py
"""Unit tests for the session-trace hash domain (DEC-064)."""

from __future__ import annotations

from praetor.hashing.domains import compute_session_trace_hash


def test_session_trace_hash_is_deterministic() -> None:
    evidence = [{"source": "ledger_history", "succeeded": True}]
    org_config = [{"section_name": "containment_policy", "succeeded": True}]
    exemplars = [{"exemplar_id": "precedent-1", "succeeded": True}]
    first = compute_session_trace_hash(evidence, org_config, exemplars)
    second = compute_session_trace_hash(evidence, org_config, exemplars)
    assert first == second
    assert len(first) == 64


def test_session_trace_hash_changes_with_content() -> None:
    base = compute_session_trace_hash([{"a": 1}], [], [])
    changed = compute_session_trace_hash([{"a": 2}], [], [])
    assert base != changed


def test_session_trace_hash_empty_session() -> None:
    empty_hash = compute_session_trace_hash([], [], [])
    assert isinstance(empty_hash, str)
    assert len(empty_hash) == 64
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/hashing/test_domains.py -v`
Expected: FAIL — `ImportError: cannot import name 'compute_session_trace_hash'`

- [ ] **Step 3: Implement the hash domain**

In `src/praetor/hashing/domains.py`, add near the other `DOMAIN_*` constants:

```python
DOMAIN_SESSION_TRACE = "praetor:v1:session_trace_hash"
```

Add near `compute_ledger_link_hash`:

```python
def compute_session_trace_hash(
    evidence_entries: list[dict[str, Any]],
    org_config_entries: list[dict[str, Any]],
    exemplar_entries: list[dict[str, Any]],
) -> str:
    """Hash-chain over one agentic judgment session's full tool-call trace
    (docs/contracts.md §agentic-session; DEC-064)."""
    payload = {
        "evidence_entries": evidence_entries,
        "org_config_entries": org_config_entries,
        "exemplar_entries": exemplar_entries,
    }
    return sha256_hex(delimited([DOMAIN_SESSION_TRACE, canonical_serialize(payload)]))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/hashing/test_domains.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Write the failing registry test**

```python
# tests/judgment/agentic/test_registry.py
"""Unit tests for SessionEvidenceRegistry (docs/superpowers/specs/2026-07-30-agentic-judgment-design.md)."""

from __future__ import annotations

from datetime import UTC, datetime

from praetor.contracts.evidence import EvidenceFact
from praetor.judgment.agentic.registry import (
    ExemplarCallRecord,
    OrgConfigCallRecord,
    SessionEvidenceRegistry,
    ToolCallRecord,
)


def _fact(evidence_id: str, provenance_path: str) -> EvidenceFact:
    return EvidenceFact(
        evidence_id=evidence_id,
        normalized_fields={"host_id": "HOST-1"},
        source_event_reference="ref-1",
        raw_source="raw",
        provenance_path=provenance_path,
        ambiguity_flag=False,
        timestamp=datetime(2026, 7, 30, tzinfo=UTC),
    )


def test_registry_collects_only_successful_facts() -> None:
    registry = SessionEvidenceRegistry()
    registry.record_evidence(
        ToolCallRecord(
            source="ledger_history",
            tool_name="ledger_history",
            query={"target_ids": ["HOST-1"]},
            facts=(_fact("ev-1", "ledger_history"),),
            succeeded=True,
        )
    )
    registry.record_evidence(
        ToolCallRecord(
            source="ledger_history",
            tool_name="ledger_history",
            query={"target_ids": ["HOST-2"]},
            facts=(),
            succeeded=False,
            error="scope violation",
        )
    )
    assert len(registry.facts) == 1
    assert registry.facts[0].evidence_id == "ev-1"


def test_registry_exemplars_and_org_config_tracked_separately() -> None:
    registry = SessionEvidenceRegistry()
    registry.record_exemplars(
        ExemplarCallRecord(
            source="similar_cases",
            tool_name="similar_cases",
            query={"limit": 3},
            exemplars=({"exemplar_id": "precedent-1"},),
            succeeded=True,
        )
    )
    registry.record_org_config(
        OrgConfigCallRecord(
            source="org_config_section",
            tool_name="org_config_section",
            query={"section_name": "containment_policy"},
            section_name="containment_policy",
            content="{}",
            succeeded=True,
        )
    )
    assert registry.exemplars == ({"exemplar_id": "precedent-1"},)
    assert len(registry.org_config_findings) == 1
    assert registry.facts == ()


def test_registry_session_trace_hash_is_order_stable_and_nonempty() -> None:
    registry = SessionEvidenceRegistry()
    registry.record_evidence(
        ToolCallRecord(
            source="ledger_history",
            tool_name="ledger_history",
            query={},
            facts=(_fact("ev-1", "ledger_history"),),
            succeeded=True,
        )
    )
    first = registry.session_trace_hash()
    second = registry.session_trace_hash()
    assert first == second
    assert len(first) == 64
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/judgment/agentic/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'praetor.judgment.agentic'`

- [ ] **Step 7: Implement the registry**

Create `src/praetor/judgment/agentic/__init__.py` (empty file).

Create `src/praetor/judgment/agentic/registry.py`:

```python
"""Session-scoped evidence registry for the agentic judgment pipeline.

See docs/superpowers/specs/2026-07-30-agentic-judgment-design.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from praetor.contracts.evidence import EvidenceFact
from praetor.hashing.domains import compute_session_trace_hash


@dataclass(frozen=True)
class ToolCallRecord:
    """One evidentiary (citable) tool invocation and its result."""

    source: str
    tool_name: str
    query: dict[str, Any]
    facts: tuple[EvidenceFact, ...]
    succeeded: bool
    error: str | None = None

    def as_hashable(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "tool_name": self.tool_name,
            "query": self.query,
            "facts": [fact.model_dump(mode="python") for fact in self.facts],
            "succeeded": self.succeeded,
            "error": self.error,
        }


@dataclass(frozen=True)
class OrgConfigCallRecord:
    """One OrgConfigSectionTool invocation. Never citable evidence — informs
    ModelJudgment.org_config_refs, not cited_evidence_refs."""

    source: str
    tool_name: str
    query: dict[str, Any]
    section_name: str
    content: str
    succeeded: bool
    error: str | None = None

    def as_hashable(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "tool_name": self.tool_name,
            "query": self.query,
            "section_name": self.section_name,
            "content": self.content,
            "succeeded": self.succeeded,
            "error": self.error,
        }


@dataclass(frozen=True)
class ExemplarCallRecord:
    """One SimilarCaseTool invocation. Non-evidentiary (illustration only)."""

    source: str
    tool_name: str
    query: dict[str, Any]
    exemplars: tuple[dict[str, Any], ...]
    succeeded: bool
    error: str | None = None

    def as_hashable(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "tool_name": self.tool_name,
            "query": self.query,
            "exemplars": list(self.exemplars),
            "succeeded": self.succeeded,
            "error": self.error,
        }


@dataclass
class SessionEvidenceRegistry:
    """Accumulates every tool call/result across all three phases for one
    agentic judgment session, in a fixed deterministic append order."""

    evidence_entries: list[ToolCallRecord] = field(default_factory=list)
    org_config_entries: list[OrgConfigCallRecord] = field(default_factory=list)
    exemplar_entries: list[ExemplarCallRecord] = field(default_factory=list)

    def record_evidence(self, record: ToolCallRecord) -> None:
        self.evidence_entries.append(record)

    def record_org_config(self, record: OrgConfigCallRecord) -> None:
        self.org_config_entries.append(record)

    def record_exemplars(self, record: ExemplarCallRecord) -> None:
        self.exemplar_entries.append(record)

    @property
    def facts(self) -> tuple[EvidenceFact, ...]:
        return tuple(
            fact
            for entry in self.evidence_entries
            if entry.succeeded
            for fact in entry.facts
        )

    @property
    def exemplars(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            exemplar
            for entry in self.exemplar_entries
            if entry.succeeded
            for exemplar in entry.exemplars
        )

    @property
    def org_config_findings(self) -> tuple[OrgConfigCallRecord, ...]:
        return tuple(entry for entry in self.org_config_entries if entry.succeeded)

    @property
    def any_evidence_source_succeeded(self) -> bool:
        return any(entry.succeeded for entry in self.evidence_entries)

    def session_trace_hash(self) -> str:
        return compute_session_trace_hash(
            [entry.as_hashable() for entry in self.evidence_entries],
            [entry.as_hashable() for entry in self.org_config_entries],
            [entry.as_hashable() for entry in self.exemplar_entries],
        )
```

Create `tests/judgment/agentic/__init__.py` (empty file).

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/judgment/agentic/test_registry.py -v`
Expected: PASS (3 tests)

- [ ] **Step 9: Commit**

```bash
git add src/praetor/hashing/domains.py src/praetor/judgment/agentic/__init__.py src/praetor/judgment/agentic/registry.py tests/hashing/test_domains.py tests/judgment/agentic/__init__.py tests/judgment/agentic/test_registry.py
git commit -m "feat(judgment): add session trace hash domain and evidence registry"
```

---

## Task 3: Phase budgets and agentic errors

**Files:**
- Create: `src/praetor/judgment/agentic/budget.py`
- Create: `src/praetor/judgment/agentic/errors.py`
- Test: Create `tests/judgment/agentic/test_budget.py`
- Test: Create `tests/judgment/agentic/test_errors.py`

**Interfaces:**
- Produces: `PhaseBudget(max_tool_calls: int, max_seconds: float)`, `BudgetTracker(budget: PhaseBudget)` with `.consume_call()` and `.calls_made`, `BudgetExceededError`. Task 11 (`phases.py`) drives every source investigator loop through `BudgetTracker`.
- Produces: `AgenticEvidenceGatheringFailedError(ProviderError)` in `praetor.judgment.agentic.errors`. Task 12 (`provider.py`) raises it when all four Phase 1 sources fail; Task 14 adds the matching orchestrator `except` clause.

- [ ] **Step 1: Write the failing budget test**

```python
# tests/judgment/agentic/test_budget.py
"""Unit tests for PhaseBudget/BudgetTracker."""

from __future__ import annotations

import pytest

from praetor.judgment.agentic.budget import (
    BudgetExceededError,
    BudgetTracker,
    PhaseBudget,
)


def test_budget_tracker_allows_calls_up_to_max() -> None:
    tracker = BudgetTracker(budget=PhaseBudget(max_tool_calls=2, max_seconds=10.0))
    tracker.consume_call()
    tracker.consume_call()
    assert tracker.calls_made == 2


def test_budget_tracker_raises_when_exceeded() -> None:
    tracker = BudgetTracker(budget=PhaseBudget(max_tool_calls=1, max_seconds=10.0))
    tracker.consume_call()
    with pytest.raises(BudgetExceededError):
        tracker.consume_call()


def test_phase_budget_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="max_tool_calls"):
        PhaseBudget(max_tool_calls=-1, max_seconds=1.0)
    with pytest.raises(ValueError, match="max_seconds"):
        PhaseBudget(max_tool_calls=1, max_seconds=0.0)


def test_zero_call_budget_never_permits_a_call() -> None:
    tracker = BudgetTracker(budget=PhaseBudget(max_tool_calls=0, max_seconds=10.0))
    with pytest.raises(BudgetExceededError):
        tracker.consume_call()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/judgment/agentic/test_budget.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'praetor.judgment.agentic.budget'`

- [ ] **Step 3: Implement budget.py**

```python
# src/praetor/judgment/agentic/budget.py
"""Per-phase execution budgets for the agentic judgment pipeline."""

from __future__ import annotations

from dataclasses import dataclass


class BudgetExceededError(Exception):
    """Raised when a phase attempts to exceed its allotted tool-call budget."""


@dataclass(frozen=True)
class PhaseBudget:
    """Bounds one phase's tool-call volume. Wall-clock (max_seconds) is
    advisory here — a real model backend enforces its own deadline using
    this value; the orchestration layer only tracks call count."""

    max_tool_calls: int
    max_seconds: float

    def __post_init__(self) -> None:
        if self.max_tool_calls < 0:
            msg = "max_tool_calls must be non-negative"
            raise ValueError(msg)
        if self.max_seconds <= 0:
            msg = "max_seconds must be positive"
            raise ValueError(msg)


@dataclass
class BudgetTracker:
    """Tracks tool-call consumption against a PhaseBudget for one run."""

    budget: PhaseBudget
    calls_made: int = 0

    def consume_call(self) -> None:
        if self.calls_made >= self.budget.max_tool_calls:
            msg = f"tool-call budget exhausted: {self.budget.max_tool_calls}"
            raise BudgetExceededError(msg)
        self.calls_made += 1
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/judgment/agentic/test_budget.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Write the failing errors test**

```python
# tests/judgment/agentic/test_errors.py
"""Unit tests for agentic pipeline error types."""

from __future__ import annotations

from praetor.judgment.agentic.errors import AgenticEvidenceGatheringFailedError
from praetor.judgment.provider import ProviderError


def test_agentic_evidence_gathering_failed_is_a_provider_error() -> None:
    assert issubclass(AgenticEvidenceGatheringFailedError, ProviderError)
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/judgment/agentic/test_errors.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 7: Implement errors.py**

```python
# src/praetor/judgment/agentic/errors.py
"""Agentic-pipeline-specific provider errors."""

from __future__ import annotations

from praetor.judgment.provider import ProviderError


class AgenticEvidenceGatheringFailedError(ProviderError):
    """Raised when every Phase 1 source investigator fails for a session."""
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/judgment/agentic/test_errors.py -v`
Expected: PASS (1 test)

- [ ] **Step 9: Commit**

```bash
git add src/praetor/judgment/agentic/budget.py src/praetor/judgment/agentic/errors.py tests/judgment/agentic/test_budget.py tests/judgment/agentic/test_errors.py
git commit -m "feat(judgment): add phase budgets and AgenticEvidenceGatheringFailedError"
```

---

## Task 4: `JudgmentRequest.evidence_bundle` and orchestrator wiring

**Files:**
- Modify: `src/praetor/judgment/provider.py`
- Modify: `src/praetor/engine/orchestrator.py`
- Test: Modify `tests/judgment/test_provider_failures.py` (or wherever `JudgmentRequest` construction is tested — add a new test function; do not remove existing ones)
- Test: Create `tests/engine/test_agentic_request_evidence_bundle_wiring.py`

**Interfaces:**
- Produces: `JudgmentRequest.evidence_bundle: EvidenceBundle | None = None` (new optional field, default `None` — fully backward compatible with every existing `JudgmentRequest(...)` construction site and all 32 eval-harness scenarios). Task 12 (`provider.py`) requires this to be non-`None` to run the agentic pipeline.

- [ ] **Step 1: Write the failing test for the new field**

```python
# tests/engine/test_agentic_request_evidence_bundle_wiring.py
"""process_alert_intake must pass the resolved EvidenceBundle into
JudgmentRequest so agentic-mode providers can query it (Task 4 of
docs/superpowers/plans/2026-07-30-agentic-judgment.md)."""

from __future__ import annotations

from dataclasses import dataclass

from praetor.contracts.evidence import EvidenceBundle
from praetor.contracts.judgment import ModelJudgment
from praetor.engine.orchestrator import WalkingSkeletonEngine
from praetor.judgment.provider import JudgmentRequest, ProviderProbeResult
from praetor.state.store import open_state_store
from tests.engine.helpers import bootstrap_active_org_config, skeleton_bundle
from tests.engine.stamp_fakes import SucceedingStampBackend


@dataclass
class _CapturingProvider:
    captured: list[JudgmentRequest]

    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        self.captured.append(request)
        from praetor.engine.skeleton import skeleton_model_judgment
        from praetor.contracts.disposition import Disposition

        return skeleton_model_judgment(proposed=Disposition.STANDARD_REVIEW)

    def probe(self, canary_payload: object) -> ProviderProbeResult:
        return ProviderProbeResult(
            success=True, provider_name="capturing", model_name="capturing", metadata={}
        )


def test_process_alert_intake_passes_evidence_bundle_on_request(tmp_path) -> None:
    store = open_state_store(tmp_path / "test.db")
    bootstrap_active_org_config(store)
    provider = _CapturingProvider(captured=[])
    engine = WalkingSkeletonEngine(
        store=store, judgment_provider=provider, stamp_backend=SucceedingStampBackend()
    )
    bundle = skeleton_bundle()
    engine.process_intake(evidence_bundle=bundle, correlate=False)

    assert len(provider.captured) == 1
    assert provider.captured[0].evidence_bundle is not None
    assert provider.captured[0].evidence_bundle.facts == bundle.facts
```

Note: if `tests/engine/helpers.py` does not already export `bootstrap_active_org_config`/`skeleton_bundle` or `tests/engine/stamp_fakes.py` does not export `SucceedingStampBackend`, check `tests/engine/test_walking_skeleton.py` for the actual current helper names/imports used to stand up a `WalkingSkeletonEngine` against a temp store with an active org config, and use those instead — mirror an existing passing test's setup exactly rather than guessing names.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/engine/test_agentic_request_evidence_bundle_wiring.py -v`
Expected: FAIL — `AttributeError: 'JudgmentRequest' object has no attribute 'evidence_bundle'`

- [ ] **Step 3: Add the field to JudgmentRequest**

In `src/praetor/judgment/provider.py`, add the import and field:

```python
from praetor.contracts.evidence import EvidenceBundle
```

Change:

```python
@dataclass(frozen=True)
class JudgmentRequest:
    """Minimal Task 13 request shape; Task 14 owns prompt/excerpt contents."""

    scenario_id: str
    payload: Mapping[str, Any] = field(default_factory=dict)
```

to:

```python
@dataclass(frozen=True)
class JudgmentRequest:
    """Minimal Task 13 request shape; Task 14 owns prompt/excerpt contents."""

    scenario_id: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    evidence_bundle: EvidenceBundle | None = None
    """Resolved EvidenceBundle for this intake, when available. Optional and
    unused by single-shot providers; agentic-mode providers require it to
    construct their tools (docs/superpowers/specs/2026-07-30-agentic-judgment-design.md)."""
```

- [ ] **Step 4: Wire it in orchestrator.py**

In `src/praetor/engine/orchestrator.py`, find:

```python
    request = JudgmentRequest(
        scenario_id=alert_identity,
        payload=prompt_payload,
    )
```

Change to:

```python
    request = JudgmentRequest(
        scenario_id=alert_identity,
        payload=prompt_payload,
        evidence_bundle=resolved_bundle,
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/engine/test_agentic_request_evidence_bundle_wiring.py -v`
Expected: PASS

- [ ] **Step 6: Run the full existing test suite to confirm no regression**

Run: `pytest tests/judgment tests/engine -v`
Expected: All PASS — the new field is optional and additive, so no existing construction site or assertion should break.

- [ ] **Step 7: Commit**

```bash
git add src/praetor/judgment/provider.py src/praetor/engine/orchestrator.py tests/engine/test_agentic_request_evidence_bundle_wiring.py
git commit -m "feat(judgment): thread resolved EvidenceBundle into JudgmentRequest"
```

---

## Task 5: Ledger history query helper

**Files:**
- Modify: `src/praetor/ledger/store.py`
- Test: Create `tests/ledger/test_target_history.py`

**Interfaces:**
- Produces: `fetch_edicts_for_target_history(conn, *, alert_reference, target_ids, limit=10) -> list[DecisionEdict]` in `praetor.ledger.store`. Task 6 (`LedgerHistoryTool`) is the sole consumer.

- [ ] **Step 1: Write the failing test**

```python
# tests/ledger/test_target_history.py
"""Unit tests for fetch_edicts_for_target_history (v1 LedgerHistoryTool
query surface — see spec's LedgerHistoryTool scope note)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from praetor.contracts.containment import ContainmentDirective, DirectiveStatus, TargetType
from praetor.contracts.disposition import Disposition
from praetor.contracts.edict import DecisionEdict
from praetor.contracts.judgment import ModelJudgment
from praetor.contracts.policy import PolicyGateResult
from praetor.ledger.store import fetch_edicts_for_target_history, init_ledger_schema
from praetor.state.sqlite_guard import critical_transaction
from praetor.ledger.store import append_ledger_record
from praetor.state.store import open_state_store


def _judgment() -> ModelJudgment:
    return ModelJudgment(
        proposed_disposition=Disposition.STANDARD_REVIEW,
        cited_evidence_refs=[],
        key_tells=[],
        org_config_refs=[],
        benign_alternatives=[],
        benign_alternatives_ruled_out=[],
        convergence_reasoning="none",
        narrative="none",
        model_name="fake",
        provider_name="fake",
    )


def _edict(decision_id: str, alert_reference: str, target_id: str | None) -> DecisionEdict:
    directive = None
    if target_id is not None:
        now = datetime(2026, 7, 30, tzinfo=UTC)
        directive = ContainmentDirective(
            directive_id=f"dir-{decision_id}",
            decision_id=decision_id,
            target_type=TargetType.HOST,
            target_id=target_id,
            scope="global",
            evidence_refs=[],
            issued_at=now,
            expires_at=now.replace(second=now.second + 1) if now.second < 59 else now,
            idempotency_key=f"idem-{decision_id}",
            actuator_constraints={},
            revocation_policy={},
            status=DirectiveStatus.EMITTED,
            live_never_contain_hash="deadbeef",
            embedded_never_contain_entries=[],
            minimum_feed_sequence_at_issue=0,
        )
    return DecisionEdict(
        decision_id=decision_id,
        alert_reference=alert_reference,
        evidence_bundle_hash="hash-" + decision_id,
        org_config_snapshot_hash="cfg-hash",
        live_never_contain_hash="deadbeef",
        model_judgment=_judgment(),
        policy_gate_result=PolicyGateResult(
            proposed_disposition=Disposition.STANDARD_REVIEW,
            final_disposition=Disposition.STANDARD_REVIEW,
        ),
        final_disposition=Disposition.STANDARD_REVIEW,
        system_fault_escalation=False,
        fault_flags=[],
        stamp_status="not_required",
        timing_metadata={},
        ledger_previous_hash=None,
        ledger_current_hash="pending",
        ticket_stamp_payload={},
        containment_directive=directive,
        decided_at=datetime(2026, 7, 30, tzinfo=UTC),
    )


def test_fetch_by_alert_reference(tmp_path) -> None:
    store = open_state_store(tmp_path / "t.db")
    init_ledger_schema(store.conn)
    with critical_transaction(store.conn):
        append_ledger_record(store.conn, _edict("d1", "alert-repeat", None))
        append_ledger_record(store.conn, _edict("d2", "alert-other", None))

    results = fetch_edicts_for_target_history(
        store.conn, alert_reference="alert-repeat", target_ids=()
    )
    assert [edict.decision_id for edict in results] == ["d1"]


def test_fetch_by_containment_target(tmp_path) -> None:
    store = open_state_store(tmp_path / "t.db")
    init_ledger_schema(store.conn)
    with critical_transaction(store.conn):
        append_ledger_record(store.conn, _edict("d1", "alert-a", "HOST-99"))
        append_ledger_record(store.conn, _edict("d2", "alert-b", "HOST-1"))

    results = fetch_edicts_for_target_history(
        store.conn, alert_reference="alert-unrelated", target_ids=("HOST-99",)
    )
    assert [edict.decision_id for edict in results] == ["d1"]


def test_fetch_respects_limit(tmp_path) -> None:
    store = open_state_store(tmp_path / "t.db")
    init_ledger_schema(store.conn)
    with critical_transaction(store.conn):
        for i in range(3):
            append_ledger_record(store.conn, _edict(f"d{i}", "alert-repeat", None))

    results = fetch_edicts_for_target_history(
        store.conn, alert_reference="alert-repeat", target_ids=(), limit=2
    )
    assert len(results) == 2
```

Note: if `open_state_store`/`critical_transaction` require additional setup beyond what's shown (e.g. schema init order), mirror the setup in `tests/ledger/conftest.py` or `tests/ledger/test_hash_chain.py` exactly.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ledger/test_target_history.py -v`
Expected: FAIL — `ImportError: cannot import name 'fetch_edicts_for_target_history'`

- [ ] **Step 3: Implement the query helper**

In `src/praetor/ledger/store.py`, add the import and function:

```python
import logging

from pydantic import ValidationError

from praetor.ledger.hash_chain import DECISION_EDICT_RECORD_TYPE
```

(Add these near the existing imports; `DecisionEdict` is already imported.)

```python
_logger = logging.getLogger(__name__)


def fetch_edicts_for_target_history(
    conn: sqlite3.Connection,
    *,
    alert_reference: str,
    target_ids: tuple[str, ...],
    limit: int = 10,
) -> list[DecisionEdict]:
    """Past edicts matching ``alert_reference`` or a prior
    ``containment_directive.target_id`` in ``target_ids``.

    v1 LedgerHistoryTool query surface — both fields are already persisted
    on every DecisionEdict, so this needs no new schema or indexing. A full
    "every past decision touching this host" index would require new
    engine-transaction wiring at edict-append time and is out of scope
    (see docs/superpowers/specs/2026-07-30-agentic-judgment-design.md).
    """
    target_clause = ""
    params: list[Any] = [DECISION_EDICT_RECORD_TYPE, alert_reference]
    if target_ids:
        placeholders = ",".join("?" for _ in target_ids)
        target_clause = (
            " OR json_extract(record_json, "
            f"'$.containment_directive.target_id') IN ({placeholders})"
        )
        params.extend(target_ids)
    params.append(limit)

    rows = conn.execute(
        f"""
        SELECT record_json
        FROM ledger_chain
        WHERE record_type = ?
          AND (json_extract(record_json, '$.alert_reference') = ?{target_clause})
        ORDER BY chain_sequence DESC
        LIMIT ?
        """,
        params,
    ).fetchall()

    edicts: list[DecisionEdict] = []
    for row in rows:
        try:
            edicts.append(DecisionEdict.model_validate_json(str(row["record_json"])))
        except ValidationError:
            _logger.warning("malformed ledger edict skipped in target history fetch")
    return edicts
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ledger/test_target_history.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/praetor/ledger/store.py tests/ledger/test_target_history.py
git commit -m "feat(ledger): add fetch_edicts_for_target_history for the ledger history tool"
```

---

## Task 6: `LedgerHistoryTool` and `WiderTelemetryTool`

**Files:**
- Create: `src/praetor/judgment/agentic/tools.py`
- Test: Create `tests/judgment/agentic/test_tools.py`

**Interfaces:**
- Produces: `ToolResult(facts, succeeded, error)`, `ScopeViolationError`, `LedgerHistoryTool(conn, alert_reference, allowed_target_ids, name="ledger_history")` with `.invoke(arguments) -> ToolResult`, `WiderTelemetryTool(facts_by_id, name="wider_telemetry")` with `.invoke(arguments) -> ToolResult`. Task 11 (`phases.py`) consumes both via `.invoke(Mapping[str, Any]) -> ToolResult`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/judgment/agentic/test_tools.py
"""Unit tests for agentic pipeline tools."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from praetor.contracts.containment import ContainmentDirective, DirectiveStatus, TargetType
from praetor.contracts.disposition import Disposition
from praetor.contracts.edict import DecisionEdict
from praetor.contracts.evidence import EvidenceFact
from praetor.contracts.judgment import ModelJudgment
from praetor.contracts.policy import PolicyGateResult
from praetor.evidence.provenance import LEDGER_HISTORY
from praetor.ledger.store import append_ledger_record, init_ledger_schema
from praetor.judgment.agentic.tools import (
    LedgerHistoryTool,
    ScopeViolationError,
    WiderTelemetryTool,
)
from praetor.state.sqlite_guard import critical_transaction
from praetor.state.store import open_state_store


def _judgment() -> ModelJudgment:
    return ModelJudgment(
        proposed_disposition=Disposition.STANDARD_REVIEW,
        cited_evidence_refs=[],
        key_tells=[],
        org_config_refs=[],
        benign_alternatives=[],
        benign_alternatives_ruled_out=[],
        convergence_reasoning="none",
        narrative="none",
        model_name="fake",
        provider_name="fake",
    )


def _edict_with_target(decision_id: str, target_id: str) -> DecisionEdict:
    now = datetime(2026, 7, 30, tzinfo=UTC)
    directive = ContainmentDirective(
        directive_id=f"dir-{decision_id}",
        decision_id=decision_id,
        target_type=TargetType.HOST,
        target_id=target_id,
        scope="global",
        evidence_refs=[],
        issued_at=now,
        expires_at=now,
        idempotency_key=f"idem-{decision_id}",
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.EMITTED,
        live_never_contain_hash="deadbeef",
        embedded_never_contain_entries=[],
        minimum_feed_sequence_at_issue=0,
    )
    return DecisionEdict(
        decision_id=decision_id,
        alert_reference="alert-x",
        evidence_bundle_hash="hash",
        org_config_snapshot_hash="cfg",
        live_never_contain_hash="deadbeef",
        model_judgment=_judgment(),
        policy_gate_result=PolicyGateResult(
            proposed_disposition=Disposition.STANDARD_REVIEW,
            final_disposition=Disposition.STANDARD_REVIEW,
        ),
        final_disposition=Disposition.STANDARD_REVIEW,
        system_fault_escalation=False,
        fault_flags=[],
        stamp_status="not_required",
        timing_metadata={},
        ledger_previous_hash=None,
        ledger_current_hash="pending",
        ticket_stamp_payload={},
        containment_directive=directive,
        decided_at=now,
    )


def test_ledger_history_tool_returns_facts_for_allowed_target(tmp_path) -> None:
    store = open_state_store(tmp_path / "t.db")
    init_ledger_schema(store.conn)
    with critical_transaction(store.conn):
        append_ledger_record(store.conn, _edict_with_target("d1", "HOST-1"))

    tool = LedgerHistoryTool(
        conn=store.conn, alert_reference="alert-x", allowed_target_ids=frozenset({"HOST-1"})
    )
    result = tool.invoke({"target_ids": ["HOST-1"]})
    assert result.succeeded is True
    assert len(result.facts) == 1
    assert result.facts[0].provenance_path == LEDGER_HISTORY
    assert result.facts[0].normalized_fields["target_id"] == "HOST-1"


def test_ledger_history_tool_rejects_out_of_scope_target(tmp_path) -> None:
    store = open_state_store(tmp_path / "t.db")
    init_ledger_schema(store.conn)
    tool = LedgerHistoryTool(
        conn=store.conn, alert_reference="alert-x", allowed_target_ids=frozenset({"HOST-1"})
    )
    with pytest.raises(ScopeViolationError):
        tool.invoke({"target_ids": ["HOST-99"]})


def test_ledger_history_tool_defaults_to_all_allowed_targets(tmp_path) -> None:
    store = open_state_store(tmp_path / "t.db")
    init_ledger_schema(store.conn)
    with critical_transaction(store.conn):
        append_ledger_record(store.conn, _edict_with_target("d1", "HOST-1"))

    tool = LedgerHistoryTool(
        conn=store.conn, alert_reference="alert-x", allowed_target_ids=frozenset({"HOST-1"})
    )
    result = tool.invoke({})
    assert result.succeeded is True
    assert len(result.facts) == 1


def _wider_fact(evidence_id: str) -> EvidenceFact:
    return EvidenceFact(
        evidence_id=evidence_id,
        normalized_fields={"host_id": "HOST-1", "command_line": "x" * 500},
        source_event_reference="ref",
        raw_source="RAW-SECRET-DO-NOT-LEAK",
        provenance_path="sysmon_event_log",
        ambiguity_flag=False,
        timestamp=datetime(2026, 7, 30, tzinfo=UTC),
    )


def test_wider_telemetry_tool_returns_all_facts_by_default() -> None:
    fact = _wider_fact("ev-1")
    tool = WiderTelemetryTool(facts_by_id={"ev-1": fact})
    result = tool.invoke({})
    assert result.succeeded is True
    assert result.facts == (fact,)


def test_wider_telemetry_tool_filters_by_requested_evidence_ids() -> None:
    fact1, fact2 = _wider_fact("ev-1"), _wider_fact("ev-2")
    tool = WiderTelemetryTool(facts_by_id={"ev-1": fact1, "ev-2": fact2})
    result = tool.invoke({"evidence_ids": ["ev-2"]})
    assert result.facts == (fact2,)


def test_wider_telemetry_tool_reports_unknown_evidence_id() -> None:
    tool = WiderTelemetryTool(facts_by_id={"ev-1": _wider_fact("ev-1")})
    result = tool.invoke({"evidence_ids": ["ev-does-not-exist"]})
    assert result.succeeded is False
    assert result.facts == ()


def test_wider_telemetry_tool_does_not_expose_raw_source_field_name_change() -> None:
    """Structural isolation guard (DEC-047 pattern): raw_source stays on the
    contract but this test pins that no *new* stringified excerpt path is
    introduced here that would bypass the excerpt truncation isolation
    layer — the tool returns EvidenceFact objects, not prompt text; the
    prompt-boundary exclusion of raw_source is exercised end-to-end in
    Task 12's provider test."""
    fact = _wider_fact("ev-1")
    tool = WiderTelemetryTool(facts_by_id={"ev-1": fact})
    result = tool.invoke({})
    assert result.facts[0].raw_source == "RAW-SECRET-DO-NOT-LEAK"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/judgment/agentic/test_tools.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'praetor.judgment.agentic.tools'`

- [ ] **Step 3: Implement tools.py (Ledger + WiderTelemetry parts)**

```python
# src/praetor/judgment/agentic/tools.py
"""Read-only, scope-bounded tools for the agentic judgment pipeline.

See docs/superpowers/specs/2026-07-30-agentic-judgment-design.md.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from praetor.contracts.edict import DecisionEdict
from praetor.contracts.evidence import EvidenceFact
from praetor.evidence.provenance import LEDGER_HISTORY
from praetor.ledger.store import fetch_edicts_for_target_history


class ScopeViolationError(ValueError):
    """Raised when a tool call requests a target outside the alert's own scope."""


@dataclass(frozen=True)
class ToolResult:
    """Result of a tool invocation producing citable EvidenceFacts."""

    facts: tuple[EvidenceFact, ...]
    succeeded: bool
    error: str | None = None


@dataclass(frozen=True)
class OrgConfigSectionResult:
    """Result of an OrgConfigSectionTool invocation. Never citable evidence."""

    section_name: str
    content: str
    succeeded: bool
    error: str | None = None


@dataclass(frozen=True)
class ExemplarToolResult:
    """Result of a SimilarCaseTool invocation. Non-evidentiary."""

    exemplars: tuple[dict[str, Any], ...]
    succeeded: bool
    error: str | None = None


def _edict_to_history_fact(edict: DecisionEdict) -> EvidenceFact:
    directive = edict.containment_directive
    normalized_fields: dict[str, Any] = {
        "decision_id": edict.decision_id,
        "alert_reference": edict.alert_reference,
        "final_disposition": edict.final_disposition.value,
        "fault_flags": list(edict.fault_flags),
    }
    if directive is not None:
        normalized_fields["target_type"] = directive.target_type.value
        normalized_fields["target_id"] = directive.target_id
    return EvidenceFact(
        evidence_id=f"ledger-history-{edict.decision_id}",
        normalized_fields=normalized_fields,
        source_event_reference=edict.decision_id,
        raw_source=edict.model_dump_json(),
        provenance_path=LEDGER_HISTORY,
        ambiguity_flag=False,
        timestamp=edict.decided_at,
    )


@dataclass(frozen=True)
class LedgerHistoryTool:
    """Past decisions matching this alert's own alert_reference or a past
    containment target within this alert's own host/account scope."""

    conn: sqlite3.Connection
    alert_reference: str
    allowed_target_ids: frozenset[str]
    name: str = "ledger_history"

    def invoke(self, arguments: Mapping[str, Any]) -> ToolResult:
        requested = arguments.get("target_ids", [])
        if not isinstance(requested, Sequence) or isinstance(requested, str):
            return ToolResult(facts=(), succeeded=False, error="target_ids must be a list")
        unknown = set(requested) - self.allowed_target_ids
        if unknown:
            msg = f"target_ids outside alert scope: {sorted(unknown)}"
            raise ScopeViolationError(msg)
        target_ids = tuple(requested) if requested else tuple(self.allowed_target_ids)
        edicts = fetch_edicts_for_target_history(
            self.conn, alert_reference=self.alert_reference, target_ids=target_ids
        )
        facts = tuple(_edict_to_history_fact(edict) for edict in edicts)
        return ToolResult(facts=facts, succeeded=True)


@dataclass(frozen=True)
class WiderTelemetryTool:
    """Untruncated re-fetch of facts already in this alert's correlated
    EvidenceBundle (see spec's WiderTelemetryTool rescoping note)."""

    facts_by_id: Mapping[str, EvidenceFact]
    name: str = "wider_telemetry"

    def invoke(self, arguments: Mapping[str, Any]) -> ToolResult:
        requested = arguments.get("evidence_ids", [])
        if not isinstance(requested, Sequence) or isinstance(requested, str):
            return ToolResult(facts=(), succeeded=False, error="evidence_ids must be a list")
        if not requested:
            return ToolResult(facts=tuple(self.facts_by_id.values()), succeeded=True)
        unknown = [eid for eid in requested if eid not in self.facts_by_id]
        if unknown:
            return ToolResult(
                facts=(), succeeded=False, error=f"unknown evidence_id(s): {unknown}"
            )
        facts = tuple(self.facts_by_id[eid] for eid in requested)
        return ToolResult(facts=facts, succeeded=True)
```

Tasks 7 and 8 append their own classes and imports to this same file (`OrgConfigSectionTool`/`SimilarCaseTool` plus whatever imports each needs) rather than recreating it — do not add imports here that only those later tasks use, or `ruff` will flag them as unused at this task's commit.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/judgment/agentic/test_tools.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/praetor/judgment/agentic/tools.py tests/judgment/agentic/test_tools.py
git commit -m "feat(judgment): add LedgerHistoryTool and WiderTelemetryTool"
```

---

## Task 7: `OrgConfigSectionTool`

**Files:**
- Modify: `src/praetor/judgment/agentic/tools.py`
- Test: Modify `tests/judgment/agentic/test_tools.py`

**Interfaces:**
- Produces: `OrgConfigSectionTool(snapshot: OrgConfigSnapshot, name="org_config_section")` with `.invoke(arguments) -> OrgConfigSectionResult`. Task 12 (`provider.py`) constructs it from `fetch_snapshot_by_hash(conn, org_config_snapshot_hash)`.

- [ ] **Step 1: Write the failing test**

Append to `tests/judgment/agentic/test_tools.py`:

```python
from praetor.config.snapshot import compute_snapshot_hash_from_binding
from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.judgment.agentic.tools import OrgConfigSectionTool


def _minimal_snapshot() -> OrgConfigSnapshot:
    """Build the smallest OrgConfigSnapshot the contract allows. If this
    fails validation, check tests/config/conftest.py or
    evals/harness.py's EXAMPLE_CONFIG-loading path for the current minimal
    fixture shape and use that loader instead of constructing by hand."""
    from tests.config.conftest import minimal_org_config_snapshot

    return minimal_org_config_snapshot()


def test_org_config_section_tool_returns_requested_section() -> None:
    snapshot = _minimal_snapshot()
    tool = OrgConfigSectionTool(snapshot=snapshot)
    result = tool.invoke({"section_name": "containment_policy"})
    assert result.succeeded is True
    assert result.section_name == "containment_policy"
    assert result.content != ""


def test_org_config_section_tool_rejects_unknown_section() -> None:
    snapshot = _minimal_snapshot()
    tool = OrgConfigSectionTool(snapshot=snapshot)
    result = tool.invoke({"section_name": "not_a_real_section"})
    assert result.succeeded is False
    assert result.facts_note_absent_by_design if False else True  # marker: no facts field exists
```

Note: remove the placeholder `facts_note_absent_by_design` assertion line above before running — it exists only to remind the implementer that `OrgConfigSectionResult` intentionally has no `.facts` field (org-config content is never citable). Replace the whole test body's last assertion with a real one:

```python
def test_org_config_section_tool_rejects_unknown_section() -> None:
    snapshot = _minimal_snapshot()
    tool = OrgConfigSectionTool(snapshot=snapshot)
    result = tool.invoke({"section_name": "not_a_real_section"})
    assert result.succeeded is False
    assert result.content == ""
```

If `tests/config/conftest.py` does not export `minimal_org_config_snapshot`, search `tests/config/` for however the existing config tests build a valid `OrgConfigSnapshot` fixture (grep for `OrgConfigSnapshot(` across `tests/config/*.py`) and copy that construction inline into `_minimal_snapshot()` instead.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/judgment/agentic/test_tools.py -v`
Expected: FAIL — `ImportError: cannot import name 'OrgConfigSectionTool'`

- [ ] **Step 3: Implement OrgConfigSectionTool**

Add these imports to the top of `src/praetor/judgment/agentic/tools.py`, alongside the existing ones:

```python
import json

from pydantic import BaseModel

from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.hashing.domains import ORG_CONFIG_SNAPSHOT_HASH_KEYS
```

Then append to `src/praetor/judgment/agentic/tools.py`:

```python
@dataclass(frozen=True)
class OrgConfigSectionTool:
    """Fetch one named org-config section instead of the whole verbatim
    render (this spec's original motivating complaint). Findings inform
    ModelJudgment.org_config_refs — never cited_evidence_refs; org-config
    content is not evidence and is not corroboration-eligible."""

    snapshot: OrgConfigSnapshot
    name: str = "org_config_section"

    def invoke(self, arguments: Mapping[str, Any]) -> OrgConfigSectionResult:
        section_name = arguments.get("section_name")
        if (
            not isinstance(section_name, str)
            or section_name not in ORG_CONFIG_SNAPSHOT_HASH_KEYS
        ):
            return OrgConfigSectionResult(
                section_name=str(section_name),
                content="",
                succeeded=False,
                error=f"unknown org-config section: {section_name!r}",
            )
        value = getattr(self.snapshot, section_name)
        if isinstance(value, BaseModel):
            content = value.model_dump_json()
        else:
            content = json.dumps(value, default=str, sort_keys=True)
        return OrgConfigSectionResult(section_name=section_name, content=content, succeeded=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/judgment/agentic/test_tools.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add src/praetor/judgment/agentic/tools.py tests/judgment/agentic/test_tools.py
git commit -m "feat(judgment): add OrgConfigSectionTool"
```

---

## Task 8: `SimilarCaseTool`

**Files:**
- Modify: `src/praetor/judgment/agentic/tools.py`
- Test: Modify `tests/judgment/agentic/test_tools.py`

**Interfaces:**
- Produces: `SimilarCaseTool(conn, evidence_facts, name="similar_cases")` with `.invoke(arguments) -> ExemplarToolResult`. Task 12 (`provider.py`) constructs it from `request.evidence_bundle.facts`.

- [ ] **Step 1: Write the failing test**

Append to `tests/judgment/agentic/test_tools.py`:

```python
from praetor.judgment.agentic.tools import SimilarCaseTool
from praetor.state.store import open_state_store as _open_state_store_for_similar


def test_similar_case_tool_returns_empty_when_no_precedents(tmp_path) -> None:
    store = _open_state_store_for_similar(tmp_path / "similar.db")
    from praetor.annotations.state import init_annotations_schema

    init_annotations_schema(store.conn)
    init_ledger_schema(store.conn)
    tool = SimilarCaseTool(
        conn=store.conn,
        evidence_facts=({"normalized_fields": {"host_id": "HOST-1"}},),
    )
    result = tool.invoke({})
    assert result.succeeded is True
    assert result.exemplars == ()


def test_similar_case_tool_rejects_invalid_limit(tmp_path) -> None:
    store = _open_state_store_for_similar(tmp_path / "similar2.db")
    from praetor.annotations.state import init_annotations_schema

    init_annotations_schema(store.conn)
    init_ledger_schema(store.conn)
    tool = SimilarCaseTool(conn=store.conn, evidence_facts=())
    result = tool.invoke({"limit": 0})
    assert result.succeeded is False
```

Note: if `praetor.annotations.state.init_annotations_schema` does not exist under that name, grep `tests/judgment/test_similar_case_retrieval.py` for however it sets up the `analyst_annotations` table for a fresh store and mirror that setup exactly.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/judgment/agentic/test_tools.py -v`
Expected: FAIL — `ImportError: cannot import name 'SimilarCaseTool'`

- [ ] **Step 3: Implement SimilarCaseTool**

Add these imports to the top of `src/praetor/judgment/agentic/tools.py`, alongside the existing ones:

```python
from praetor.judgment.excerpt import MAX_PROMPT_EXEMPLARS
from praetor.retrieval.similar_cases import retrieve_similar_case_exemplars
```

Then append to `src/praetor/judgment/agentic/tools.py`:

```python
@dataclass(frozen=True)
class SimilarCaseTool:
    """Human-confirmed similar cases, agent-queried instead of pre-injected.
    Same source as today's fixed top-3 exemplars — non-evidentiary."""

    conn: sqlite3.Connection
    evidence_facts: tuple[Mapping[str, Any], ...]
    name: str = "similar_cases"

    def invoke(self, arguments: Mapping[str, Any]) -> ExemplarToolResult:
        limit = arguments.get("limit", MAX_PROMPT_EXEMPLARS)
        if not isinstance(limit, int) or limit < 1:
            return ExemplarToolResult(
                exemplars=(), succeeded=False, error="limit must be a positive int"
            )
        exemplars = retrieve_similar_case_exemplars(
            self.conn, evidence_facts=self.evidence_facts, limit=limit
        )
        return ExemplarToolResult(exemplars=tuple(exemplars), succeeded=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/judgment/agentic/test_tools.py -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
git add src/praetor/judgment/agentic/tools.py tests/judgment/agentic/test_tools.py
git commit -m "feat(judgment): add SimilarCaseTool"
```

---

## Task 9: Model protocols

**Files:**
- Create: `src/praetor/judgment/agentic/model.py`
- Test: Create `tests/judgment/agentic/test_model.py`

**Interfaces:**
- Produces: `ToolCallDecision(arguments)`, `InvestigationSummary(narrative)`, `HypothesisCase(stance, key_points, cited_evidence_ids, narrative)`, and Protocols `SourceInvestigatorModel.next_action(*, prior_call_count, last_call_succeeded) -> ToolCallDecision | InvestigationSummary`, `HypothesisModel.build_case(*, stance, registry_facts, budget) -> HypothesisCase`, `LeadModel.reconcile(*, registry_facts, malicious_case, benign_case, budget) -> ModelJudgment`. Task 10 (`fake_model.py`) implements all three; Task 11 (`phases.py`) drives all three.

- [ ] **Step 1: Write the failing test**

```python
# tests/judgment/agentic/test_model.py
"""Structural tests for the agentic model-calling Protocols."""

from __future__ import annotations

from praetor.judgment.agentic.model import (
    HypothesisCase,
    InvestigationSummary,
    ToolCallDecision,
)


def test_tool_call_decision_is_frozen() -> None:
    decision = ToolCallDecision(arguments={"target_ids": ["HOST-1"]})
    assert decision.arguments == {"target_ids": ["HOST-1"]}


def test_investigation_summary_holds_narrative() -> None:
    summary = InvestigationSummary(narrative="found nothing further")
    assert summary.narrative == "found nothing further"


def test_hypothesis_case_fields() -> None:
    case = HypothesisCase(
        stance="malicious",
        key_points=("unusual parent process",),
        cited_evidence_ids=("ev-1",),
        narrative="looks malicious",
    )
    assert case.stance == "malicious"
    assert case.key_points == ("unusual parent process",)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/judgment/agentic/test_model.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement model.py**

```python
# src/praetor/judgment/agentic/model.py
"""Model-calling protocols for the agentic judgment pipeline.

These Protocols are the seam between pipeline orchestration (phases.py)
and any concrete model backend. FakeSourceInvestigatorModel /
FakeHypothesisModel / FakeLeadModel (fake_model.py) are the only
implementations built in this plan; a real Gemini-backed implementation
translating these calls into function-calling wire traffic is deferred
follow-on work.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from praetor.contracts.evidence import EvidenceFact
from praetor.contracts.judgment import ModelJudgment
from praetor.judgment.agentic.budget import PhaseBudget


@dataclass(frozen=True)
class ToolCallDecision:
    """A source investigator's decision to invoke its bound tool."""

    arguments: dict[str, Any]


@dataclass(frozen=True)
class InvestigationSummary:
    """A source investigator's decision that it has gathered enough."""

    narrative: str


@dataclass(frozen=True)
class HypothesisCase:
    stance: str
    key_points: tuple[str, ...]
    cited_evidence_ids: tuple[str, ...]
    narrative: str


@runtime_checkable
class SourceInvestigatorModel(Protocol):
    def next_action(
        self, *, prior_call_count: int, last_call_succeeded: bool | None
    ) -> ToolCallDecision | InvestigationSummary:
        """Decide the next tool call, or conclude with a summary."""


@runtime_checkable
class HypothesisModel(Protocol):
    def build_case(
        self, *, stance: str, registry_facts: Sequence[EvidenceFact], budget: PhaseBudget
    ) -> HypothesisCase:
        """Build the strongest case for ``stance`` from gathered facts."""


@runtime_checkable
class LeadModel(Protocol):
    def reconcile(
        self,
        *,
        registry_facts: Sequence[EvidenceFact],
        malicious_case: HypothesisCase,
        benign_case: HypothesisCase,
        budget: PhaseBudget,
    ) -> ModelJudgment:
        """Produce the final ModelJudgment from both hypothesis cases."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/judgment/agentic/test_model.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/praetor/judgment/agentic/model.py tests/judgment/agentic/test_model.py
git commit -m "feat(judgment): add agentic model-calling protocols"
```

---

## Task 10: Fake model implementations

**Files:**
- Create: `src/praetor/judgment/agentic/fake_model.py`
- Test: Create `tests/judgment/agentic/test_fake_model.py`

**Interfaces:**
- Produces: `FakeSourceInvestigatorModel(call_plan: tuple[dict[str, Any], ...])`, `FakeHypothesisModel(case_factory: Callable[[str, Sequence[EvidenceFact]], HypothesisCase])`, `FakeLeadModel(judgment_factory: Callable[..., ModelJudgment])` — all implementing the Task 9 Protocols deterministically. Task 12's `AgenticJudgmentProvider` integration test and Task 14's harness scenario both use these.

- [ ] **Step 1: Write the failing test**

```python
# tests/judgment/agentic/test_fake_model.py
"""Unit tests for deterministic Fake model implementations."""

from __future__ import annotations

from datetime import UTC, datetime

from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceFact
from praetor.judgment.agentic.budget import PhaseBudget
from praetor.judgment.agentic.fake_model import (
    FakeHypothesisModel,
    FakeLeadModel,
    FakeSourceInvestigatorModel,
)
from praetor.judgment.agentic.model import HypothesisCase, InvestigationSummary, ToolCallDecision


def test_fake_source_investigator_replays_call_plan_then_summarizes() -> None:
    model = FakeSourceInvestigatorModel(
        call_plan=({"target_ids": ["HOST-1"]}, {"target_ids": ["HOST-1", "HOST-2"]})
    )
    first = model.next_action(prior_call_count=0, last_call_succeeded=None)
    assert isinstance(first, ToolCallDecision)
    assert first.arguments == {"target_ids": ["HOST-1"]}

    second = model.next_action(prior_call_count=1, last_call_succeeded=True)
    assert isinstance(second, ToolCallDecision)

    third = model.next_action(prior_call_count=2, last_call_succeeded=True)
    assert isinstance(third, InvestigationSummary)


def test_fake_hypothesis_model_delegates_to_factory() -> None:
    model = FakeHypothesisModel(
        case_factory=lambda stance, facts: HypothesisCase(
            stance=stance, key_points=(f"{len(facts)} facts seen",), cited_evidence_ids=(), narrative=""
        )
    )
    case = model.build_case(
        stance="malicious", registry_facts=(), budget=PhaseBudget(max_tool_calls=0, max_seconds=1.0)
    )
    assert case.stance == "malicious"
    assert case.key_points == ("0 facts seen",)


def test_fake_lead_model_delegates_to_factory() -> None:
    from praetor.engine.skeleton import skeleton_model_judgment

    model = FakeLeadModel(
        judgment_factory=lambda **kwargs: skeleton_model_judgment(proposed=Disposition.ESCALATE)
    )
    malicious = HypothesisCase(stance="malicious", key_points=(), cited_evidence_ids=(), narrative="")
    benign = HypothesisCase(stance="benign", key_points=(), cited_evidence_ids=(), narrative="")
    judgment = model.reconcile(
        registry_facts=(),
        malicious_case=malicious,
        benign_case=benign,
        budget=PhaseBudget(max_tool_calls=0, max_seconds=1.0),
    )
    assert judgment.proposed_disposition == Disposition.ESCALATE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/judgment/agentic/test_fake_model.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement fake_model.py**

```python
# src/praetor/judgment/agentic/fake_model.py
"""Deterministic Fake implementations of the agentic model Protocols, for
tests and the eval harness (mirrors judgment/fake_provider.py's role for
single-shot mode)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from praetor.contracts.evidence import EvidenceFact
from praetor.contracts.judgment import ModelJudgment
from praetor.judgment.agentic.budget import PhaseBudget
from praetor.judgment.agentic.model import HypothesisCase, InvestigationSummary, ToolCallDecision


@dataclass
class FakeSourceInvestigatorModel:
    """Replays a fixed, ordered call plan, then concludes with a summary."""

    call_plan: tuple[dict[str, object], ...] = ()
    summary_narrative: str = "investigation complete"
    calls_seen: int = field(default=0, init=False)

    def next_action(
        self, *, prior_call_count: int, last_call_succeeded: bool | None
    ) -> ToolCallDecision | InvestigationSummary:
        self.calls_seen += 1
        if prior_call_count < len(self.call_plan):
            return ToolCallDecision(arguments=dict(self.call_plan[prior_call_count]))
        return InvestigationSummary(narrative=self.summary_narrative)


@dataclass
class FakeHypothesisModel:
    case_factory: Callable[[str, Sequence[EvidenceFact]], HypothesisCase]

    def build_case(
        self, *, stance: str, registry_facts: Sequence[EvidenceFact], budget: PhaseBudget
    ) -> HypothesisCase:
        _ = budget
        return self.case_factory(stance, registry_facts)


@dataclass
class FakeLeadModel:
    judgment_factory: Callable[..., ModelJudgment]

    def reconcile(
        self,
        *,
        registry_facts: Sequence[EvidenceFact],
        malicious_case: HypothesisCase,
        benign_case: HypothesisCase,
        budget: PhaseBudget,
    ) -> ModelJudgment:
        _ = budget
        return self.judgment_factory(
            registry_facts=registry_facts,
            malicious_case=malicious_case,
            benign_case=benign_case,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/judgment/agentic/test_fake_model.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/praetor/judgment/agentic/fake_model.py tests/judgment/agentic/test_fake_model.py
git commit -m "feat(judgment): add deterministic Fake model implementations"
```

---

## Task 11: Phase 1 — source fan-out

**Files:**
- Create: `src/praetor/judgment/agentic/phases.py`
- Test: Create `tests/judgment/agentic/test_phases.py`

**Interfaces:**
- Produces: `SourceFanoutResult(ledger_history_succeeded, org_config_succeeded, similar_cases_succeeded, wider_telemetry_succeeded)` with `.all_failed` property, and `run_source_fanout(*, ledger_model, ledger_tool, org_config_model, org_config_tool, similar_case_model, similar_case_tool, wider_telemetry_model, wider_telemetry_tool, budget, registry) -> SourceFanoutResult`. Task 13 (`provider.py`) is the consumer.

- [ ] **Step 1: Write the failing test**

```python
# tests/judgment/agentic/test_phases.py
"""Unit tests for the Phase 1 source fan-out driver."""

from __future__ import annotations

from datetime import UTC, datetime

from praetor.contracts.evidence import EvidenceFact
from praetor.evidence.provenance import LEDGER_HISTORY
from praetor.judgment.agentic.budget import PhaseBudget
from praetor.judgment.agentic.fake_model import FakeSourceInvestigatorModel
from praetor.judgment.agentic.phases import run_source_fanout
from praetor.judgment.agentic.registry import SessionEvidenceRegistry
from praetor.judgment.agentic.tools import ExemplarToolResult, OrgConfigSectionResult, ToolResult


def _fact() -> EvidenceFact:
    return EvidenceFact(
        evidence_id="ev-1",
        normalized_fields={"host_id": "HOST-1"},
        source_event_reference="ref",
        raw_source="raw",
        provenance_path=LEDGER_HISTORY,
        ambiguity_flag=False,
        timestamp=datetime(2026, 7, 30, tzinfo=UTC),
    )


class _StubTool:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def invoke(self, arguments: dict[str, object]) -> object:
        self.calls.append(dict(arguments))
        return self.result


def test_fanout_runs_all_four_sources_and_records_registry() -> None:
    registry = SessionEvidenceRegistry()
    budget = PhaseBudget(max_tool_calls=3, max_seconds=5.0)

    ledger_tool = _StubTool(ToolResult(facts=(_fact(),), succeeded=True))
    org_config_tool = _StubTool(
        OrgConfigSectionResult(section_name="containment_policy", content="{}", succeeded=True)
    )
    similar_case_tool = _StubTool(ExemplarToolResult(exemplars=({"exemplar_id": "p1"},), succeeded=True))
    wider_telemetry_tool = _StubTool(ToolResult(facts=(), succeeded=True))

    result = run_source_fanout(
        ledger_model=FakeSourceInvestigatorModel(call_plan=({"target_ids": ["HOST-1"]},)),
        ledger_tool=ledger_tool,
        org_config_model=FakeSourceInvestigatorModel(call_plan=({"section_name": "containment_policy"},)),
        org_config_tool=org_config_tool,
        similar_case_model=FakeSourceInvestigatorModel(call_plan=({},)),
        similar_case_tool=similar_case_tool,
        wider_telemetry_model=FakeSourceInvestigatorModel(call_plan=()),
        wider_telemetry_tool=wider_telemetry_tool,
        budget=budget,
        registry=registry,
    )

    assert result.ledger_history_succeeded is True
    assert result.org_config_succeeded is True
    assert result.similar_cases_succeeded is True
    assert result.wider_telemetry_succeeded is True
    assert result.all_failed is False
    assert len(registry.facts) == 1
    assert len(registry.exemplars) == 1
    assert len(registry.org_config_findings) == 1


def test_fanout_all_sources_failed_marks_all_failed() -> None:
    registry = SessionEvidenceRegistry()
    budget = PhaseBudget(max_tool_calls=1, max_seconds=5.0)

    failing_evidence_tool = _StubTool(ToolResult(facts=(), succeeded=False, error="boom"))
    failing_org_config_tool = _StubTool(
        OrgConfigSectionResult(section_name="x", content="", succeeded=False, error="boom")
    )
    failing_exemplar_tool = _StubTool(ExemplarToolResult(exemplars=(), succeeded=False, error="boom"))

    result = run_source_fanout(
        ledger_model=FakeSourceInvestigatorModel(call_plan=({},)),
        ledger_tool=failing_evidence_tool,
        org_config_model=FakeSourceInvestigatorModel(call_plan=({},)),
        org_config_tool=failing_org_config_tool,
        similar_case_model=FakeSourceInvestigatorModel(call_plan=({},)),
        similar_case_tool=failing_exemplar_tool,
        wider_telemetry_model=FakeSourceInvestigatorModel(call_plan=({},)),
        wider_telemetry_tool=failing_evidence_tool,
        budget=budget,
        registry=registry,
    )

    assert result.all_failed is True


def test_fanout_partial_failure_does_not_mark_all_failed() -> None:
    registry = SessionEvidenceRegistry()
    budget = PhaseBudget(max_tool_calls=1, max_seconds=5.0)

    ok_tool = _StubTool(ToolResult(facts=(_fact(),), succeeded=True))
    failing_evidence_tool = _StubTool(ToolResult(facts=(), succeeded=False, error="boom"))
    failing_org_config_tool = _StubTool(
        OrgConfigSectionResult(section_name="x", content="", succeeded=False, error="boom")
    )
    failing_exemplar_tool = _StubTool(ExemplarToolResult(exemplars=(), succeeded=False, error="boom"))

    result = run_source_fanout(
        ledger_model=FakeSourceInvestigatorModel(call_plan=({},)),
        ledger_tool=ok_tool,
        org_config_model=FakeSourceInvestigatorModel(call_plan=({},)),
        org_config_tool=failing_org_config_tool,
        similar_case_model=FakeSourceInvestigatorModel(call_plan=({},)),
        similar_case_tool=failing_exemplar_tool,
        wider_telemetry_model=FakeSourceInvestigatorModel(call_plan=({},)),
        wider_telemetry_tool=failing_evidence_tool,
        budget=budget,
        registry=registry,
    )

    assert result.all_failed is False
    assert result.ledger_history_succeeded is True
    assert result.org_config_succeeded is False


def test_fanout_respects_budget_and_stops_calling() -> None:
    registry = SessionEvidenceRegistry()
    budget = PhaseBudget(max_tool_calls=1, max_seconds=5.0)
    ok_tool = _StubTool(ToolResult(facts=(_fact(),), succeeded=True))

    # call_plan has 3 entries but budget only allows 1 call.
    over_budget_model = FakeSourceInvestigatorModel(
        call_plan=({"a": 1}, {"a": 2}, {"a": 3})
    )

    result = run_source_fanout(
        ledger_model=over_budget_model,
        ledger_tool=ok_tool,
        org_config_model=FakeSourceInvestigatorModel(call_plan=()),
        org_config_tool=_StubTool(OrgConfigSectionResult(section_name="x", content="{}", succeeded=True)),
        similar_case_model=FakeSourceInvestigatorModel(call_plan=()),
        similar_case_tool=_StubTool(ExemplarToolResult(exemplars=(), succeeded=True)),
        wider_telemetry_model=FakeSourceInvestigatorModel(call_plan=()),
        wider_telemetry_tool=_StubTool(ToolResult(facts=(), succeeded=True)),
        budget=budget,
        registry=registry,
    )
    assert result.ledger_history_succeeded is True
    assert len(ok_tool.calls) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/judgment/agentic/test_phases.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'praetor.judgment.agentic.phases'`

- [ ] **Step 3: Implement Phase 1 in phases.py**

```python
# src/praetor/judgment/agentic/phases.py
"""Phase orchestration for the agentic judgment pipeline.

See docs/superpowers/specs/2026-07-30-agentic-judgment-design.md.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from praetor.judgment.agentic.budget import BudgetExceededError, BudgetTracker, PhaseBudget
from praetor.judgment.agentic.model import InvestigationSummary, SourceInvestigatorModel
from praetor.judgment.agentic.registry import (
    ExemplarCallRecord,
    OrgConfigCallRecord,
    SessionEvidenceRegistry,
    ToolCallRecord,
)
from praetor.judgment.agentic.tools import (
    ExemplarToolResult,
    LedgerHistoryTool,
    OrgConfigSectionResult,
    OrgConfigSectionTool,
    SimilarCaseTool,
    ToolResult,
    WiderTelemetryTool,
)


def _drive_investigation(
    model: SourceInvestigatorModel,
    budget: PhaseBudget,
    invoke: Callable[[dict[str, Any]], tuple[bool, object]],
) -> list[tuple[dict[str, Any], bool, object]]:
    """Drive one source investigator's bounded loop.

    Returns a list of (query_arguments, succeeded, raw_result) in call
    order. Stops when the model signals InvestigationSummary or the
    budget is exhausted, whichever comes first.
    """
    tracker = BudgetTracker(budget=budget)
    last_succeeded: bool | None = None
    calls: list[tuple[dict[str, Any], bool, object]] = []
    while True:
        action = model.next_action(
            prior_call_count=tracker.calls_made, last_call_succeeded=last_succeeded
        )
        if isinstance(action, InvestigationSummary):
            break
        try:
            tracker.consume_call()
        except BudgetExceededError:
            break
        succeeded, raw_result = invoke(action.arguments)
        calls.append((dict(action.arguments), succeeded, raw_result))
        last_succeeded = succeeded
    return calls


def _run_evidence_source(
    *,
    source: str,
    model: SourceInvestigatorModel,
    tool: LedgerHistoryTool | WiderTelemetryTool,
    budget: PhaseBudget,
) -> tuple[bool, list[ToolCallRecord]]:
    def invoke(arguments: dict[str, Any]) -> tuple[bool, ToolResult]:
        result = tool.invoke(arguments)
        return result.succeeded, result

    calls = _drive_investigation(model, budget, invoke)
    records = [
        ToolCallRecord(
            source=source,
            tool_name=tool.name,
            query=query,
            facts=result.facts,
            succeeded=succeeded,
            error=result.error,
        )
        for query, succeeded, result in calls
    ]
    return any(record.succeeded for record in records), records


def run_ledger_history_source(
    *, model: SourceInvestigatorModel, tool: LedgerHistoryTool, budget: PhaseBudget
) -> tuple[bool, list[ToolCallRecord]]:
    return _run_evidence_source(source="ledger_history", model=model, tool=tool, budget=budget)


def run_wider_telemetry_source(
    *, model: SourceInvestigatorModel, tool: WiderTelemetryTool, budget: PhaseBudget
) -> tuple[bool, list[ToolCallRecord]]:
    return _run_evidence_source(source="wider_telemetry", model=model, tool=tool, budget=budget)


def run_org_config_source(
    *, model: SourceInvestigatorModel, tool: OrgConfigSectionTool, budget: PhaseBudget
) -> tuple[bool, list[OrgConfigCallRecord]]:
    def invoke(arguments: dict[str, Any]) -> tuple[bool, OrgConfigSectionResult]:
        result = tool.invoke(arguments)
        return result.succeeded, result

    calls = _drive_investigation(model, budget, invoke)
    records = [
        OrgConfigCallRecord(
            source="org_config_section",
            tool_name=tool.name,
            query=query,
            section_name=result.section_name,
            content=result.content,
            succeeded=succeeded,
            error=result.error,
        )
        for query, succeeded, result in calls
    ]
    return any(record.succeeded for record in records), records


def run_similar_case_source(
    *, model: SourceInvestigatorModel, tool: SimilarCaseTool, budget: PhaseBudget
) -> tuple[bool, list[ExemplarCallRecord]]:
    def invoke(arguments: dict[str, Any]) -> tuple[bool, ExemplarToolResult]:
        result = tool.invoke(arguments)
        return result.succeeded, result

    calls = _drive_investigation(model, budget, invoke)
    records = [
        ExemplarCallRecord(
            source="similar_cases",
            tool_name=tool.name,
            query=query,
            exemplars=result.exemplars,
            succeeded=succeeded,
            error=result.error,
        )
        for query, succeeded, result in calls
    ]
    return any(record.succeeded for record in records), records


@dataclass(frozen=True)
class SourceFanoutResult:
    ledger_history_succeeded: bool
    org_config_succeeded: bool
    similar_cases_succeeded: bool
    wider_telemetry_succeeded: bool

    @property
    def all_failed(self) -> bool:
        return not (
            self.ledger_history_succeeded
            or self.org_config_succeeded
            or self.similar_cases_succeeded
            or self.wider_telemetry_succeeded
        )


def run_source_fanout(
    *,
    ledger_model: SourceInvestigatorModel,
    ledger_tool: LedgerHistoryTool,
    org_config_model: SourceInvestigatorModel,
    org_config_tool: OrgConfigSectionTool,
    similar_case_model: SourceInvestigatorModel,
    similar_case_tool: SimilarCaseTool,
    wider_telemetry_model: SourceInvestigatorModel,
    wider_telemetry_tool: WiderTelemetryTool,
    budget: PhaseBudget,
    registry: SessionEvidenceRegistry,
) -> SourceFanoutResult:
    """Run all four Phase 1 source investigators concurrently, then append
    their results to ``registry`` in a fixed deterministic order (ledger,
    org-config, similar-cases, wider-telemetry) regardless of which thread
    actually finished first — keeps session_trace_hash reproducible."""
    with ThreadPoolExecutor(max_workers=4) as executor:
        ledger_future = executor.submit(
            run_ledger_history_source, model=ledger_model, tool=ledger_tool, budget=budget
        )
        org_config_future = executor.submit(
            run_org_config_source, model=org_config_model, tool=org_config_tool, budget=budget
        )
        similar_case_future = executor.submit(
            run_similar_case_source,
            model=similar_case_model,
            tool=similar_case_tool,
            budget=budget,
        )
        wider_telemetry_future = executor.submit(
            run_wider_telemetry_source,
            model=wider_telemetry_model,
            tool=wider_telemetry_tool,
            budget=budget,
        )
        ledger_succeeded, ledger_records = ledger_future.result()
        org_config_succeeded, org_config_records = org_config_future.result()
        similar_cases_succeeded, similar_case_records = similar_case_future.result()
        wider_telemetry_succeeded, wider_telemetry_records = wider_telemetry_future.result()

    for record in ledger_records:
        registry.record_evidence(record)
    for record in org_config_records:
        registry.record_org_config(record)
    for record in similar_case_records:
        registry.record_exemplars(record)
    for record in wider_telemetry_records:
        registry.record_evidence(record)

    return SourceFanoutResult(
        ledger_history_succeeded=ledger_succeeded,
        org_config_succeeded=org_config_succeeded,
        similar_cases_succeeded=similar_cases_succeeded,
        wider_telemetry_succeeded=wider_telemetry_succeeded,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/judgment/agentic/test_phases.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/praetor/judgment/agentic/phases.py tests/judgment/agentic/test_phases.py
git commit -m "feat(judgment): add Phase 1 source fan-out driver"
```

---

## Task 12: Phase 2 (hypothesis debate) and Phase 3 (lead reconciliation)

**Files:**
- Modify: `src/praetor/judgment/agentic/phases.py`
- Test: Modify `tests/judgment/agentic/test_phases.py`

**Interfaces:**
- Produces: `run_hypothesis_debate(*, malicious_model, benign_model, registry) -> tuple[HypothesisCase, HypothesisCase]` and `run_lead_reconciliation(*, lead_model, registry, malicious_case, benign_case, budget) -> ModelJudgment`. Task 13 (`provider.py`) is the consumer.

- [ ] **Step 1: Write the failing test**

Append to `tests/judgment/agentic/test_phases.py`:

```python
from praetor.contracts.disposition import Disposition
from praetor.engine.skeleton import skeleton_model_judgment
from praetor.judgment.agentic.fake_model import FakeHypothesisModel, FakeLeadModel
from praetor.judgment.agentic.model import HypothesisCase
from praetor.judgment.agentic.phases import run_hypothesis_debate, run_lead_reconciliation


def test_hypothesis_debate_runs_both_stances() -> None:
    registry = SessionEvidenceRegistry()
    registry.record_evidence(
        ToolCallRecord(
            source="ledger_history",
            tool_name="ledger_history",
            query={},
            facts=(_fact(),),
            succeeded=True,
        )
    )
    malicious_model = FakeHypothesisModel(
        case_factory=lambda stance, facts: HypothesisCase(
            stance=stance, key_points=(f"{len(facts)}-facts",), cited_evidence_ids=(), narrative=""
        )
    )
    benign_model = FakeHypothesisModel(
        case_factory=lambda stance, facts: HypothesisCase(
            stance=stance, key_points=("benign-explanation",), cited_evidence_ids=(), narrative=""
        )
    )
    malicious_case, benign_case = run_hypothesis_debate(
        malicious_model=malicious_model, benign_model=benign_model, registry=registry
    )
    assert malicious_case.stance == "malicious"
    assert malicious_case.key_points == ("1-facts",)
    assert benign_case.stance == "benign"


def test_lead_reconciliation_produces_judgment() -> None:
    registry = SessionEvidenceRegistry()
    malicious_case = HypothesisCase(stance="malicious", key_points=(), cited_evidence_ids=(), narrative="")
    benign_case = HypothesisCase(stance="benign", key_points=(), cited_evidence_ids=(), narrative="")
    lead_model = FakeLeadModel(
        judgment_factory=lambda **kwargs: skeleton_model_judgment(proposed=Disposition.ESCALATE)
    )
    judgment = run_lead_reconciliation(
        lead_model=lead_model,
        registry=registry,
        malicious_case=malicious_case,
        benign_case=benign_case,
        budget=PhaseBudget(max_tool_calls=0, max_seconds=15.0),
    )
    assert judgment.proposed_disposition == Disposition.ESCALATE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/judgment/agentic/test_phases.py -v`
Expected: FAIL — `ImportError: cannot import name 'run_hypothesis_debate'`

- [ ] **Step 3: Implement Phase 2 and Phase 3**

Append to `src/praetor/judgment/agentic/phases.py`:

```python
from praetor.contracts.judgment import ModelJudgment
from praetor.judgment.agentic.model import HypothesisCase, HypothesisModel, LeadModel


def run_hypothesis_debate(
    *,
    malicious_model: HypothesisModel,
    benign_model: HypothesisModel,
    registry: SessionEvidenceRegistry,
) -> tuple[HypothesisCase, HypothesisCase]:
    """Run both hypothesis debaters concurrently, reasoning-only over the
    Phase 1 registry (no new tool calls — see spec's Phase 2 tool-access
    decision)."""
    facts = registry.facts
    budget = PhaseBudget(max_tool_calls=0, max_seconds=15.0)
    with ThreadPoolExecutor(max_workers=2) as executor:
        malicious_future = executor.submit(
            malicious_model.build_case, stance="malicious", registry_facts=facts, budget=budget
        )
        benign_future = executor.submit(
            benign_model.build_case, stance="benign", registry_facts=facts, budget=budget
        )
        return malicious_future.result(), benign_future.result()


def run_lead_reconciliation(
    *,
    lead_model: LeadModel,
    registry: SessionEvidenceRegistry,
    malicious_case: HypothesisCase,
    benign_case: HypothesisCase,
    budget: PhaseBudget,
) -> ModelJudgment:
    """Produce the final ModelJudgment. ``budget`` must be a fixed,
    independent allotment for this phase — never derived from Phase 1/2
    leftover time — so reconciliation always has real time to run (spec's
    'protected minimum time allotment' requirement)."""
    return lead_model.reconcile(
        registry_facts=registry.facts,
        malicious_case=malicious_case,
        benign_case=benign_case,
        budget=budget,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/judgment/agentic/test_phases.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/praetor/judgment/agentic/phases.py tests/judgment/agentic/test_phases.py
git commit -m "feat(judgment): add Phase 2 hypothesis debate and Phase 3 lead reconciliation"
```

---

## Task 13: `AgenticJudgmentProvider`

**Files:**
- Modify: `src/praetor/contracts/judgment.py`
- Create: `src/praetor/judgment/agentic/provider.py`
- Test: Create `tests/judgment/agentic/test_provider.py`

**Interfaces:**
- Produces: `ModelJudgment.session_trace_hash: str | None = None` (new optional field, backward compatible — every existing `ModelJudgment(...)` construction across the whole codebase and test suite omits it and gets `None`, matching single-shot mode exactly).
- Produces: `AgenticJudgmentProvider` implementing `JudgmentProvider` (`generate_judgment(request) -> ModelJudgment`, `probe(canary_payload) -> ProviderProbeResult`), setting `session_trace_hash` on every judgment it returns. Task 14 wires its failure path into the orchestrator's Outcome Matrix and threads `session_trace_hash` from `ModelJudgment` into `DecisionEdict`; the eval harness (Task 14) constructs it for the new scenario.

- [ ] **Step 1: Write the failing test**

```python
# tests/judgment/agentic/test_provider.py
"""End-to-end tests for AgenticJudgmentProvider, wired entirely with Fakes."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.engine.skeleton import skeleton_model_judgment
from praetor.judgment.agentic.errors import AgenticEvidenceGatheringFailedError
from praetor.judgment.agentic.fake_model import (
    FakeHypothesisModel,
    FakeLeadModel,
    FakeSourceInvestigatorModel,
)
from praetor.judgment.agentic.model import HypothesisCase
from praetor.judgment.agentic.provider import AgenticJudgmentProvider
from praetor.judgment.provider import JudgmentRequest, ProviderUnavailableError
from praetor.ledger.store import init_ledger_schema
from praetor.state.store import open_state_store


def _bundle() -> EvidenceBundle:
    fact = EvidenceFact(
        evidence_id="ev-1",
        normalized_fields={"host_id": "HOST-1"},
        source_event_reference="ref",
        raw_source="raw",
        provenance_path="sysmon_event_log",
        ambiguity_flag=False,
        timestamp=datetime(2026, 7, 30, tzinfo=UTC),
    )
    return EvidenceBundle(facts=[fact])


def _passthrough_hypothesis_model(stance: str) -> FakeHypothesisModel:
    return FakeHypothesisModel(
        case_factory=lambda s, facts: HypothesisCase(
            stance=s, key_points=(), cited_evidence_ids=(), narrative=""
        )
    )


def _passthrough_lead_model(disposition: Disposition = Disposition.STANDARD_REVIEW) -> FakeLeadModel:
    return FakeLeadModel(judgment_factory=lambda **kwargs: skeleton_model_judgment(proposed=disposition))


def _make_provider(store, *, all_sources_fail: bool = False) -> AgenticJudgmentProvider:
    plan = () if all_sources_fail else ({},)
    return AgenticJudgmentProvider(
        conn=store.conn,
        make_ledger_model=lambda request: FakeSourceInvestigatorModel(call_plan=plan),
        make_org_config_model=lambda request: FakeSourceInvestigatorModel(call_plan=()),
        make_similar_case_model=lambda request: FakeSourceInvestigatorModel(call_plan=()),
        make_wider_telemetry_model=lambda request: FakeSourceInvestigatorModel(call_plan=plan),
        make_malicious_model=lambda request: _passthrough_hypothesis_model("malicious"),
        make_benign_model=lambda request: _passthrough_hypothesis_model("benign"),
        make_lead_model=lambda request: _passthrough_lead_model(),
    )


def test_generate_judgment_requires_evidence_bundle(tmp_path) -> None:
    store = open_state_store(tmp_path / "t.db")
    init_ledger_schema(store.conn)
    provider = _make_provider(store)
    request = JudgmentRequest(scenario_id="s1", payload={"org_config_snapshot_hash": "h"})
    with pytest.raises(ProviderUnavailableError):
        provider.generate_judgment(request)


def test_generate_judgment_end_to_end_with_fakes(tmp_path) -> None:
    store = open_state_store(tmp_path / "t.db")
    init_ledger_schema(store.conn)
    provider = _make_provider(store)
    request = JudgmentRequest(
        scenario_id="s1", payload={"org_config_snapshot_hash": "h"}, evidence_bundle=_bundle()
    )
    judgment = provider.generate_judgment(request)
    assert judgment.model_name == "agentic-pipeline-v1"
    assert judgment.provider_name == "agentic"
    assert judgment.session_trace_hash is not None
    assert len(judgment.session_trace_hash) == 64


def test_generate_judgment_raises_when_all_sources_fail(tmp_path) -> None:
    store = open_state_store(tmp_path / "t.db")
    init_ledger_schema(store.conn)
    provider = _make_provider(store, all_sources_fail=True)
    request = JudgmentRequest(
        scenario_id="s1", payload={"org_config_snapshot_hash": "h"}, evidence_bundle=_bundle()
    )
    with pytest.raises(AgenticEvidenceGatheringFailedError):
        provider.generate_judgment(request)


def test_probe_reports_success() -> None:
    from praetor.state.store import open_state_store as _open

    provider = AgenticJudgmentProvider(
        conn=None,  # type: ignore[arg-type]
        make_ledger_model=lambda request: FakeSourceInvestigatorModel(),
        make_org_config_model=lambda request: FakeSourceInvestigatorModel(),
        make_similar_case_model=lambda request: FakeSourceInvestigatorModel(),
        make_wider_telemetry_model=lambda request: FakeSourceInvestigatorModel(),
        make_malicious_model=lambda request: _passthrough_hypothesis_model("malicious"),
        make_benign_model=lambda request: _passthrough_hypothesis_model("benign"),
        make_lead_model=lambda request: _passthrough_lead_model(),
    )
    result = provider.probe({"canary": "x"})
    assert result.success is True
```

Note on the `test_generate_judgment_raises_when_all_sources_fail` case: the org-config and similar-case sources both use empty call plans (`call_plan=()`), which means their `FakeSourceInvestigatorModel` immediately returns `InvestigationSummary` without ever calling their (working, non-failing) tools — so those two sources produce **zero** `ToolCallRecord`/`ExemplarCallRecord` entries, not failed ones. `SourceFanoutResult.all_failed` must therefore treat "never attempted" the same as "attempted and failed" for the purposes of the all-sources-failed check — confirm this in Step 3's implementation: a source with zero calls has `succeeded=False` from `_run_evidence_source`/`run_org_config_source`/`run_similar_case_source` (since `any(...)` over an empty list is `False`), so this already falls out correctly from Task 11's implementation. No change needed there — just confirm the test passes as evidence this behavior is correct.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/judgment/agentic/test_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'praetor.judgment.agentic.provider'`

- [ ] **Step 3: Add `session_trace_hash` to `ModelJudgment`, then implement provider.py**

In `src/praetor/contracts/judgment.py`, add to `ModelJudgment` (after `provider_name`):

```python
    session_trace_hash: str | None = None
    """Agentic-mode session evidence registry hash (DEC-064). None for
    single-shot-mode judgments — every existing construction site is
    unaffected by this addition."""
```

```python
# src/praetor/judgment/agentic/provider.py
"""AgenticJudgmentProvider: a JudgmentProvider implementing the 3-phase
agentic pipeline. Drop-in replacement for single-shot providers at
whatever call site constructs the engine (no orchestrator.py branching
required — see spec's Rollout section)."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from praetor.config.state import fetch_snapshot_by_hash
from praetor.contracts.judgment import ModelJudgment
from praetor.evidence.provenance import HOST_ID_FIELD
from praetor.judgment.agentic.budget import PhaseBudget
from praetor.judgment.agentic.errors import AgenticEvidenceGatheringFailedError
from praetor.judgment.agentic.model import HypothesisModel, LeadModel, SourceInvestigatorModel
from praetor.judgment.agentic.phases import (
    run_hypothesis_debate,
    run_lead_reconciliation,
    run_source_fanout,
)
from praetor.judgment.agentic.registry import SessionEvidenceRegistry
from praetor.judgment.agentic.tools import (
    LedgerHistoryTool,
    OrgConfigSectionTool,
    SimilarCaseTool,
    WiderTelemetryTool,
)
from praetor.judgment.provider import (
    JudgmentRequest,
    ProviderProbeResult,
    ProviderUnavailableError,
)

DEFAULT_SOURCE_BUDGET = PhaseBudget(max_tool_calls=5, max_seconds=20.0)
DEFAULT_LEAD_BUDGET = PhaseBudget(max_tool_calls=0, max_seconds=15.0)


def _resolve_scope(request: JudgmentRequest) -> tuple[str, frozenset[str]]:
    assert request.evidence_bundle is not None
    target_ids = {
        str(fact.normalized_fields[HOST_ID_FIELD])
        for fact in request.evidence_bundle.facts
        if isinstance(fact.normalized_fields.get(HOST_ID_FIELD), str)
        and fact.normalized_fields[HOST_ID_FIELD].strip()
    }
    return request.scenario_id, frozenset(target_ids)


@dataclass(frozen=True)
class AgenticJudgmentProvider:
    conn: sqlite3.Connection
    make_ledger_model: Callable[[JudgmentRequest], SourceInvestigatorModel]
    make_org_config_model: Callable[[JudgmentRequest], SourceInvestigatorModel]
    make_similar_case_model: Callable[[JudgmentRequest], SourceInvestigatorModel]
    make_wider_telemetry_model: Callable[[JudgmentRequest], SourceInvestigatorModel]
    make_malicious_model: Callable[[JudgmentRequest], HypothesisModel]
    make_benign_model: Callable[[JudgmentRequest], HypothesisModel]
    make_lead_model: Callable[[JudgmentRequest], LeadModel]
    provider_name: str = "agentic"
    model_name: str = "agentic-pipeline-v1"
    source_budget: PhaseBudget = DEFAULT_SOURCE_BUDGET
    lead_budget: PhaseBudget = DEFAULT_LEAD_BUDGET

    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        if request.evidence_bundle is None:
            msg = "agentic judgment requires request.evidence_bundle"
            raise ProviderUnavailableError(msg)

        alert_reference, allowed_target_ids = _resolve_scope(request)

        snapshot_hash = str(request.payload.get("org_config_snapshot_hash", ""))
        snapshot = fetch_snapshot_by_hash(self.conn, snapshot_hash)
        if snapshot is None:
            msg = f"no org config snapshot found for hash {snapshot_hash!r}"
            raise ProviderUnavailableError(msg)

        ledger_tool = LedgerHistoryTool(
            conn=self.conn,
            alert_reference=alert_reference,
            allowed_target_ids=allowed_target_ids,
        )
        org_config_tool = OrgConfigSectionTool(snapshot=snapshot)
        similar_case_tool = SimilarCaseTool(
            conn=self.conn,
            evidence_facts=tuple(
                fact.model_dump(mode="python") for fact in request.evidence_bundle.facts
            ),
        )
        wider_telemetry_tool = WiderTelemetryTool(
            facts_by_id={fact.evidence_id: fact for fact in request.evidence_bundle.facts}
        )

        registry = SessionEvidenceRegistry()
        fanout_result = run_source_fanout(
            ledger_model=self.make_ledger_model(request),
            ledger_tool=ledger_tool,
            org_config_model=self.make_org_config_model(request),
            org_config_tool=org_config_tool,
            similar_case_model=self.make_similar_case_model(request),
            similar_case_tool=similar_case_tool,
            wider_telemetry_model=self.make_wider_telemetry_model(request),
            wider_telemetry_tool=wider_telemetry_tool,
            budget=self.source_budget,
            registry=registry,
        )
        if fanout_result.all_failed:
            msg = f"all Phase 1 sources failed for scenario {request.scenario_id!r}"
            raise AgenticEvidenceGatheringFailedError(msg)

        malicious_case, benign_case = run_hypothesis_debate(
            malicious_model=self.make_malicious_model(request),
            benign_model=self.make_benign_model(request),
            registry=registry,
        )
        judgment = run_lead_reconciliation(
            lead_model=self.make_lead_model(request),
            registry=registry,
            malicious_case=malicious_case,
            benign_case=benign_case,
            budget=self.lead_budget,
        )
        return judgment.model_copy(
            update={
                "model_name": self.model_name,
                "provider_name": self.provider_name,
                "session_trace_hash": registry.session_trace_hash(),
            }
        )

    def probe(self, canary_payload: Mapping[str, Any]) -> ProviderProbeResult:
        return ProviderProbeResult(
            success=True,
            provider_name=self.provider_name,
            model_name=self.model_name,
            metadata={"canary_seen": bool(canary_payload)},
        )
```

Note: if `praetor.config.state` does not export `fetch_snapshot_by_hash` under that exact name, check the actual export (it was seen referenced from `fetch_active_snapshot`'s body during planning: `return fetch_snapshot_by_hash(conn, active.snapshot_hash)`) — the name should match; if not, grep `src/praetor/config/state.py` for the real function name and use that instead.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/judgment/agentic/test_provider.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Run the full agentic test suite**

Run: `pytest tests/judgment/agentic tests/evidence/test_provenance.py tests/hashing/test_domains.py tests/ledger/test_target_history.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/praetor/judgment/agentic/provider.py tests/judgment/agentic/test_provider.py
git commit -m "feat(judgment): add AgenticJudgmentProvider composing all three phases"
```

---

## Task 14: Outcome Matrix fault flag, `DecisionEdict.session_trace_hash`, and docs

**Files:**
- Modify: `src/praetor/metrics/events.py`
- Modify: `src/praetor/contracts/fault_flags.py`
- Modify: `src/praetor/contracts/edict.py`
- Modify: `src/praetor/engine/orchestrator.py`
- Modify: `src/praetor/judgment/fake_provider.py`
- Create: `evals/scenarios/agentic_evidence_gathering_failed.yaml`
- Modify: `docs/decisions.md`
- Modify: `docs/contracts.md`
- Modify: `docs/architecture.md`
- Test: Create `tests/engine/test_agentic_evidence_gathering_failed_intake.py`
- Test: Modify `tests/evals/test_eval_harness.py` (no code changes expected — this task's job is to make the existing `test_outcome_matrix_completeness_guard` pass with the new flag; do not weaken that test)

**Interfaces:**
- Produces: `OutcomeMatrixFaultFlag.AGENTIC_EVIDENCE_GATHERING_FAILED`, `OUTCOME_MATRIX_SFE[...] = True`, `DecisionEdict.session_trace_hash: str | None = None` (optional, backward compatible — `None` for every single-shot-mode edict).

- [ ] **Step 1: Write the failing orchestrator test**

Mirror `tests/engine/test_provider_unavailable_intake.py` exactly (same setup pattern) but with a provider that raises `AgenticEvidenceGatheringFailedError`:

```python
# tests/engine/test_agentic_evidence_gathering_failed_intake.py
"""process_alert_intake must map AgenticEvidenceGatheringFailedError to the
agentic_evidence_gathering_failed Outcome Matrix row (DEC-064), mirroring
provider_unavailable (DEC-061)."""

from __future__ import annotations

from dataclasses import dataclass

from praetor.contracts.judgment import ModelJudgment
from praetor.contracts.disposition import Disposition
from praetor.engine.orchestrator import WalkingSkeletonEngine
from praetor.judgment.agentic.errors import AgenticEvidenceGatheringFailedError
from praetor.judgment.provider import JudgmentRequest, ProviderProbeResult
from praetor.metrics.events import OutcomeMatrixFaultFlag
from praetor.state.store import open_state_store
from tests.engine.helpers import bootstrap_active_org_config, skeleton_bundle
from tests.engine.stamp_fakes import SucceedingStampBackend


@dataclass
class _AlwaysFailsAgenticProvider:
    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        raise AgenticEvidenceGatheringFailedError("all sources failed")

    def probe(self, canary_payload: object) -> ProviderProbeResult:
        return ProviderProbeResult(
            success=False, provider_name="agentic", model_name="agentic", metadata={}
        )


def test_intake_escalates_on_agentic_evidence_gathering_failure(tmp_path) -> None:
    store = open_state_store(tmp_path / "t.db")
    bootstrap_active_org_config(store)
    engine = WalkingSkeletonEngine(
        store=store,
        judgment_provider=_AlwaysFailsAgenticProvider(),
        stamp_backend=SucceedingStampBackend(),
    )
    result = engine.process_intake(evidence_bundle=skeleton_bundle(), correlate=False)

    assert result.disposition == Disposition.ESCALATE
    assert (
        OutcomeMatrixFaultFlag.AGENTIC_EVIDENCE_GATHERING_FAILED.value in result.fault_flags
    )
    assert result.edict is not None
    assert result.edict.system_fault_escalation is True
```

Note: use whatever `bootstrap_active_org_config`/`skeleton_bundle`/`SucceedingStampBackend` helpers `tests/engine/test_provider_unavailable_intake.py` actually imports — mirror that file's imports exactly rather than the names guessed here if they differ.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/engine/test_agentic_evidence_gathering_failed_intake.py -v`
Expected: FAIL — `AttributeError: AGENTIC_EVIDENCE_GATHERING_FAILED`

- [ ] **Step 3: Register the fault flag**

In `src/praetor/metrics/events.py`, add to `OutcomeMatrixFaultFlag`:

```python
    AGENTIC_EVIDENCE_GATHERING_FAILED = "agentic_evidence_gathering_failed"
```

In `src/praetor/contracts/fault_flags.py`, add to `OUTCOME_MATRIX_SFE`:

```python
    OutcomeMatrixFaultFlag.AGENTIC_EVIDENCE_GATHERING_FAILED: True,
```

- [ ] **Step 4: Add the orchestrator except clause**

In `src/praetor/engine/orchestrator.py`, add the import:

```python
from praetor.judgment.agentic.errors import AgenticEvidenceGatheringFailedError
```

After the existing `except ProviderUnavailableError:` block (around line 402-409), add:

```python
    except AgenticEvidenceGatheringFailedError:
        return _finish_system_fault(
            store,
            attempt,
            judgment_provider,
            fault_flag=OutcomeMatrixFaultFlag.AGENTIC_EVIDENCE_GATHERING_FAILED.value,
            metrics_collector=metrics_collector,
        )
```

Note this deliberately uses `_finish_system_fault` directly (not `_finish_provider_fault`) — it does **not** trip the provider-health breaker, since an all-sources-evidence-gathering failure is a data-layer problem, not a signal about LLM provider health; conflating the two domains would let a SQLite/store hiccup needlessly trip the breaker that gates single-shot provider calls too.

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/engine/test_agentic_evidence_gathering_failed_intake.py -v`
Expected: PASS

- [ ] **Step 6: Add the eval-harness scenario for Outcome Matrix completeness**

`test_outcome_matrix_completeness_guard` (`tests/evals/test_eval_harness.py`) will now fail because `AGENTIC_EVIDENCE_GATHERING_FAILED` has no scenario coverage. The `engine_intake` runner drives `FakeProvider`, not `AgenticJudgmentProvider` — for harness purposes we only need the same typed-exception → fault-flag mapping proven, which reuses `FakeProvider` exactly like `FakeProviderMode.UNAVAILABLE` does for `provider_unavailable`.

In `src/praetor/judgment/fake_provider.py`, add to `FakeProviderMode`:

```python
    AGENTIC_EVIDENCE_GATHERING_FAILED = "agentic_evidence_gathering_failed"
```

In `FakeProvider.generate_judgment`, add before the `FakeProviderMode.MALFORMED_JSON` check:

```python
        if mode == FakeProviderMode.AGENTIC_EVIDENCE_GATHERING_FAILED:
            from praetor.judgment.agentic.errors import AgenticEvidenceGatheringFailedError

            raise AgenticEvidenceGatheringFailedError("fake all-sources-failed")
```

In `evals/harness.py`, find `_provider_mode` (around line 473) and add the new mode string to whatever mapping it uses from `setup["provider_mode"]` string to `FakeProviderMode` — mirror exactly how `"unavailable"` is mapped to `FakeProviderMode.UNAVAILABLE` there.

Create `evals/scenarios/agentic_evidence_gathering_failed.yaml`, mirroring `evals/scenarios/provider_unavailable.yaml`:

```yaml
schema_version: "1"
scenario_id: agentic_evidence_gathering_failed
description: All Phase 1 agentic evidence sources failing escalates with system_fault_escalation true.
runner: engine_intake
setup:
  alert_identity: agentic_evidence_gathering_failed
  provider_mode: agentic_evidence_gathering_failed
expectations:
  final_disposition: escalate
  fault_flags:
    - agentic_evidence_gathering_failed
  system_fault_escalation: true
  metrics:
    policy_gate_evaluations_total: 0
    llm_failure_by_fault_flag:
      agentic_evidence_gathering_failed: 1
```

Note: the `metrics.llm_failure_by_fault_flag` expectation assumes `_finish_system_fault` records the failure the same way `_finish_provider_fault` does. Since Step 4 used `_finish_system_fault` directly (skipping the breaker hook, not the metrics recording), check `_finish_system_fault`'s body for whether it unconditionally records `llm_failure_by_fault_flag` regardless of the breaker-hook parameters — if it only records that metric when called via `_finish_provider_fault`, adjust this scenario's `metrics` block to match what `_finish_system_fault` actually records (read the function body — it was shown during planning at `src/praetor/engine/orchestrator.py:716-745` — before finalizing this expectation), rather than assuming the two paths behave identically.

- [ ] **Step 7: Run the full eval harness**

Run: `pytest tests/evals/test_eval_harness.py -v`
Expected: All PASS, including `test_outcome_matrix_completeness_guard`

- [ ] **Step 8: Add `DecisionEdict.session_trace_hash` and thread it through from `ModelJudgment`**

In `src/praetor/contracts/edict.py`, add the field:

```python
    session_trace_hash: str | None = None
    """Agentic-mode session evidence registry hash (DEC-064), copied from
    ModelJudgment.session_trace_hash (added in Task 13). None for
    single-shot-mode edicts."""
```

In `src/praetor/engine/edict.py`, in `build_decision_edict`, find the `DecisionEdict(` constructor call and add one field, copying it straight from the judgment that was already passed in:

```python
    return DecisionEdict(
        decision_id=decision_id,
        alert_reference=attempt.alert_identity,
        evidence_bundle_hash=bundle_hash,
        org_config_snapshot_hash=attempt.org_config_snapshot_hash,
        live_never_contain_hash=live_hash,
        model_judgment=judgment,
        session_trace_hash=judgment.session_trace_hash,
        policy_gate_result=PolicyGateResult(
```

(Insert `session_trace_hash=judgment.session_trace_hash,` immediately after `model_judgment=judgment,` — leave every other field in that call exactly as it is today.)

Add a new test file `tests/contracts/test_edict_session_trace_hash.py`:

```python
"""ModelJudgment/DecisionEdict.session_trace_hash backward compatibility
and pass-through (DEC-064, Task 13/14 of
docs/superpowers/plans/2026-07-30-agentic-judgment.md)."""

from __future__ import annotations

from praetor.contracts.disposition import Disposition
from praetor.contracts.judgment import ModelJudgment


def _judgment(session_trace_hash: str | None = None) -> ModelJudgment:
    return ModelJudgment(
        proposed_disposition=Disposition.STANDARD_REVIEW,
        cited_evidence_refs=[],
        key_tells=[],
        org_config_refs=[],
        benign_alternatives=[],
        benign_alternatives_ruled_out=[],
        convergence_reasoning="none",
        narrative="none",
        model_name="fake",
        provider_name="fake",
        session_trace_hash=session_trace_hash,
    )


def test_model_judgment_session_trace_hash_defaults_to_none() -> None:
    judgment = ModelJudgment(
        proposed_disposition=Disposition.STANDARD_REVIEW,
        cited_evidence_refs=[],
        key_tells=[],
        org_config_refs=[],
        benign_alternatives=[],
        benign_alternatives_ruled_out=[],
        convergence_reasoning="none",
        narrative="none",
        model_name="fake",
        provider_name="fake",
    )
    assert judgment.session_trace_hash is None


def test_model_judgment_session_trace_hash_round_trips() -> None:
    judgment = _judgment(session_trace_hash="deadbeef" * 8)
    assert judgment.session_trace_hash == "deadbeef" * 8
```

Add one more test to `tests/engine/test_engine_ids.py` (or wherever `build_decision_edict` is already directly unit-tested — grep `tests/engine/*.py` for `build_decision_edict(` to find it; if no file calls it directly, add this to a new `tests/engine/test_edict_session_trace_hash.py` instead), reusing that file's existing `ProcessingAttempt`/`SkeletonDisposition` construction pattern:

```python
def test_build_decision_edict_copies_session_trace_hash_from_judgment() -> None:
    from praetor.engine.edict import build_decision_edict, skeleton_policy_result
    from tests.contracts.test_edict_session_trace_hash import _judgment

    judgment = _judgment(session_trace_hash="deadbeef" * 8)
    edict = build_decision_edict(
        attempt=_some_processing_attempt(),  # reuse this file's existing attempt fixture
        judgment=judgment,
        disposition=skeleton_policy_result(judgment),
        live_never_contain_entries=[],
        stamp_status="not_required",
        ticket_stamp_payload={},
    )
    assert edict.session_trace_hash == "deadbeef" * 8
```

Replace `_some_processing_attempt()` with whatever this test file's existing helper for building a `ProcessingAttempt` fixture is actually called — every other test in that file already builds one; call the same helper rather than constructing a new one.

- [ ] **Step 9: Run the full test suite**

Run: `pytest -v`
Expected: All PASS — `session_trace_hash` is optional with a default, so no existing `DecisionEdict` construction anywhere in the codebase or tests should break.

- [ ] **Step 10: Update docs**

In `docs/decisions.md`, add a new row to the table and a full section, following the exact format of DEC-059/DEC-061:

```markdown
| DEC-064 | 2026-07-30 | Agentic judgment: `ledger_history` added to the DEC-059 non-attacker-controllable provenance set; `org_config_section` and `similar_cases` are explicitly **not** corroboration-eligible (org-config content flows through `ModelJudgment.org_config_refs`, never `cited_evidence_refs`; similar-case exemplars remain illustration-only per existing `EXEMPLAR_SCOPE_INSTRUCTIONS`); new Outcome Matrix row `agentic_evidence_gathering_failed` (`system_fault_escalation=true`) for all-Phase-1-sources-failed | Extends DEC-059's corroboration floor to a genuine second independent observation source (Praetor's own past decisions) without opening a free-corroboration hole via always-available static content; mirrors DEC-061's minimal-orchestrator-catch pattern for the new failure mode | `docs/superpowers/specs/2026-07-30-agentic-judgment-design.md`; `src/praetor/evidence/provenance.py`; `src/praetor/judgment/agentic/`; `src/praetor/metrics/events.py`; `src/praetor/contracts/fault_flags.py` |
```

In `docs/contracts.md`, add the `agentic_evidence_gathering_failed` row to the §13 Outcome Matrix table (same columns as the `provider_unavailable` row) and document `DOMAIN_SESSION_TRACE`/`compute_session_trace_hash` alongside the other hash domains in whatever section documents `DOMAIN_LEDGER_LINK`.

In `docs/architecture.md`, add one row to the "Major subsystems" package table:

```markdown
| `praetor.judgment.agentic` | 3-phase agentic judgment pipeline (opt-in `JudgmentProvider`) | — |
```

- [ ] **Step 11: Commit**

```bash
git add src/praetor/metrics/events.py src/praetor/contracts/fault_flags.py src/praetor/contracts/edict.py src/praetor/engine/orchestrator.py src/praetor/judgment/fake_provider.py evals/harness.py evals/scenarios/agentic_evidence_gathering_failed.yaml docs/decisions.md docs/contracts.md docs/architecture.md tests/engine/test_agentic_evidence_gathering_failed_intake.py tests/contracts/
git commit -m "feat(judgment): register agentic_evidence_gathering_failed Outcome Matrix row and session_trace_hash"
```

---

## Final verification

- [ ] Run the full suite: `pytest -v` — all pass, including the 32 original eval-harness scenarios (untouched) plus the new `agentic_evidence_gathering_failed` scenario.
- [ ] Run `ruff check .` and `mypy .` — clean (fix anything the new package introduces before considering this plan done).
- [ ] Confirm no file outside `src/praetor/judgment/agentic/`, `src/praetor/evidence/provenance.py`, `src/praetor/hashing/domains.py`, `src/praetor/ledger/store.py`, `src/praetor/judgment/provider.py`, `src/praetor/judgment/fake_provider.py`, `src/praetor/contracts/edict.py`, `src/praetor/contracts/fault_flags.py`, `src/praetor/metrics/events.py`, `src/praetor/engine/orchestrator.py`, `evals/`, and `docs/` was touched — `PolicyGate` evaluation logic (`src/praetor/policy/`) must show zero diffs, matching this plan's Global Constraints.
