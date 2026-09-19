# Verifier packet — eval-kernel-11-thr-cmdline

Treat implementer claims as unevidenced. scope=task.

## Goal
Task 11 — thr.instruction_in_cmdline.

## Acceptance criteria
- Both arms pass on the deterministic FakeProvider half.
- Instruction-like command_line survives excerpting.
- No silent skip of a live-model half if present.
- The verifier checks only Task 11 acceptance, not Sprint 1 gate completion.

## Commands
- pytest tests/evals/e2e/test_thr_instruction_in_cmdline.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_thr_instruction_in_cmdline.py
- mypy evals/e2e_kernel.py

## Manual checks
- Live Vertex is not a merge-gate requirement.

## Implementer result (unevidenced)
.workflow/eval-kernel-11-thr-cmdline/results/implementer-result.md

Write .workflow/eval-kernel-11-thr-cmdline/results/verifier-result.md
Outcome: pass | gaps | human_needed
