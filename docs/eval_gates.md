# Eval gates

This document distinguishes deterministic eval evidence from probabilistic probes.

## Structural prompt isolation (Task 14) — deterministic

**What it proves**

- `raw_source` never appears in provider-facing payload keys or values
- Every excerpt text is at most `MAX_PROMPT_EXCERPT_CHARS` (200)
- Truncated excerpts set `incomplete=true` and include exact `[...omitting N characters]` markers

**Where it runs**

- `tests/judgment/test_prompt_isolation.py`
- Mandatory harness scenario `prompt_construction_isolation` (`evals/scenarios/prompt_construction_isolation.yaml`)

**CI behavior**

- Included in default `pytest -q`
- Failure blocks merge

## Similar-case retrieval (V2-034) — deterministic

**What it proves**

- Retrieval selects only human-confirmed precedents (`disposition_correct=true` on analyst annotations)
- Ranking contract: token overlap with current evidence excerpt text, then recency of confirmation, then stable `decision_id` tie-break; at most `MAX_PROMPT_EXEMPLARS` (3)
- Retrieved cases wire into `prompt_exemplar_block` via V2-033 exemplar types
- Exemplar payloads are bounded and excluded from evidence hash derivation (`prompt_excerpt_set` and `evidence_bundle_hash` unchanged when exemplars are present)
- Citation validity and raw-source exclusion behavior are unchanged

**Ranking contract**

1. Eligibility: decision has at least one analyst annotation with `disposition_correct=true`.
2. Exclusion: active `decision_id` (when provided) is never retrieved.
3. Similarity: token overlap between current evidence excerpt-eligible text and precedent summary (narrative, key tells, benign alternatives, analyst comment).
4. Recency: among equal overlap, prefer the more recently stored human-confirmed annotation.
5. Stability: tie-break on `decision_id` ascending.
6. Bound: return at most `MAX_PROMPT_EXEMPLARS` (3).

**Where it runs**

- `tests/judgment/test_similar_case_retrieval.py`
- `src/praetor/retrieval/ranking.py` (contract docstring)

**CI behavior**

- Included in default `pytest -q` via `tests/judgment/`
- Failure blocks merge

## Real-provider adversarial excerpt probe (Task 27) — probabilistic

**What it exercises**

- Instruction-like text embedded in normalized, excerpt-eligible fields (e.g. `command_line`) that survives Task 14 sanitization
- Optional live Vertex/Gemini call via `VertexProvider` when `PRAETOR_REAL_PROVIDER_PROBE=1` and an API key is configured

**What it does not prove**

- That a live model will resist prompt injection on every run
- That containment or disposition outcomes are safe under adversarial model behavior

**Where it runs**

- `evals/real_provider_adversarial.py`
- `tests/evals/test_real_provider_adversarial.py` (integration test marked `@pytest.mark.integration` and `@pytest.mark.probabilistic`)

**CI behavior**

- Default `pytest` excludes `integration` and `probabilistic` markers
- Deterministic unit tests (mocked Vertex provider path, structural pre-checks) run in CI
- Live probe results are logged for operator review only

**Manual live run**

```powershell
$env:PRAETOR_REAL_PROVIDER_PROBE = "1"
$env:PRAETOR_GEMINI_API_KEY = "<key>"
python -m evals.real_provider_adversarial
```

See also `docs/decisions.md` DEC-047.

## Eval harness regression locking (V2-036) — deterministic

**What it proves**

- Every confirmed model error is either pinned by a mandatory harness scenario under `evals/scenarios/` or covered by an explicit waiver recorded in `docs/decisions.md` / `memory-bank/decisions.md`
- Scenario YAML passes schema validation (`evals/schemas/scenario_schema.json`) and expectation-key validation at load time (AG-0077)
- Escalate outcomes declare `fault_flags` and `system_fault_escalation` consistent with `docs/contracts.md` §13 / Outcome Matrix
- Outcome Matrix escalate-producing fault flags remain covered by `test_outcome_matrix_completeness_guard`

**Minimum scenario quality**

1. `schema_version` is `"1"`; `scenario_id` matches the filename stem.
2. `runner` is one of the harness runners enumerated in the scenario schema.
3. `description` is non-empty and states the behavior under test.
4. Escalate blocks include `final_disposition`, `fault_flags`, and `system_fault_escalation`.
5. `fault_flags` use canonical `OutcomeMatrixFaultFlag` enum values with SFE polarity matching `evals/outcome_matrix.py`.
6. New escalate-producing fault flags ship with a companion scenario in the same change (GR-0012); startup-only flags may be waived per AG-0070 with a documented decision.

**Expectation-key validation**

The harness assertion layer maintains a runner-scoped key registry (`RUNNER_EXPECTATION_KEYS` in `evals/harness.py`). At scenario load:

- **Unknown keys** — any top-level expectation key not in `ALL_EXPECTATION_KEYS` is rejected.
- **Stale keys** — keys recognized globally but not consumed by the scenario's `runner` are rejected (prevents typos and copy-paste drift across runners).
- **Nested keys** — `revocation_feed_degraded_mode` `auto_contain` / `standard_review` blocks may only use `final_disposition`, `fault_flags`, and `system_fault_escalation`.

Silently ignored YAML keys produce false-green passes; the validator fails closed.

**Where it runs**

- `evals/harness.py` — `load_scenario` / `_validate_expectations`
- `tests/evals/test_expectation_key_validation.py` — CI guard for registry completeness and stale/unknown keys
- `tests/evals/test_eval_harness.py` — schema, Outcome Matrix completeness, full harness pass

**CI behavior**

- Included in default `pytest -q` via `tests/evals/`
- Failure blocks merge

**Workflow discipline**

- `.workflow/_template/` requires every confirmed model error in a task's final report to cite `evals/scenarios/<scenario_id>.yaml` or an explicit waiver decision ID

## Phase gates (release checklist)

Phase gates aggregate task-level evidence. Run from repo root after `pip install -e ".[dev]"`.

### Phase 1 — Durable walking skeleton (Tasks 1–12)

```powershell
python -m pytest -q
python -m mypy src
python -m ruff check src tests
python -m pytest -q tests/benchmarks/test_smoke_benchmark.py
```

Pass: contracts exported, WAL + singleton enforced, lifecycle/outboxes operational, smoke benchmark runs against provisional targets, recovery never emits containment.

### Phase 2 — Judgment and policy (Tasks 13–27)

```powershell
python -m evals.harness
python -m pytest -q tests/evals/
python -m pytest -q tests/policy/ tests/judgment/ tests/metrics/
```

Pass: mandatory eval scenarios, Outcome Matrix completeness, reference consumer verifier, adversarial probe documented as probabilistic (above). Production intake integration validated at Task 28a / Phase 3.

### Phase 3 — Correlation (Tasks 28–31)

```powershell
python -m evals.run_phase3_gate
python -m evals.correlation_gate
python -m pytest -q tests/correlation/ tests/evals/test_phase3_regression_gate.py
```

Pass: identity compliance on real fixtures, correlation accuracy gate, citation-anchored host targeting, PolicyGate wired into intake with deferred directive persist.

### Phase 4 — Detection portability (Tasks 32–33)

```powershell
python tools/compile_sigma.py --check
python -m pytest -q tests/detections/ tests/splunk/
```

Pass: Sigma validation, deterministic SPL, Splunk demo artifacts with checksum-verified fixtures; Sigma↔SPL matcher sets pinned per rule over manifest fixtures; `savedsearches.conf` uses fixture-stable dispatch window (`2026-06-08`).

**`tools/` mypy exclusion**

`python -m mypy .` strict-checks `praetor`, `consumer_sdk`, and `evals` only. The `tools/` tree (Sigma compiler, SPL matcher, Splunk ingest) is excluded via `pyproject.toml` `[tool.mypy] exclude` because it is operator/demo scripting outside the production source packages and currently carries pySigma untyped-export noise. Ruff still lints `tools/**/*.py`. To typecheck tooling explicitly: `python -m mypy tools/compile_sigma.py tools/spl_match.py tools/fixture_events.py tools/splunk_conf.py` (advisory, not a merge gate).

### Phase 5 — Operator readiness (Tasks 34–35)

```powershell
python -m pytest -q tests/codification/
python -m pytest -q tests/benchmarks/test_serialized_path.py
python -m pytest -q tests/docs/
python -m evals.run_phase5_benchmark
```

The benchmark step is self-contained: it creates a temporary DB, activates
``configs/example_org.yaml``, runs 30 DEC-053 production-path iterations, and
prints sustained rate vs the active provisional targets. No pre-existing
``state/bench.db`` is required.

Pass: org-config sweep produces review-only proposed artifacts; production throughput ceiling measured and documented in `docs/operator_runbook.md`; operator runbook and architecture cover responsibility boundaries; Splunk live demo is env-gated (`PRAETOR_SPLUNK_HEC_HOST` / `PRAETOR_SPLUNK_HEC_TOKEN`) per `splunk/README.md` — default CI excludes `@pytest.mark.integration`.

## Non-gating: judgment capability spike

`python -m evals.capability_spike --manifest <m.yaml> --capture <c.jsonl> --out <r.jsonl>`

Measures whether the single-shot judgment layer separates malicious from benign
telemetry, and how much of any failure is caused by correlation's two-event-type
coverage limit (Path A vs Path B).

**Not a CI gate.** Requires `PRAETOR_CAPABILITY_SPIKE=1` and a Gemini API key;
exits 0 with a skip message otherwise. Scores `ModelJudgment.proposed_disposition`
only — PolicyGate output is recorded but never scored, because the gate controls
authority rather than judgment quality.

Design: `docs/superpowers/specs/2026-08-01-capability-spike-design.md`
