# Verifier packet — eval-kernel-13-thr-multi-host

Treat implementer claims as unevidenced. scope=task.

## Goal
Task 13 — thr.ambiguous_multi_host_target.

## Acceptance criteria
- Both arms pass.
- Two distinct cited hosts produce ambiguous_containment_target escalate.
- Uses production process_alert_intake call shape.
- The verifier checks only Task 13 acceptance, not Sprint 1 gate completion.

## Commands
- pytest tests/evals/e2e/test_thr_ambiguous_multi_host_target.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_thr_ambiguous_multi_host_target.py
- mypy evals/e2e_kernel.py

## Implementer result (unevidenced)
.workflow/eval-kernel-13-thr-multi-host/results/implementer-result.md

Write .workflow/eval-kernel-13-thr-multi-host/results/verifier-result.md
Outcome: pass | gaps | human_needed
