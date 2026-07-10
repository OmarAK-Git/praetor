# Implementer Packet — V2-034 Similar-Case Retrieval

**implementation_model:** composer-2.5-fast

## Objective

Implement similar-case retrieval selecting human-confirmed precedent cases per ranking contract; wire into judgment prompt via exemplar block; prove via tests/eval that citation validity and raw-source exclusion unchanged.

## Allowed files

- `src/praetor/retrieval/`
- `src/praetor/judgment/prompt.py`
- `src/praetor/annotations/`
- `tests/judgment/`, `tests/annotations/`
- `docs/eval_gates.md`, `evals/`, `specs/`, `memory-bank/`

## Do-not-touch

- Do not mark queue done. No gate verification.
- Exemplars must not affect evidence hash.

## Verification

```bash
pytest tests/judgment/ tests/annotations/ -q
```

Write `.workflow/v2-034-similar-case-retrieval/results/implementer-result.md`.
