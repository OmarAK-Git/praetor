# Verifier result — agentic-judgment-11-phase1

**Verdict: PASS (survives)**

**Claim under test:** Task 11 is done — Phase 1 fans out four source investigators concurrently with per-source `BudgetTracker` limits; per-source failures degrade into `SessionEvidenceRegistry`; focused Phase 1 tests pass.

---

## Fresh command evidence

Working directory: `C:\Users\oalan\Praetor\.worktrees\agentic-judgment`  
`PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`

| Command | Outcome |
|---|---|
| `pytest tests/judgment/agentic/test_phases.py -v` | **4 passed** in 0.28s |
| `ruff check src/praetor/judgment/agentic/phases.py tests/judgment/agentic/test_phases.py` | All checks passed |
| `mypy src/praetor/judgment/agentic/phases.py` | Success: no issues found in 1 source file |

---

## Focus-check findings

### 1. Concurrency — survives

- `run_source_fanout` uses `ThreadPoolExecutor(max_workers=4)` and submits all four `run_*_source` helpers (`phases.py:189-213`).
- All four `.result()` joins complete inside the `with` block (`phases.py:214-219`); registry mutation is only afterward on the calling thread (`phases.py:221-228`). No worker-thread registry writes.

**Gap (non-blocking):** No test proves temporal overlap. Sequential substitution would still pass the suite. Implementation nonetheless matches the prescribed concurrent executor.

### 2. Per-source budgets — survives

- `_drive_investigation` constructs `BudgetTracker(budget=budget)` per call (`phases.py:49`). `PhaseBudget` is frozen; trackers own independent `calls_made`.
- Independent probe: two concurrent over-budget models with `max_tool_calls=2` each made exactly 2 calls (`{'l': 2, 'w': 2}`).
- `test_fanout_respects_budget_and_stops_calling` asserts `len(ok_tool.calls) == 1` with `max_tool_calls=1`.

**Gap (non-blocking):** Budget test only stresses the ledger source; other sources use `call_plan=()`. Isolation is proven by structure + independent probe, not by a four-way concurrent budget test.

### 3. Graceful degradation — survives

- Source success is `any(record.succeeded for record in records)` (`phases.py:91`, `130`, `152`); empty records → `False`.
- `SourceFanoutResult.all_failed` is the negated OR of the four flags (`phases.py:162-169`).
- Failed invocations still become records and are appended (loops do not filter on `succeeded`). Independent probe of the all-fail path:
  - `evidence_entries`: 2 (`ledger_history`, `wider_telemetry`), both `succeeded=False`
  - `org_config_entries`: 1 failed
  - `exemplar_entries`: 1 failed
- `test_fanout_partial_failure_does_not_mark_all_failed` and `test_fanout_all_sources_failed_marks_all_failed` cover aggregate flags.

**Gap (non-blocking):** Suite never asserts failed rows landed in `*_entries`. Production behavior confirmed by probe, not by tests. Unhandled `tool.invoke` exceptions still propagate via `future.result()` (tool-level `succeeded=False` only — matches plan).

### 4. Fixed registry order — survives

Append order is ledger → org-config → similar-cases → wider-telemetry via `record_evidence` / `record_org_config` / `record_exemplars` / `record_evidence` (`phases.py:221-228`), after all futures complete — independent of thread finish order.

**Gap (non-blocking):** No shuffle/barrier test pinning `session_trace_hash` stability under reordered completion.

### 5. `wider_telemetry` happy-path `call_plan` deviation — survives (fixture fix, not semantic change)

Independent confirmation:

| Fixture | Result |
|---|---|
| `FakeSourceInvestigatorModel(call_plan=())` | `next_action` → `InvestigationSummary` immediately |
| `run_wider_telemetry_source(..., call_plan=())` | `succeeded=False`, `n_records=0` (`any([])` is `False`) |
| Plan happy-path with `call_plan=()` | `wider_telemetry_succeeded is False` — would fail `assert ... is True` |
| Implementer `call_plan=({},)` | Coherent with happy-path asserts |

Task 13 plan note (~line 2496) requires zero-call sources to count as not succeeded for `all_failed`. Production semantics unchanged; only the inconsistent plan fixture was corrected.

### 6. Boundary / untouched paths — survives (for this task)

- Task-scoped new files only: `src/praetor/judgment/agentic/phases.py`, `tests/judgment/agentic/test_phases.py` (both `??`).
- `src/praetor/policy/*`: git status dirty but **zero content diff** (CRLF noise only).
- `src/praetor/judgment/provider.py` has an `evidence_bundle` field addition — belongs to **task 04** (`agentic-judgment-04-request-wiring`), not Task 11. Out of this task's `files_allowed`; not introduced by the implementer for Phase 1.

---

## Acceptance criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Four-way concurrent fan-out with per-source `BudgetTracker` | Met (code + budget test + isolation probe) |
| 2 | Per-source failures degrade into registry | Met (code + failed-record probe; tests weak) |
| 3 | Focused Phase 1 tests pass | Met (4/4 fresh) |

---

## Gaps (non-blocking)

1. No concurrency-overlap proof in tests.
2. No registry-order / `session_trace_hash` stability test under shuffled completion.
3. Failed-record append not asserted by the suite (verified by independent probe).
4. Plan doc Task 11 Step 1 still shows `wider_telemetry` `call_plan=()` with `succeeded is True` — doc inconsistency remains; out of `files_allowed`.

## Strongest reason the claim survives

Fresh scoped verification is green, and adversarial probes confirmed the three load-bearing behaviors the suite under-tests: per-source budget isolation, failed-record registry append, and zero-call ⇒ not-succeeded (validating the `call_plan=({},)` fixture fix as non-semantic). No production defect found that falsifies the acceptance criteria.
