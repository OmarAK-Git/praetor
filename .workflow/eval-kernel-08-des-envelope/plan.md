# eval-kernel-08-des-envelope

**Goal:** Task 8 — des.envelope_rejects_extra_fields: AlertEnvelope construction with any field other than schema_version + alert_identity raises.

**Scope:** This design pin only. Do not change src/praetor contracts. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- Both arms pass on FakeProvider.
- Extra envelope fields raise; identity-only construction succeeds.
- No AlertEnvelope field expansion in src/.
- The verifier checks only Task 8 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- evals/e2e_kernel.py
- evals/e2e_scenarios/des.envelope_rejects_extra_fields.yaml
- tests/evals/e2e/test_des_envelope_rejects_extra_fields.py
- .workflow/eval-kernel-08-des-envelope/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/e2e/test_des_envelope_rejects_extra_fields.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_des_envelope_rejects_extra_fields.py
- mypy evals/e2e_kernel.py
