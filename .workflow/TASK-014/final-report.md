# Final Report: TASK-014

## Summary

Complete. Task 14 added provider-facing prompt construction and excerpt hygiene: sanitized `PromptExcerptSet` payloads, 200-character head+tail excerpt truncation, incomplete-content notices, verbatim org-config context, and structured-output instructions.

Code review found and the implementation now covers two hardening cases: normalized/nested `raw_source` keys are stripped, and walking-skeleton top-level `process_name` evidence remains available to the prompt.

## Completed requirements

| Requirement | Evidence |
|---|---|
| REQ-001 | `PromptFact.evidence_id`; `tests/judgment/test_prompt_isolation.py` stable-ID assertions. |
| REQ-002 | `MAX_PROMPT_EXCERPT_CHARS = 200`; scoped tests assert all excerpt lengths are capped. |
| REQ-003 | `_head_tail_truncate` emits `[...omitting N characters]`; scoped test parses and verifies count. |
| REQ-004 | Head+tail truncation keeps leading and trailing command content. |
| REQ-005 | `INCOMPLETE_CONTENT_WARNING` appears when any excerpt is truncated. |
| REQ-006 | `raw_source` is recursively excluded from prompt output, including normalized/nested fields. |
| REQ-007 | `process_alert_intake` passes `org_config_verbatim`; over-budget config still escalates before provider call. |
| REQ-008 | `STRUCTURED_OUTPUT_SCHEMA_INSTRUCTIONS` tells providers to return JSON validating as `ModelJudgment`. |
| REQ-009 | `JudgmentRequest.payload` carries `prompt_excerpt_set` rather than raw bundle facts. |

## Files changed

- `src/praetor/judgment/excerpt.py`
- `src/praetor/judgment/prompt.py`
- `src/praetor/judgment/__init__.py`
- `src/praetor/engine/orchestrator.py`
- `tests/judgment/test_prompt_isolation.py`
- `.workflow/TASK-014/*`
- `memory-bank/activeContext.md`
- `memory-bank/progress.md`
- `memory-bank/tasks.md`

## Verification performed

- `python -m pytest -q tests/judgment/test_prompt_isolation.py` — red before implementation: `ModuleNotFoundError: No module named 'praetor.judgment.excerpt'`; review red: 3 expected failures for nested `raw_source` and missing `process_name`; final green: 5 passed
- `python -m pytest -q tests/judgment/` — 15 passed
- `python -m pytest -q tests/engine/` — 26 passed
- `python -m pytest -q` — 359 passed
- `python -m mypy src` — success, 72 source files
- `python -m ruff check src tests` — all checks passed
- Focused code review — no blocking prompt/excerpt issues remain after review fixes

## Known gaps

- Real provider adversarial probing remains Task 27.
- Generalized evidence citation validation remains Task 15.
- PolicyGate remains Task 17.

## Follow-up tasks

- TASK-015: Evidence Citation Validator.
- Later Phase 2 tasks: PolicyGate, provider-health breaker, eval harness, real-provider adversarial probe.

## Archive decision

- Accepted

## safe_to_commit

yes
