# Praetor docs — start here

This directory is the depth behind the root [`README.md`](../README.md). The root README is the
showcase; these documents are the layered reference. Each has **one job** — read by intent, not
front-to-back.

## If you're new, read in this order

1. [`prd.md`](prd.md) — **Why** Praetor exists (problem, thesis, the 7 product decisions).
2. [`spec.md`](spec.md) — **What** it does (architecture, Outcome Matrix, acceptance criteria, non-goals). **Frozen** — the behavioral source of truth.
3. [`architecture.md`](architecture.md) — **Structure** (subsystems, durable boundaries, data flow).
4. [`contracts.md`](contracts.md) — **Pins** (hash domains, ID derivations, the Outcome Matrix). The single source of truth for anything that must not silently diverge.

## The full map

| Document | Job | Status |
|---|---|---|
| [`prd.md`](prd.md) | Why — problem, thesis, product decisions, success criteria | Authoritative |
| [`spec.md`](spec.md) | What — architecture, Outcome Matrix, acceptance criteria, non-goals | **Frozen** source of truth |
| [`plan.md`](plan.md) | How — 35 tasks, sprint groupings, phase gates | Authoritative |
| [`contracts.md`](contracts.md) | Pins — hash domains, ID constructions, Outcome Matrix, consumer pre-actuation | Authoritative (SSOT for hashes/IDs) |
| [`decisions.md`](decisions.md) | The `DEC-xxx` ledger — implementation choices that refine spec/contracts, with full rationale | Authoritative (cited by code & tests) |
| [`architecture.md`](architecture.md) | Structure — component boundaries, durable boundaries, data flow | Reference |
| [`operator_runbook.md`](operator_runbook.md) | Operate — SQLite requirements, startup/recovery order, throughput ceiling, failure handling | Reference |
| [`eval_gates.md`](eval_gates.md) | Verify — deterministic vs probabilistic evals, per-phase gate commands | Reference |
| [`demo_run_of_show.md`](demo_run_of_show.md) | Demo — 4-minute walkthrough script for `notebooks/praetor_walkthrough.ipynb` | Working aid |
| [`proposals/`](proposals/) | v2 planning — **DRAFT, not ratified**; does not modify the frozen v1 spec | Draft (see below) |

## How these relate (so nothing looks redundant)

- **`spec.md` and `contracts.md` are the constitution.** Everything else refines or operationalizes
  them — it does not contradict them. When spec is frozen, refinements land in `contracts.md`
  (major) or `decisions.md` (implementation detail), per the project's doc-change hierarchy.
- **`decisions.md` is the `DEC-xxx` record.** Code and the demo notebook cite specific decisions
  (e.g. `DEC-053`, `DEC-059`). There is also a short index of these at `../memory-bank/decisions.md`
  for agent context — that file is a *pointer*; the rationale lives **here**.
- **`architecture.md` / `operator_runbook.md` / `eval_gates.md`** describe structure, operations, and
  verification respectively. They reference `schemas/` for field-level shapes rather than duplicating
  them.

## `proposals/` — v2, not v1

These are forward-looking design docs for a possible v2 hardening pass. **Nothing in here is
ratified, and none of it modifies the frozen v1 spec.**

| Document | Contents |
|---|---|
| [`proposals/v2_hardening.md`](proposals/v2_hardening.md) | Candidate v2 changes (corroboration floor, authorization posture, feedback loop) |
| [`proposals/v2_implementation_plan.md`](proposals/v2_implementation_plan.md) | V2 task breakdown |
| [`proposals/delivery_backlog.md`](proposals/delivery_backlog.md) | Single prioritized backlog for v2 gap-closure and rewire planning |

## Generated, not authored

Field-level contract shapes live in [`../schemas/`](../schemas/) and are **generated** from the
Pydantic models in `src/praetor/contracts/` (`python -m praetor.contracts.schema_export`). The models
are authoritative; the JSON Schema is a derived artifact.
