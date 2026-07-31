# Verifier result — agentic-judgment-10-fake-models

**Verdict:** PASS (claim **survives**)

**Strongest reason:** Fresh pytest/ruff/mypy all clean; runtime `isinstance` against Task 9 Protocols is True for all three Fakes; implementation matches plan Task 10 Step 3; zero `raw_source` / EvidenceFact field access in `fake_model.py`.

---

## Claim restated

Task 10 adds deterministic `FakeSourceInvestigatorModel`, `FakeHypothesisModel`, and `FakeLeadModel` implementing the Task 9 model Protocols; fakes never read `EvidenceFact.raw_source`; focused fake-model tests pass; no provider composition / policy / phases changes in this task's deliverables.

---

## Evidence gathered (independent)

### Commands (PYTHONPATH=`C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`)

| Command | Outcome |
|---------|---------|
| `pytest tests/judgment/agentic/test_fake_model.py -v` | **3 passed** in 0.26s |
| `ruff check src/praetor/judgment/agentic/fake_model.py tests/judgment/agentic/test_fake_model.py` | All checks passed |
| `mypy src/praetor/judgment/agentic/fake_model.py` | Success: no issues found in 1 source file |
| Runtime `isinstance(Fake*, Protocol)` for all three | **True** |
| Determinism probe: same `prior_call_count` with `last_call_succeeded` ∈ {None, False, True} | Same `ToolCallDecision.arguments` / same `InvestigationSummary.narrative` |

### File reads

| Check | Evidence |
|-------|----------|
| Three Fake classes + plan Step 3 fidelity | `fake_model.py:20-69` matches `docs/.../2026-07-30-agentic-judgment.md` ~1745–1807 (cosmetic signature wraps only) |
| Keyword-only Protocol methods | `inspect.signature`: all three methods use `*` before params |
| `raw_source` in `fake_model.py` | Zero matches (`Select-String` / ripgrep) |
| EvidenceFact field access in fake | None — only `Sequence[EvidenceFact]` typed pass-through to factories (`fake_model.py:45-49`, `59-68`) |
| No HTTP/client/orchestration | Zero matches for http/gemini/vertex/phases imports in `fake_model.py` |
| Prescribed tests present | `test_fake_model.py`: three named tests at L19, L34, L52 |
| Task deliverables scoped | Only `?? fake_model.py` and `?? test_fake_model.py` as new Task 10 files; no `phases.py` |
| No provider composition | Module is pure dataclasses + factory delegation |

### Protocol conformance (CRITICAL)

```
SourceInvestigator: True
Hypothesis: True
Lead: True
```

Signatures:

- `next_action(self, *, prior_call_count, last_call_succeeded) -> ToolCallDecision | InvestigationSummary`
- `build_case(self, *, stance, registry_facts, budget) -> HypothesisCase`
- `reconcile(self, *, registry_facts, malicious_case, benign_case, budget) -> ModelJudgment`

### Determinism (CRITICAL)

`FakeSourceInvestigatorModel.next_action` indexes solely by `prior_call_count` vs `len(call_plan)` (`fake_model.py:32-35`). `last_call_succeeded` is accepted and unused. Fresh probe confirmed identical outputs across `last_call_succeeded` values. Factory fakes add no randomness/I/O.

### Behavioral tests (CRITICAL)

All three plan-prescribed tests exist and pass:

1. `test_fake_source_investigator_replays_call_plan_then_summarizes` — two `ToolCallDecision` then `InvestigationSummary`
2. `test_fake_hypothesis_model_delegates_to_factory` — stance + key_points from factory
3. `test_fake_lead_model_delegates_to_factory` — `Disposition.ESCALATE` via `skeleton_model_judgment`

---

## Adversarial probes (did not refute)

| Probe | Result |
|-------|--------|
| Weakened assertions (2nd plan args / summary narrative unchecked) | Plan Step 1 verbatim — letter-compliant; behavior still correct under manual probe |
| `calls_seen` side effect could drive replay | Does not — only `prior_call_count` selects plan entry |
| Factory `len(facts)` in test leaks raw_source | Test factory only; fake never reads fact fields |
| Dirty `src/praetor/policy/*` / `fake_provider.py` in worktree | Pre-existing worktree dirt (CRLF/warnings; not Task 10 deliverables). Task 10 files are the two new untracked allowed paths only |
| `tools.py` writes `raw_source=` | Outside fake_model; not a Fake read |

---

## Gaps (non-blocking)

1. Tests do not assert second plan-entry arguments or `InvestigationSummary.narrative` (plan-prescribed weakness).
2. No automated test for `last_call_succeeded` independence or Protocol `isinstance` (verified manually this run).
3. Worktree carries unrelated dirty policy/fake_provider paths; do not attribute to Task 10, but they exist in the same tree.

---

## Acceptance criteria

| Criterion | Status |
|-----------|--------|
| Fake* implement Protocols deterministically | **Met** |
| Fakes never read `EvidenceFact.raw_source` | **Met** |
| Focused fake-model tests pass | **Met** (3/3) |
| No provider composition in this task | **Met** |
