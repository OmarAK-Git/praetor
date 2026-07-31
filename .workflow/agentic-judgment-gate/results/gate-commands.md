# agentic-judgment-gate — command results (skeptic re-run)

**Worktree:** `C:\Users\oalan\Praetor\.worktrees\agentic-judgment`  
**PYTHONPATH:** `C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`  
**Verified by:** skeptic-verifier (gate)  
**Run date:** 2026-07-30

Prior `gate-commands.md` treated as unevidenced; commands re-executed below.

---

## Gate commands (fresh)

| # | Command | Exit code | Result |
|---|---------|-----------|--------|
| 1 | `python -m pytest -q` | 0 | **PASS** — 1100 passed, 2 deselected, 0 failed (109.98s) |
| 2 | `python -m ruff check src tests evals consumer_sdk` | 0 | **PASS** — All checks passed |
| 3 | `python -m mypy src evals consumer_sdk` | 0 | **PASS** — Success: no issues found in 141 source files |
| 4 | `python tools/schema_export.py --check` | 0 | **PASS** (exit 0) |

---

## Verifier artifacts (01–14)

All 14 paths exist under `.workflow/agentic-judgment-0{1-9}*/results/verifier-result.md` and `10`–`14`. Each head section records PASS/survives; no FAIL/refuted markers in first 35 lines.

---

## PolicyGate evaluation logic

Baseline: `HEAD` / `master` = `a3441a99f4f1c42fc4ac5311aebb3858f86e6e53` (merge-base == HEAD; implementation is working-tree).

Python CRLF-normalized byte-equality vs `HEAD:` for every file under `src/praetor/policy/`:

- `gate.py`, `identity.py`, `containment_policy.py`, `directive_builder.py`, `circuit_breaker.py`, `rate_limit.py`, `state.py`, `__init__.py` → **IDENTICAL**
- `git diff --ignore-cr-at-eol --numstat HEAD -- src/praetor/policy/` → empty

Working-tree CRLF dirt only; evaluation semantics untouched.

---

## Single-shot FakeProvider / VertexProvider

| Check | Result |
|-------|--------|
| `vertex_provider.py` CRLF-normalized vs HEAD | **IDENTICAL** |
| `FakeProvider.generate_judgment` default path | still single call → `ModelJudgment`; probe `session_trace_hash is None`, `calls==1` |
| FakeProvider WT delta | additive only: `AGENTIC_EVIDENCE_GATHERING_FAILED` mode (+ import / branch); existing modes unchanged |
| `VertexProvider.generate_judgment` | no tool/multi-turn loop (inspect source) |

---

## ledger_history corroboration path

| Check | Result |
|-------|--------|
| `_NON_ATTACKER_CONTROLLABLE_PATHS` | `{windows_security_log, ledger_history}` only |
| New constant | `LEDGER_HISTORY = "ledger_history"` (only addition vs HEAD provenance) |
| Tool emission | only `LedgerHistoryTool` sets `provenance_path=LEDGER_HISTORY` |
| Org config / similar cases | explicitly non-evidentiary / not corroboration-eligible |
| Unknown paths (`org_config`, `wider_telemetry`, `similar_case`) | still attacker-controllable (`True`) |

---

## Gate summary

| Check | Status |
|-------|--------|
| pytest | PASS (fresh) |
| ruff | PASS (fresh) |
| mypy | PASS (fresh) |
| schema_export --check | PASS (fresh) |
| Verifier artifacts 01–14 | PASS (14/14 present, all PASS/survives) |
| PolicyGate evaluation logic untouched | PASS (content-identical after CRLF normalize) |
| Single-shot Fake/Vertex intact | PASS |
| ledger_history only new corroboration-eligible path | PASS |

**Overall gate:** PASS
