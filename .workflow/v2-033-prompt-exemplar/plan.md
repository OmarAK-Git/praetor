# Workflow Plan — V2-033 Judgment Prompt Exemplar Slot

**Tier:** T2  
**Goal (verbatim):** V2-033 — Judgment prompt exemplar slot: prompt template accepts an optional exemplar block; exemplar rendering is bounded, auditable, and clearly separated from cited evidence; evidence hash and PromptExcerptSet behavior are unchanged.

**Scope:** Prompt exemplar slot and isolation only. Do not run V2 Gate 5 exit.

## Acceptance criteria

1. Prompt template accepts an optional exemplar block.
2. Exemplar rendering is bounded, auditable, and clearly separated from cited evidence.
3. Evidence hash and PromptExcerptSet behavior are unchanged.
4. Verifier checks only V2-033 acceptance, not V2 Gate 5 completion.

## Allowed files

- `src/praetor/judgment/prompt.py`
- `src/praetor/judgment/excerpt.py`
- `tests/judgment/test_prompt_isolation.py`
- `evals/scenarios/`
- `specs/`, `IMPLEMENTATION_PLAN.md`, `memory-bank/`

## Verification

```bash
pytest tests/judgment/test_prompt_isolation.py -q
```
