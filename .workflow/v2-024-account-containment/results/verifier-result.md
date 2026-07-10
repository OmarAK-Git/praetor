# Verifier Result — V2-024 Account Containment Production Enablement

- verification_model: claude-opus-4-8-thinking-high
- outcome: pass
- scope: V2-024 acceptance criteria ONLY (V2 Gate 4 / phase-level completion explicitly not evaluated)

## Commands run (fresh)

### 1. Task verification command

```text
$ python -m pytest tests/config/ tests/policy/ tests/correlation/ -q
........................................................................ [ 40%]
........................................................................ [ 81%]
.................................                                        [100%]
177 passed in 14.86s
```

Matches implementer's claimed `177 passed`. No skips, no xfails.

### 2. Acceptance-critical tests, run by name (targeted evidence)

```text
$ python -m pytest \
  tests/config/test_org_config_loader.py::test_account_auto_contain_true_passes_when_identity_gates_satisfied \
  tests/config/test_org_config_loader.py::test_account_auto_contain_true_rejected_when_identity_gates_unsatisfied \
  tests/config/test_config_gate.py::test_phase3_self_attest_does_not_bypass_account_gate \
  tests/policy/test_policy_gate.py::test_account_containment_disabled_when_gate_false \
  tests/policy/test_policy_gate.py::test_account_auto_contain_when_feature_gate_enabled \
  tests/correlation/test_account_containment_harness.py::test_account_containment_enabled_harness_scenario -v

tests/config/test_org_config_loader.py::test_account_auto_contain_true_passes_when_identity_gates_satisfied PASSED
tests/config/test_org_config_loader.py::test_account_auto_contain_true_rejected_when_identity_gates_unsatisfied PASSED
tests/config/test_config_gate.py::test_phase3_self_attest_does_not_bypass_account_gate PASSED
tests/policy/test_policy_gate.py::test_account_containment_disabled_when_gate_false PASSED
tests/policy/test_policy_gate.py::test_account_auto_contain_when_feature_gate_enabled PASSED
tests/correlation/test_account_containment_harness.py::test_account_containment_enabled_harness_scenario PASSED
6 passed in 1.80s
```

## Per-criterion evidence

### AC-1 — `account_auto_contain_enabled=true` passes preflight only when identity gates are satisfied by local deterministic tests — MET

- `src/praetor/config/preflight.py:45-62` `_identity_gates_satisfied()` shells out to `pytest -q tests/correlation/test_correlator_identity_compliance.py` and returns True only on returncode 0. Returns False if the test file is missing. This is a real, local, deterministic gate — not a self-attested config flag.
- `preflight.py:96-100`: if `account_auto_contain_enabled` is truthy and `_identity_gates_satisfied()` is False, raises `PreflightError("account_containment_prerequisite", ...)`.
- Gating is load-bearing, proven both directions:
  - PASS direction: `test_account_auto_contain_true_passes_when_identity_gates_satisfied` uses the **real** (unmocked) subprocess gate and passes → snapshot `account_auto_contain_enabled is True`.
  - REJECT direction: `test_account_auto_contain_true_rejected_when_identity_gates_unsatisfied` monkeypatches `_identity_gates_satisfied → False`, asserts `PreflightError.code == "account_containment_prerequisite"`.
  - Bypass-resistance: `test_phase3_self_attest_does_not_bypass_account_gate` sets `version_metadata.phase_3_identity_gates_passed=True` AND `account_auto_contain_enabled=True` with the deterministic gate forced False; preflight still rejects. Confirms the org-config self-attest flag is never consulted (grep confirms `phase_3_identity_gates_passed` is not read in preflight).

### AC-2 — Production account `auto_contain` harness scenario passes with SID-backed, corroborated identity — MET

- Scenario `evals/scenarios/account_containment_enabled.yaml`: runner `policy_gate`, `proposed_disposition: auto_contain`, `policy_preconditions.account_auto_contain_enabled: true` + `containment_default_action: auto_contain`; expects `final_disposition: auto_contain`, `containment_target_type: account`, `containment_target_id: S-1-5-21-1234567890-123456789-123456789-1001`.
- Fixture `tests/fixtures/synthetic/account_eligible_valid.json` is genuinely SID-backed and corroborated: identity SID `S-1-5-21-...-1001`, plus a `sysmon_event_log` fact and a `windows_security_log` fact carrying `target_sid` — satisfying `meets_account_corroboration`.
- Harness wiring is real, not a stub: `evals/harness.py:932-946` applies both `account_auto_contain_enabled=True` and (when requested) `containment_policy` default `auto_contain` onto the persisted snapshot before running the gate.
- Gate path exercised end-to-end: `gate.py:368-378` — account target → eligibility (SID + corroboration) authorized → `account_auto_contain_enabled` True → proceeds to auto_contain and emits an account-target directive.
- `test_account_containment_enabled_harness_scenario` loads and runs the scenario and asserts `result.passed is True`. Confirmed PASS on fresh run. Corroborating unit: `test_account_auto_contain_when_feature_gate_enabled` asserts `final_disposition == AUTO_CONTAIN` and directive `target_type == ACCOUNT`.

### AC-3 — Feature-disabled configs still escalate `account_containment_disabled` — MET

- `gate.py:377-378`: authorized account eligibility + `account_auto_contain_enabled` False → `_escalate(proposed, ACCOUNT_CONTAINMENT_DISABLED, system_fault=False)`. `gate.py` unchanged for this path (as implementer claimed).
- `test_account_containment_disabled_when_gate_false` (default snapshot, gate off) asserts `final_disposition == ESCALATE` and `fault_flags == [ACCOUNT_CONTAINMENT_DISABLED]`. Fresh PASS.
- Disabled harness scenario `evals/scenarios/account_containment_feature_gate_disabled.yaml` (same corroborated fixture, no enable precondition) expects escalate + `account_containment_disabled`, `system_fault_escalation: false` — consistent and covered by the harness suite.

### AC-4 — Verifier checks only V2-024 acceptance, not V2 Gate 4 — MET

- I evaluated only the four task-scoped criteria and ran only the task verification command plus the named acceptance tests. I did not run or gate on `run_phase3_gate` / V2 Gate 4 exit. No phase-level completion was asserted.

## Skeptical probes attempted (and why the claim survives)

- "Does the PASS-direction preflight test actually exercise the gate, or pass vacuously?" — It uses the real unmocked subprocess gate; the REJECT test proves the same code path raises when the gate is False. The gate is therefore load-bearing, not decorative.
- "Can org-config self-attestation bypass the gate?" — No: `phase_3_identity_gates_passed` is not read by preflight; dedicated test confirms rejection even when self-attested True.
- "Is the enabled harness scenario a real auto_contain, or a fixture that trivially matches?" — The gate requires SID-backed + corroborated identity AND the enable flag AND an auto_contain-capable policy; all three are set through the real snapshot-override path and the fixture supplies genuine two-source corroboration with a matching account SID target.
- "Stale evidence?" — All results produced by fresh runs this session (177 passed; 6/6 named tests passed).

## Gaps

None within V2-024 scope.
