# Workflow Plan — V2-034 Similar-Case Retrieval

**Tier:** T2  
**Goal:** V2-034 — Similar-case retrieval: retrieval selects only human-confirmed cases that satisfy a documented ranking contract; exemplar payloads are bounded and excluded from evidence hash derivation; contract eval proves retrieval is wired without changing citation validity or raw-source exclusion.

**Scope:** Similar-case retrieval and judgment wiring only. Do not run V2 Gate 5 exit.

## Acceptance criteria

1. Retrieval selects only human-confirmed cases per documented ranking contract.
2. Exemplar payloads bounded and excluded from evidence hash derivation.
3. Contract eval proves retrieval wired without changing citation validity or raw-source exclusion.
4. V2-034 scope only.

## Verification

```bash
pytest tests/judgment/ tests/annotations/ -q
```

## Context

- Builds on V2-033 exemplar slot (`PromptExemplarBlock` in judgment/prompt.py)
- Human-confirmed = analyst annotations with `disposition_correct=True` or explicit confirmation flag
- Ranking contract must be documented (eval_gates.md or module docstring)
