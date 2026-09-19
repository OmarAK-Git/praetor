# Code review — eval-kernel-10-des-evidence-hash (Task 10)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 10 only (`des.evidence_hash_stable`). Sprint 1 gate and remaining IDs ignored.
**Diff reviewed:** commit `4e78711` (`evals/e2e_kernel.py`, `evals/e2e_scenarios/des.evidence_hash_stable.yaml`, `tests/evals/e2e/test_des_evidence_hash_stable.py`) plus current disk contents of those files. HEAD is `4e78711`; working tree matches that commit for the three product paths. `src/praetor/**` has an empty diff vs parent.

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 10 (through commit, before Task 11)
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §5 `des.evidence_hash_stable`
- `.workflow/eval-kernel-10-des-evidence-hash/packets/code-reviewer.md`
- `.workflow/eval-kernel-10-des-evidence-hash/plan.md` acceptance
- Hash path: `praetor.engine.ids.hash_evidence_bundle` → `canonical_hash` / `_format_datetime_utc` (six-digit UTC)

## Blocking findings

None.

## Checks

| Check | Result |
|---|---|
| Same logical bundle hashes equal | `_run_des_hash` resolves `setup.bundle=host` via `_resolve_policy_bundle` (`FIXED_NOW` host facts) and calls `hash_evidence_bundle` twice (`evals/e2e_kernel.py:339-350`). Pins `hashes_equal` to `first == second`. Dispatch wired for this ID (`:101-102`). |
| `hash_length` is SHA-256 hex | Observed length is `len(first)` from `hash_evidence_bundle` → `canonical_hash` → `sha256_hex` (64 lowercase hex chars). YAML expects `64`. Fresh test asserts `hash_length == 64`. |
| Drift is harness, never model | Pin mismatch sets `failure_class="harness"` (`e2e_kernel.py:107-110`). Executor exceptions emit `status=error`, `failure_class=harness` (`:155-162`). New code never assigns `model`. Provider is `fake`; this executor does not call a provider. |
| Both arms pass on FakeProvider | YAML pins both arms `provider: fake` with `hashes_equal: true` / `hash_length: 64`. Test asserts `{old_build, new_build}`, `status=pass`, `failure_class=none`. Fresh run: 1 passed. |
| YAML / test / executor match Task 10 snippet | `des.evidence_hash_stable.yaml`, `test_des_evidence_hash_stable.py`, and `_run_des_hash` match plan Step 3 / Step 1 text (including diagnostic `first`/`second`). Scorecard pins are the two named keys. `theater_detector: post_hoc_protocol` stays clean (`excerpt_blob=""`). |
| Writes only allowed files | `4e78711` is the three Task 10 product paths only. No `src/praetor/**`, no OM scenario edits, no Task 11–19 YAML. `REQUIRED_E2E_SCENARIO_IDS` already listed this ID (Task 1). Sprint 1 gate not run. |
| Extra product scope | None. Dispatch branch + `_run_des_hash` are the approved additive surface. |
| Verification (this review) | `pytest tests/evals/e2e/test_des_evidence_hash_stable.py -q` → 1 passed in 2.25s; `ruff check` clean; `mypy evals/e2e_kernel.py` clean. |

YAML, test, dispatch, and hash calls match the approved Task 10 snippet. Disk files match `4e78711`. Canonical six-digit UTC formatting is the existing `canonical_hash` path; this task does not re-implement it.

## Non-blocking notes

1. **Same-object double-hash, not two reconstructions** (`evals/e2e_kernel.py:342-344`). The executor hashes one in-memory bundle twice. That catches a non-deterministic `hash_evidence_bundle` (wall-clock / nonce). It does not compare `old_build.first` to `new_build.first`, and it does not rebuild the bundle between calls. `_host_bundle` uses `FIXED_NOW`, so two independent constructions would match today; a later `datetime.now()` fixture would keep this pin green. Plan-faithful.

2. **Happy-path test would accept a stubbed dict** (`tests/evals/e2e/test_des_evidence_hash_stable.py:20-21`). Asserted keys are only `hashes_equal` and `hash_length`. A hardcoded `{hashes_equal: True, hash_length: 64}` would keep the test green. Diagnostic `first`/`second` are on the row but unused. Prescribed.

3. **Dispatch does not require `realm == design`** (`evals/e2e_kernel.py:101`). Same pattern as Tasks 6–9. YAML realm is `design`. Inconsistency only.

4. **`post_hoc_protocol` cannot trip on this path.** `run_e2e_scenario` hardcodes `excerpt_blob=""` (`evals/e2e_kernel.py:119`). Plan-faithful; the theater name is not independent proof.

## Findings

### Critical

None.

### Important

None.

### Minor

1. **Intra-call equality vs cross-run digest** (`evals/e2e_kernel.py:342-349`, `tests/evals/e2e/test_des_evidence_hash_stable.py:15-21`). Track only. Plan-faithful. A later assert that both arms' `first` digests are equal (and hex-shaped) would make the "two kernel runs" wording load-bearing.

2. **No negative row that a hash mismatch is `failure_class=harness`** (`evals/e2e_kernel.py:107-110`). Classification is the existing kernel pin loop, not new Task 10 logic. Track only; do not treat the passing test as proof of the mismatch path.
