# Verifier packet — eval-kernel-21-docs-pointer

Treat implementer claims as unevidenced. scope=task.

## Goal
Task 21 — Docs pointer.

## Acceptance criteria
- docs/eval_gates.md points at the Sprint 1 plan and the new workflow.
- memory-bank current-focus / next-up point here instead of CBC AlertEnvelope spike as the next authorized step.
- CBC queue items are not fully retired (Sprint 3).
- The verifier checks only Task 21 acceptance, not Sprint 1 gate completion.

## Commands
- pytest tests/docs/test_eval_kernel_pointer.py -q

Write .workflow/eval-kernel-21-docs-pointer/results/verifier-result.md
Outcome: pass | gaps | human_needed
