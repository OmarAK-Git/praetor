# Praetor docs — start here

This directory is the depth behind the root [`README.md`](../README.md). The root README is the
showcase; these documents are the layered reference. Each has **one job** — read by intent, not
front-to-back.

## If you're new, read in this order

1. [`prd.md`](prd.md) — **Why** Praetor exists (problem, thesis, the 7 product decisions).
2. [`spec.md`](spec.md) — **What** it does (architecture, Outcome Matrix, acceptance criteria, non-goals). v1 baseline plus V2 mirrors (DEC-058+).
3. [`architecture.md`](architecture.md) — **Structure** (subsystems, durable boundaries, data flow).
4. [`contracts.md`](contracts.md) — **Pins** (hash domains, ID derivations, the Outcome Matrix). The single source of truth for anything that must not silently diverge.

## The full map

| Document | Job | Status |
|---|---|---|
| [`prd.md`](prd.md) | Why — problem, thesis, product decisions, success criteria | Authoritative |
| [`spec.md`](spec.md) | What — architecture, Outcome Matrix, acceptance criteria, non-goals | Authoritative (v1 + V2 mirrors) |
| [`plan.md`](plan.md) | How (v1) — 35 tasks, sprint groupings, phase gates | Authoritative (v1 complete) |
| [`contracts.md`](contracts.md) | Pins — hash domains, ID constructions, Outcome Matrix, consumer pre-actuation | Authoritative (SSOT for hashes/IDs; includes V2 rows) |
| [`decisions.md`](decisions.md) | The `DEC-xxx` ledger — including V2 DEC-058–063 | Authoritative (cited by code & tests) |
| [`architecture.md`](architecture.md) | Structure — component boundaries, durable boundaries, data flow | Reference (v1 + V2 packages) |
| [`operator_runbook.md`](operator_runbook.md) | Operate — SQLite requirements, startup/recovery order, throughput ceiling, failure handling | Reference |
| [`eval_gates.md`](eval_gates.md) | Verify — deterministic vs probabilistic evals, per-phase gate commands | Reference |
| [`demo_run_of_show.md`](demo_run_of_show.md) | Demo — Act I thesis + optional Act II V2 beats for `notebooks/praetor_walkthrough.ipynb` | Working aid |
| [`proposals/`](proposals/) | V2 planning artifacts — **Gates 0–5 complete** | Complete + backlog reconcile |

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

## `proposals/` — V2 (complete)

V2 hardening (tasks V2-001–036, Gates 0–5) **shipped** as of 2026-07-10. Behavioral
authority is `spec.md` (mirrored), `contracts.md`, and `decisions.md` (DEC-058+).

| Document | Contents |
|---|---|
| [`proposals/v2_hardening.md`](proposals/v2_hardening.md) | Design rationale for corroboration, posture, feedback loop (now implemented) |
| [`proposals/v2_implementation_plan.md`](proposals/v2_implementation_plan.md) | V2 task breakdown and gate criteria (**COMPLETE**, Gates 0–5) |
| [`proposals/delivery_backlog.md`](proposals/delivery_backlog.md) | Harvested backlog — many rows closed by V2; residual Open rows are post-V2 follow-ups or pending reconcile |

Correctness audit: [`.workflow/v2-correctness-audit/final-report.md`](../.workflow/v2-correctness-audit/final-report.md).

## Generated, not authored

Field-level contract shapes live in [`../schemas/`](../schemas/) and are **generated** from the
Pydantic models in `src/praetor/contracts/` (`python -m praetor.contracts.schema_export`). The models
are authoritative; the JSON Schema is a derived artifact.
