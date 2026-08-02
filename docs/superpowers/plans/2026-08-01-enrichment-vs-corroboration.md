# Enrichment vs Corroboration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split host `auto_contain` authorization into presence-based provenance corroboration (`insufficient_corroboration`) and cited source-event enrichment (`insufficient_enrichment`), wire PolicyGate/OM/harness, and add a separate public-demo scenario with SOC-manager copy.

**Architecture:** Approach A from `docs/superpowers/specs/2026-08-01-enrichment-vs-corroboration-design.md`. Corroboration counts ≥2 eligible `provenance_path` values in the **host-scoped evidence bundle**. Enrichment counts ≥2 distinct `source_event_reference` values among **target-anchoring cited** facts. Gate evaluates corroboration then enrichment. GR-0012: ratify OM row in decision task; add enum only with harness scenario.

**Tech Stack:** Python 3.11+, pytest, existing PolicyGate / evidence / evals harness, `notebooks/walkthrough_scenarios.py` + `tools/build_demo_page.py`.

## Global Constraints

- Design SoT: `docs/superpowers/specs/2026-08-01-enrichment-vs-corroboration-design.md`.
- Do **not** commit unless the user asks.
- Do **not** install dependencies or edit harness global config without approval.
- Work on primary checkout (`C:\Users\oalan\Praetor`); no worktree required.
- New fault flag follows GR-0012 (decision-only OM row first; enum + harness together).
- Enrichment is **host-only**; account stays on DEC-065 temporary ≥1 supporting-fact floor.
- `ledger_history` remains not corroboration-eligible and not enrichment-eligible.
- Attacker-controllable table stays advisory (do not re-enable DEC-059 trusted-path enforcement).
- Gates use Grok (`cursor-grok-4.5-high`); implementer `composer-2.5`; code-review after every code-changing implement; skeptic-verify every task.
- Do not claim completion without fresh verification evidence.

## File map

| File | Responsibility |
|---|---|
| `docs/decisions.md` | DEC-066 ratification; DEC-065 host supersession note |
| `docs/contracts.md` §12a / §13 | Presence corroboration + enrichment pins; OM rows |
| `docs/spec.md` | Mirror host pins if still required to stay in sync |
| `src/praetor/evidence/provenance.py` | Bundle corroboration + cited enrichment helpers |
| `tests/evidence/test_host_corroboration.py` | Presence corroboration unit tests (retarget) |
| `tests/evidence/test_host_enrichment.py` | Enrichment unit tests (new) |
| `src/praetor/policy/gate.py` | Wire both checks in order |
| `src/praetor/policy/identity.py` | Fault string constants / helper name pins |
| `src/praetor/metrics/events.py` (+ related fault maps) | `INSUFFICIENT_ENRICHMENT` enum + SFE map |
| `evals/scenarios/insufficient_corroboration.yaml` | Retarget to single-path presence failure |
| `evals/scenarios/insufficient_enrichment.yaml` | New thin-citation scenario |
| `tests/fixtures/synthetic/` | Fixtures for both failure modes |
| `tests/policy/test_host_corroboration_gate.py` | Gate tests for both flags |
| `notebooks/walkthrough_scenarios.py` | Two demo scenarios + green-path `enriched=` cites |
| `tools/build_demo_page.py` / `demo/index.html` | Rebuild public demo |
| `evals/outcome_matrix.py` | Polarity map entry if separate from enum module |

---

### Task 1: DEC-066 + contracts (decision-only)

**Files:**
- Modify: `docs/decisions.md`
- Modify: `docs/contracts.md` (§12a, §13)
- Modify: `docs/spec.md` (host corroboration / OM mirror pins only)
- Optional: `docs/architecture.md` only if it restates the old host floor
- Create/update: `.workflow/enrichment-split-01-decision/`

**Interfaces:**
- Consumes: ratified design Approach A
- Produces: DEC-066 text; §12a presence + enrichment pins; §13 rows for `insufficient_corroboration` (retargeted) and `insufficient_enrichment` (new, SFE=false); **no** enum member yet (GR-0012)

- [ ] **Step 1: Draft DEC-066** in `docs/decisions.md` index + section:

  - Host corroboration = ≥2 distinct corroboration-eligible `provenance_path` in host-scoped bundle facts.
  - Host enrichment = ≥2 distinct `source_event_reference` among target-anchoring cited facts; fault `insufficient_enrichment`; SFE=false.
  - Supersedes DEC-065 **host** temporary cited ≥1 floor; account DEC-065 temporary floor remains.
  - Sole-ambiguity subsumed by enrichment ≥2.
  - Rejected: ≥2 cited provenance paths as enrichment unit.
  - Trusted-path table remains advisory.

- [ ] **Step 2: Rewrite `docs/contracts.md` §12a** into:
  - Provenance trust table (unchanged eligibility; still advisory for attacker-controllable enforcement).
  - Host corroboration (presence) subsection.
  - Host enrichment (cited source events) subsection.
  - Account temporary floor pointer to DEC-065 (unchanged behavior).

- [ ] **Step 3: Update §13 Outcome Matrix**
  - Retarget `insufficient_corroboration` row text to presence failure.
  - Add `insufficient_enrichment` row: escalate / false.

- [ ] **Step 4: Sync `docs/spec.md`** host pins / OM mirror if present.

- [ ] **Step 5: VERIFY-E01** — decision/contracts grep gate

```bash
rg -n "DEC-066|insufficient_enrichment|source_event_reference" docs/decisions.md docs/contracts.md docs/spec.md
rg -n "insufficient_corroboration" docs/contracts.md
```

Expected: DEC-066 present; enrichment predicate pinned to `source_event_reference`; both OM rows present; host presence ≥2 documented; no enum required yet.

**Acceptance:**
- DEC-066 accepted with host/account split explicit.
- §12a/§13 match Approach A.
- GR-0012 honored (OM row text only; no `OutcomeMatrixFaultFlag` member in this task).

---

### Task 2: Provenance helpers + unit tests

**Files:**
- Modify: `src/praetor/evidence/provenance.py`
- Modify: `tests/evidence/test_host_corroboration.py`
- Create: `tests/evidence/test_host_enrichment.py`
- Modify if needed: `tests/evidence/test_provenance.py`
- Create/update: `.workflow/enrichment-split-02-helpers/`

**Interfaces:**
- Consumes: DEC-066 pins from Task 1
- Produces:
  - `meets_host_bundle_corroboration(facts: Sequence[EvidenceFact], *, target_host_id: str) -> bool`
  - `meets_host_cited_enrichment(cited: Sequence[ResolvedEvidenceCitation], *, target_host_id: str, facts_by_id: Mapping[str, EvidenceFact]) -> bool`
  - Deprecate/remove host cited-floor behavior from `meets_host_cited_corroboration` (delete or turn into a thin wrapper only if call sites need a transition — prefer delete + update call sites in Task 3)

- [ ] **Step 1: Write failing enrichment tests** in `tests/evidence/test_host_enrichment.py`:

```python
def test_two_distinct_source_events_same_path_enrich():
    # two sysmon facts, different source_event_reference, both anchor host → True

def test_single_cited_event_fails_enrichment():
    # dual-path bundle facts exist but only one anchoring cite → False

def test_ledger_history_cite_does_not_count():
    # ledger_history anchoring cite ignored for enrichment cardinality
```

- [ ] **Step 2: Write failing / retargeted corroboration tests** in `tests/evidence/test_host_corroboration.py`:

```python
def test_two_eligible_paths_in_host_scoped_bundle_pass():
def test_single_path_bundle_fails_even_if_cited():
def test_cross_host_second_path_does_not_count():
def test_ledger_history_path_not_corroboration_eligible():
```

- [ ] **Step 3: Run tests — expect FAIL**

```bash
pytest tests/evidence/test_host_corroboration.py tests/evidence/test_host_enrichment.py -q
```

- [ ] **Step 4: Implement helpers** in `provenance.py` per design (host-scoped presence; distinct `source_event_reference`; exclude `_NON_CORROBORATION_ELIGIBLE_PATHS`).

- [ ] **Step 5: Run tests — expect PASS**

```bash
pytest tests/evidence/test_host_corroboration.py tests/evidence/test_host_enrichment.py tests/evidence/test_provenance.py -q
ruff check src/praetor/evidence/provenance.py tests/evidence/test_host_corroboration.py tests/evidence/test_host_enrichment.py
mypy src/praetor/evidence/provenance.py
```

**VERIFY-E02:** evidence unit suites green; helpers match DEC-066.

**Acceptance:**
- Presence ≥2 host-scoped eligible paths passes; single path fails; cross-host pollution does not count.
- Enrichment ≥2 distinct `source_event_reference` among anchoring cites passes; single cite fails; same path allowed twice; `ledger_history` excluded.

---

### Task 3: PolicyGate + enum + harness (GR-0012 implement)

**Files:**
- Modify: `src/praetor/policy/gate.py`
- Modify: `src/praetor/policy/identity.py`
- Modify: `src/praetor/metrics/events.py` (and any SFE / canonical flag maps that must include the new member)
- Modify: `evals/outcome_matrix.py` if polarity lives there separately
- Modify: `evals/scenarios/insufficient_corroboration.yaml` + synthetic fixture
- Create: `evals/scenarios/insufficient_enrichment.yaml` + synthetic fixture
- Modify: `tests/policy/test_host_corroboration_gate.py` (and other policy/engine/eval tests asserting old DEC-065 host semantics)
- Touch as needed: `tests/engine/`, `tests/evals/`, `tests/correlation/` only where old host-floor assertions break
- Create/update: `.workflow/enrichment-split-03-gate-harness/`

**Interfaces:**
- Consumes: helpers from Task 2; OM row text from Task 1
- Produces: live gate behavior; `OutcomeMatrixFaultFlag.INSUFFICIENT_ENRICHMENT`; harness coverage for both flags

- [ ] **Step 1: Add enum + polarity** (`INSUFFICIENT_ENRICHMENT`, SFE=false) in the same change set as harness scenario (AG-0068 / GR-0012).

- [ ] **Step 2: Wire gate order** after DEC-052 target resolution for `target_type == "host"`:

```python
if not meets_host_bundle_corroboration(evidence_bundle.facts, target_host_id=target.target_id):
    return _escalate(proposed, INSUFFICIENT_CORROBORATION, system_fault=False)
if not meets_host_cited_enrichment(
    citation_result.resolved,
    target_host_id=target.target_id,
    facts_by_id={fact.evidence_id: fact for fact in evidence_bundle.facts},
):
    return _escalate(proposed, INSUFFICIENT_ENRICHMENT, system_fault=False)
```

- [ ] **Step 3: Retarget harness `insufficient_corroboration`** to single eligible provenance path in host-scoped bundle (presence failure). Update description + fixture.

- [ ] **Step 4: Add harness `insufficient_enrichment`** — dual-path bundle, model cites only one anchoring source event; expect escalate / `insufficient_enrichment` / SFE=false.

- [ ] **Step 5: Update policy/gate unit tests** for both branches; fix green-path host `auto_contain` tests to supply dual-path bundles **and** ≥2 cited source events.

- [ ] **Step 6: VERIFY-E03**

```bash
pytest tests/policy/test_host_corroboration_gate.py tests/policy/test_policy_gate.py tests/evals/test_eval_harness.py -q
# plus any other suites touched in this task
ruff check src/praetor/policy src/praetor/metrics/events.py tests/policy
```

Expected: both OM scenarios covered; completeness guard green; single-path → corroboration flag; thin citation with dual path → enrichment flag.

**Acceptance:**
- Gate emits the correct flag for each failure mode; order is presence then enrichment.
- `test_outcome_matrix_completeness_guard` passes with the new enum + scenario.
- Old DEC-065 “sole ambiguous cite ⇒ insufficient_corroboration” assertions are gone or retargeted to enrichment.

---

### Task 4: Public demo scenarios + page rebuild

**Files:**
- Modify: `notebooks/walkthrough_scenarios.py`
- Modify/regenerate: `demo/index.html` via `tools/build_demo_page.py`
- Modify if needed: `notebooks/check_walkthrough.py`, `notebooks/_regen_walkthrough.py`, notebook markers
- Create/update: `.workflow/enrichment-split-04-demo/`

**Interfaces:**
- Consumes: live gate flags from Task 3
- Produces: two non-conflated SOC-manager scenarios on the HTML demo

- [ ] **Step 1: Retarget existing thin-evidence scenario**
  - Key may remain temporarily, but prefer renaming labels: e.g. keep key `insufficient_corroboration` for presence-fail OR split keys cleanly:
    - `insufficient_corroboration` — `dual_provenance=False`; assert `insufficient_corroboration`
    - `insufficient_enrichment` — `dual_provenance=True`, single cite; assert `insufficient_enrichment`
  - Copy: What happens / Setup / Why it matters; no jargon; do not say “thin evidence” for both.

- [ ] **Step 2: Rename helper kwarg** `corroborated=` → `enriched=` (update all call sites). Green-path host contain scenarios must pass enrichment (≥2 cites) and corroboration (dual path).

- [ ] **Step 3: Rebuild demo + check**

```bash
python tools/build_demo_page.py --write
python tools/build_demo_page.py --check
# if notebook regen/check is part of the shared registry CI:
python notebooks/_regen_walkthrough.py
python notebooks/check_walkthrough.py notebooks/praetor_walkthrough.ipynb
```

- [ ] **Step 4: VERIFY-E04** — demo scenarios assert distinct flags; `--check` green; SOC copy does not conflate presence vs citation depth.

**Acceptance:**
- Two dials on `demo/index.html` with distinct keys/labels/copy.
- Assertions match engine flags.
- Shared registry stays the single source for notebook + demo.

---

### Task 5: Sprint / phase exit gate

**Files:**
- `.workflow/enrichment-split-gate/`
- `memory-bank/tasks.md`, `memory-bank/progress.md`, `memory-bank/activeContext.md` (status sync only)

**VERIFY-E05 (phase_exit):**

```bash
pytest -q
ruff check src tests evals consumer_sdk
mypy src evals consumer_sdk
```

**Acceptance:**
- Full suite green.
- All task verifier artifacts PASS.
- DEC-066 reflected in docs + code; account still on DEC-065 temporary floor; no trusted-path enforcement silently re-enabled.
- Demo `--check` still green if run as part of gate commands or manual_checks.

---

## Spec coverage self-check

| Design requirement | Task |
|---|---|
| Presence corroboration ≥2 host-scoped paths | 1, 2, 3 |
| Enrichment ≥2 `source_event_reference` | 1, 2, 3 |
| `insufficient_enrichment` OM row SFE=false | 1, 3 |
| Retarget `insufficient_corroboration` | 1, 3, 4 |
| Host-only enrichment | 1, 3 |
| DEC-052 preserved | 3 (ordering after target resolution) |
| Sole-ambiguity subsumed | 1, 2, 3 |
| DEC-065 account temporary retained | 1, 5 |
| Two demo scenarios, non-conflated copy | 4 |
| GR-0012 two-phase flag | 1 then 3 |
| Land under temporary-floor era | 1 (DEC-066 supersession) |

## Execution handoff

Plan saved to `docs/superpowers/plans/2026-08-01-enrichment-vs-corroboration.md`.

GSD queue items (pending): `enrichment-split-01-decision` → `02-helpers` → `03-gate-harness` → `04-demo` → `enrichment-split-gate`.

Start drain with `/gsd-autopilot-loop` (do not start until the operator asks).
