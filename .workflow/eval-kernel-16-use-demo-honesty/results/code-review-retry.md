# Code review (retry) — eval-kernel-16-use-demo-honesty (Task 16)

**Verdict:** request_changes

**Reviewer:** code-reviewer (fresh context)
**Scope:** Retry after `7583b10` blocking findings. Task 16 only. Sprint 1 gate ignored.
**Diff reviewed:** commit `db5d196` vs `7583b10` (`evals/e2e_kernel.py`, revert of the two `docs/superpowers/**` SoT files, `.workflow/.../implementer-result-retry.md`). HEAD is `db5d196`. YAML and test are unchanged from `7583b10`.

**Spec / plan used:**
- `.workflow/eval-kernel-16-use-demo-honesty/packets/implementer-retry.md`
- `.workflow/eval-kernel-16-use-demo-honesty/packets/code-reviewer.md`
- `.workflow/eval-kernel-16-use-demo-honesty/plan.md` acceptance
- Prior review `.workflow/eval-kernel-16-use-demo-honesty/results/code-review.md`

## Retry confirmation

| Required | Result |
|---|---|
| SoT spec/plan restored to pre-`7583b10` wording | **Pass.** `git diff 7583b10^ HEAD` on both files is empty. Blobs match: plan `a2c6110c5691…`, spec `6e53b8a46040…`. Restored: “Do not claim trustworthy judgment” (`2026-09-07-eval-kernel-sprint1.md:16`), Task 4 trip fixture `Praetor judgment works and is production-ready.` (`:1027`), literal `_UNEARNED_CLAIM` (`:1079-1080`), YAML description `claim judgment works` (`:2834`), spec §5/§8 “judgment works” / “trustworthy judgment”. |
| Theater regex not hidden via concatenation | **Pass.** `evals/theater.py:14-17` is the literal `r"judgment works\|trustworthy judgment\|production-ready judgment"`; `git diff 7583b10^ HEAD -- evals/theater.py` is empty. Plan snippet matches. No split/`+` hide in kernel. |
| Pin still works | **Pass on current corpus.** `pytest tests/evals/e2e/test_use_demo_honesty_gate.py tests/evals/test_theater.py -q` → 15 passed. Needles in-repo live only under `docs/superpowers/**` (plus detector/test/workflow text). `evals/theater.py` itself is not a `copy_root`. |
| `docs/superpowers` excluded from walk **only** | **Fail.** Helper skips `superpowers` but also drops every **file** child of `docs/` because theater walks `root.rglob("*")` and never reads a file root. See Important #1. |

## Checks

| Check | Result |
|---|---|
| Unearned demo claims trip `unearned_demo_claim` | Detector unchanged (`evals/theater.py:67-80`). YAML still calls it (`use.demo_honesty_gate.yaml:24`). SoT no longer mutated to dodge. Remaining hole: root-level `docs/*.md` is not walked, so a claim there would not trip. |
| Stump-only win is not a claim | Unchanged. Detector returns clean when `cite_to_subject_primary_earned` is true (`evals/theater.py:68-69`). YAML keeps the flag `false`. |
| Both arms pass when copy is honest | Happy-path test still asserts both arms, `status=pass`, `unearned_claim_found is False` (`test_use_demo_honesty_gate.py:15-20`). Green for current non-superpowers copy; not a proof that all “other docs” were scanned. |
| Writes only retry-allowed files | **Pass.** `db5d196` touches `evals/e2e_kernel.py`, the two SoT files (revert only), and `.workflow/eval-kernel-16-use-demo-honesty/results/implementer-result-retry.md`. YAML/test untouched. |
| Extra product scope | `_demo_honesty_copy_roots` is the authorized walk filter. Shape is wrong (file children). No Sprint 1 gate. |
| Verification (this review) | `pytest` 15 passed in 3.73s; `ruff check` clean; `mypy evals/e2e_kernel.py` clean. Probe: `Path("docs/README.md").rglob("*")` → `[]`. |

Prior Criticals on SoT rewrite and regex concatenation are cleared. **request_changes** because the retry’s “exclude only `docs/superpowers/`; still scan other docs” is not met for `docs/*.md`.

## Findings

### Critical

None. The two prior Criticals are fixed.

### Important

1. **Walk excludes more than `docs/superpowers/`** (`evals/e2e_kernel.py:456-467` + `evals/theater.py:70-71`).

   `_demo_honesty_copy_roots` replaces `docs` with every `iterdir()` child except `name == "superpowers"`. Directory children (`archive/`, `proposals/`, `images/`) still work. File children become copy roots. `_unearned_demo_claim` only does `root.rglob("*")`, which on a file yields nothing (probed: `docs/README.md` → 0 paths). Those files are never `read_text`’d.

   Unscanned product copy at `docs/` root:

   - `docs/README.md`
   - `docs/architecture.md`
   - `docs/contracts.md`
   - `docs/decisions.md`
   - `docs/eval_gates.md`
   - `docs/operator_runbook.md`
   - `docs/plan.md`
   - `docs/prd.md`
   - `docs/spec.md`

   Retry packet: “exclude only `docs/superpowers/` from the walk … (still scan other docs, notebooks, demo, and evals/e2e_scenarios).” Notebooks/demo/`evals/e2e_scenarios` still pass through. Other **docs** at repo-docs root do not.

   Current needle grep is clean outside `docs/superpowers/**`, so the pin is green for today’s corpus. That does not make the walk shape honest. A later “judgment works” in `docs/prd.md` or `docs/README.md` would stay green.

   **Fix (in `e2e_kernel.py` only):** do not add file children as rglob roots. Exclude only the `superpowers` directory from a **directory** walk of `docs/`, and still visit root-level `.md`/`.html`/`.py`/`.txt`. Two in-scope shapes:

   - Wrap `Path("docs")` so `rglob` yields every descendant except those with `superpowers` in `parts` (root files included).
   - Append only non-`superpowers` **directory** children, then scan `docs` file children with the same suffix set before returning (or pass them through a directory root `rglob` can see).

   Do not “fix” this by editing `evals/theater.py` or by rewriting SoT again.

### Minor

1. **Happy-path pin test would still accept a stub** (`tests/evals/e2e/test_use_demo_honesty_gate.py:18-20`). No committed trip that `unearned_claim_found` becomes true on planted copy, and nothing asserts root `docs/*.md` is walked. Prescribed Step 1; track unless a walk-shape test is added with the Important fix.

2. Carry-forward (not retry regressions): outer `unearned_demo_claim` still uses `copy_roots=()` (`e2e_kernel.py:140`); relative roots are CWD-dependent; `.yaml` under `evals/e2e_scenarios` is not scanned (`evals/theater.py:72-73`).

## Verdict rationale

`db5d196` restores both SoT files byte-identical to `7583b10^`, leaves `_UNEARNED_CLAIM` literal, and keeps the kernel pin. That clears the previous theater/SoT dodge and the `files_allowed` violation. The authorized superpowers walk skip is implemented incorrectly: exploding `docs/` into children silently drops nine root markdown files from `rglob`. Retry required exclude-**only**-superpowers. **request_changes** until the walk scans other docs, including `docs/*.md`.
