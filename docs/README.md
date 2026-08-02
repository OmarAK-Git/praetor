# Praetor docs — start here

This directory is the depth behind the root [`README.md`](../README.md). The root README is the
showcase; these documents are the layered reference. Each has **one job** — read by intent, not
front-to-back.

## If you're new, read in this order

1. [`prd.md`](prd.md) — **Why** Praetor exists (problem, thesis, the 7 product decisions).
2. [`spec.md`](spec.md) — **What** it does (architecture, Outcome Matrix, acceptance criteria, non-goals). v1 baseline plus V2 mirrors (DEC-058+).
3. [`architecture.md`](architecture.md) — **Structure** (subsystems, durable boundaries, data flow).
4. [`contracts.md`](contracts.md) — **Pins** (hash domains, ID derivations, the Outcome Matrix). The single source of truth for anything that must not silently diverge.
5. [`decisions.md`](decisions.md) — **Why we chose X** — the `DEC-xxx` ledger (cited by code & tests).

## Live map (authoritative)

| Document | Job | Status |
|---|---|---|
| [`prd.md`](prd.md) | Why — problem, thesis, product decisions, success criteria | Authoritative |
| [`spec.md`](spec.md) | What — architecture, Outcome Matrix, acceptance criteria, non-goals | Authoritative (v1 + V2 mirrors) |
| [`contracts.md`](contracts.md) | Pins — hash domains, ID constructions, Outcome Matrix, consumer pre-actuation | Authoritative (SSOT for hashes/IDs) |
| [`decisions.md`](decisions.md) | The `DEC-xxx` ledger | Authoritative (cited by code & tests) |
| [`architecture.md`](architecture.md) | Structure — component boundaries, durable boundaries, data flow | Reference |
| [`eval_gates.md`](eval_gates.md) | Verify — deterministic vs probabilistic evals, per-phase gate commands | Reference |

## Ops (skip unless you need it)

| Document | Job | Notes |
|---|---|---|
| [`operator_runbook.md`](operator_runbook.md) | Deploy/operate — SQLite, startup/recovery, throughput, failure handling | Pin-tested; not day-to-day product reading |

## Historical (complete — not live backlog)

| Document | Job | Status |
|---|---|---|
| [`plan.md`](plan.md) | How (v1) — 35 tasks, sprint groupings, phase gates | v1 complete |
| [`proposals/`](proposals/) | V2 planning + reverse-spec disposition trail | Gates 0–5 complete; history only |
| [`superpowers/`](superpowers/) | Sprint specs/plans (agentic, RFC remediation, spikes, etc.) | Execution artifacts |
| [`archive/`](archive/) | Reverse-spec as-built/debt snapshot, raw RFCs, spike checklist | **HISTORICAL** — do not treat as open work |

## How these relate (so nothing looks redundant)

- **`spec.md` and `contracts.md` are the constitution.** Everything else refines or operationalizes
  them — it does not contradict them. Major pins live in `contracts.md`; implementation choices in
  `decisions.md`. Spec carries the behavioral narrative and Outcome Matrix mirror.
- **`decisions.md` is the `DEC-xxx` record.** Code and the demo notebook cite specific decisions
  (e.g. `DEC-053`, `DEC-059`). There is also a short index of these at `../memory-bank/decisions.md`
  for agent context — that file is a *pointer*; the rationale lives **here**.
- **`architecture.md` / `operator_runbook.md` / `eval_gates.md`** describe structure, operations, and
  verification respectively. They reference `schemas/` for field-level shapes rather than duplicating
  them.

## `proposals/` — V2 (complete history)

V2 hardening (tasks V2-001–036, Gates 0–5) **shipped** as of 2026-07-10. Behavioral
authority is `spec.md` (mirrored), `contracts.md`, and `decisions.md` (DEC-058+). These files are
planning trail, not an open backlog.

| Document | Contents |
|---|---|
| [`proposals/v2_hardening.md`](proposals/v2_hardening.md) | Design rationale for corroboration, posture, feedback loop (now implemented) |
| [`proposals/v2_implementation_plan.md`](proposals/v2_implementation_plan.md) | V2 task breakdown and gate criteria (**COMPLETE**, Gates 0–5) |
| [`proposals/delivery_backlog.md`](proposals/delivery_backlog.md) | Harvested backlog — mostly closed; residual Future / Accepted Deferral rows only |
| [`proposals/reverse_spec_rfc_disposition.md`](proposals/reverse_spec_rfc_disposition.md) | Verdicts on the reverse-spec RFC dump |

Correctness audit: [`.workflow/v2-correctness-audit/final-report.md`](../.workflow/v2-correctness-audit/final-report.md).

## `archive/` — historical snapshots

| Document | Contents |
|---|---|
| [`archive/as_built.md`](archive/as_built.md) | Reverse-spec extract of the codebase as of 2026-07-18 |
| [`archive/debt_ledger.md`](archive/debt_ledger.md) | Debt probe companion to as-built (many items later closed) |
| [`archive/reverse_spec_rfcs.md`](archive/reverse_spec_rfcs.md) | Raw RFC dump that fed the disposition doc |
| [`archive/capability_spike_implementation_plan.md`](archive/capability_spike_implementation_plan.md) | Completed spike checklist (prefer `superpowers/plans/` for detail) |

## Generated, not authored

Field-level contract shapes live in [`../schemas/`](../schemas/) and are **generated** from the
Pydantic models in `src/praetor/contracts/` (`python -m praetor.contracts.schema_export`). The models
are authoritative; the JSON Schema is a derived artifact.
