# Temporary corroboration floor (DEC-065)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Temporarily relax host/account corroboration to “≥1 anchoring cited fact (any provenance)” so single-shot judgment is not blocked by a two-path floor while only Sysmon+Security exist; supersede DEC-064’s `ledger_history` corroboration eligibility; keep sole-`ambiguity_flag` reject; document upgrade-to-≥2 when real multi-source telemetry lands.

**Why:** Host/ledger history is Praetor SoT, not an independent event source — counting it as a second provenance path undermines the rule. Agentic judgment helps gathering quality later; this change mainly unblocks single-shot today.

## Global constraints

- Do **not** commit unless the user asks.
- Do **not** install dependencies or edit harness global config.
- Work on primary checkout (`C:\Users\oalan\Praetor`); no worktree required.
- Keep `LEDGER_HISTORY` constant for tool/audit tagging; remove it from the non-attacker-controllable set.
- Preserve Outcome Matrix row `insufficient_corroboration` (redefine failing case to sole ambiguous cite / zero anchoring cites).
- Preserve DEC-064 Outcome Matrix `agentic_evidence_gathering_failed` and `session_trace_hash` bits.
- Registry → gate merge remains deferred (out of scope).
- Single-shot remains production default; do not wire `AgenticJudgmentProvider` into runtime.

## DEC-065 (summary)

| Pin | Value |
|---|---|
| Host floor (temporary) | ≥1 cited fact that anchors the host target (DEC-052), any `provenance_path` |
| Trusted-path / attacker-controllable check | Deferred until multi-telemetry; table remains advisory |
| Upgrade flag | Document: restore ≥2 distinct provenance paths (+ define attacker-controllable table) when real multi-source events land |
| Sole `ambiguity_flag=true` cite | Still fails corroboration |
| `ledger_history` corroboration | **Not eligible** — supersedes DEC-064 trust-table extension |
| Account floor (temporary) | ≥1 supporting fact, any provenance (still feature-gated) |

---

## Task 1: Decision + contracts

**Files:**
- Modify: `docs/decisions.md` (DEC-065; mark DEC-064 corroboration trust extension superseded)
- Modify: `docs/contracts.md` §12a
- Modify: `docs/spec.md` host/account corroboration pins that still say ≥2 (keep in sync with contracts)
- Optional touch: `docs/architecture.md` only if it restates the ≥2 floor

**Acceptance:**
- DEC-065 accepted with upgrade flag wording.
- §12a states temporary ≥1 floor, sole-ambiguity reject, deferred attacker-controllable enforcement, `ledger_history` not corroboration-eligible.
- DEC-064 row notes corroboration trust extension superseded by DEC-065; OM + session_trace_hash remain.

---

## Task 2: Provenance helpers + unit tests

**Files:**
- Modify: `src/praetor/evidence/provenance.py`
- Modify: `tests/evidence/test_host_corroboration.py`
- Modify: `tests/evidence/test_account_corroboration.py`
- Modify: `tests/evidence/test_provenance.py`

**Behavior:**
- `meets_host_cited_corroboration`: pass when ≥1 target-anchoring cited fact; fail when zero anchoring cites OR exactly one anchoring cite with `ambiguity_flag=true`. Drop distinct-path ≥2 and trusted-path checks.
- `meets_account_corroboration`: pass when ≥1 fact present (any provenance); fail on empty.
- Remove `LEDGER_HISTORY` from `_NON_ATTACKER_CONTROLLABLE_PATHS` (constant may remain). Update provenance unit tests accordingly.

**Acceptance:**
- Single sysmon host citation passes; sole ambiguous citation fails; empty/no-anchor fails.
- Single-fact account corroboration passes; empty fails.
- `is_attacker_controllable_provenance(LEDGER_HISTORY)` is True (fail-closed default / not trusted).

---

## Task 3: Gate + harness scenario

**Files:**
- Modify: `evals/scenarios/insufficient_corroboration.yaml` (failing case = sole ambiguous host citation, not single provenance)
- Modify: `tests/policy/test_host_corroboration_gate.py` (and any other policy/engine tests that assert single-provenance → insufficient_corroboration)
- Modify as needed: `tests/engine/test_gate_target_ownership.py`, `tests/policy/test_policy_gate.py`, correlation tests that assert account pair-only semantics if they break

**Acceptance:**
- Harness `insufficient_corroboration` still covers the OM row with escalate / flag / SFE=false for sole ambiguous cite.
- Single-provenance host auto_contain no longer escalates solely for insufficient_corroboration.
- Task-scoped pytest green for touched suites.

---

## Task 4: Sprint gate (`phase_exit`)

**Commands:**
- `pytest -q`
- `ruff check src tests evals consumer_sdk`
- `mypy src evals consumer_sdk`

**Acceptance:**
- Full suite green; docs/decision/code agree on temporary floor; no runtime agentic default wiring added.
