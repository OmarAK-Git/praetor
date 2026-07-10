# Verifier Result — V2-035 Statute Curation Workflow

**Verdict (task acceptance + stated command): SURVIVES**
**Caveat: 5 ruff lint errors in the delivered test files (see Findings).**

Role: adversarial skeptic-verifier. I gathered my own evidence (ran the command, read the diff and code paths). I did not trust the implementer transcript.

## Claim under review

Completion of V2-035 per its four acceptance criteria, verified by:

```
pytest tests/codification/ tests/config/ -q
```

## Evidence gathered

### Stated command — PASS

```
python -m pytest tests/codification/ tests/config/ -q
109 passed in 10.47s   (exit 0)
```

Ran the full two directories (no test-selection gaming), 0 skipped/xfail. Matches the implementer's claimed `109 passed`.

### Criterion 1 — Annotation-to-proposed-statute artifact is review-only, not activatable — SURVIVES

- `build_proposed_statute_artifact` stamps `artifact_kind: proposed_statute` + `activation_status: proposed_for_review_only` (`statute_curation.py:74-102`).
- The "not activatable" guarantee is enforced by a *real* preflight path, not a test stub: `run_preflight` calls `_reject_proposed_sweep_artifact` as its first step (`preflight.py:143`), which raises `proposed_artifact_not_activatable` when `is_proposed_org_config_artifact` is true. That helper was broadened to a shared `REVIEW_ONLY_PROPOSED_ARTIFACT_KINDS` set covering both `proposed_org_config` and `proposed_statute` (`placeholders.py:16-29`).
- Confirmed by `test_proposed_statute_artifact_is_review_only_and_not_activatable` (asserts the real error code from real `run_preflight`) and `test_promotion_rejects_review_only_proposed_artifact_without_stripping` (promotion with `activation_ready=False` is rejected with the same code).

### Criterion 2 — SOC-lead promotion runs full preflight + records activation audit — SURVIVES

- `promote_statute_curation` (`activation.py:121-185`) authenticates via `authenticate_org_config_activation` → `authenticate_write(surface=ORG_CONFIG_ACTIVATION)`, which enforces `principal.role == required_role` (`verifier.py:111-116`). The role gate is genuine, not mocked: `test_wrong_role_rejected_for_statute_promotion` proves an `analyst` principal raises `InsufficientRoleError`.
- Promotion strips review-only markers via `activation_ready_config` and then delegates to the *same* `activate_org_config` used for normal activation, i.e. the full `run_preflight` + reconciliation path (`activation.py:163-169`). No weakened/alternate preflight.
- Audit trail recorded on the workflow via `StatuteCurationActivationAudit` (snapshot hash, reviewer, revoked/retired/emitted ids, batch id). `test_soc_lead_promotion_runs_preflight_and_records_activation_audit` verifies the returned audit's `snapshot_hash` equals the activation hash *and* that `fetch_active_org_config(store.conn)` returns a record with that same hash — proving preflight/activation actually ran end-to-end against the store.

### Criterion 3 — Workflow artifact captures source annotations, proposed edits, reviewer, activation result — SURVIVES

- `StatuteCurationWorkflow` holds `source_annotations`, `proposed_edits`, `reviewer`, `proposed_config`, and `activation_audit` (`statute_curation.py:50-57`).
- `test_workflow_artifact_captures_annotations_edits_reviewer_and_activation_slot` asserts all four are captured, audit slot starts `None`, and JSON round-trip preserves them.
- Activation result is captured post-promotion via `with_activation_audit`; verified in criterion-2 test.

### Criterion 4 — V2-035 scope only — SURVIVES

- Changed source files are confined to the curation feature: `codification/{models,placeholders,statute_curation,__init__}.py`, `config/activation.py`, plus the two new test files and runbook. The `placeholders.py` broadening reuses existing preflight wiring (no `preflight.py` edit), and the full 109-test run across both dirs passing confirms the sweep-artifact behavior was not regressed by the shared-set change.

### Independent checks beyond the stated command

- `mypy src/praetor/codification/statute_curation.py src/praetor/config/activation.py` → `Success: no issues found` (exit 0).

## Findings (not part of the stated acceptance command, but gate-relevant)

`ruff check` fails on the delivered **test** files (source modules are clean):

- `tests/codification/test_statute_curation.py`: I001 (import block unsorted — `load_org_config_source` imported after a blank line), F401 (`pathlib.Path` unused), E501 (line 94 > 88).
- `tests/config/test_statute_curation_activation.py`: F401 (`render_proposed_statute_yaml` unused), F401 (`PreflightError` unused).

4 of 5 are `--fix` auto-fixable. These do **not** refute any of the four acceptance criteria or the stated `pytest` command, but this repo's workflow treats `ruff check .` as a gate, and no `lint-remediation-result.md` exists for this task (unlike sibling V2 tasks). Recommend a lint pass before gate exit.

## Conclusion

The four acceptance criteria and the required `pytest tests/codification/ tests/config/ -q` command all survive adversarial scrutiny with reproduced, first-hand evidence. The only defect is trivial lint noise in the two new test files, which is outside the task's stated verification command but should be cleaned up for gate readiness.
