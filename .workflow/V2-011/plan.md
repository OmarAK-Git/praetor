# Workflow Plan — V2-011

## Goal

Wire DEC-059 host corroboration floor into PolicyGate: cited facts must span ≥2 provenance paths with ≥1 non-attacker-controllable source; sole ambiguous cited fact blocks host `auto_contain`; account path unchanged.

## Scope

### In scope

- `meets_host_cited_corroboration` in `provenance.py` using citation validator metadata
- PolicyGate host-target check → `insufficient_corroboration` (`system_fault_escalation=false`)
- `OutcomeMatrixFaultFlag` + harness completeness + scenario YAML
- Update default host test/harness bundles to corroborated sysmon+security pairs for passing auto_contain paths
- Targeted policy/evidence tests per V2-011 criteria

### Out of scope

- V2-012+ default-action posture
- Correlator host isolation (V2-014)
- Doc changes (`docs/` frozen for implementation tasks)

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Host `auto_contain` with one cited provenance escalates `insufficient_corroboration`. |
| REQ-002 | Two distinct cited paths pass only when ≥1 is non-attacker-controllable. |
| REQ-003 | Sole cited `ambiguity_flag=true` fact cannot authorize host containment. |
| REQ-004 | Account corroboration / `ambiguous_target_identity` unchanged. |
| REQ-005 | Harness scenario covers `insufficient_corroboration`. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Policy gate test: single-sysmon cite → escalate + flag. |
| AC-002 | REQ-002 | Policy gate test: sysmon+security cite → auto_contain (permissive policy). |
| AC-003 | REQ-003 | Policy gate test: sole ambiguous cite → escalate + flag. |
| AC-004 | REQ-004 | Existing account escalation tests still pass unchanged. |
| AC-005 | REQ-005 | `evals/scenarios/insufficient_corroboration.yaml` + completeness guard green. |

## Implementation Plan

| Task | Description | Files | Status |
|---|---|---|---|
| T-001 | Provenance helpers + attacker-controllable table | `provenance.py`, `citations.py` types | pending |
| T-002 | PolicyGate host corroboration gate | `gate.py`, `identity.py` | pending |
| T-003 | Enum + outcome matrix | `metrics/events.py`, `outcome_matrix.py` | pending |
| T-004 | Fixtures + tests + harness scenario | `conftest.py`, `harness.py`, `tests/`, `evals/scenarios/` | pending |
