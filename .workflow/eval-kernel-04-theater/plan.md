# eval-kernel-04-theater

**Goal:** Task 4 — Theater detector registry: all six named checks from spec §8, trips fail the suite even if disposition matched a label.

**Scope:** Theater detector registry only. Do not wire production scenarios yet. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- THEATER_DETECTOR_NAMES includes all six spec §8 names.
- Each named check has a unit test that trips and one that stays clean.
- Unknown detector names raise a harness error.
- The verifier checks only Task 4 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- evals/theater.py
- tests/evals/test_theater.py
- .workflow/eval-kernel-04-theater/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/test_theater.py -q
- ruff check evals/theater.py tests/evals/test_theater.py
- mypy evals/theater.py
