# Verifier result — capability-spike-01-corpus

- **model:** cursor-grok-4.5-high
- **verdict:** PASS
- **commit checked:** `18916847b97160e2b78fdae08e9ea8d1b4c91fe4` (HEAD)

## Acceptance criteria

| Criterion | Result | Evidence |
|-----------|--------|----------|
| `load_anchor_manifest` loads valid YAML into frozen `Anchor`/`AnchorManifest` | PASS | `test_load_valid_manifest` loads `fixtures/manifest_valid.yaml` → `AnchorManifest` with 4 anchors. Code: `@dataclass(frozen=True)` on both types (`evals/capability/corpus.py:26-37`). Independent probe: mutation raises `FrozenInstanceError`; `malicious`/`benign` balance 2/2. |
| Naive timestamps coerced to UTC; duplicate ids, unbalanced classes, invalid `expected_class`, empty rationale → `ManifestError` | PASS | Coercion at `corpus.py:60-61`. Tests: `test_duplicate_anchor_ids_rejected`, `test_unbalanced_classes_rejected`, `test_unknown_expected_class_rejected`, `test_missing_rationale_rejected` all raise `ManifestError`. Independent probe: naive str/datetime → `tzinfo=UTC`. |
| Committed tests pass offline with FakeProvider-free fixtures | PASS | 6 passed, no `FakeProvider`/network/provider imports in package or tests. Fixture is static YAML only. |

## Verification commands (re-run by verifier)

```
pytest tests/evals/capability/test_corpus.py -q
......                                                                   [100%]
6 passed in 0.07s
EXIT:0

ruff check evals/capability tests/evals/capability
All checks passed!
EXIT:0

mypy evals/capability
Success: no issues found in 2 source files
EXIT:0
```

## Hard constraints

| Check | Result | Evidence |
|-------|--------|----------|
| No `src/praetor/` edits in commit | PASS | `git diff-tree --name-only -r 1891684` → only `evals/capability/*` and `tests/evals/capability/*` (5 files, all `A`). |
| No harness/scenario edits | PASS | Commit file list has no `evals/harness.py` or `evals/scenarios/`. |
| No `praetor.judgment.agentic` imports | PASS | Grep on `evals/capability`: no matches. Imports are stdlib + `yaml` only. |
| Nothing in `evals/capability` imported by `evals/harness.py` | PASS | Grep on `evals/harness.py` for capability imports: no matches. Broader `evals/` import grep: no capability consumers. |

## Gaps (non-blocking)

- `test_naive_timestamps_are_coerced_to_utc` loads the Z-suffixed fixture; on this PyYAML, those parse as already-aware UTC, so the test only asserts `tzinfo is not None` and does not exercise the naive branch. Behavior still present and independently confirmed via `_coerce_time` on naive str/datetime. Matches the plan-prescribed test as written.

## Scope note

Phase/sprint-level gaps ignored per packet (`verification.scope` is task).
