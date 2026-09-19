# Implementer result (retry 2) — eval-kernel-16-use-demo-honesty

## Changes

| File | Rationale |
|------|-----------|
| `evals/e2e_kernel.py` | `_DemoHonestyDocsRoot` wraps `docs/` so `rglob` skips `docs/superpowers/` while still scanning root-level files and other subdirs |

## Approach

Blocking review: decomposing `docs/` into file children made them rglob roots, so `README.md`, `eval_gates.md`, etc. were never scanned. Replaced child expansion with a directory walk wrapper that keeps YAML copy roots unchanged (`docs`, `notebooks`, `demo`, `evals/e2e_scenarios`) and excludes only the `superpowers` subtree via `exclude in path.parents`. SoT and theater regex untouched.

## Verification

```
pytest tests/evals/e2e/test_use_demo_honesty_gate.py tests/evals/test_theater.py -q
...............                                                          [100%]
15 passed in 3.95s

ruff check evals/e2e_kernel.py
All checks passed!

mypy evals/e2e_kernel.py
Success: no issues found in 1 source file
```

## Unresolved

None.
