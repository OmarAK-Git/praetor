# Review — V2-005

## Gaps / follow-ons

- **V2-006:** Sole `escalate` match still falls through to `ALLOW` at policy layer; catch-all escalate in example config is validated and matched but not yet blocking.
- **V2-012:** `default_action` replaces catch-all rule scope as the canonical catch-all primitive per DEC-058.
- **V2-013:** Implicit ALLOW fallthrough removal and example/eval explicit permit rewrite.
- **docs/contracts.md** §3a scope shape mirror deferred (task hard limit: no `docs/` edits).

## Scope note

- `codification/sweep.py` template updated to `{ catch_all: true }` so activation-ready sweep artifacts pass the new preflight (required by `test_placeholders_replaced_artifact_passes_preflight`).

## Risk

- Low: schema tightening only; policy authorization semantics unchanged until V2-006/V2-013.
