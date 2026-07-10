# Praetor — demo run-of-show

Audience: **SOC / security engineers.** Goal: land the thesis — *the model recommends, the
deterministic gate authorizes* — then show **V2 hardening** without turning the talk into a
feature dump.

Asset: `notebooks/praetor_walkthrough.ipynb` (real `process_alert_intake`, offline).

Two acts:

| Act | Beats | Time box |
|---|---|---|
| **I — Thesis** | contain · review · refuse on a DC | ~3:00 |
| **II — V2** (optional / overtime) | corroboration · escalate-default · report · exemplars · statute | ~2:00 |

For a **4-minute cut**, run Act I only and point at the Act II table of contents.

---

## Pre-record setup

1. Open `notebooks/praetor_walkthrough.ipynb`.
2. **Kernel → Restart**, run **Setup** cells once (imports / helpers / boot).
3. Leave Act I + Act II case cells un-run for live demos.
4. Bump font size. Have `configs/example_org.yaml` ready for the statute beat.
5. Fallback: committed outputs render on GitHub — scroll and narrate.

---

## Act I — Thesis (~3:00)

### 0:00 — The problem

> Detection is solved-ish. The expensive question is *what do we do about this alert?* Humans
> don't scale; brittle SOAR trees don't capture org context. Praetor: LLM judges, **deterministic
> gate authorizes.**

### 0:30 — The rule

> Intelligence may be non-deterministic. Authority to act is not. Three dispositions —
> `standard_review`, `escalate`, `auto_contain`. **No `auto_close`.**

### 1:00 — Beat 1: malicious → `AUTO_CONTAIN`

> Macro → encoded PowerShell on a workstation. Org defaults to **escalate**; this host has an
> **explicit allow**. Citations + corroboration pass → directive: host-isolation, **300s** cap,
> idempotency key, never-contain hash. Emit-only — Praetor does not touch EDR.

### 1:50 — Beat 2: benign → `STANDARD_REVIEW`

> Routine logon. Model says review; gate agrees; **no directive.** Safe floor.

### 2:15 — Beat 3: never-contain DC → refuse

> Same `auto_contain` proposal on `DC01` (never-contain). Gate **refuses** with
> `never_contain_live_conflict`. Model may propose; it cannot bypass.

### 3:00 — Close Act I (or continue)

> Statute lives in `example_org.yaml`. Every decision is hash-chained. Eval harness pins 32
> Outcome-Matrix scenarios.

---

## Act II — V2 hardening (optional)

Keep each beat to one sentence + one cell.

| Beat | Line |
|---|---|
| **4 Corroboration** | One citation → `insufficient_corroboration`. Containment needs convergent evidence. |
| **5 Posture** | Fully corroborated, **no allow rule** → escalate-by-default. Not granted by omission. |
| **6 Progressive report** | Read-only override rates by asset class. Decision support, not auto-policy. |
| **7 Exemplars** | Human-confirmed precedents can enter the prompt as illustration-only. |
| **8 Statute curation** | `proposed_statute` is review-only — preflight refuses activation until SOC-lead promote. |

---

## Backup Q&A

- **Hallucinated evidence?** Citations must resolve in the bundle.
- **Fleet-wide isolate?** Rate limits + containment breaker in org config.
- **Who actuates?** Downstream consumer; fails closed on stale/expired/revoked directives.
- **Immutable ledger?** Tamper-*evident* hash chain, not a blockchain claim.

## Title kit

- **Title:** "Praetor: LLM proposes containment — gate refuses it on your DC"
- **One-liner:** "Post-detection disposition. The model recommends; the system authorizes."
- **Pin:** Act I three outcomes + Act II V2 floors. Code: `notebooks/praetor_walkthrough.ipynb`.
