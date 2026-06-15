# Review: TASK-031

## Scope adherence

- Citation-anchored host targeting (Option A / DEC-052) in `containment_policy.py` + `gate.py`; orchestrator uses directive target from gate evaluation.
- New fault flag wired: `identity.py`, `metrics/events.py`, `outcome_matrix.py`, `docs/contracts.md` §13, `evals/scenarios/multi_host_target_ambiguity.yaml`.
- Phase 3 noisy gate re-greened with window filter (9999) + honest noise bounds; host safety via citation-anchored `evaluate_policy_gate`.
- No `docs/spec.md` changes.

## Findings

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| REVIEW-001 | info | Plan says "marked integration" and "real OTRF fixture"; v1 uses committed local fixtures. | Same precedent as TASK-028/029/030. |
| REVIEW-002 | gap | External OTRF/Mordor bulk download not implemented. | Recorded; committed fixtures stand in. |
| REVIEW-004 | forward pressure | Correlator may still collect cross-host in-window noise (1004); targeting no longer polluted (DEC-052). | `test_correlator_should_drop_cross_host_in_window_noise` strict xfail remains. |

## Binding assertions (REQ-002 / REQ-003)

- **REQ-002:** Window discrimination via `excluded_record_ids: [9999]`; in-window noise bounded at honest ceilings (`max_collected_facts: 5`, `max_noise_overcollection: 2`). Gate GREEN on healthy tree.
- **REQ-003:** Host containment via citation-anchored gate: directive targets literal `WORKSTATION1`, not uncited `WORKSTATION2` noise.

## REQ-001 intake gap

- Correlated bundle + `evaluate_policy_gate` exercised in phase 3 gate and policy tests.
- TASK-028a `process_alert_intake` telemetry path not in phase 3 gate CLI; orchestrator deferred persist uses gate directive target.

## safe_to_commit

yes — gate GREEN on healthy tree 2026-06-15
