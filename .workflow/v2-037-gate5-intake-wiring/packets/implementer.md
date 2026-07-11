# Implementer Packet — V2-037 Gate 5 Intake Wiring

**implementation_model:** composer-2.5-fast

## Objective

Wire Gate 5 libraries into the live intake path:

1. Persist dimensional PolicyGate evaluations via `record_policy_gate_evaluation`.
2. Inject similar-case exemplars into the judgment prompt during `process_alert_intake`.

## Original goal

V2-037 — Gate 5 intake wiring: persist policy_gate_evaluations from production intake (schema init + record with target_type/asset_class) and inject similar-case exemplars into the judgment prompt on the live orchestrator path.

## Relevant docs and state

- Approved design in chat: schema ensure + record in edict critical_transaction; asset_class = first matching group else `ungrouped`, `unknown` if no target; similar-case retrieve before provider call into existing excerpt-set builder.
- `docs/proposals/v2_hardening.md` Item 3/4 follow-ups
- `docs/operator_runbook.md` progressive reporting section
- `src/praetor/metrics/evaluations.py` — `init_policy_gate_evaluation_schema`, `record_policy_gate_evaluation`
- `src/praetor/reporting/progressive_authorization.py`
- `src/praetor/judgment/prompt.py` — `build_judgment_prompt_payload_from_excerpt_set` already accepts `exemplar_block`
- `src/praetor/retrieval/similar_cases.py` — `retrieve_similar_case_exemplars`
- `src/praetor/policy/containment_policy.py` — `_asset_groups_for_target`
- `src/praetor/policy/state.py` — `ensure_production_policy_tables`, `REQUIRED_PRODUCTION_POLICY_TABLES`
- `src/praetor/engine/orchestrator.py` — `process_alert_intake`
- `.workflow/_dream/playbook.digest.md` — GR-0017 (critical_transaction write groups), AG-0021 (lazy imports)

## Allowed files (strict)

- `src/praetor/engine/`
- `src/praetor/policy/`
- `src/praetor/metrics/`
- `src/praetor/judgment/`
- `src/praetor/retrieval/`
- `src/praetor/runtime/`
- `docs/operator_runbook.md`
- `docs/proposals/v2_hardening.md`
- `docs/architecture.md`
- `tests/engine/`
- `tests/runtime/`
- `tests/metrics/`
- `tests/judgment/`
- `specs/`, `IMPLEMENTATION_PLAN.md`, `memory-bank/tasks.md`, `memory-bank/progress.md`, `memory-bank/activeContext.md`
- `.workflow/v2-037-gate5-intake-wiring/`

## Do-not-touch

- Do not mark the queue item done.
- Do not run full-suite pytest/ruff/mypy or any phase gate.
- Do not install dependencies or edit `.claude`/`.codex`.
- Do not change containment disposition semantics, Outcome Matrix, or evidence hashing.
- Do not widen beyond `files_allowed` — stop with `approval_gates` if blocked.

## Acceptance criteria

1. Production schema ensure creates `policy_gate_evaluations`; `open_production_state_store` path has the table.
2. Completed `process_alert_intake` persists a `policy_gate_evaluations` row with `target_type` and `asset_class` (first matching asset group, else `ungrouped`; `unknown` when no resolved target).
3. `process_alert_intake` builds the judgment prompt with retrieved human-confirmed similar-case exemplars when precedents exist; empty retrieval leaves prompt without exemplar block.
4. Task-scoped tests cover recording + exemplar injection; disposition/containment behavior unchanged.

## Verification commands

```bash
pytest tests/engine/test_gate5_intake_wiring.py tests/runtime/test_production_state_init.py tests/metrics/test_progressive_authorization_reporting.py tests/judgment/test_similar_case_retrieval.py -q
```

## Implementation hints

### Schema init

- Call `init_policy_gate_evaluation_schema` from `ensure_production_policy_tables`.
- Add `policy_gate_evaluations` to `REQUIRED_PRODUCTION_POLICY_TABLES`.
- Update `tests/runtime/test_production_state_init.py` `REQUIRED_PRODUCTION_TABLES` to match.
- Also call schema init outside the edict `critical_transaction` in intake (before `with critical_transaction`) so non-production test stores that somehow skip ensure still work; `CREATE IF NOT EXISTS` is idempotent. Do **not** call `executescript` inside an open critical transaction.

### Evaluation recording

- Inside the same `critical_transaction` that appends the edict (after stamp-resolved path), call `record_policy_gate_evaluation`.
- Use **post-stamp** proposed/final dispositions from the edict (or disposition object used to build the edict) so override flag matches what was committed.
- Dimensions helper (prefer public function in `policy/containment_policy.py` or `metrics/evaluations.py`):
  - no `resolved_target` → `target_type="unknown"`, `asset_class="unknown"`
  - else `target_type=target.target_type`, `asset_class=first(_asset_groups_for_target(...)) or "ungrouped"`
- `evaluated_at=datetime.now(UTC)` (or stamp/edict time if already available).
- Also record on deferred-persist conflict rebuild path if that path still commits an edict in the same transaction.

### Similar-case prompt injection

- Before provider call, keep existing `excerpt_set` from correlation.
- `exemplars = retrieve_similar_case_exemplars(store.conn, evidence_facts=..., exclude_decision_id=decision_id)` — compute `decision_id` early via `decision_id_for_attempt` (deterministic).
- `exemplar_block = build_prompt_exemplar_block(exemplars) if exemplars else None`
- Pass `exemplar_block` into `build_judgment_prompt_payload_from_excerpt_set`.
- Empty retrieval → no `prompt_exemplar_block` key (unchanged behavior).

### Tests

Create `tests/engine/test_gate5_intake_wiring.py`:

1. After successful auto_contain/escalate intake (reuse tripwire fixtures), assert one row in `policy_gate_evaluations` for the decision_id with expected dimensions.
2. Seed a human-confirmed annotation precedent, use a capturing judgment provider that records the request payload, assert `prompt_exemplar_block` present when precedents match; assert absent when none.
3. Production table presence covered by updating `test_production_state_init.py`.

### Docs

- Clear the “follow-up: not wired” notes in `docs/proposals/v2_hardening.md`, `docs/architecture.md`, and adjust runbook if it still says evaluation rows must be recorded manually.

## Expected result

Write `.workflow/v2-037-gate5-intake-wiring/results/implementer-result.md` with:

- files changed
- design summary
- verification command output (verbatim)
- any approval_gates or deferred items

Do not update queue status.
