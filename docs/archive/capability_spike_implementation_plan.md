# Judgment Capability Spike

> **HISTORICAL.** Archived root checklist for the judgment capability spike (complete). Prefer the detailed plan at [`docs/superpowers/plans/2026-08-01-judgment-capability-spike.md`](../superpowers/plans/2026-08-01-judgment-capability-spike.md). Live SSOT: [`docs/spec.md`](../spec.md), [`docs/contracts.md`](../contracts.md), [`docs/decisions.md`](../decisions.md).

**Tier:** T2 (sprint with T3 phase-exit gate)  
**Goal:** Offline-testable eval measuring whether single-shot judgment separates malicious from benign telemetry, and how much failure is correlation coverage vs judgment quality (Path A vs Path B).  
**Status:** complete  
**Updated:** 2026-08-01

## Sources

- Design: `docs/superpowers/specs/2026-08-01-capability-spike-design.md`
- Detailed plan: `docs/superpowers/plans/2026-08-01-judgment-capability-spike.md`
- Loader: `tools/load_capability_spike_queue.py`
- Active sprint: `judgment-capability-spike` in `.workflow/autopilot-queue.json`
- Gate evidence: `.workflow/capability-spike-gate/results/verifier-result.md`

## Checklist (GSD) — all done

1. `capability-spike-01-corpus` — done (`1891684`)
2. `capability-spike-02-flatten` — done (`41eae19`)
3. `capability-spike-03-bundle` — done (`9cb454a`)
4. `capability-spike-04-runner` — done (`37083e0` + fix `82b41ad` for Path A `anchor_time`)
5. `capability-spike-05-score` — done (`98debe4`)
6. `capability-spike-06-cli` — done (`2450e66`)
7. `capability-spike-gate` — done (pytest 1146, harness 34/34, spike skip OK)

## After the plan (operator)

Spike is built. Live run still needs OTRF capture + labeled manifest + `PRAETOR_CAPABILITY_SPIKE=1` + Gemini key.
