# Plan — v2-gate-5-exit

## Goal

V2 Gate 5 exit (PASS-only): feedback and progressive authorization sprint complete per docs/proposals/v2_implementation_plan.md § V2 Gate 5.

## Scope

Full V2 Gate 5 exit verification only. No new implementation; confirm pass criteria for V2-032 through V2-036.

## Tier

T2 (`phase_exit`, `run_mode: chat_gate`)

## Allowed files

- `.workflow/v2-gate-5-exit/`
- `memory-bank/progress.md`
- `memory-bank/activeContext.md`
- `memory-bank/tasks.md`

## Acceptance criteria

1. Promotion reporting is read-only and human-led (V2-032).
2. Prompt exemplars are bounded and outside the evidence hash path (V2-033).
3. Similar-case retrieval uses only human-confirmed cases (V2-034).
4. Statute curation is review-only until activation (V2-035).
5. Confirmed model errors become eval scenarios or documented waivers (V2-036).
6. Full pytest, ruff, and mypy pass.

## Verification commands

```
pytest -q
ruff check .
mypy .
```

## Dependencies (all done)

- v2-032-progressive-reporting
- v2-033-prompt-exemplar
- v2-034-similar-case-retrieval
- v2-035-statute-curation
- v2-036-eval-regression
