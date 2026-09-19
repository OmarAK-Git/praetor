# Implementer retry — eval-kernel-04-theater

Blocking code-review finding: tests miss a clean path for every detector and miss a trip test for post_hoc_protocol.

Stay in files_allowed: evals/theater.py, tests/evals/test_theater.py, .workflow/eval-kernel-04-theater/

Add tests so that:
1. Each of the six named detectors has a unit test that trips.
2. Each of the six named detectors has a unit test (or parametrized case) that stays clean.
3. Unknown names still raise.

Do not mark queue done. Commit and push if clean.
Write .workflow/eval-kernel-04-theater/results/implementer-result-retry.md
