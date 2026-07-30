# Verifier Result — rfc-remediation-04-precedent-logging

**Outcome:** PASS  
**Verifier:** skeptic-verifier (fresh context; implementer/reviewer claims treated as unevidenced)  
**Commit checked:** `ad2ebf76e5b7bcacb4f0830f351144ad786548c7` (= `HEAD`)  
**Scope:** task acceptance criteria only (plan allowed paths)

## Claim under test

Malformed ledger edicts skipped during human-confirmed precedent fetch are logged with a warning that includes the decision ID; similar-case retrieval, ranking, PolicyGate, and authorization behavior are unchanged.

## Independent commands (reproduced)

| Command | Result |
|---------|--------|
| `pytest tests/annotations/test_precedent.py tests/judgment/test_similar_case_retrieval.py -v` | **6 passed** in 0.79s (exit 0) |
| `ruff check .` | All checks passed! (exit 0) |
| `mypy .` | Success: no issues found in 134 source files (exit 0) |

Working tree for the two implementation paths matches the commit (`git diff ad2ebf7 --` empty for those files). Commit file set is exactly the allow-list: `M src/praetor/annotations/precedent.py`, `A tests/annotations/test_precedent.py`.

## Acceptance criteria

### AC1 — Malformed edict skipped with warning containing decision ID — PASS

- Module logger: `_logger = logging.getLogger(__name__)` → `praetor.annotations.precedent` (`precedent.py:15`; confirmed at runtime).
- On `ValidationError` in `_fetch_decision_edict`, warning then `return None` (`precedent.py:90-95`):
  - message: `"malformed ledger edict for decision_id=%s skipped in precedent fetch"`
  - arg: `decision_id`
- Parent (`ad2ebf7^`) had the same `except ValidationError: return None` with no log; only the warning was added.
- Fixture `{"decision_id": "dec-corrupt", "not_a_valid": "edict"}` is findable via `json_extract(..., '$.decision_id')` and raises `ValidationError` under `DecisionEdict.model_validate_json` (independently confirmed) — exercises the malformed branch, not the missing-row path.
- `test_fetch_human_confirmed_precedents_logs_and_skips_malformed_edict` PASSED: `precedents == []` and warning message contains both `"malformed ledger edict"` and `decision_id`.

### AC2 — Existing similar-case retrieval unchanged — PASS

- Commit does not edit ranking, exemplar wiring, prompt payload, or `fetch_human_confirmed_precedents` control flow beyond the logged `ValidationError` arm.
- `fetch_human_confirmed_precedents` still `continue`s when `edict is None` (`precedent.py:50-52`).
- Independent run of `tests/judgment/test_similar_case_retrieval.py` (5 tests covering fetch, ranking, retrieval wiring, prompt exemplars, citation/`raw_source` exclusion) all PASSED.

### AC3 — No ranking, PolicyGate, or authorization behavior changes — PASS

- Commit touches only allowed files; no ranking/PolicyGate/auth product modules in the diff.
- Public signatures of `_fetch_decision_edict` and `fetch_human_confirmed_precedents` unchanged.
- Skip outcome preserved vs parent: still `return None` on `ValidationError`; only observability added.
- Auth appears only in the test fixture via `submit_annotation` / `PrincipalMapVerifier` (unchanged production auth surface).

## Attempts to refute (failed)

1. **Stale / mismatched tree** — `HEAD` is `ad2ebf7`; no dirty diff on the two paths; commit is an ancestor of `HEAD`.
2. **Test misses ValidationError path** — corrupt JSON is valid JSON with `decision_id`, so the row is found; `DecisionEdict.model_validate_json` independently raises `ValidationError`. Missing-row path would leave `caplog.records` empty and fail the assertion.
3. **Semantic drift beyond logging** — parent vs commit hunk is additive (`import logging`, `_logger`, warning call) before the pre-existing `return None`.
4. **Retrieval/ranking regression** — focused similar-case suite still green (5/5) and still imports `fetch_human_confirmed_precedents`.
5. **Broad claim from narrow green** — AC3 grounded in commit file list + parent-branch inspection, not suite breadth alone.

## Residual notes (non-blocking; do not change outcome)

- Test asserts message substrings only, not `record.levelno == logging.WARNING` (matches approved plan snippet / remediation-01 pattern).
- Non-`ValidationError` parse failures (e.g. invalid JSON → `JSONDecodeError`) remain unlogged; out of this task’s prescribed branch.

## Verdict

**PASS (survives)** — all three acceptance criteria are backed by independently reproduced pytest/ruff/mypy evidence plus parent-vs-commit inspection of the `_fetch_decision_edict` skip branch.
