# V2 Correctness Audit — Final Report

**Date:** 2026-07-10  
**Tier:** T2  
**Plan:** `.workflow/v2-correctness-audit/plan.md`

## Verdict

**V2 build is substantively correct and homogeneous.** Safety-critical authorization rewires (Gates 0–4) are implemented, tested, and live on the intake path. Gate 5 product features exist as library/operator modules with intentional production-wiring follow-ups. The dominant gap is **documentation debt**, not code drift.

## Fresh verification (2026-07-10)

| Check | Result |
|---|---|
| `python -m pytest -q` | **1029 passed**, 2 deselected (exit 0) |
| `python -m ruff check .` | All checks passed (exit 0) |
| `python -m mypy .` | Success — 134 source files (exit 0) |
| `python notebooks/check_walkthrough.py notebooks/praetor_walkthrough.ipynb` | **OK** — AUTO_CONTAIN / directive / STANDARD_REVIEW / ESCALATE / never_contain_live_conflict present |
| Eval scenarios | **32** under `evals/scenarios/` |

Logs: `pytest_v2_audit.txt`, `ruff_v2_audit.txt`, `mypy_v2_audit.txt`, `walkthrough_v2_audit.txt`

## Spec / plan drift

| Theme | Code | Doc sync |
|---|---|---|
| `default_action` + escalate blocks (DEC-058) | Live in policy + example_org | Hardening/backlog/README stale |
| Host corroboration (DEC-059 / V2-011) | Live in PolicyGate | contracts §12a current; hardening headers stale |
| Provider unavailable (DEC-061) | Live in intake | contracts §13 current |
| PolicyGate sole containment boundary (V2-025) | AST + integration tests | backlog still Open |
| Progressive reporting (V2-032) | Module + tests; **not fed by orchestrator** | Runbook current; disclosed gate follow-up |
| Similar-case retrieval (V2-034) | Module + tests; **not called from intake** | eval_gates current; disclosed follow-up |
| Statute curation (V2-035) | Review-only + promote path | Runbook current |
| Frozen `docs/spec.md` | Intentionally behind contracts/decisions | Expected; mirror deferred |

**Frozen-spec contradictions** (expected under doc hierarchy): default-allow language, account-only corroboration, incomplete Outcome Matrix. Authoritative V2 behavior lives in `docs/contracts.md` + `docs/decisions.md`.

## Homogeneity / over-engineering

- Safety path extends v1 spine (`contracts → policy → engine → ledger`); no parallel engines.
- New packages (`reporting/`, `retrieval/`) are small, read-only / operator-adjacent.
- AST guards and codification workflow are the heaviest additions — purposeful, not decorative.
- Ranking is token-overlap + recency (no vector DB). Vertex provider is stdlib HTTP.
- **Not over-built.** Residual: walking-skeleton naming in orchestrator; `HOST_ID_FIELD` duplication (minor).

## Design-decision recording

| ID | In `docs/decisions.md`? | Notes |
|---|---|---|
| DEC-058–061 | Yes | Gate 0 complete |
| DEC-062 (SID presence waiver) | **Was missing** — only in memory-bank | Promoted in this audit |
| DEC-063 (normalizer PE-0024) | **Was missing** — only in memory-bank | Promoted in this audit |
| Gate 5 product contracts | In plan/eval_gates/runbook | No new DEC rows required for library features |

## Known follow-ups (not blocking V2 completeness)

1. Wire `record_policy_gate_evaluation` + schema init into production open/intake (V2-032 operational feed).
2. Wire `build_judgment_prompt_payload_with_similar_cases` into orchestrator (V2-034 live exemplars).
3. Promote `docs/spec.md` Outcome Matrix / posture mirror when owner unfreezes (permission required).
4. Mark `docs/proposals/v2_implementation_plan.md` COMPLETE (permission required).
5. Full row-by-row `delivery_backlog.md` reconciliation (banner + major Closed updates in this audit).

## Doc updates performed (this audit)

- `README.md`, `docs/README.md`, `docs/architecture.md`, `docs/demo_run_of_show.md`
- `docs/operator_runbook.md`, `docs/proposals/v2_hardening.md`, `docs/proposals/delivery_backlog.md`
- `docs/decisions.md` (DEC-062/063), `docs/contracts.md` (§12a implementation tag)
- `OPS.md`, `memory-bank/activeContext.md`, `memory-bank/progress.md`

## Permission requested (applied 2026-07-10)

- `docs/spec.md` — V2 mirrors applied (Outcome Matrix, DEC-058/059/062, host corroboration, posture).
- `docs/proposals/v2_implementation_plan.md` — Status **COMPLETE** with Gate 0–5 exit pointers.
