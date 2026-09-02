# Active Context

## Current focus

**2026-09-02 — PROD-CAP-001 landed.** Truncation vs parse-error. Next: CBC AlertEnvelope spike spec (no live run until spec approved).

**2026-09-02 — Authorized next: PROD-CAP-001 (+002 audit), then CBC AlertEnvelope spike spec (no live run until spec approved).** T1 production PR in progress.

**2026-08-02 — ATLAS manifest authored.** `evals/capability/manifests/atlasv2_attack_day.yaml` — 13+13 distinct-action / spaced-benign + 2 unresolved (S-2/S-3); `unchained_steps=2` (no usable Path B seed). Path A empty-bundle is measurement. Next: build capture JSONL + live spike. Design: `docs/superpowers/specs/2026-08-01-capability-spike-design.md`.

**2026-08-02 — Capability spike schema amended.** `unresolved` label, citation-mix A≈B thresholds (ε=0.05, >80% on `{1,4624}`), EventID/Channel join pin, always-on label-quality counters.

**2026-08-01 — Judgment capability spike COMPLETE (build).** Sprint drained; gate pytest **1146**, harness **34/34**. Measurement-only under `evals/capability*` + `evals/capability_spike.py`. Evidence: `.workflow/capability-spike-gate/results/verifier-result.md`.

**2026-08-01 — Enrichment vs corroboration COMPLETE.** Sprint `enrichment-vs-corroboration` drained; gate pytest **1105**. DEC-066: host presence corroboration (`insufficient_corroboration`) + cited source-event enrichment (`insufficient_enrichment`, SFE=false). Evidence: `.workflow/enrichment-split-gate/results/verifier-result.md`.

**2026-07-31 — Public demo copy rewrite COMPLETE.** SOC-manager voice across all scenarios.

**2026-07-31 — Corroboration floor temporary (DEC-065) COMPLETE.** Account temporary floor retained; host path superseded by DEC-066.
