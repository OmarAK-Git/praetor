# Code review — agentic-judgment-10-fake-models

**Reviewer:** code-reviewer (fresh context)  
**Scope:** Task 10 — deterministic Fake* model Protocol implementations  
**Spec:** `.workflow/agentic-judgment-10-fake-models/plan.md`  
**Design:** `docs/superpowers/plans/2026-07-30-agentic-judgment.md` Task 10 (lines 1663–1820)

## Verdict: **PASS**

Remediation required before verification: **No**

---

## What was reviewed

| Area | Evidence |
|------|----------|
| Production | `src/praetor/judgment/agentic/fake_model.py` (untracked, new) |
| Tests | `tests/judgment/agentic/test_fake_model.py` (untracked, new) |
| Diff baseline | Matches Task 10 Step 3 in `docs/superpowers/plans/2026-07-30-agentic-judgment.md` verbatim (cosmetic signature wraps for ruff E501 only) |
| Tests (fresh run) | `pytest tests/judgment/agentic/test_fake_model.py -v` → **3 passed** in 0.25s |
| Lint/type | `ruff check` and `mypy` on scoped paths — clean |
| Protocol conformance | `isinstance(Fake*, Protocol)` for all three → **True** (fresh runtime check) |
| `raw_source` isolation | Zero `.raw_source` references in `fake_model.py`; repo-wide grep over `*.py`/`*.md` in worktree — no matches |
| PolicyGate / provider | No changes outside `files_allowed` |

---

## Focus-area review

### 1. Spec compliance — PASS

All prescribed surfaces present in `fake_model.py`:

| Surface | Location | Status |
|---------|----------|--------|
| `FakeSourceInvestigatorModel(call_plan, summary_narrative, calls_seen)` | `fake_model.py:20-34` | Present; replays plan by `prior_call_count`, then `InvestigationSummary` |
| `FakeHypothesisModel(case_factory)` | `fake_model.py:37-49` | Present; delegates to injected factory |
| `FakeLeadModel(judgment_factory)` | `fake_model.py:52-69` | Present; delegates to injected factory with keyword args |

Tests match Task 10 Step 1 (3 behavioral tests). Unused plan imports (`datetime`, `UTC`, `EvidenceFact`) correctly omitted from test file.

### 2. Protocol conformance — PASS

All three fakes satisfy Task 9 `@runtime_checkable` Protocols:

| Fake | Protocol | Method signature match | `isinstance` |
|------|----------|------------------------|--------------|
| `FakeSourceInvestigatorModel` | `SourceInvestigatorModel` | `next_action(*, prior_call_count, last_call_succeeded)` → `ToolCallDecision \| InvestigationSummary` | True |
| `FakeHypothesisModel` | `HypothesisModel` | `build_case(*, stance, registry_facts, budget)` → `HypothesisCase` | True |
| `FakeLeadModel` | `LeadModel` | `reconcile(*, registry_facts, malicious_case, benign_case, budget)` → `ModelJudgment` | True |

Determinism: `FakeSourceInvestigatorModel` indexes `call_plan` solely by `prior_call_count`; `last_call_succeeded` is accepted per Protocol but intentionally ignored (plan-prescribed). Factory fakes are pure delegation.

### 3. `raw_source` isolation — PASS

- `fake_model.py` contains **no** attribute access on `EvidenceFact` instances — only `Sequence[EvidenceFact]` typed parameters passed through to caller-injected factories.
- No `.raw_source` reads anywhere in task files or worktree `*.py`/`*.md`.
- DEC-047 boundary preserved: fakes cannot leak raw source even if `registry_facts` carry it, because they never inspect fact fields.

### 4. Correctness — PASS

- `ToolCallDecision(arguments=dict(self.call_plan[prior_call_count]))` shallow-copies plan dicts, preventing caller mutation of stored plan entries — matches plan and Task 9 note.
- Empty `call_plan=()` immediately returns `InvestigationSummary` when `prior_call_count >= 0` — required for Task 11/12 sources that skip tool calls.
- `budget` accepted and discarded (`_ = budget`) on hypothesis/lead fakes — matches Protocol surface without inventing budget logic.
- `calls_seen` increments per `next_action` call for harness observability; does not affect replay logic.

### 5. Security — PASS

- No I/O, deserialization, or prompt assembly.
- No policy or single-shot provider changes.
- Injected factories are test-controlled; fake implementations themselves impose no new attack surface.

### 6. Simplicity — PASS

- Implementation is plan-prescribed verbatim; no duplicate abstractions.
- Module docstring correctly positions fakes as test/harness stand-ins (mirrors `fake_provider.py` role).

### 7. Tests — PASS (within Task 10 scope)

- Three tests cover call-plan replay, hypothesis factory delegation, and lead factory delegation.
- Tests would fail without the module (TDD red phase confirmed by implementer).
- Return-type `isinstance` checks on `ToolCallDecision` / `InvestigationSummary` present in investigator test.

---

## Findings

### Critical

None.

### Important

None.

### Minor (non-blocking)

1. **`test_fake_model.py:27-28`** — Second `ToolCallDecision` asserted by type only; second plan entry `{"target_ids": ["HOST-1", "HOST-2"]}` not checked. Matches plan Step 1 verbatim.

2. **`test_fake_model.py:30-31`** — `InvestigationSummary` asserted by type only; `summary_narrative` default (`"investigation complete"`) not asserted. Matches plan Step 1 verbatim.

3. **`fake_model.py:26,31`** — `calls_seen` side effect not covered by tests. Plan includes the field; observability is harness-oriented (Task 12+).

4. **Protocol `isinstance` tests** — Not in plan Step 1; conformance verified structurally and via fresh runtime `isinstance` probe. Optional explicit test could be added later but is not required by acceptance criteria.

---

## Spec compliance

| Acceptance criterion | Status |
|---------------------|--------|
| `FakeSourceInvestigatorModel` / `FakeHypothesisModel` / `FakeLeadModel` implement Protocols deterministically | Met — plan-faithful; runtime `isinstance` True |
| Fakes never read `EvidenceFact.raw_source` | Met — no fact field access; zero `raw_source` references |
| Focused fake-model tests pass | Met — 3/3 pytest, ruff, mypy |
| Files allowed only | Met — only `fake_model.py`, `test_fake_model.py`, workflow dir touched |
| PolicyGate / single-shot provider untouched | Met |

---

## Summary

Task 10 delivers deterministic Fake* Protocol implementations exactly as specified. Verification commands pass on fresh run. Protocol conformance confirmed. No `raw_source` reads. Proceed to skeptic verification.
