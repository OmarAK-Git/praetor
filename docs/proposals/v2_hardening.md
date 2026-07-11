# Praetor v2 — Hardening Proposal

**Status: IMPLEMENTED (V2 Gates 0–5 closed 2026-07-10).** Design rationale retained for
provenance. `docs/spec.md` (v1) remains frozen; accepted items landed via `docs/contracts.md`
and `docs/decisions.md` (DEC-058–063). Behavioral authority is contracts/decisions, not this
proposal. Historical “how v1 behaved” grounding below describes **pre-V2** behavior.

## Why a v2

v1 proved the thesis: *the model's judgment may be non-deterministic; its authority may not.*
The deterministic PolicyGate bounds **authority** (never-contain floor, rate/breaker ceiling,
300s expiry, emit-only, full audit) — it does **not** verify that a proposed containment is
*correct*, and it cannot, because judging the threat is the non-deterministic act.

Threat-modeling v1 surfaced one architectural truth and three improvement levers:

- **Truth:** the gate is an *authorization* layer, not a *verification* layer. For a target
  that is not on never-contain, has no explicit `deny` rule, and is within rate budget, a
  citation-resolving `auto_contain` proposal **passes**. Correctness rests entirely on the
  model + correct evidence retrieval. (Grounding below.)
- **Lever 1 — evidence robustness:** host `auto_contain` rests on as little as one cited fact.
- **Lever 2 — authorization posture:** `auto_contain` is default-**allow** (denylist), so an
  un-enumerated critical asset is containable by default — **confirmed drift**, compounded by a
  silent `scope` validation bug that nullifies an operator's intended safe default (see Item 2).
- **Lever 3 — the feedback loop:** analyst corrections are *captured* but never *applied*, and
  the model has no mechanism to improve in-context over time.

## How v1 behaved before V2 (historical grounding)

- The gate reads only `judgment.proposed_disposition` and `judgment.cited_evidence_refs`
  (`src/praetor/policy/gate.py:277,294,301`). It **never reads** `key_tells`,
  `convergence_reasoning`, or `narrative` — the model's *reasoning* is recorded in the edict
  for humans, but plays **zero role** in authorization.
- `validate_evidence_citations` (`src/praetor/evidence/citations.py`) is **structural**: it
  confirms each cited `evidence_id`/`field_path` *exists* in the bundle. It blocks
  **fabricated** evidence (invented facts) and does nothing about **misinterpreted real**
  evidence (a wrong conclusion drawn from facts that do exist).
- `evaluate_target_containment_policy` (`src/praetor/policy/containment_policy.py:222`)
  returns **ALLOW when no rule matches the target** — default-allow. The example config's only
  rule (`scope: global`, a string) matches nothing and is effectively a no-op.
- The validator already resolves, but the gate ignores for hosts, the
  `provenance_path` and `ambiguity_flag` of each cited fact (`citations.py:77–85`).
- The judgment prompt (`src/praetor/judgment/prompt.py:55`) contains the excerpts, the verbatim
  statute, and instructions — **no exemplar/few-shot slot**.

---

## Item 1 — Evidence corroboration floor for host `auto_contain`  **[IMPLEMENTED — V2-011]**

**Status:** **ratified (DEC-059, V2-002) and implemented (V2-011)** — corroboration is a first-class host + account concept; `insufficient_corroboration` Outcome Matrix row in `docs/contracts.md` §13; provenance trust table in §12a; PolicyGate enforces the host floor.

**Problem.** Host containment can be authorized on a single cited fact. An attacker who can
author telemetry (or an honest-but-fallible model on an ambiguous single signal) can therefore
get a containment through. v1 already solved *which* host (citation-anchored targeting, DEC-052)
but not *whether the evidence is sufficient*.

**Proposal.** Require, before authorizing host `auto_contain`, that the cited facts:
- span **≥2 distinct `provenance_path` values**, with **≥1 not attacker-controllable**
  (e.g. not a raw command line / raw log string), and
- contain **no cited fact with `ambiguity_flag = true`** as the sole basis.

This mirrors the account rule that **already exists** —
`evaluate_account_containment_eligibility` requires two facts from distinct provenance paths,
one not attacker-controlled (spec § Account Containment). v2 extends that same discipline to
hosts, reusing the `provenance_path`/`ambiguity_flag` the citation validator already resolves.

**Effect.** Raises the bar from "forge one log line" to "forge convergent evidence across
independent collection systems." It does **not** verify the threat (impossible deterministically)
— it raises *evidence sufficiency*, which is the closest deterministic proxy.

**Open question for review.** *Why does the v1 spec under-articulate corroboration for hosts?*
Hypothesis: v1 scoped host containment as the shippable path and treated account **identity**
as the higher-risk problem (SID spoofing, name ambiguity), so the heavy corroboration landed on
accounts while hosts got target-selection integrity (citation-anchoring) instead of
evidence-sufficiency. **Accepted (DEC-059):** corroboration is now a first-class spec/contracts
concept for both host and account authorization, not an account-only rule.

**Fault flag:** `insufficient_corroboration` (policy/safety class,
`system_fault_escalation = false`), pinned in `docs/contracts.md` §13. Enum + harness scenario
wire in V2-011 per completeness contract.

---

## Item 2 — Containment-rule `scope` validation + authorization posture  **[IMPLEMENTED — V2-005–013]**

This began as the "default-deny vs denylist" posture question (was on HOLD pending an owner
counter-argument). Cross-review with the original spec author **resolved it: v1's default-allow is
drift, not a decision** — it contradicts the containment thesis (uncertainty should fall to
`standard_review`; containment should be *earned*, not granted-by-omission). Two coupled problems
are documented here for later implementation.

### Root cause (confirmed v1 bug)

`ContainmentRule` (`src/praetor/contracts/org_config_sections.py:36`) is `extra="allow"` and
declares only `name` and `action`. **`scope` is not a declared field** — it rides in as an untyped
extra. Nothing validates it: preflight checks *rate-limit* scopes but never *rule* scopes. The gate
reads it via `getattr(rule, "scope", None)` and skips any rule whose scope isn't a dict
(`containment_policy.py:232`). So `scope: global` (a string) is **silently dropped**, the rule
matches nothing, and `evaluate_target_containment_policy` falls through to `ALLOW` (`:251`).

**The inversion:** an operator who writes `default_escalate` / `scope: global` believes they set a
cautious default. The parser drops the rule and the fallthrough is `ALLOW` — so their *most cautious*
config produces the *least safe* behavior (containment-permitted-by-default), **silently**. Same
class as a works-today / fails-silently bug on the safety-critical path.

### 2a. Validation hardening — chosen near-term direction (option B)

Make malformed/unknown rule config **fail loudly at activation** instead of being silently skipped,
*without yet flipping the posture*:
- declare `scope` as a **typed field** on `ContainmentRule`;
- flip `ContainmentRule` / `ContainmentPolicy` to **`extra="forbid"`** (strict validation is the
  norm in every other contract model);
- **preflight rejects** a malformed/unknown `scope` (type mismatch → `PreflightError`, not a skip).

Effect: a mistyped or unrecognized rule is caught at activation, not silently nullified. Default-allow
remains for now (so this stays a contained change), but the *silent inversion* is gone.

### 2b. Posture flip + catch-all primitive — deeper v2 change (deferred)

2a alone leaves a gap: there is **no catch-all primitive** — rules only match a specific
`target_id`/`asset_id`/subnet, so even after 2a an operator *still* cannot express "escalate by
default." The real posture fix is coupled to a new primitive:
- add a `default_action` (catch-all, lowest precedence) so "escalate/deny by default, allow only
  these asset groups" is expressible in one place;
- flip the policy-layer default to **deny** (a no-rule target does not reach `auto_contain`).

**Blast radius (plan for it):** flipping default-deny stops the example config's hosts from
auto-containing, which breaks the walkthrough notebook Case 1 (→ the `walkthrough` CI checker that
asserts `AUTO_CONTAIN` / `CONTAINMENT DIRECTIVE EMITTED`), the eval `confirmed_malicious_sequence`
scenario, and policy tests that lean on default-allow. The fix must therefore also rewrite
`configs/example_org.yaml` to express the affirmative allow it always implied (e.g. `auto_contain`
permitted only for `eng-workstation-pool`) and update the notebook + scenarios. The example config
stops being a no-op and starts *demonstrating* the intended posture.

**Regression test (required when 2b lands):** a target with no matching rule must **not** reach
`auto_contain`.

**Open posture question still worth a deliberate answer:** denylist favors automation coverage,
allowlist favors blast-radius safety — the right v2 answer may be a **deployment-configurable
default** (`default_action` in org config) rather than a hard-coded posture.

**Ratified (DEC-058, V2-001):** deployment-configurable `default_action` wins. v1 implicit
default-allow is retired drift. Recommended new-deployment default: `escalate`. Sole matching
`escalate` rules block `auto_contain` (not hint-only). See `docs/decisions.md` DEC-058 for full
rule-action and precedence semantics.

---

## Item 3 — Progressive Authorization ("probationary autonomy")  **[IMPLEMENTED — V2-032]**

**Concept.** Treat the agent like a new employee: it starts on a narrow mandate and **earns**
authority as trust is demonstrated, with the SOC lead, analysts, and the model all learning
together against the statute and the eval scenarios.

**Mechanism (shipped):**
- **Start narrow.** Example org uses `default_action: escalate` with scoped `allow` rules.
- **Measure.** `praetor.reporting.build_progressive_authorization_report` aggregates PolicyGate
  override rate + annotation outcomes per `(target_type, asset_class)` over a window.
- **Promote deliberately.** SOC-led audited config change only — documented in
  `docs/operator_runbook.md`. No self-tuning.

**Operational:** `process_alert_intake` persists evaluation rows on edict commit and initializes
`policy_gate_evaluations` via production schema ensure.

---

## Item 4 — Feedback maturation (safe, human-in-the-middle)  **[IMPLEMENTED — V2-033–036]**

Auto-retraining stays **out** (spec non-goal; PRD DEC-006 "no self-tuning containment
authority"): feedback poisoning + loss of auditability. The sanctioned loop:

1. **Similar-case in-context exemplars — [DONE V2-033/034].** Bounded `PromptExemplarBlock` +
   human-confirmed retrieval (`praetor.retrieval`). Exemplars stay outside the evidence hash path.
   **Operational:** `process_alert_intake` retrieves human-confirmed precedents into the judgment prompt when matches exist.
2. **Statute curation — [DONE V2-035].** Annotation → `proposed_statute` → review →
   `promote_statute_curation` with preflight + activation audit.
3. **Eval-scenario regression locking — [DONE V2-036].** Workflow template + expectation-key CI
   guard; documented in `docs/eval_gates.md`.

---

## Non-goals preserved in v2

- No auto-retraining / self-tuning authority.
- Praetor still does not actuate (emit-only); the consumer's independent critical-asset check
  remains the final backstop.
- `docs/spec.md` v1 stays frozen; accepted items land via the documented hierarchy
  (`docs/contracts.md` for major refinements, `docs/decisions.md` for details) when v2 opens.

## Independent-review checklist

- [x] Item 1: accept corroboration floor for hosts? Promote corroboration to a first-class spec
      concept? Confirm the `insufficient_corroboration` flag + Outcome Matrix wiring.
      **Ratified DEC-059 (V2-002); implemented V2-011.**
- [x] Item 2: posture **ratified (DEC-058, V2-001)** — default-allow retired as drift;
      deployment-configurable required `default_action`; `escalate` blocks containment.
      **2a:** typed `scope` + `extra="forbid"` + preflight (V2-005). **2b:** `default_action` +
      no-rule fallthrough + example config / notebook / scenarios (V2-012, V2-013).
- [x] Item 3: progressive-authorization reporting view (V2-032); SOC-led promotion in runbook.
- [x] Item 4: similar-case retrieval + exemplar slot (V2-033/034); statute curation (V2-035);
      eval regression locking (V2-036).
