# Implementer Packet — V2-033 Judgment Prompt Exemplar Slot

**implementation_model:** composer-2.5-fast

## Objective

Add optional exemplar block to judgment prompt template. Exemplars bounded, auditable, separated from cited evidence. Do not change evidence hash or PromptExcerptSet behavior.

## Original goal

V2-033 — Judgment prompt exemplar slot: prompt template accepts an optional exemplar block; exemplar rendering is bounded, auditable, and clearly separated from cited evidence; evidence hash and PromptExcerptSet behavior are unchanged.

## Allowed files

- `src/praetor/judgment/prompt.py`
- `src/praetor/judgment/excerpt.py`
- `tests/judgment/test_prompt_isolation.py`
- `evals/scenarios/`, `specs/`, `IMPLEMENTATION_PLAN.md`, `memory-bank/`

## Do-not-touch

- Do not mark queue done. Do not run gate verification.
- Exemplars must NOT enter evidence hash derivation or PromptExcerptSet.

## Verification

```bash
pytest tests/judgment/test_prompt_isolation.py -q
```

## Expected result

Write `.workflow/v2-033-prompt-exemplar/results/implementer-result.md`.
