# Praetor — Product Requirements (PRD)

*The why. Sits above the Specification (the what) and the Implementation Plan (the how). Where the spec says "PolicyGate validates citations against real bundle IDs," this document says why that check has to exist at all.*

---

## The problem

A SOC's detection layer answers one question — *did something fire?* — and it answers it deterministically. The expensive, judgment-heavy question comes next: *given that it fired, what do we do about it?* Today that triage is either a human reading every alert (slow, fatiguing, the bottleneck) or a hand-maintained decision tree of if-then rules (brittle, and no matter how elaborate, still just an exaggerated if-then). Neither scales, and the rule-tree approach can't encode the contextual judgment that makes triage hard: the same event is routine at one org and a five-alarm fire at another.

## The thesis

Model judgment is genuinely useful for that next decision — *but only if it is constrained.* Praetor's bet is not "let an LLM decide." It is: **an LLM can render contextual judgment, and that judgment becomes trustworthy when it is wrapped in stable contracts, schema-enforced citations, deterministic safety controls, and a reviewable audit trail.** The intelligence is allowed to be non-deterministic; the *authority to act* is not. That separation is the entire product.

## Who it's for

A SOC that already has detection and wants to reduce the human cost of triage without surrendering control or auditability. Praetor is an **add-on**, not a platform: it consumes alerts the SOC already produces and emits decisions the SOC's existing SOAR/EDR can act on. Portability is a first-class requirement, not a nice-to-have.

---

## The decisions that define the product, and why

**1. The model recommends; the system authorizes.**
The LLM emits a `ModelJudgment` — a *proposed* disposition with rationale and citations. A deterministic `PolicyGate` decides the *final* disposition. The edict records both. Why: written reasoning is generated at the same instant as the action and read only afterward — it is an *audit* artifact, not a *gate*. If the gate were the model's own confidence, "the model felt sure" would be the only justification on record, which is unreviewable. Separating recommendation from authorization is what lets an auditor distinguish "the model assessed low risk" from "the model wanted to contain but policy blocked it." Those are different facts and they must not collapse into one.

**2. Three dispositions, and there is no fourth that hides things.**
`standard_review`, `escalate`, `auto_contain`. Every one of them is *additive to safety*: two route to a human, one acts on high conviction and is reviewable. There is deliberately no `auto_close`. Why: auto_close is the only candidate disposition whose failure mode is *silent* — it makes a real threat disappear with nobody watching. The moment Praetor owns a suppression path, it stops being a tool that adds safety checks and becomes a tool that can create blind spots. Uncertainty always falls *down* to standard_review; "I'm not sure" is not a new state, it's the floor.

**3. Auto-containment must clear deterministic gates, not vibes.**
Containment is operationally expensive (you may isolate a prod host or kill a real session) and adversarially sensitive. So `auto_contain` is the only disposition that requires passing hard, non-deterministic-free checks before a directive is emitted: validated citations, never-contain exclusions, rate limits, circuit breaker, expiry, idempotency. Why: the cost of a wrong containment is asymmetric and irreversible-at-speed, so the bar to *act* must be deterministic and inspectable, even though the bar to *suspect* can be the model's judgment.

**4. Citations are schema-enforced and resolve to real facts.**
The rationale must cite evidence IDs or field paths that actually exist in the bundle, validated at runtime; failure falls back to escalate. Why: a fluent paragraph that cites nothing can sound completely convincing while being unfaithful to the evidence — that is exactly the hallucination case the whole design exists to survive. Machine-checkable citation turns "show your work" from rhetoric into a test. It also narrows the prompt-injection surface, because the model reasons over typed fields and cites IDs rather than obeying attacker-controlled prose.

**5. The org config is the statute, and it is rendered in full.**
A human-authored, versioned config makes the same engine behave differently per environment, and it is included *verbatim* in the judgment context until a hard budget forces structured refactoring. Why: selectively including "only the relevant sections" sounds efficient but silently drops safety-critical exclusions when the link between an alert and a never-contain entry isn't a clean key match. Token discipline means making the config *smaller*, never *incomplete*. Safety sections have no scoped variant — they are always present.

**6. Feedback is human-gated, and we say so honestly.**
Analyst annotations never touch the model or runtime policy; they inform a SOC lead who deliberately edits the config on a cadence. Why: a self-tuning containment authority is the hardest thing here to make defensible, and a live feedback loop invites drift and poisoning. The honest framing matters — this is *gated by human review*, not "structurally impossible," because a patient adversary could still nudge annotation patterns toward a weakening edit. Naming the residual risk is part of the product, not an admission against it.

**7. The record is tamper-evident and reconstructable — not immutable, not replayable.**
The v1 ledger is a hash-chained append-only audit log (detects tampering; does not prevent it against a compromised writer). "Replay" means a human can fully reconstruct the case from stored inputs — *not* that the system can recompute an identical model output, which commercial LLMs cannot guarantee. Why: overclaiming "immutable" or "replayable" to an auditor or legal reader is a credibility risk that the architecture cannot actually back. Claim what is true.

---

## What success looks like

Praetor v1 succeeds if a SOC lead can look at any contained ticket and see — without reading source code — what fired, what local evidence was correlated, what the model proposed, which deterministic checks authorized or downgraded it, and why; if `auto_contain` provably cannot fire without passing every safety gate; and if the whole decision content is portable enough to hand to another SOC's Splunk and SOAR. The differentiator over a complex rule tree is not that Praetor decides — it's that it decides *with contextual judgment* and *proves the decision was safe to make.*

## What it is explicitly not (v1)

A detection engine, a severity scorer, a live enforcer, an external-enrichment service, a self-learning system, a suppressor, or a computational replay engine. Each non-goal is a fence against a specific failure mode; see the Specification for the full list and the deferred-work roadmap.

---

*Companion documents: **Specification** (contracts, components, acceptance criteria) and **Implementation Plan** (22 tasks, dependencies, phase gates).*
