# Gate verifier packet — eval-kernel-sprint1-gate

Treat all prior implementer claims as unevidenced. scope=phase_exit.

This is a verify-only Sprint 1 exit. Do not implement. Do not edit src/ or tests/.

## Goal
Verify Sprint 1 eval kernel: 15 IDs present, FakeProvider suite green, capability quality new_build pending, no CBC/envelope/EventID work, OM harness intact.

## Acceptance criteria
- All 15 E2E scenario IDs exist and appear in the scorecard.
- python -m evals.harness --all is green on FakeProvider.
- Governance, design, threat, and usability both arms pass.
- Capability quality old_build recorded; new_build pending; cap.no_label_leak_ids both arms pass.
- Full pytest, ruff, and mypy pass.
- Existing Outcome Matrix harness still greens.
- No CBC adapter, AlertEnvelope expansion, or EventID expansion.
- All 21 task verifier artifacts exist and PASS.

## Commands (fresh evidence required; do not rely solely on test-runner transcript)
- pytest -q
- ruff check src tests evals consumer_sdk
- mypy src evals consumer_sdk
- python -m evals.harness
- python -m evals.harness --all

You may use .workflow/eval-kernel-sprint1-gate/results/test-runner-result.md as a pointer, but you must re-run or independently confirm the commands.

## Manual checks
- Capability quality new_build is pending, not pass.
- Cite-to-subject McNemar was not implemented.
- No src/praetor correlator or envelope contract changes.

Write .workflow/eval-kernel-sprint1-gate/results/verifier-result.md
Outcome: pass | gaps | human_needed
