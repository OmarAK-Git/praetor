# Implementer result — capability-spike-01-corpus

- **model:** composer-2.5

## Files changed

| File | Rationale |
|------|-----------|
| `evals/capability/__init__.py` | New package init for capability spike evals |
| `evals/capability/corpus.py` | Anchor manifest schema, validation, and YAML loader |
| `tests/evals/capability/__init__.py` | Test package init |
| `tests/evals/capability/test_corpus.py` | Six offline tests for manifest loading and validation |
| `tests/evals/capability/fixtures/manifest_valid.yaml` | Balanced 4-anchor fixture (2 malicious, 2 benign) |

## Commands run

| Command | Exit code |
|---------|-----------|
| `python -m pytest tests/evals/capability/test_corpus.py -v` (pre-impl, expected fail) | 2 |
| `pytest tests/evals/capability/test_corpus.py -q` | 0 (6 passed) |
| `ruff check evals/capability tests/evals/capability` | 0 |
| `mypy evals/capability` | 0 |

## Commit

- **hash:** `1891684`
- **message:** Add labeled anchor manifest loader for capability spike.

## Blockers

None.
