# Verifier result — eval-kernel-08-des-envelope (Task 8)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

Claim restated: Task 8 is done — `des.envelope_rejects_extra_fields` pins that `AlertEnvelope` construction with any field other than `schema_version` + `alert_identity` raises; identity-only construction succeeds; both `old_build` and `new_build` pass on FakeProvider; no `AlertEnvelope` field expansion in `src/`.

Implementer results (`1 passed`, ruff/mypy green, `alert.py` untouched) were treated as unevidenced until re-run.

Skeptic verdict on the completion claim: **survives**.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| Both arms pass on FakeProvider | **met** | YAML pins both arms `provider: fake` with identical `raises_validation_error: true` / `accepted_legal_envelope: true` (`evals/e2e_scenarios/des.envelope_rejects_extra_fields.yaml:11-20`). Fresh `test_envelope_rejects_extra_fields_both_arms` passed. Independent kernel dump: both arms `status=pass`, `failure_class=none`, `provider=fake`. Scorecard `provider` is the YAML `fake` pin, not a live Vertex path. This pin does not instantiate `FakeProvider`; `_run_des_envelope` only constructs `AlertEnvelope`. |
| Extra envelope fields raise; identity-only construction succeeds | **met** | `_run_des_envelope` (`evals/e2e_kernel.py:310-338`) first `model_validate`s `schema_version` + `alert_identity` only, then retries with `setup["extra_field"]` (`cbc_edr_alert` → `{"id": "cbc-row-1"}`). Independent probe: identity-only returns `alert_identity=des.envelope_rejects_extra_fields`; CBC extra raises `ValidationError` with `type=extra_forbidden`, `loc=('cbc_edr_alert',)`; a second unrelated extra key also raises. `ContractModel` is `extra="forbid"` (`src/praetor/contracts/_base.py:14`). Fresh scorecard observed both arms: `raises_validation_error=True`, `accepted_legal_envelope=True`, `rejected_cbc_field=cbc_edr_alert`. |
| No AlertEnvelope field expansion in src/ | **met** | `AlertEnvelope` fields remain only `schema_version` + `alert_identity` (`src/praetor/contracts/alert.py:10-17`; live `model_fields` = those two). `git diff 21eb3fc e74f3ad -- src/` empty. Working-tree blob `src/praetor/contracts/alert.py` hash `5aedd637fa18427bbf908ee27444b7690f6b9904` equals `HEAD:src/praetor/contracts/alert.py`. Last `alert.py` commit is `6fccc79`, not Task 8. JSON twin still `additionalProperties: false` with the same two properties (`schemas/alert_envelope.json`). Sole `class AlertEnvelope` in `src/`. |
| Verifier checks only Task 8 acceptance, not Sprint 1 gate completion | **met** | Commands limited to the packet set. No remaining-13 YAML required; no Sprint 1 / phase-exit suite run. Queue item still `in_progress`. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest tests/evals/e2e/test_des_envelope_rejects_extra_fields.py -q` | **0** | `.` — 1 passed in 2.25s (no skips) |
| `ruff check evals/e2e_kernel.py tests/evals/e2e/test_des_envelope_rejects_extra_fields.py` | **0** | All checks passed |
| `mypy evals/e2e_kernel.py` | **0** | Success: no issues found in 1 source file |

Re-run in this session against `C:\Users\oalan\Praetor` working tree. Implementer transcript was not treated as evidence.

Pytest duration (~2.3s) is consistent with real kernel load (gov YAMLs + missing-ID error rows; the test filters to this ID).

Product files: `git diff e74f3ad` empty for `evals/e2e_kernel.py`, `evals/e2e_scenarios/des.envelope_rejects_extra_fields.yaml`, `tests/evals/e2e/test_des_envelope_rejects_extra_fields.py`. HEAD includes `e74f3ad` (`feat(evals): pin des.envelope_rejects_extra_fields against CBC expansion`; 3 files). `src/praetor/` and `schemas/alert_envelope.json` clean.

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| `src/praetor/contracts/alert.py` is unchanged | **met** | `git diff HEAD -- src/praetor/contracts/alert.py` empty. `git hash-object` == `git rev-parse HEAD:src/praetor/contracts/alert.py` (`5aedd637fa18427bbf908ee27444b7690f6b9904`). Not in `e74f3ad`. Empty `git diff 21eb3fc e74f3ad -- src/praetor/contracts/alert.py src/praetor/contracts/_base.py`. |
| Writes only allowed files | **met** | `e74f3ad` product paths are the three allowed code/test/YAML files. No `src/praetor/**`, no OM scenario edits, no Task 9–19 YAML. |
| YAML / test match Task 8 snippet | **met** | `des.envelope_rejects_extra_fields.yaml` and `test_des_envelope_rejects_extra_fields.py` match plan Step 3 / Step 1. Scorecard pins are the two named keys. `theater_detector: post_hoc_protocol` stays clean (`excerpt_blob=""`; detector only trips on protocol-mutation markers). |

## Independent probes (not in packet)

- Loader: `list_e2e_scenarios` returns `des.envelope_rejects_extra_fields` with `runner=e2e_kernel`, realm `design`, pins exactly the two Task 8 keys, `theater_detector=post_hoc_protocol`, setup `extra_field=cbc_edr_alert` / `extra_value={"id": "cbc-row-1"}`.
- Fresh `run_e2e_kernel` dump: both arms pass; observed includes the two pins plus `rejected_cbc_field=cbc_edr_alert`; notes empty (theater did not trip).
- Direct `AlertEnvelope.model_validate`:
  - identity-only: succeeds; fields are only `alert_identity` + `schema_version`.
  - `cbc_edr_alert` extra: `ValidationError` / `extra_forbidden` / loc `('cbc_edr_alert',)` — the rejected key is unknown, not a typed-field mismatch.
  - unrelated extra key also raises (intent: any field other than the legal pair).
- `_run_des_envelope(doc)` returns the same three observed keys the test asserts.
- Dispatch is ID-gated (`evals/e2e_kernel.py:97-98`); does not also require `realm == design` (Task 5 dispatch does). YAML realm is `design`. Inconsistency only.
- Existing unit pin `tests/contracts/test_validators.py:197-201` already forbids a generic extra key. This E2E ID is the locked design pin against CBC envelope expansion, not a new contract rule.

## Gaps

None that fail Task 8 acceptance.

Residual (non-blocking, not Task 8 AC failures):

- `except ValidationError` is unscoped (`evals/e2e_kernel.py:331-332`). Any validation failure on the extra payload sets `raises_validation_error=True`. Adding `cbc_edr_alert` as a typed field that rejects a dict would keep the pin green (type error, not `extra=forbid`). Adding it as a dict-compatible field would fail the pin. This is the plan snippet. Independent probe showed `extra_forbidden` today; do not treat a bare `ValidationError` as future-proof proof the rejected key was unknown.
- `rejected_cbc_field` is echoed from YAML (`evals/e2e_kernel.py:321,337`). It is `str(setup["extra_field"])`, not an error-detail extract. The test asserts `== "cbc_edr_alert"`. A stubbed dict with the same three observed keys would keep the test green. Prescribed. `rejected_cbc_field` is not a scorecard pin.
- `_run_des_envelope` ignores `arm`; both arms execute the same envelope construction. Prescribed: identical expected pins on both arms.
- `post_hoc_protocol` cannot trip on this path. `run_e2e_scenario` hardcodes `excerpt_blob=""` (`evals/e2e_kernel.py:116`). Plan-faithful; the theater name is not independent proof.
- Queue item `eval-kernel-08-des-envelope` remains `in_progress` (implementer packet: do not mark done).
