# Review: TASK-014

## Spec compliance review

- REVIEW-001: Complete.
- Stable evidence IDs are preserved on every `PromptFact`.
- Excerpts are capped to 200 code points and use exact `[...omitting N characters]` markers.
- Unbounded prompt values use head+tail truncation and mark incomplete content.
- `raw_source` is excluded from top-level, normalized, and nested prompt output.
- Active org config verbatim text is passed to the provider payload after the existing budget gate.
- Structured-output instructions are present in `build_judgment_prompt_payload`.
- Provider-facing evidence content is limited to `prompt_excerpt_set`; no raw bundle facts are passed.

## Code quality review

- Added focused `excerpt.py` and `prompt.py` modules instead of expanding provider classes.
- Kept walking-skeleton orchestration changes limited to provider request construction.
- Code review initially found two important issues: nested/normalized `raw_source` leakage and missing walking-skeleton `process_name` excerpt. Both now have regression coverage and fixes.
- Follow-up code review reported no blocking prompt/excerpt issues.

## Risk review

- Residual risk: structural prompt isolation does not prove resistance against real-provider adversarial behavior; Task 27 owns that probe.
- Residual risk: generalized evidence citation validation remains Task 15.
- Residual risk: PolicyGate remains Task 17 and was not implemented here.

## Human review notes

- None.
