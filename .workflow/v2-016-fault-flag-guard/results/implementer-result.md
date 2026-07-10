# Implementer Result — V2-016 Static Policy Fault-Flag Guard

## Files Changed

- `src/praetor/contracts/fault_flags.py` — canonical SFE map, edict fault-flag validation, policy/engine literal scanner
- `src/praetor/engine/edict.py` — `validate_decision_edict_fault_flags` at start of `build_decision_edict`
- `evals/outcome_matrix.py` — import SFE map from contracts (single source)
- `tests/contracts/test_fault_flag_guard.py` — static literal subset guard
- `tests/policy/test_edict_fault_flags.py` — unknown flag + SFE polarity rejection tests

## Verification

```
pytest tests/contracts/ tests/policy/ tests/evals/ -q
208 passed, 1 deselected in 22.13s
```

## Approval Gates

None hit.
