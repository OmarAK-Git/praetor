# Code review — agentic-judgment-05-ledger-history

**Reviewer:** code-reviewer (fresh context)  
**Scope:** Task 5 — `fetch_edicts_for_target_history` ledger query helper  
**Spec:** `.workflow/agentic-judgment-05-ledger-history/plan.md`

## Verdict: **PASS**

Remediation required before verification: **No**

---

## What was reviewed

| Area | Evidence |
|------|----------|
| Diff | `src/praetor/ledger/store.py` (+`fetch_edicts_for_target_history`, logging/ValidationError imports); new `tests/ledger/test_target_history.py` (untracked) |
| SQL scope | `WHERE record_type = ? AND (json_extract(..., '$.alert_reference') = ? OR json_extract(..., '$.containment_directive.target_id') IN (...))` — matches design OR semantics |
| Schema | `_LEDGER_SCHEMA_SQL` and `append_ledger_record` body unchanged in diff |
| PolicyGate boundary | `git diff HEAD -- src/praetor/policy/` — no content changes |
| Tests (fresh run) | `pytest tests/ledger/test_target_history.py -v` → 3 passed |
| Lint/type | `ruff check` and `mypy` on scoped paths — clean |

---

## Findings

### Critical

None.

### Important

None.

### Minor (non-blocking)

1. **`tests/ledger/test_target_history.py:114-124`** — `test_fetch_respects_limit` asserts `len(results) == 2` only; does not assert newest-first ordering (`ORDER BY chain_sequence DESC`). Acceptable for task acceptance criteria but a stronger test would pin `decision_id` order (`d2`, `d1`).

2. **`tests/ledger/test_target_history.py`** — No test for combined OR in one call (row matching `alert_reference` while another matches `target_id` in the same result set). Covered implicitly by separate unit tests; combined case is low risk.

3. **`src/praetor/ledger/store.py:136-137`** — Malformed `record_json` rows are skipped with a warning rather than failing the query. Matches prescribed plan behavior; no test covers the skip path.

4. **`tests/ledger/test_target_history.py`** — File is untracked (`??`); expected per standing order not to commit.

---

## Spec compliance

| Acceptance criterion | Status |
|---------------------|--------|
| `fetch_edicts_for_target_history` returns edicts by `alert_reference` or `containment_directive.target_id` | Met — SQL uses exact JSON paths; `test_fetch_by_alert_reference` and `test_fetch_by_containment_target` pass |
| Query respects `limit`; no new indexes/schema | Met — `LIMIT ?` parameterized; `_LEDGER_SCHEMA_SQL` unchanged; no `CREATE INDEX` |
| Focused ledger history tests pass | Met — 3/3 passed (fresh run) |
| Read-only helper; no edict-append path changes | Met — `append_ledger_record` untouched |
| PolicyGate evaluation logic untouched | Met — no `src/praetor/policy/` diff |
| Files allowed only | Met — production change confined to `store.py`; tests in `test_target_history.py` |

---

## Correctness / security / simplicity

- **SQL correctness:** Filters `record_type = decision_edict` via `DECISION_EDICT_RECORD_TYPE` constant; OR clause omitted when `target_ids` empty (alert-reference-only query). Parameterized placeholders for all dynamic values — no injection surface from f-string (structure-only interpolation).
- **JSON null handling:** `json_extract` on missing `containment_directive` yields SQL `NULL`, which does not satisfy `IN (...)` — correct for edicts without directives.
- **Deserialization:** `DecisionEdict.model_validate_json` on stored canonical JSON matches existing ledger read patterns.
- **Security:** Read-only SELECT; no permission widening; no new deserialization of untrusted input beyond existing ledger trust model.
- **Simplicity:** Implementation matches plan Task 5 Step 3 verbatim; no duplicate query helpers in repo.

---

## Summary

Implementation matches plan Task 5 and design spec LedgerHistoryTool v1 scope (alert recurrence OR prior containment `target_id` on already-persisted fields). No schema changes, append path unchanged, PolicyGate untouched. Proceed to skeptic verification.
