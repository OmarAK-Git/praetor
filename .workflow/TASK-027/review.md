# Review: TASK-027 (gatekeeper reopen)

## Spec compliance review

- REVIEW-001: `mypy src evals consumer_sdk` gates all `evals/` modules; `real_provider_adversarial.py` and `harness.py` pass strict mypy (102 files).
- REVIEW-002: Mocked Gemini path tests cover happy path, HTTPError, URLError, missing candidate text, non-string text, and prompt carries `SCENARIO_ID` + `INJECTION_MARKER`.
- REVIEW-003: `assert_structural_preconditions` reads excerpt texts from `request.payload["prompt_excerpt_set"]`; truncated fixture exercises `incomplete=true` + omission marker from payload.
- REVIEW-004: `raw_source_excluded` uses structural `_payload_has_raw_source_key` tree walk, not substring grep.
- REVIEW-005: `docs/decisions.md` DEC-047 and `docs/eval_gates.md` distinguish Task 14 structural vs Task 27 probabilistic evidence.

## Code quality review

- `tests/evals/__init__.py` intentionally omitted: adding it shadows top-level `evals` when pytest resolves imports from `tests/` path.
- `types-PyYAML` added to dev deps; removed stale `type: ignore` on `config/loader.py` yaml imports.
- `evals/harness.py` `PolicyGateKwargs` TypedDict fixes mypy `**kwargs` expansion.

## Risk review

- Live model compliance remains non-deterministic; integration test still non-gating.
- Truncated fixture uses marker at command_line tail so head+tail truncation preserves `INJECTION_MARKER` in payload excerpts.

## Human review notes

- None.
