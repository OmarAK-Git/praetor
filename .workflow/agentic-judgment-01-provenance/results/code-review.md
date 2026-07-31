# Code review — agentic-judgment-01-provenance

**Reviewer:** code-reviewer (fresh context)  
**Scope:** Task 1 — provenance trust classification for `ledger_history` (DEC-064)  
**Spec:** `docs/superpowers/plans/2026-07-30-agentic-judgment.md` Task 1; design `docs/superpowers/specs/2026-07-30-agentic-judgment-design.md` §PolicyGate / corroboration floor extension

## Verdict: **PASS**

Remediation required before verification: **No**

---

## What was reviewed

| Area | Evidence |
|------|----------|
| Diff | `git diff HEAD` — `provenance.py` (+2 lines: constant + frozenset member); new `tests/evidence/test_provenance.py` |
| PolicyGate boundary | `git diff HEAD -- src/praetor/policy/` — no content changes; `meets_account_corroboration` / `meets_host_cited_corroboration` bodies untouched |
| Tests (fresh run) | `pytest tests/evidence/test_provenance.py -v` → 3 passed; `pytest tests/evidence/test_host_corroboration.py -q` → 10 passed |
| Lint/type | `ruff check` and `mypy` on changed files — clean |
| Playbook GR/AG | No new package, no PolicyGate write-path changes, no Outcome Matrix enum, no contracts.md pin in this task |

---

## Findings

### Critical

None.

### Important

None.

### Nit

1. **`tests/evidence/test_provenance.py`** — `test_existing_classifications_unchanged` and `test_unknown_provenance_path_defaults_attacker_controllable` overlap `tests/evidence/test_host_corroboration.py` (lines 70–79). Acceptable: plan prescribes these three tests for Task 1; duplication is intentional regression guard.

2. **`src/praetor/evidence/__init__.py`** — `LEDGER_HISTORY` is not re-exported from the package `__init__`. Not required by Task 1; later plan tasks import from `praetor.evidence.provenance` directly.

3. **Integration corroboration** — No test that `sysmon_event_log` + `ledger_history` cited facts satisfy `meets_host_cited_corroboration`. Out of Task 1 acceptance criteria; host-corroboration integration is exercised in later agentic tasks per plan.

---

## Spec compliance

| Acceptance criterion | Status |
|---------------------|--------|
| `LEDGER_HISTORY` constant exists; `is_attacker_controllable_provenance(LEDGER_HISTORY)` is `False` | Met — constant `"ledger_history"` added to `_NON_ATTACKER_CONTROLLABLE_PATHS` |
| `WINDOWS_SECURITY_LOG` / `SYSMON_EVENT_LOG` classifications unchanged | Met — verified by new test and existing `test_host_corroboration.py` (10/10 pass) |
| Unknown provenance paths default attacker-controllable | Met — default branch unchanged (`return True`) |
| TDD per plan | Met — tests match plan Task 1 Step 1 verbatim; implementer documented expected `ImportError` before implementation |
| Files allowed only | Met — only `provenance.py`, `test_provenance.py`, and workflow artifacts touched |
| PolicyGate evaluation logic untouched | Met — only trust-classification table extended; corroboration helpers consume `is_attacker_controllable_provenance` unchanged |

---

## PolicyGate boundary check

The design (DEC-064) explicitly allows extending `_NON_ATTACKER_CONTROLLABLE_PATHS` while keeping `meets_host_cited_corroboration` / `meets_account_corroboration` **logic** unchanged. Implementation matches: no edits under `src/praetor/policy/`, no edits to corroboration function bodies. Future host corroboration via `ledger_history` + telemetry flows through the existing `any(not is_attacker_controllable_provenance(path) for path in paths)` check — intended strengthening, not a gate rewrite.

`meets_account_corroboration` remains sysmon+security-log only; `ledger_history` correctly does not affect account corroboration.

---

## Playbook GR/AG risks assessed

- **GR-0015** (DEC in `decisions.md`): DEC-064 full record deferred to later wiring tasks; Task 1 scope is trust table only — no blocker.
- **GR-0016** (pinned contract test vectors): `ledger_history` string exercised via `LEDGER_HISTORY` constant in test — sufficient for this table entry.
- **AG-0043 / AG-0074 / AG-0076** (PolicyGate purity, deferred directive, metrics timing): No gate/orchestrator changes — not triggered.
- **AG-0001** (scope guard): No new package — not triggered.
- **AG-0068** (Outcome Matrix enum): Not in Task 1 scope — not triggered.

---

## Summary

Minimal, correct implementation of Task 1. Trust table extended as specified; tests and static checks pass; PolicyGate evaluation boundary preserved. Proceed to skeptic verification.
