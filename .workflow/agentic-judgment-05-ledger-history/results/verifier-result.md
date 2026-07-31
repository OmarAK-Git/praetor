# Verifier result — agentic-judgment-05-ledger-history

**Verdict:** PASS (claim survives)
**Role:** skeptic-verifier (fresh context; implementer transcript treated as unevidenced)

## Claim under test

Task 5 adds `fetch_edicts_for_target_history` that returns matching `DecisionEdict`s by `alert_reference` or containment `target_id`, respects `limit`, invents no new ledger indexes/schema, leaves PolicyGate untouched, and focused tests pass.

## Fresh command evidence

Working directory: `C:\Users\oalan\Praetor\.worktrees\agentic-judgment`  
`PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`

| Command | Result |
|---------|--------|
| `pytest tests/ledger/test_target_history.py -v` | **3 passed** in 0.48s (exit 0) |
| `ruff check src/praetor/ledger/store.py tests/ledger/test_target_history.py` | All checks passed (exit 0) |
| `mypy src/praetor/ledger/store.py` | Success: no issues found in 1 source file (exit 0) |

## Focus-check evidence

### 1. SQL scope — PASS

`src/praetor/ledger/store.py:93-138`:

- `WHERE record_type = ?` bound to `DECISION_EDICT_RECORD_TYPE` (`"decision_edict"` from `hash_chain.py:33`)
- AND `(json_extract(..., '$.alert_reference') = ?{target_clause})`
- `target_clause` is empty unless `target_ids` is truthy; when present it is `OR json_extract(..., '$.containment_directive.target_id') IN (...)`
- Empty `target_ids=()` → alert-reference branch only (confirmed in `test_fetch_by_alert_reference` at `tests/ledger/test_target_history.py:95-97`)

### 2. No new schema — PASS

`git diff HEAD -U0 -- src/praetor/ledger/store.py` adds only:

- imports (`logging`, `ValidationError`, `DECISION_EDICT_RECORD_TYPE`)
- `_logger`
- new `fetch_edicts_for_target_history` after `fetch_ledger_tip_hash`

No hunks alter `_LEDGER_SCHEMA_SQL`, `init_ledger_schema`, or `append_ledger_record`. No `CREATE INDEX` in the diff (only docstring mention of indexing).

### 3. PolicyGate untouched — PASS

`git diff HEAD -- src/praetor/policy/` and `--numstat` / `--ignore-cr-at-eol` show **no content hunks**.  
Byte compare: `src/praetor/policy/gate.py` WT == HEAD == index (`equal True`).  
`git status` lists policy files as ` M` — **stat/line-ending noise only**, not content changes.

### 4. Limit — PASS

`test_fetch_respects_limit` (`tests/ledger/test_target_history.py:114-124`): 3 appended edicts, `limit=2`, asserts `len(results) == 2`. Fresh pytest run passed.

### 5. Target match isolation — PASS

`test_fetch_by_containment_target` (`tests/ledger/test_target_history.py:108-111`) uses `alert_reference="alert-unrelated"` with `target_ids=("HOST-99",)` and expects only `d1` — match cannot be via alert reference.

## Acceptance criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Match by `alert_reference` or containment `target_id` | Met | SQL + `test_fetch_by_alert_reference` / `test_fetch_by_containment_target` |
| Respects `limit`; no new indexes beyond existing fields | Met | `LIMIT ?`; schema/append untouched; JSON extract on existing fields |
| Focused ledger history tests pass | Met | Fresh 3/3 pass |

## Gaps (non-blocking)

1. **Order unasserted:** `test_fetch_respects_limit` checks length only, not `ORDER BY chain_sequence DESC` (`d2`, `d1`). Implementation orders DESC; test does not pin it.
2. **No combined OR case:** separate tests cover each branch; no single call asserting both alert-match and target-match rows together.
3. **Malformed skip untested:** `ValidationError` → warn-and-skip path (`store.py:136-137`) has no test.
4. **Worktree dirt noise:** many `src/praetor/ledger/*` and `src/praetor/policy/*` files show ` M` in status; content diff for this task is confined to `store.py` (+53/−1) plus untracked `tests/ledger/test_target_history.py`.

## Strongest reason claim survives

Independent fresh pytest/ruff/mypy all green, and direct read of the SQL + diffs confirms the five skeptic focus checks (including empty-`target_ids` alert-only branch, unchanged schema/append, and target isolation via non-matching alert reference) without relying on the implementer transcript.
