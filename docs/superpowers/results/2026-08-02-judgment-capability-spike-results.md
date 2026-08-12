# Judgment capability spike — results

**Date:** 2026-08-03  
**Status:** complete (clean negative on the primary question)  
**Design:** [`docs/superpowers/specs/2026-08-01-capability-spike-design.md`](../specs/2026-08-01-capability-spike-design.md)  
**Plan:** [`docs/superpowers/plans/2026-08-01-judgment-capability-spike.md`](../plans/2026-08-01-judgment-capability-spike.md)  
**Decision:** [DEC-067](../../decisions.md#dec-067--capability-spike-routing-coverage-not-the-bottleneck-judgment-unmeasured-above-baseline)  
**Artifact:** `evals/capability/captures/atlasv2_capability_spike_results.jsonl`  
**Pre-refill backup:** `evals/capability/captures/atlasv2_capability_spike_results.prerefill.jsonl`  
**Analyses dump:** `evals/capability/captures/atlasv2_capability_spike_writeup_analyses.txt`

## Answer in one paragraph

On the production Path A surface (Sysmon EventID 1 + Security 4624), single-shot GenAI judgment is **not distinguishable** from a `path_a_fact_count` majority stump at n=26 (McNemar b=3, c=1, exact two-sided p=0.625). That is a successful spike: the design treats a clean negative as a defensible answer. Separately, richer Path B evidence does **not** help and directionally hurts benign specificity (paired A-vs-B McNemar b=7, c=0, p=0.015625). Absolute rates are conditional on synthetic 50/50 raw-telemetry windows, not on Praetor’s AlertEnvelope population.

---

## 1. Primary answer — judgment vs trivial heuristic (Path A)

**Question:** has single-shot judgment earned anything above a trivial heuristic on the production path?

| Comparator | Right / 26 |
|---|---:|
| Path A model (anchor-majority) | 22 |
| `path_a_fact_count` stump | 20 |

**Model vs stump 2×2 (anchor-majority, path-matched stump):**

| | Stump right | Stump wrong |
|---|---:|---:|
| **Model right** | 19 | 3 (ben-05, ben-11, ben-12) |
| **Model wrong** | 1 (ben-08) | 3 (ben-01, ben-02, ben-03) |

**McNemar (exact two-sided):** b=3 (model-only wins), c=1 (stump-only wins), discordant n=4, **p=0.625**.

No detectable improvement over fact-count. Nearly all outcomes agree with the stump (22/26 shared). Capability above a trivial heuristic on Path A remains **unmeasured / not shown**.

---

## 2. Secondary answer — coverage is not the bottleneck

**Question:** is Path A failing because correlation starves the model of evidence types?

| | Path B right | Path B wrong |
|---|---:|---:|
| **Path A right** | 15 | 7 |
| **Path A wrong** | 0 | 4 |

Discordant pairs: **A✓ B✗ = 7** (ben-04, ben-07, ben-09, ben-10, ben-12, ben-13, mal-12); **A✗ B✓ = 0**.

**McNemar exact two-sided p=0.015625.** Every discordant pair favors Path A.

Cell-level recall vs specificity (post-refill, balanced denominators):

| | Path A | Path B |
|---|---:|---:|
| malicious → escalate\|auto_contain | 92.31% (36/39) | 87.18% (34/39) |
| benign → standard_review | 68.42% (26/38) | 34.21% (13/38) |

Malicious recall is flat across paths. The entire A–B delta is **benign specificity collapsing** when extras are added. This routes investment **away from expanding normalizers** on this evidence.

Path B vs its own stump (`path_b_pre_cap_count`): b=1, c=6, exact two-sided **p=0.125** — **no detectable difference, directionally unfavorable** (not “the stump wins”).

---

## 3. Error structure (Path A)

Path A is **13/13 on malicious anchors by majority**. All four anchor-level errors are benign false positives:

- ben-01 (cmd.exe, 2/3 cells)
- ben-02 (cmd.exe, 3/3 cells)
- ben-03 (WINWORD.EXE, 3/3 cells)
- ben-08 (firefox.exe, 1/2 judged cells; one run truncated)

**Rule used below:** 3/3 judged cells wrong = failure mode; 1/3 = instability. Do not sum those into one “miss count.”

Malicious single-run `standard_review` flips (mal-07, mal-09, mal-11 — one cell each) are reported only under **§6 Stability**, not as malicious misses.

---

## 4. Hypothesis (not finding) — seed-identity clustering

Seed basename from manifest rationale `image=` (Security 4688 NewProcessName). Malicious seeds are uniformly `payload.exe` (13/13).

**Path A benign FP structure:**

| Bucket | Anchors | Pattern |
|---|---|---|
| Consistent failure (3/3) | ben-02 (cmd.exe), ben-03 (WINWORD.EXE) | failure mode |
| Near-consistent (2/3) | ben-01 (cmd.exe) | failure mode |
| Single-run flip (1/3 or 1/2) | ben-06 (wmpnscfg), ben-08/11 (firefox), ben-13 (EXCEL) | instability |

**Path B benign FP structure (25 FP cells / 38 judged):**

| Bucket | Anchors |
|---|---|
| Consistent (3/3) | ben-01, ben-02 (cmd.exe); ben-03 (WINWORD); ben-10 (EXCEL) |
| Majority-wrong (2/3) | ben-04 (explorer); ben-07/09/12 (firefox); ben-13 (EXCEL) |
| Single-run (1/3 or 1/2) | ben-06 (wmpnscfg); ben-08/11 (firefox) |

Path B’s specificity collapse is **broad-and-noisy** (12/26 Path B anchors unstable), not a single-seed story — but cmd.exe and WINWORD remain fully consistent failures on both paths.

**Lead hypothesis for follow-on:** the discriminator may be reacting to process-create / window surface features correlated with seed identity (cmd / Office) rather than attack behavior, which would also explain Path A’s redundancy with fact-count. n is small (two consistent Path A failure-mode seeds). State as hypothesis, not finding. Malicious seeds do not share those basenames (`payload.exe` only).

---

## 5. Stability caveat

Temperature pinned at **1.0**; 3 runs per (anchor, path).

| Path | Unstable anchors | IDs |
|---|---:|---|
| correlation (A) | **8/26** | ben-01, ben-06, ben-08, ben-11, ben-13; mal-07, mal-09, mal-11 |
| flattened (B) | **12/26** | ben-04, ben-06, ben-07, ben-08, ben-09, ben-11, ben-12, ben-13; mal-02, mal-07, mal-09, mal-12 |

Path B flips disposition on nearly half its anchors. **Anchor-majority and McNemar are the valid units**; cell-level rates overstate precision. The three malicious single-cell “misses” on Path A are exactly the three unstable malicious anchors — T=1.0 sampling noise on otherwise majority-correct anchors.

---

## 6. Scope limitation (required)

This spike measured judgment over **raw telemetry windows** at a **synthetic 50/50** malicious/benign base rate. Praetor’s production input is `AlertEnvelope`: something upstream already fired, so the real population carries a **high malicious prior** and consists of **detector alerts**, not arbitrary host activity. Path A’s benign FP rate may be reasonable calibration against that population rather than a product defect.

The **A-vs-B delta is unaffected** — both paths saw identical anchors, so the base-rate construction error cancels. Every **absolute** rate above is conditional on a distribution that does not ship.

**Follow-on population:** ATLASv2 ships `cbc-edr-alerts` / `cbc-ngav-alerts` (232 alerts on the h1 benign capture alone) as the in-distribution AlertEnvelope-shaped population for a follow-on spike.

---

## Headline rates (post-refill)

| Path | Cell separation | Anchor majority |
|---|---:|---:|
| correlation | 80.52% (62/77) | 84.62% (22/26) |
| flattened | 61.04% (47/77) | 57.69% (15/26) |

Trivial stump baselines (both features): **76.92% (20/26)** — not the same 20 anchors (16 shared right, 4 exclusive each way); two costumes for nearby heuristics, not two independent baselines cleared.

Citation-mix Path B concentration on {1, 4624}: **37.69%** → `tie_interpretation=not_a_tie`.

Remaining errors after refill: 2× `ProviderOutputTruncatedError` (ben-08 correlation r2; ben-08 flattened r0).

---

## Provenance (pre-registration and mid-flight)

A negative result is only as credible as its pre-registration.

| Pin | Status |
|---|---|
| Labels frozen before first provider call | Manifest committed; no post-hoc relabel |
| A≈B epsilon = 0.05; Path-A-citation concentration threshold = 0.80 | Fixed in `evals/capability/score.py` before live run |
| Extras-budget ladder criterion | Pre-registered in design amendment; ladder **not** run (ben-06 probe passed at 256) |
| Confound features + graded warn ≥ 0.90 | Wired before scoring; no WARN fired |
| Pre-refill results preserved | `atlasv2_capability_spike_results.prerefill.jsonl` |
| Provider config vs production | Spike-local: `responseSchema=ModelJudgment`, `maxOutputTokens=16384`, `thinkingBudget=0`, **temperature=1.0** pinned; Vertex ADC on `gdg-yorku`, model `gemini-2.5-flash` |

**Mid-flight bug fix (legitimate refill, not exclusion):** Path B `normalized_fields` carried Windows EventData timestamps with seven fractional digits (`NewTime` / `PreviousTime`). Canonical serialization requires exactly six. Fixed in `evals/capability/flatten.py` only; the 18 `CanonicalSerializationError` cells were dropped from the JSONL and re-run. Refill moved Path B cell separation from **66.67% → 61.04%** — against the more favorable reading. That direction is evidence against post-hoc cherry-picking.

Production bugs surfaced here are filed out of band (not solved in this spike): see DEC-067 and `memory-bank/tasks.md` § Production follow-ups from capability spike.

---

## What this does / does not authorize

| Does | Does not |
|---|---|
| Defend “do not expand normalizers on this evidence” | Claim judgment is useless in production AlertEnvelope traffic |
| Defend “capability above fact-count stump not shown on Path A” | Authorize shrinking Path B or changing prompts from scored dispositions |
| Justify a follow-on spike on CBC alert population | Promote the flattener or change DEC-066 floors |
