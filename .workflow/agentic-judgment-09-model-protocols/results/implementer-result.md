# Implementer result — agentic-judgment-09-model-protocols

## Files changed

| File | Rationale |
|------|-----------|
| `src/praetor/judgment/agentic/model.py` | Added frozen dataclasses (`ToolCallDecision`, `InvestigationSummary`, `HypothesisCase`) and `@runtime_checkable` Protocols (`SourceInvestigatorModel`, `HypothesisModel`, `LeadModel`) per plan Task 9. |
| `tests/judgment/agentic/test_model.py` | Structural TDD tests for dataclass fields and immutability (written first, then implementation). |

## TDD sequence

1. Wrote `test_model.py` — `pytest` failed with `ModuleNotFoundError: No module named 'praetor.judgment.agentic.model'`.
2. Implemented `model.py` per plan spec.
3. Fixed one `ruff E501` line-length violation in `HypothesisModel.build_case` signature (wrapped parameters).

## Verification commands and outcomes

All run with `PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`.

| Command | Outcome |
|---------|---------|
| `pytest tests/judgment/agentic/test_model.py -v` | **PASS** — 3 passed in 0.26s |
| `ruff check src/praetor/judgment/agentic/model.py tests/judgment/agentic/test_model.py` | **PASS** — All checks passed |
| `mypy src/praetor/judgment/agentic/model.py` | **PASS** — Success: no issues found in 1 source file |

## Gaps / notes

- No real LLM wire integration (out of scope; deferred to follow-on work).
- Protocol structural conformance (`isinstance` against fakes) is covered in Task 10 (`fake_model.py`).
- No commit performed (per standing orders).
