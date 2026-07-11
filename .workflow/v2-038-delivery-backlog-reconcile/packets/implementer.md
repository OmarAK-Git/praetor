# Implementer Packet — V2-038 Delivery Backlog Reconcile

**implementation_model:** composer-2.5-fast

## Objective

Reconcile stale Open/Partial rows in docs/proposals/delivery_backlog.md against V2 completion evidence. Update the status banner. Do not invent closures.

## Original goal

V2-038 — Reconcile docs/proposals/delivery_backlog.md Open/Partial rows against V2 completion evidence (Gates 0–5 + V2-037); update banner; leave true residual Open / Accepted Deferral / Future rows honest.

## Evidence sources (read, do not invent)

- docs/proposals/v2_implementation_plan.md (COMPLETE, Gates 0–5)
- .workflow/v2-gate-*-exit/results/
- .workflow/v2-029-detection-splunk/results/verifier-result.md (T7/T9/T10)
- .workflow/v2-016 through v2-023, v2-019, v2-020, v2-030, v2-032–v2-037
- memory-bank/progress.md, .workflow/v2-correctness-audit/final-report.md

## Known closures to apply (verify each against evidence before marking)

| Backlog item | Likely close as |
|---|---|
| T7 Sigma↔SPL equivalence | Closed (V2-029) |
| T9 fixture-stable dispatch window | Closed (V2-029) |
| T10 tools mypy exclusion documented | Closed (V2-029) |
| T5 scope-guard Phase 5 docs allowlist | Closed (V2-023) if evidence shows docs paths allowed |
| DecisionEdict fault_flag↔SFE validator | Closed (V2-016) if construction validation landed |
| External tip anchor / runbook | Closed (V2-019) if tip-anchor + docs landed |
| record_feed_export_lag on export path | Closed (V2-020) if export completion records lag |
| record_llm_failure LLM_FAILURE_FAULT_FLAGS guard | Closed (V2-020) |
| MetricsCollector thread-safety docs | Closed (V2-020) if documented |
| Burst / measurement_context | Closed (V2-030) |
| Progressive auth / similar-case intake follow-ups | Closed (V2-032/034/037) — note intake wired |
| Feed floor Partial | Closed (V2-019) if floor reconciliation done, else keep Partial |
| Rate-limit scope Partial (DEC-030) | Keep Partial or Accepted Deferral unless fully closed |
| T11 Live Splunk HEC | Keep Open (owned by V2-039; do not close here) |
| Future/Exploratory P5 | Keep Open |
| Accepted Deferral rows | Leave as Accepted Deferral |

If evidence is ambiguous, leave Open/Partial and note in implementer-result — do not force Closed.

## Banner

Update Status to: V2 Gates 0–5 + V2-037 complete; residual true follow-ups = live Splunk HEC (T11/V2-039) + deferred roadmap / Accepted Deferral items. Remove Gate 5 intake wiring from residual list.

## Allowed files (strict)

- docs/proposals/delivery_backlog.md
- docs/proposals/v2_hardening.md (only if checklist boxes need sync)
- memory-bank/tasks.md, memory-bank/progress.md, memory-bank/activeContext.md
- .workflow/v2-038-delivery-backlog-reconcile/

## Do-not-touch

- No src/ or tests/ code changes.
- Do not mark queue done.
- Do not close T11.
- Do not run phase gates.

## Expected result

Write .workflow/v2-038-delivery-backlog-reconcile/results/implementer-result.md with:
- table of status transitions (old → new) with evidence pointers
- rows left Open/Partial/Deferral and why
- banner text after edit
