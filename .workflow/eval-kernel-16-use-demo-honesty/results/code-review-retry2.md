# Code review (retry 2) — eval-kernel-16-use-demo-honesty (Task 16)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Scoped re-review after `60cc56d`. Prior remaining blocker only: `docs/*.md` file roots were not scanned. Confirm `_DemoHonestyDocsRoot` (or equivalent) now scans `docs/` except `docs/superpowers/` only. SoT files still restored. Theater regex still literal.
**Diff reviewed:** commit `60cc56d` vs `db5d196` (`evals/e2e_kernel.py` + `.workflow/.../implementer-result-retry2.md`). HEAD is `60cc56d`. YAML, test, `evals/theater.py`, and both SoT files are untouched by this commit.

**Spec / plan used:**
- `.workflow/eval-kernel-16-use-demo-honesty/packets/implementer-retry.md`
- `.workflow/eval-kernel-16-use-demo-honesty/packets/code-reviewer.md`
- `.workflow/eval-kernel-16-use-demo-honesty/plan.md` acceptance
- Prior reviews `.workflow/eval-kernel-16-use-demo-honesty/results/code-review.md` and `code-review-retry.md`

## Retry-2 confirmation

| Required | Result |
|---|---|
| `_DemoHonestyDocsRoot` (or equivalent) scans `docs/` except `docs/superpowers/` only | **Pass.** Wrapper keeps `docs` as a directory root and filters `rglob` with `self._exclude in path.parents` where exclude is `docs/superpowers` (`evals/e2e_kernel.py:456-480`). Probe: all 9 root `docs/*.md` are yielded and suffix-scanned; 15 files under `docs/superpowers/` yielded 0; 20 non-superpowers files yielded exactly those 20 (0 missing, 0 extra). `notebooks`, `demo`, `evals/e2e_scenarios` still pass through as plain `Path`. |
| SoT spec/plan still restored to pre-`7583b10` wording | **Pass.** `git diff 7583b10^ HEAD` on both files is empty. Blobs still match: plan `a2c6110c569129d8055c723f32c677812b08e53f`, spec `6e53b8a460409ed55b8a264a76f5020f8ac8d9b5`. Restored needles remain in SoT (`2026-09-07-eval-kernel-sprint1.md:16,1027,1079-1080,2834`; spec `:22,:53,:205,:332`). `60cc56d` does not touch `docs/`. |
| Theater regex still literal | **Pass.** `evals/theater.py:14-17` is still `r"judgment works\|trustworthy judgment\|production-ready judgment"`. `git diff 7583b10^ HEAD -- evals/theater.py` is empty. No split/`+` hide in kernel. |
| Prior file-as-root hole closed | **Pass.** Child `iterdir()` expansion is gone. `Path("docs/README.md").rglob("*")` is still `[]` (the old failure mode); the wrapper no longer uses file children as roots. |

Live detector probe (read-only, no planted copy):

- Wrapped roots (`_demo_honesty_copy_roots`): `unearned_demo_claim` **does not trip**.
- Raw `Path("docs")` (no exclude): **trips** on `docs\superpowers\plans\2026-09-07-eval-kernel-sprint1.md`.
- Same raw roots with `cite_to_subject_primary_earned=True`: clean.

That shows the exclude is load-bearing, SoT still contains the needles, and a stump-only/earned flag is still not treated as a claim.

## Checks

| Check | Result |
|---|---|
| Unearned demo claims trip `unearned_demo_claim` | Detector unchanged (`evals/theater.py:67-80`). YAML still calls it (`use.demo_honesty_gate.yaml:24`). Walk now includes root `docs/*.md` and other non-superpowers docs. Current corpus needles live only under `docs/superpowers/**` (plus detector/test/workflow text, none of which are dishonest product copy). A later “judgment works” in `docs/prd.md` or `docs/README.md` would now be read. |
| Stump-only win is not a claim | Unchanged. Detector returns clean when `cite_to_subject_primary_earned` is true (`evals/theater.py:68-69`). YAML keeps the flag `false`. Probe above confirms earned=true stays clean even when SoT needles are in the walk. |
| Both arms pass when copy is honest | Happy-path test still asserts both arms, `status=pass`, `unearned_claim_found is False` (`test_use_demo_honesty_gate.py:15-20`). Green with the corrected walk. |
| Writes only retry-allowed files | **Pass.** `60cc56d` touches `evals/e2e_kernel.py` and `.workflow/eval-kernel-16-use-demo-honesty/results/implementer-result-retry2.md` only. |
| Extra product scope | Authorized walk filter only. No Sprint 1 gate. No SoT rewrite. No theater.py edit. |
| Verification (this review) | `pytest tests/evals/e2e/test_use_demo_honesty_gate.py tests/evals/test_theater.py -q` → 15 passed in 4.04s; `ruff check` clean; `mypy evals/e2e_kernel.py` clean. Walk probe as above. |

## Findings

### Critical

None. Prior Criticals (SoT rewrite, regex concatenation) stay cleared.

### Important

None. Prior Important #1 (file children of `docs/` were rglob roots, so nine root markdown files were never read) is fixed in `evals/e2e_kernel.py:456-480`.

### Minor

1. **Happy-path pin test would still accept a stub** (`tests/evals/e2e/test_use_demo_honesty_gate.py:18-20`). No committed assertion that a planted `docs/*.md` needle trips, or that `docs/superpowers/**` is skipped while root docs are scanned. Prescribed Step 1; track only. This review’s walk probe is not a regression test.

2. Carry-forward (not retry-2 regressions): outer `unearned_demo_claim` still uses `copy_roots=()` (`e2e_kernel.py:140`); relative roots are CWD-dependent; `.yaml` under `evals/e2e_scenarios` is not scanned (`evals/theater.py:72-73`).

## Verdict rationale

`60cc56d` replaces the broken child-expansion walk with `_DemoHonestyDocsRoot`, which rglobs `docs/` as a directory and skips only paths whose parents include `docs/superpowers`. Probe shows every current `docs/*.md` and every other non-superpowers docs file is visited; superpowers files are not. SoT blobs remain byte-identical to `7583b10^`. `_UNEARNED_CLAIM` remains the literal regex. The previous retry’s exclude-**only**-superpowers requirement is now met. **approve**.
