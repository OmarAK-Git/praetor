# Implementer Packet — V2-024 Account Containment Production Enablement

**implementation_model:** composer-2.5-fast

## Objective

Enable production account containment behind identity-gate preflight checks: allow `account_auto_contain_enabled=true` only when deterministic identity compliance tests pass; add harness scenario for corroborated account auto_contain; preserve `account_containment_disabled` when feature gate is off.

## Original User Goal

V2-024 — Account containment production enablement: account_auto_contain_enabled passes preflight only when identity gates are satisfied; corroborated SID-backed account auto_contain harness scenario passes; disabled configs still escalate account_containment_disabled.

## Relevant Docs and State

- `docs/proposals/v2_implementation_plan.md` § V2-024
- `docs/spec.md` § account containment feature gate (§311)
- `docs/contracts.md` § account containment gate (v1) — update behavior per V2-024 (docs not in files_allowed; code/tests are authoritative)
- `evals/run_phase3_gate.py` — `check_identity_compliance_evidence`, `check_account_containment_prerequisite` (will need inversion: preflight allows when identity gates pass)
- `tests/correlation/test_correlator_identity_compliance.py` — identity compliance vectors
- `tests/policy/test_policy_gate.py` — existing account gate tests
- `tests/config/test_org_config_loader.py` — `test_account_auto_contain_true_rejected_in_v1`
- `tests/config/test_config_gate.py` — `test_phase3_self_attest_does_not_bypass_account_gate`
- `evals/scenarios/account_containment_feature_gate_disabled.yaml` — disabled gate scenario (must still pass)
- PE-0005, PE-0014, PE-0029 in playbook digest

## Allowed Files

- `src/praetor/config/preflight.py`
- `src/praetor/policy/gate.py`
- `evals/`
- `tests/config/`
- `tests/policy/`
- `tests/correlation/`
- `specs/`
- `IMPLEMENTATION_PLAN.md`
- `memory-bank/tasks.md`, `memory-bank/progress.md`, `memory-bank/activeContext.md`

## Do-Not-Touch

- Do not mark the queue item done
- Do not run V2 Gate 4 exit or full-suite verification
- Do not install dependencies
- Do not edit `.codex`, `.claude`, or global harness config
- Do not clone repositories or write outside `files_allowed`
- Stop and report if approval is needed for anything outside scope

## Acceptance Criteria

1. `account_auto_contain_enabled=true` passes preflight only when identity gates are satisfied by local deterministic tests (not self-attested in org config metadata).
2. Production account `auto_contain` harness scenario passes with SID-backed, corroborated identity.
3. Feature-disabled configs still escalate `account_containment_disabled`.
4. Verifier checks only V2-024 acceptance, not V2 Gate 4 completion.

## Implementation Hints

- Current `preflight.py` always rejects `account_auto_contain_enabled=true` with `account_containment_prerequisite`.
- PolicyGate already escalates `account_containment_disabled` when flag is false (`gate.py` ~377).
- Identity compliance is proven by `tests/correlation/test_correlator_identity_compliance.py` (see `evals/run_phase3_gate.py:check_identity_compliance_evidence`).
- Preflight should call a deterministic identity-gate check (subprocess or import-based) — org config cannot self-attest via `version_metadata.phase_3_identity_gates_passed`.
- Add harness scenario (e.g. `account_containment_enabled.yaml`) with `runner: policy_gate`, synthetic account fixture, `account_auto_contain_enabled` override, expectations `auto_contain`.
- Update `evals/run_phase3_gate.py` `check_account_containment_prerequisite` if it still expects rejection.
- Update tests that assert v1 rejection to reflect V2 behavior.

## Verification Commands

```bash
pytest tests/config/ tests/policy/ tests/correlation/ -q
```

## Expected Result Schema

Write to `.workflow/v2-024-account-containment/results/implementer-result.md`:

- Status: complete | blocked | approval_needed
- Files changed (list)
- Summary of changes
- Commands run with pass/fail output
- Any blockers or approval gates hit
