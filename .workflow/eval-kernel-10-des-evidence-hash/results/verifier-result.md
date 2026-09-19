# Verifier result — eval-kernel-10-des-evidence-hash (Task 10)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

Claim restated: Task 10 is done — `des.evidence_hash_stable` pins that the same logical `EvidenceBundle` yields the same `evidence_bundle_hash` across two kernel runs; both `old_build` and `new_build` pass on FakeProvider; hash drift is `failure_class=harness`, never `model`.

Implementer results (`1 passed`, ruff/mypy green, commit `4e78711`) were treated as unevidenced until re-run.

Skeptic verdict on the completion claim: **survives**.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| Both arms pass | **met** | YAML pins both arms `provider: fake` with `hashes_equal: true` / `hash_length: 64` (`evals/e2e_scenarios/des.evidence_hash_stable.yaml:10-19`). Fresh `test_des_evidence_hash_stable.py` → 1 passed. Independent `run_e2e_kernel` dump: both arms `status=pass`, `failure_class=none`, `provider=fake`, `observed.hashes_equal=True`, `observed.hash_length=64`. |
| Two kernel runs of the same logical bundle produce the same evidence_bundle_hash | **met** | `run_e2e_kernel` executes each loaded scenario once per arm (`evals/e2e_kernel.py:435-437`). Independent dump: `old_build.first` == `new_build.first` == live `hash_evidence_bundle(_host_bundle(host_id='ws-01'))` == `7cd028fdd33c8b708a29d5a57eb86ea77c2c5138c34db5cc546cb2bfe82bc246` (64 lowercase hex). Two separately constructed host bundles also matched. Executor calls `hash_evidence_bundle` twice on the resolved bundle (`evals/e2e_kernel.py:339-350`) and pins `hashes_equal` to `first == second`. Path is `EvidenceBundle.model_dump()` → `canonical_hash` → `sha256_hex` (`src/praetor/engine/ids.py:16-18`); timestamps go through `_format_datetime_utc` six-digit UTC (`src/praetor/hashing/canonical.py:41-47`). `_host_bundle` uses `FIXED_NOW` (`evals/harness.py:366-388`). |
| Drift is classified harness/design, not model | **met** | Pin mismatch sets `failure_class="harness"` (`evals/e2e_kernel.py:107-110`). Executor exceptions emit `status=error`, `failure_class=harness` (`:155-162`). `evals/e2e_kernel.py` never assigns `failure_class="model"`. Independent probes: expected `hashes_equal: false` → `fail/harness`; expected `hash_length: 32` → `fail/harness`; `bundle: no_such_bundle` → `error/harness`. Provider is `fake`; this executor does not call a provider. |
| Verifier checks only Task 10 acceptance, not Sprint 1 gate completion | **met** | Commands limited to the packet set. No remaining YAML required; no Sprint 1 / phase-exit suite run. Queue item still `in_progress`. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest tests/evals/e2e/test_des_evidence_hash_stable.py -q` | **0** | `.` — 1 passed in 2.36s (no skips) |
| `ruff check evals/e2e_kernel.py tests/evals/e2e/test_des_evidence_hash_stable.py` | **0** | All checks passed |
| `mypy evals/e2e_kernel.py` | **0** | Success: no issues found in 1 source file |

Re-run in this session against `C:\Users\oalan\Praetor` working tree. Implementer transcript was not treated as evidence.

Pytest duration (~2.4s) is consistent with real kernel load (gov + envelope + path-b YAMLs + missing-ID error rows; the test filters to this ID).

Product files match HEAD `4e78711`:
- `evals/e2e_kernel.py` `f0f5375f373edd062c6c0b6b365e0379510c9c41`
- `evals/e2e_scenarios/des.evidence_hash_stable.yaml` `67eb17deee88d693c50f7ad7d96982c1f3b5cb5a`
- `tests/evals/e2e/test_des_evidence_hash_stable.py` `e2ad9ffa4dae2f23e12658be6d00938746f27e32`

`git diff 4e78711^ 4e78711 --name-only` names only those three files. `git diff HEAD -- src/praetor` empty. Working tree matches HEAD for the three product paths.

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| Writes only allowed files | **met** | `4e78711` product paths are the three allowed code/test/YAML files. No `src/praetor/**`, no OM scenario edits, no Task 11–19 YAML. `REQUIRED_E2E_SCENARIO_IDS` already listed this ID (Task 1). |
| YAML / test / executor match Task 10 snippet | **met** | `des.evidence_hash_stable.yaml`, `test_des_evidence_hash_stable.py`, and `_run_des_hash` match plan Step 3 / Step 1 (including diagnostic `first`/`second`). Scorecard pins are the two named keys. `theater_detector: post_hoc_protocol`. |
| Dispatch wired | **met** | `run_e2e_scenario` calls `_run_des_hash` for `des.evidence_hash_stable` (`evals/e2e_kernel.py:101-102`). Loader returns the YAML: realm `design`, pins `('hashes_equal', 'hash_length')`, setup `{bundle: host, host_id: ws-01}`. |

## Independent probes (not in packet)

- Loader: `list_e2e_scenarios` returns exactly one `des.evidence_hash_stable` document.
- Fresh `run_e2e_kernel` dump: 2 rows; both `pass` / `none` / `fake` / `design`; observed first/second identical 64-hex digest above.
- `_run_des_hash` output matches a direct `hash_evidence_bundle` call on `_resolve_policy_bundle(setup)` and on a separately constructed `_host_bundle(host_id='ws-01')`. The happy-path test is not being satisfied by a stubbed `{hashes_equal: True, hash_length: 64}` on this tree.
- Pin-mismatch and exception probes (above) classify as `harness`, never `model`.
- `post_hoc_protocol` cannot trip on this path: `run_e2e_scenario` hardcodes `excerpt_blob=""` (`evals/e2e_kernel.py:119`); detector only trips on `post_hoc_relabel` / `prompt_changed_after_score` in that blob (`evals/theater.py:98-101`). Plan-faithful.
- Dispatch is ID-gated (`evals/e2e_kernel.py:101`); does not also require `realm == design`. YAML realm is `design`. Inconsistency only.

## Gaps

None that fail Task 10 acceptance.

Residual (non-blocking, not Task 10 AC failures):

- Intra-call same-object double-hash (`evals/e2e_kernel.py:342-344`). Catches a non-deterministic `hash_evidence_bundle`. The prescribed test does not assert `old_build.first == new_build.first` or rebuild the bundle between calls. Cross-arm equality was confirmed in this session, not by the packet test. Plan-faithful.
- Happy-path test would accept a stubbed dict (`tests/evals/e2e/test_des_evidence_hash_stable.py:20-21`). Diagnostic `first`/`second` are on the row but unused. Prescribed. This session compared those digests to live `hash_evidence_bundle`.
- No dedicated negative row that a hash mismatch is `failure_class=harness`. Classification is the existing kernel pin loop. Track only; this session's mismatch probes are not part of the committed test.
- `post_hoc_protocol` with empty `excerpt_blob` cannot trip. Theater name is not independent proof. Plan-faithful.
- Queue item `eval-kernel-10-des-evidence-hash` remains `in_progress` (implementer packet: do not mark done).
