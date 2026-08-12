# Judgment Capability Spike

**Tier:** T2 (sprint with T3 phase-exit gate)  
**Goal:** Offline-testable eval measuring whether single-shot judgment separates malicious from benign telemetry, and how much failure is correlation coverage vs judgment quality (Path A vs Path B).  
**Status:** **done** (2026-08-03) — clean negative on primary question; coverage not the bottleneck  
**Updated:** 2026-08-03

## Sources

- Design: `docs/superpowers/specs/2026-08-01-capability-spike-design.md`
- Plan: `docs/superpowers/plans/2026-08-01-judgment-capability-spike.md`
- **Results / write-up:** `docs/superpowers/results/2026-08-02-judgment-capability-spike-results.md`
- Decision: DEC-067 in `docs/decisions.md`
- Manifest: `evals/capability/manifests/atlasv2_attack_day.yaml`
- Results JSONL: `evals/capability/captures/atlasv2_capability_spike_results.jsonl`
- Pre-refill backup: `evals/capability/captures/atlasv2_capability_spike_results.prerefill.jsonl`

## Headline (do not re-tune)

- Path A vs `path_a_fact_count` stump: McNemar b=3 c=1, **p=0.625** — judgment not distinguishable from fact-count.
- Path A vs Path B (anchor-majority): McNemar b=7 c=0, **p=0.015625** — denser evidence hurts; do not expand normalizers on this evidence.
- Absolute rates are conditional on synthetic 50/50 raw windows, not AlertEnvelope traffic.

## Closed

Manifest authored · capture built · Path B ⊇ A + constant extras · spike Vertex provider · live 156-cell run · serialization refill (18 cells) · write-up + DEC-067.
