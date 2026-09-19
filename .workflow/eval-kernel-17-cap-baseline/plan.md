# eval-kernel-17-cap-baseline

**Goal:** Task 17 — cap.baseline_bag_path_a: Path A bag is production correlator output fed to process_alert_intake; new_build is pending, not pass.

**Scope:** This capability pin only. Do not claim judgment quality. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- old_build is recorded; new_build status is pending, not pass.
- Bag is correlate_telemetry Path A (Sysmon 1 + Security 4624) into process_alert_intake.
- FakeProvider stipulation is not scored as a capability quality pass.
- The verifier checks only Task 17 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- evals/e2e_kernel.py
- evals/e2e_scenarios/cap.baseline_bag_path_a.yaml
- tests/evals/e2e/test_cap_baseline_bag_path_a.py
- .workflow/eval-kernel-17-cap-baseline/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/e2e/test_cap_baseline_bag_path_a.py tests/evals/test_scorecard.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_cap_baseline_bag_path_a.py
- mypy evals/e2e_kernel.py
