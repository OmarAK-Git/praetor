# eval-kernel-sprint1-gate

**Goal:** Verify Sprint 1 eval kernel: 15 IDs present, FakeProvider suite green, capability quality new_build pending, no CBC/envelope/EventID work, OM harness intact.

**Scope:** Verify-only Sprint 1 exit; no feature implementation.

**Tier:** T3

**Acceptance criteria:**

- All 15 E2E scenario IDs exist and appear in the scorecard.
- python -m evals.harness --all is green on FakeProvider.
- Governance, design, threat, and usability both arms pass.
- Capability quality old_build recorded; new_build pending; cap.no_label_leak_ids both arms pass.
- Full pytest, ruff, and mypy pass.
- Existing Outcome Matrix harness still greens.
- No CBC adapter, AlertEnvelope expansion, or EventID expansion.
- All 21 task verifier artifacts exist and PASS.

**Allowed files:**

- .workflow/eval-kernel-sprint1-gate/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest -q
- ruff check src tests evals consumer_sdk
- mypy src evals consumer_sdk
- python -m evals.harness
- python -m evals.harness --all
