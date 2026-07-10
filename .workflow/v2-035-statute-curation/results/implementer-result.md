# Implementer Result — V2-035 Statute Curation Workflow

## Files changed

| File | Rationale |
|---|---|
| `src/praetor/codification/models.py` | `PROPOSED_STATUTE_ARTIFACT_KIND` and `STATUTE_CURATABLE_SECTIONS` constants |
| `src/praetor/codification/placeholders.py` | `is_proposed_statute_artifact`; broaden review-only preflight guard to include `proposed_statute` |
| `src/praetor/codification/statute_curation.py` | Workflow artifact, proposed statute builder, JSON serialization, activation-ready stripping |
| `src/praetor/codification/__init__.py` | Export statute curation symbols |
| `src/praetor/config/activation.py` | `promote_statute_curation` — SOC-lead full preflight activation with audit trail |
| `tests/codification/test_statute_curation.py` | Review-only preflight, workflow artifact, edit validation, round-trip tests |
| `tests/config/test_statute_curation_activation.py` | SOC-lead promotion, audit recording, role guard, YAML output tests |
| `docs/operator_runbook.md` | Statute curation workflow section (curatable sections, artifact, promotion, non-goals) |

## Design summary

### Review-only proposed statute (`codification/statute_curation.py`)

- `build_proposed_statute_artifact` applies explicit `StatuteEdit` replacements to curatable sections (`normal_admin_patterns`, `containment_exclusions`, `containment_policy`) and marks output with `artifact_kind: proposed_statute` and `activation_status: proposed_for_review_only`.
- `build_statute_curation_workflow` assembles a tracked artifact with source annotations, proposed edits, reviewer, proposed config, and an `activation_audit` slot (null until promotion).
- `render_statute_curation_workflow_json` / `statute_curation_workflow_from_json` provide durable JSON round-trip for operator tickets.

### Preflight guard (`codification/placeholders.py`)

- `is_proposed_org_config_artifact` now rejects both `proposed_org_config` (sweep) and `proposed_statute` (curation) artifact kinds via shared `REVIEW_ONLY_PROPOSED_ARTIFACT_KINDS` — no `preflight.py` edit required.
- Preflight returns `proposed_artifact_not_activatable` for proposed statute YAML.

### SOC-lead promotion (`config/activation.py`)

- `promote_statute_curation` authenticates SOC lead, strips review-only markers via `activation_ready_config`, runs full `activate_org_config` preflight + reconciliation, and records `StatuteCurationActivationAudit` on the workflow artifact (snapshot hash, reviewer, reconciliation side effects).
- Optional `output_path` writes activation-ready YAML for ticket attachment.

### Operator runbook

- Documents curatable sections, workflow artifact fields, review-only preflight guard, `promote_statute_curation` promotion path, and explicit non-goals (no auto-apply from annotations).

## Verification

```bash
pytest tests/codification/ tests/config/ -q
```

```
109 passed in 9.61s
```

## Acceptance mapping

| Criterion | Evidence |
|---|---|
| Annotation-to-proposed-statute artifact is review-only and not activatable | `test_proposed_statute_artifact_is_review_only_and_not_activatable` |
| SOC-lead promotion runs full preflight and records activation audit trail | `test_soc_lead_promotion_runs_preflight_and_records_activation_audit` |
| Workflow artifact captures source annotations, proposed edits, reviewer, activation result | `test_workflow_artifact_captures_annotations_edits_reviewer_and_activation_slot` |
| Operator runbook section for statute curation | `docs/operator_runbook.md` § Statute curation workflow |

## Unresolved / deferred

- Queue **not** marked done (per task instructions).
- Workflow JSON persistence to SQLite/state store deferred — artifact is serializable but not yet wired to `open_state_store` schema init (outside files_allowed).
