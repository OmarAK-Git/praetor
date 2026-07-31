# Skeptic-verifier result — agentic-judgment-gate (phase_exit)

## Verdict

**PASS** (claim **survives**)

## Claim restated

Phase-exit gate `agentic-judgment-gate` is complete: full pytest/ruff/mypy green, `schema_export.py --check` green, all 14 task verifier artifacts present and non-failing, PolicyGate evaluation logic under `src/praetor/policy/` untouched vs merge base, single-shot FakeProvider/VertexProvider paths intact, and `ledger_history` is the only new corroboration-eligible provenance path.

## Evidence gathered (fresh this run)

### Commands (`PYTHONPATH=…/src`)

| Command | Outcome |
|---------|---------|
| `python -m pytest -q` | **1100 passed**, 2 deselected, exit 0 (109.98s) |
| `python -m ruff check src tests evals consumer_sdk` | All checks passed, exit 0 |
| `python -m mypy src evals consumer_sdk` | Success: no issues in 141 source files, exit 0 |
| `python tools/schema_export.py --check` | exit 0 |

### Verifier artifacts 01–14

All 14 `results/verifier-result.md` files exist. Head-section scan: each records PASS/survives; no FAIL/refuted markers.

### PolicyGate evaluation logic untouched

- `git merge-base HEAD master` = `a3441a9…` = `HEAD` = `master` (code lives in working tree).
- CRLF-normalized equality vs `HEAD:` for all of `src/praetor/policy/*.py` including `gate.py`, `identity.py`, `containment_policy.py` → **IDENTICAL**.
- `git diff --ignore-cr-at-eol --numstat HEAD -- src/praetor/policy/` empty.

**Refutation attempt:** raw `git hash-object` differed from `git show master:…` — explained by CRLF vs LF; content semantics unchanged after normalize. Does not refute.

### Single-shot FakeProvider / VertexProvider intact

- `vertex_provider.py` CRLF-normalized identical to HEAD; `generate_judgment` remains prompt → single `_call_generate_content` → parse (no tool loop).
- `FakeProvider` still single-shot: default `VALID` returns one `ModelJudgment` with `session_trace_hash is None` (runtime probe).
- Only FakeProvider delta: additive `AGENTIC_EVIDENCE_GATHERING_FAILED` mode for Outcome Matrix harness — does not alter existing single-shot modes.

### ledger_history only new corroboration-eligible path

- Working-tree `provenance.py` vs HEAD: only adds `LEDGER_HISTORY` to `_NON_ATTACKER_CONTROLLABLE_PATHS` (was `{WINDOWS_SECURITY_LOG}`).
- Runtime: non-attacker set is exactly `ledger_history` + `windows_security_log`; `sysmon` / unknown / `wider_telemetry` / `similar_case` remain attacker-controllable.
- Only agentic tool emitting `provenance_path=LEDGER_HISTORY` is `LedgerHistoryTool` (`tools.py`); org-config and similar-case tools are non-evidentiary.

## Acceptance matrix

| Criterion | Verdict |
|-----------|---------|
| Full pytest green (fresh) | Met |
| Repo-wide ruff + mypy green (fresh) | Met |
| All 14 task verifier artifacts exist | Met |
| PolicyGate evaluation logic untouched | Met |
| Single-shot Fake/Vertex intact | Met |
| ledger_history only new corroboration-eligible path | Met |
| schema export --check green | Met |

## Strongest reason the claim survives

Independent re-execution of all four gate commands passed, PolicyGate sources are content-identical to baseline after CRLF normalization, and provenance inspection shows exactly one new non-attacker-controllable path (`ledger_history`) with no competing new evidence provenance emitters.
