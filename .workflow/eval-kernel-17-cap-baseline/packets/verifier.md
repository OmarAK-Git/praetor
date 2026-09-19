# Verifier packet — eval-kernel-17-cap-baseline

Treat implementer claims as unevidenced. scope=task.

## Goal
Task 17 — cap.baseline_bag_path_a.

## Acceptance criteria
- old_build is recorded; new_build status is pending, not pass.
- Bag is correlate_telemetry Path A (Sysmon 1 + Security 4624) into process_alert_intake.
- FakeProvider stipulation is not scored as a capability quality pass.
- The verifier checks only Task 17 acceptance, not Sprint 1 gate completion.

## Commands
- pytest tests/evals/e2e/test_cap_baseline_bag_path_a.py tests/evals/test_scorecard.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_cap_baseline_bag_path_a.py
- mypy evals/e2e_kernel.py

## Manual checks
- No Path B import.
- No judgment-quality pass claimed.

## Implementer result (unevidenced)
.workflow/eval-kernel-17-cap-baseline/results/implementer-result.md

Write .workflow/eval-kernel-17-cap-baseline/results/verifier-result.md
Outcome: pass | gaps | human_needed
