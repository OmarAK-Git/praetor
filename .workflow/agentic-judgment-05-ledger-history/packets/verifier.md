# Verifier packet — agentic-judgment-05-ledger-history

## Goal
Add `fetch_edicts_for_target_history` ledger query helper for LedgerHistoryTool.

## Acceptance criteria
- `fetch_edicts_for_target_history` returns matching `DecisionEdict`s by `alert_reference` or containment `target_id`.
- Query respects `limit` and does not invent new indexes beyond existing ledger fields.
- Focused ledger history tests pass.

## Changed files
- `src/praetor/ledger/store.py`
- `tests/ledger/test_target_history.py` (new, untracked)

## Commands (`PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`)
- `pytest tests/ledger/test_target_history.py -v`
- `ruff check src/praetor/ledger/store.py tests/ledger/test_target_history.py`
- `mypy src/praetor/ledger/store.py`

## Focus checks (skeptic)
1. **SQL scope:** In `fetch_edicts_for_target_history`, confirm `WHERE` clause is `record_type = decision_edict` AND (`alert_reference` equality OR `containment_directive.target_id` IN `target_ids`). When `target_ids=()`, only alert-reference branch applies.
2. **No new schema:** `git diff HEAD -- src/praetor/ledger/store.py` must not alter `_LEDGER_SCHEMA_SQL`, `init_ledger_schema`, or `append_ledger_record`.
3. **PolicyGate untouched:** `git diff HEAD -- src/praetor/policy/` must show no content changes.
4. **Limit:** `test_fetch_respects_limit` with 3 appended edicts and `limit=2` returns exactly 2 rows.
5. **Target match isolation:** `test_fetch_by_containment_target` uses non-matching `alert_reference` so match is via `target_id` only.

## Implementer result
`.workflow/agentic-judgment-05-ledger-history/results/implementer-result.md`

## Code review
`.workflow/agentic-judgment-05-ledger-history/results/code-review.md` — **PASS**

Treat claims as unevidenced until checked. Write `results/verifier-result.md` with PASS/BLOCK and command evidence.
