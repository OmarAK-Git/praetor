# Verifier packet — eval-kernel-06-gov-feed-unhealthy

Treat implementer claims as unevidenced. scope=task.

## Goal
Task 6 — gov.feed_unhealthy_blocks_contain.

## Acceptance criteria
- Both arms pass on FakeProvider.
- Unhealthy feed blocks auto_contain and allows standard_review.
- Uses the same degraded-mode contract as the playbook fixture.
- The verifier checks only Task 6 acceptance, not Sprint 1 gate completion.

## Commands
- pytest tests/evals/e2e/test_gov_feed_unhealthy_blocks_contain.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_gov_feed_unhealthy_blocks_contain.py
- mypy evals/e2e_kernel.py

## Implementer result (unevidenced)
.workflow/eval-kernel-06-gov-feed-unhealthy/results/implementer-result.md

Write .workflow/eval-kernel-06-gov-feed-unhealthy/results/verifier-result.md
Outcome: pass | gaps | human_needed
