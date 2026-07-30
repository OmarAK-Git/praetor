# Code Review — rfc-remediation-04-precedent-logging

**Verdict: PASS**

**Commit reviewed:** `ad2ebf76e5b7bcacb4f0830f351144ad786548c7`  
**Scope:** RFC-005 / DEBT-022 observability — log malformed ledger edicts skipped during human-confirmed precedent fetch  
**Plan:** `.workflow/rfc-remediation-04-precedent-logging/plan.md`  
**Source:** `docs/superpowers/plans/2026-07-30-reverse-spec-rfc-remediation.md` Task 4  
**Implementer result:** `.workflow/rfc-remediation-04-precedent-logging/results/implementer-result.md`

## Summary

Additive warning on the existing `ValidationError → return None` branch in `_fetch_decision_edict`. Skip/continue behavior, public signatures, and similar-case retrieval/ranking/authorization paths are unchanged. Commit touches only the two allowed files; message matches the source plan.

## Spec compliance

| Acceptance criterion | Result |
|---|---|
| Malformed edict skipped with warning containing its decision ID | Met — `_logger.warning("malformed ledger edict for decision_id=%s skipped in precedent fetch", decision_id)` then `return None` |
| Existing similar-case retrieval unchanged | Met — no edits to ranking, exemplars, prompt wiring, or `fetch_human_confirmed_precedents` control flow beyond the logged branch; focused + `tests/judgment/test_similar_case_retrieval.py` → 6 passed |
| No ranking, PolicyGate, or authorization behavior changes | Met — commit does not touch those modules; annotation auth path used only in the test fixture |

**Interfaces (source plan):** No signature change to `_fetch_decision_edict` or `fetch_human_confirmed_precedents`; only module `_logger` + warning on the prescribed branch.

**Allowed files only:** `M src/praetor/annotations/precedent.py`, `A tests/annotations/test_precedent.py`.

**Expected adaptations (not defects):**

- Plan’s `"logging.LogCaptureFixture"` / `logging.WARNING` → `pytest.LogCaptureFixture` and string `"WARNING"` (ruff / repo convention; same as remediation-01).
- Corrupt JSON extracted to `corrupt_json` for line length; payload identical to the plan.

## Logging quality & decision-ID visibility

- Logger is `logging.getLogger(__name__)` → `praetor.annotations.precedent` (test scopes `caplog` to that name).
- Message matches the plan verbatim, including the `malformed ledger edict` phrase required by the assertion.
- `decision_id` is passed as a `%s` argument (not interpolated into the format string incorrectly); it appears in `record.message`.
- Does not dump raw `record_json` or raise/halt — matches the rescoped “log, don’t change semantics” intent for DEBT-022.

## Unchanged skip / retrieval semantics

Parent (`ad2ebf7^`) already had `except ValidationError: return None`. Diff adds only the warning before that return.

Preserved call-chain behavior:

- `_fetch_decision_edict`: still `None` when row missing; still `None` on `ValidationError`; still returns validated `DecisionEdict` on success.
- `fetch_human_confirmed_precedents`: still `continue` when `edict is None` (lines 50–52); ranking / PolicyGate / auth not in this commit.

## Correctness

- Corrupt fixture `{"decision_id": "dec-corrupt", "not_a_valid": "edict"}` is findable via `json_extract(..., '$.decision_id')` and fails `DecisionEdict.model_validate_json` (many required fields missing) — exercises the intended branch, not the missing-row path.
- Annotation + ledger setup mirrors the plan and the existing similar-case fixture pattern (`submit_annotation` + `ledger_chain`), which is the real production path that can annotate a decision whose ledger body later fails edict validation.
- No concurrency, signature, or error-handling regressions found.

## Security

Observability-only. No new trust boundaries, no permission widening, no change to PolicyGate / containment authorization. Logging decision ID (already a lookup key) without dumping the corrupt payload is appropriate.

## Simplicity / scope

Matches the prescribed implementation. No drive-by edits, no ranking/PolicyGate/auth product changes, no queue edits. Diff +7 / +90 on the two allowed files only.

## Tests

- `test_fetch_human_confirmed_precedents_logs_and_skips_malformed_edict` asserts both skip (`precedents == []`) and warning content (`malformed ledger edict` + `decision_id`).
- Would fail without the warning (empty `caplog.records`); would fail if the missing-row path were hit instead (no warning).
- Does not re-test ranking/exemplar wiring (correctly left to `test_similar_case_retrieval.py` per Task 4 note).
- Fresh re-run: 6 passed (`test_precedent.py` + `test_similar_case_retrieval.py`).

## Findings

### Critical

None.

### Important

None.

### Minor (non-blocking)

1. **`tests/annotations/test_precedent.py:87-90`** — Assertion checks message substrings only, not `record.levelno == logging.WARNING`. Acceptable; mirrors the approved plan snippet and remediation-01 precedent.

## Checked (audit trail)

- `git show` / `git diff-tree` for `ad2ebf7` (files, message, full hunk)
- Parent `_fetch_decision_edict` vs post-change (`return None` preserved)
- Plan acceptance criteria + source-plan Task 4 steps vs committed code/test
- Decision-ID present in warning format args and captured message
- No ranking / PolicyGate / authorization product edits in commit
- Implementer packet boundaries honored
- Fresh pytest of focused + similar-case suites (6 passed)
