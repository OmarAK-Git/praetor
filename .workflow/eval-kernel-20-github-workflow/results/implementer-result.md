# Implementer result — eval-kernel-20-github-workflow

## Summary

Added GitHub Actions `eval-kernel` workflow as the Sprint 1 FakeProvider merge gate: pytest eval guards plus `python -m evals.harness --all`. No Vertex secret, no probe/spike env vars, no notebook-only gate.

## Files changed

| File | Rationale |
|---|---|
| `.github/workflows/eval-kernel.yml` | CI job: `pip install -e ".[dev]"`, `pytest tests/evals/ -q`, `python -m evals.harness --all` on ubuntu-latest / Python 3.12 |
| `tests/evals/test_e2e_kernel.py` | Added `test_harness_all_exits_zero_after_full_suite` subprocess test for `--all` |
| `tests/evals/test_eval_kernel_workflow.py` | Guards workflow is pytest + harness, not notebook-only; no probe/spike env |
| `memory-bank/activeContext.md` | Task 20 complete; Task 21 next |

## Verification

```
pytest tests/evals/test_e2e_kernel.py::test_harness_all_exits_zero_after_full_suite tests/evals/test_eval_kernel_workflow.py -q
..                                                                       [100%]
2 passed in 12.85s
```

```
python -m evals.harness --all
exit 0 — 34 OM PASS lines + 30 kernel scorecard lines; cap.baseline_bag_path_a / cap.stump_parity_guard new_build [PENDING]
```

```
ruff check tests/evals/test_eval_kernel_workflow.py tests/evals/test_e2e_kernel.py
All checks passed!
```

## Unresolved

None. Queue not marked done per packet.
