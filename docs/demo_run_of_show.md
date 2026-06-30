# Praetor — 4-minute demo run-of-show

Audience: **SOC / security engineers.** Goal: land the thesis — *the model recommends, the
deterministic gate authorizes* — by showing the **same `auto_contain` proposal** get honored on a
workstation and **refused** on a domain controller, live, through the real engine.

Asset: `notebooks/praetor_walkthrough.ipynb` (drives `process_alert_intake` end-to-end, offline).

---

## Pre-record setup (do this BEFORE you hit record)

1. Open `notebooks/praetor_walkthrough.ipynb` in VS Code or Jupyter Lab.
2. **Kernel → Restart, then run the setup cells once** (imports, narration glue, boot/activate).
   These have no drama — you don't want to wait on imports on camera.
3. **Leave the three CASE cells un-run** (`Case 1`, `Case 2`, `Case 3`). You'll run those live.
   - Case 1 cell id `b9d954a6` (WORKSTATION1 → auto_contain)
   - Case 2 cell id `880cb4ab` (WORKSTATION7 → standard_review)
   - Case 3 cell id `58ddf3ad` (DC01 → refused)
4. Bump editor font size (Ctrl+= a few times). Outputs must be readable at 1080p.
5. Have `configs/example_org.yaml` open in a second tab for the 3:00 beat.
6. Zero-risk fallback: if running live makes you nervous, the notebook outputs are **already
   committed** — open it on GitHub and scroll. Same script, you just say "I've run this" instead.

Target length 4:00. Narration is written to be read at ~150 wpm. Cut anything in _(italics)_ if
you're over time.

---

## The run-of-show

### 0:00 — The problem (no notebook yet; you on camera or on a title slide)

> "Detection is a solved-ish problem — your SIEM fires alerts all day. The expensive question is
> the next one: *what do we actually do about this one?* Today you've got two answers, and both
> are bad. A human triages every alert — that doesn't scale and it burns people out. Or you wire
> up a SOAR playbook — an if-then tree that's brittle, blind to org context, and editing it is a
> change ticket. Praetor is a third answer: an LLM renders the judgment, and a **deterministic
> policy gate** decides what's actually allowed to happen."

### 0:30 — The one sentence that is the whole product

> "Here's the rule the entire system is built around: **the model recommends, the system
> authorizes.** Intelligence is allowed to be non-deterministic. The authority to *act* is not.
> Let me show you what that buys you. Three alerts, real engine, no mocks downstream of the LLM."

_Action: switch to the notebook, scrolled to the top markdown cell (the disposition table)._

> "Three possible outcomes — `standard_review`, `escalate`, `auto_contain`. Notice what's **not**
> here: there's no `auto_close`. Praetor cannot silently make a threat disappear. Uncertainty
> always routes to a human."

### 1:00 — Case 1: malicious chain → auto_contain (run cell `b9d954a6`)

_Action: run the Case 1 cell. Point at the output as you talk._

> "Case one. `winword.exe` spawned an encoded PowerShell child on a workstation — that's a
> textbook macro-intrusion chain. The model proposes `auto_contain`. Now watch the gates: citations
> resolve to real telemetry, the host isn't on the never-contain list, rate limits are fine,
> breakers are closed, the ticket stamp succeeds — so Praetor decides `AUTO_CONTAIN` and emits a
> **containment directive**."

_Point at the directive block._

> "And look at the directive itself — this is the SOC-relevant part. Scope is host-isolation.
> Lifetime is **exactly 300 seconds** — a hard cap, it expires itself. There's an **idempotency
> key**, so a re-judged alert can't double-isolate the box. And it carries a **never-contain
> snapshot hash** the downstream consumer re-checks before it actuates. Praetor never touches your
> EDR — it emits an honest, short-lived, revocable signal and hands off."

### 1:50 — Case 2: benign → standard_review (run cell `880cb4ab`)

_Action: run Case 2._

> "Case two, fast — a routine interactive logon. Model says `standard_review`, gate agrees, **no
> directive.** Nothing isolated, a human still sees it. That's the safe floor. I'm showing you this
> so the next one lands: the gate isn't just a rubber stamp."

### 2:15 — Case 3: the money shot — refusal on a never-contain host (run cell `58ddf3ad`)

_Action: run Case 3. Let the output sit for a beat before you talk._

> "Case three. A SOC lead has flagged the domain controller `DC01` as **never-contain** — you do
> not auto-isolate your DC, ever. Now an alert proposes `auto_contain` on `DC01`. Same proposal as
> case one. Suspicious PowerShell, encoded command, lsass handle access — the model is convinced,
> it proposes containment again."

_Point at `PRAETOR DECIDED : ESCALATE` and the fault flag._

> "And Praetor **refuses.** The live never-contain check overrides the model and escalates with
> `never_contain_live_conflict`. No directive. The DC is untouched. The model was *allowed to
> propose* it — it just can't bypass the gate. That's the line: **uncertainty flows downward, the
> model never holds the authority to act.**"

_Optional, if you have time:_

> "And notice `system_fault_escalation` is `False` — this isn't an error or a crash. It's a
> **deliberate safety gate firing.** The system is working exactly as designed."

### 3:00 — Why a SOC can trust it (switch to `example_org.yaml`)

> "Two things make this auditable instead of magic. One — the policy isn't buried in code, it's
> **statute.**"

_Action: switch to `configs/example_org.yaml`, point at the `never_contain` block._

> "This is the whole playbook a SOC lead owns: the never-contain list, default-to-escalate posture,
> rate limits, breaker thresholds, the 300-second directive cap. Human-authored, versioned, and
> rendered **in full** into every judgment — safety sections are never silently dropped to save
> tokens."

_Action: switch back to the notebook, point at any `ledger_current_hash` line._

> "Two — every decision, contained or not, wrote a `decision_id` and a **hash-chained ledger row.**
> Tamper-evident audit trail. You can reconstruct any case."

### 3:35 — Where it stands / close

> "Everything you saw ran through the real intake path — the only mocks are the LLM and the ticket
> system. Beyond these three, there's an eval harness — `python -m evals.harness` — that adjudicates
> **26 Outcome-Matrix scenarios**: malformed model JSON, provider timeouts, breaker-open,
> stale feed, every failure mode, each with a pinned expected disposition. 778 tests, mypy strict,
> five build phases done."

> "Detection tells you something fired. Praetor decides what happens next — with judgment you can
> actually trust, because the authority to act is deterministic, bounded, and on the record."

_End._

---

## Backup Q&A (anticipate these from a SOC audience)

- **"What if the LLM hallucinates evidence?"** Citations are machine-checked — the model's rationale
  must cite evidence refs that resolve in the alert bundle. Unresolvable citations downgrade to
  `escalate`. Fluent prose alone doesn't clear the gate. (Shown exhaustively in `evals.harness`.)
- **"What's stopping it from isolating half the fleet?"** Per-host / per-subnet / per-asset-group
  rate limits and a containment circuit breaker, both in `example_org.yaml`. Trip the breaker and
  `auto_contain` is off the table until it resets.
- **"You said it never actuates — so what does?"** Praetor emits the directive; a downstream consumer
  owns receipt-to-actuation and **fails closed** on a stale, expired, or revoked directive. Reference
  implementation is `consumer_sdk/reference_verifier.py`.
- **"Is the ledger really immutable?"** No, and we don't claim that — it's **hash-chained and
  tamper-evident.** A modified row breaks the chain at startup verification. We don't overclaim.
- **"Where do detections come from?"** Upstream, not Praetor's job. There are Sigma rules in
  `detections/sigma/` that compile to SPL for a Splunk path, but Praetor consumes whatever your SOC
  already produces.

## Title / description kit (for YouTube / LinkedIn / repo)

- **Title:** "Praetor: an LLM proposes containment — a deterministic gate refuses it on your DC"
- **One-liner:** "Post-detection disposition engine. The model recommends; the system authorizes."
- **Pinned comment / description:** Three real alerts through the real engine — a malicious chain
  gets auto-contained, a benign logon routes to review, and the same auto-contain proposal is
  *refused* on a never-contain domain controller. No `auto_close`, machine-checked citations,
  hash-chained audit. Code: `notebooks/praetor_walkthrough.ipynb`.
