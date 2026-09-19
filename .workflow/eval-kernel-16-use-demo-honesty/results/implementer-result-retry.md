# Implementer result (retry) — eval-kernel-16-use-demo-honesty

## Changes

| File | Rationale |
|------|-----------|
| `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` | Reverted to pre-7583b10 SoT wording (restored trip fixture and literal regex) |
| `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` | Reverted to pre-7583b10 SoT wording |
| `evals/e2e_kernel.py` | Added `_demo_honesty_copy_roots` to expand `docs` while excluding `docs/superpowers/` from the scan |

## Approach

Blocking review: 7583b10 rewrote SoT to dodge `_UNEARNED_CLAIM`. Reverted both spec/plan files via `git checkout 7583b10^`. Instead of mutating scanned copy, `_run_use_demo_honesty` now walks `docs/` children except `superpowers/`, plus notebooks, demo, and evals/e2e_scenarios unchanged. Theater regex untouched.

## Verification

```
pytest tests/evals/e2e/test_use_demo_honesty_gate.py tests/evals/test_theater.py -q
...............                                                          [100%]
15 passed in 3.91s

ruff check evals/e2e_kernel.py tests/evals/e2e/test_use_demo_honesty_gate.py
All checks passed!

mypy evals/e2e_kernel.py
Success: no issues found in 1 source file
```

## Unresolved

None.
