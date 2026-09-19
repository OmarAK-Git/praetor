# Verifier result — eval-kernel-16-use-demo-honesty (Task 16)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

Claim restated: Task 16 is done — `use.demo_honesty_gate` pins that demo/walkthrough/kernel copy does not claim unearned judgment; both `old_build` and `new_build` pass; unearned capability claims trip theater detector `unearned_demo_claim`; a stump-only win is not treated as a claim; SoT spec/plan still contain the literal “judgment works” / “trustworthy judgment” wording (not rewritten to dodge the scanner).

Implementer results (`1 passed`, ruff/mypy green, SoT revert + walk-wrapper claims) were treated as unevidenced until re-run.

Skeptic verdict on the completion claim: **survives**.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| Both arms pass when demo copy does not claim unearned judgment | **met** | YAML pins both arms `unearned_claim_found: false`, `provider: fake` (`evals/e2e_scenarios/use.demo_honesty_gate.yaml:14-21`). Fresh `test_use_demo_honesty_gate.py` → 1 passed, 0 skipped. Independent `run_e2e_kernel` dump: 2 rows; both `status=pass`, `failure_class=none`, `provider=fake`, `realm=usability`; observed `unearned_claim_found=False`, `cite_to_subject_primary_earned=False`. Live `_run_use_demo_honesty` on the loaded YAML returns the same booleans (not a hardcoded stub in this session’s call). |
| Unearned capability claims trip theater_detector `unearned_demo_claim` | **met** | Detector unchanged (`evals/theater.py:14-17,67-80`). YAML names `theater_detector: unearned_demo_claim` (`use.demo_honesty_gate.yaml:24`). Executor calls `run_theater_detector("unearned_demo_claim", ...)` (`evals/e2e_kernel.py:487-500`). Planted `claim.md` with “Praetor judgment works and is production-ready.” + `earned=False` → detector `tripped=True`; executor `unearned_claim_found=True`; `run_e2e_scenario` → `fail` / `harness`. Raw `Path("docs")` (no superpowers exclude) trips on `docs\superpowers\plans\2026-09-07-eval-kernel-sprint1.md`. Wrapped roots stay clean on the current corpus. Fake wrap: SoT needle under `docs/superpowers/` does not trip; same needle in `docs/prd.md` does. |
| A stump-only win is not treated as a claim | **met** | Detector short-circuits clean only when `cite_to_subject_primary_earned` is true (`evals/theater.py:68-69`). YAML/executor keep the flag `false` and never derive it from stump results (`use.demo_honesty_gate.yaml:12`; `e2e_kernel.py:486,499-504`). Copy that only says “A stump-only win is not a claim. Judgment beat path_a_fact_count stump.” does **not** trip (`unearned_claim_found=False`; row `pass` / `none`). Planted real claim + `earned=True` also stays clean — stump/cite-earned is not itself a claim. No `stump_pair` / quality-win path in this executor. |
| SoT spec/plan still contain “judgment works” / “trustworthy judgment” (not rewritten) | **met** | `git diff 7583b10^ HEAD` on both SoT files is empty. Blobs match: plan `a2c6110c569129d8055c723f32c677812b08e53f`, spec `6e53b8a460409ed55b8a264a76f5020f8ac8d9b5`. Live needles: plan `:16` “Do not claim trustworthy judgment”; Task 4 fixture “Praetor judgment works…” (`:1027`); literal `_UNEARNED_CLAIM` (`:1080`); YAML description “claim judgment works” (`:2834`). Spec `:22,:53` “trustworthy judgment”; `:205,:332` “judgment works” plus “A stump-only win is not a claim.” `evals/theater.py` regex is still the literal `r"judgment works\|trustworthy judgment\|production-ready judgment"`; `git diff 7583b10^ HEAD -- evals/theater.py` is empty. Raw-docs trip above is independent proof the needles remain on disk. |
| Verifier checks only Task 16 acceptance, not Sprint 1 gate completion | **met** | Commands limited to the packet set. No Sprint 1 / phase-exit suite run. Queue item still `in_progress`. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest tests/evals/e2e/test_use_demo_honesty_gate.py -q` | **0** | `.` — 1 passed in 3.77s (no skips) |
| `ruff check evals/e2e_kernel.py tests/evals/e2e/test_use_demo_honesty_gate.py` | **0** | All checks passed |
| `mypy evals/e2e_kernel.py` | **0** | Success: no issues found in 1 source file |

Re-run in this session against `C:\Users\oalan\Praetor` working tree. Implementer transcript was not treated as evidence.

Pytest duration (~3.8s) is consistent with real kernel load (prior YAMLs + missing-ID error rows; the test filters to this ID).

HEAD is `60cc56dcb98cfc74bc77ba2c5f9989e834b2d40b` (`fix(evals): scan docs root files in demo honesty walk`). Product paths for this task (`evals/e2e_kernel.py`, `evals/e2e_scenarios/use.demo_honesty_gate.yaml`, `tests/evals/e2e/test_use_demo_honesty_gate.py`, both SoT files, `evals/theater.py`) have empty `git status --short` and match HEAD. `7583b10` SoT rewrite was reverted in `db5d196`; current SoT blobs equal `7583b10^`.

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| Dispatch wired | **met** | `run_e2e_scenario` calls `_run_use_demo_honesty` for `use.demo_honesty_gate` (`evals/e2e_kernel.py:115-116`). ID is in `REQUIRED_E2E_SCENARIO_IDS` (`:61`). |
| YAML / test / executor match Task 16 snippet | **met** | YAML matches plan Step 3. Test matches Step 1. Executor matches Step 3 except authorized `_demo_honesty_copy_roots` wrap of `docs` (`e2e_kernel.py:456-480,498`). Scorecard pin is `unearned_claim_found`. |
| Walk excludes only `docs/superpowers/` | **met** | `_DemoHonestyDocsRoot.rglob` skips `self._exclude in path.parents` (`e2e_kernel.py:465-469`). Probe: 9 root `docs/*.md` yielded; 0 of 15 superpowers suffix files yielded; 19 non-superpowers docs suffix files yielded with 0 missing / 0 extra. `notebooks`, `demo`, `evals/e2e_scenarios` still exist and pass through as plain `Path`. |
| Writes only retry-allowed files | **met** | `60cc56d` touches `evals/e2e_kernel.py` + workflow retry-2 result. `db5d196` reverts the two SoT files (retry-allowed) and edits the kernel. YAML/test untouched after `7583b10`. `evals/theater.py` never edited. |

## Independent probes (not in packet)

- Loader: exactly one `use.demo_honesty_gate`; realm `usability`; theater `unearned_demo_claim`; both arms `provider: fake`; pin `unearned_claim_found`; setup `copy_roots=[docs,notebooks,demo,evals/e2e_scenarios]`, `cite_to_subject_primary_earned=False`.
- Fresh `run_e2e_kernel` dump: 2 rows; both `pass` / `none` / `fake` / `usability`; notes empty (outer theater did not trip).
- Corpus grep of `_UNEARNED_CLAIM` needles in `docs/**/*.md`, `notebooks`, `demo`: hits only under `docs/superpowers/**` (plus the scenario YAML description, which the suffix filter does not scan).
- Wrapped roots + unearned: detector clean.
- Raw `docs/` + unearned: trips on restored SoT plan.
- Raw `docs/` + earned: clean.
- Temp `claim.md` (“judgment works”) + unearned: trips; executor `unearned_claim_found=True`; scorecard `fail` / `harness`.
- Temp stump-only copy (no banned phrases) + unearned: clean; executor `False`; scorecard `pass` / `none`.
- Temp claim + earned: clean — earned primary is not treated as a claim.
- Fake `docs/` tree: superpowers SoT needle skipped; root `prd.md` needle trips.

## Gaps

None that fail Task 16 acceptance.

Residual (non-blocking, not Task 16 AC failures):

- Happy-path pin test would accept a stubbed `{unearned_claim_found: False, cite_to_subject_primary_earned: False}` dict (`tests/evals/e2e/test_use_demo_honesty_gate.py:18-20`). Prescribed Step 1. This session planted a claim through the live executor and flipped the pin, so do not treat the committed booleans as independent proof by themselves.
- Inner trip becomes `failure_class=harness` (pin mismatch), not `theater_detector`. Outer `unearned_demo_claim` still uses `copy_roots=()` (`e2e_kernel.py:140`), so it cannot trip. Plan executor snippet + pin loop are the same. Spec/interfaces wording says trip → `theater_detector`; AC requires the named detector to fire, which it does on the inner call. Track only.
- Relative `copy_roots` are CWD-dependent (`e2e_kernel.py:475`; YAML `:7-11`). Plan-faithful.
- `evals/e2e_scenarios` is a copy root but `.yaml` is not scanned (`evals/theater.py:72-73`). The pin’s own description still contains `judgment works`. Pre-existing Task 4 suffix filter.
- No committed assertion that a planted `docs/*.md` needle trips, or that `docs/superpowers/**` is skipped while root docs are scanned. This session’s walk/trip probes are not part of the committed test.
- Both arms run the same executor with no arm parameter. Prescribed.
- Queue item `eval-kernel-16-use-demo-honesty` remains `in_progress` (implementer packet: do not mark done).
