# eval-kernel-10-des-evidence-hash

**Goal:** Task 10 — des.evidence_hash_stable: same logical EvidenceBundle yields the same evidence_bundle_hash across two kernel runs.

**Scope:** This design pin only. Do not run Sprint 1 gate.

**Tier:** T2

**Acceptance criteria:**

- Both arms pass.
- Two kernel runs of the same logical bundle produce the same evidence_bundle_hash.
- Drift is classified harness/design, not model.
- The verifier checks only Task 10 acceptance, not Sprint 1 gate completion.

**Allowed files:**

- evals/e2e_kernel.py
- evals/e2e_scenarios/des.evidence_hash_stable.yaml
- tests/evals/e2e/test_des_evidence_hash_stable.py
- .workflow/eval-kernel-10-des-evidence-hash/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

**Verification commands:**

- pytest tests/evals/e2e/test_des_evidence_hash_stable.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_des_evidence_hash_stable.py
- mypy evals/e2e_kernel.py
