# Judgment capability spike — design

**Date:** 2026-08-01
**Status:** complete (2026-08-03) — results: [`docs/superpowers/results/2026-08-02-judgment-capability-spike-results.md`](../results/2026-08-02-judgment-capability-spike-results.md); routing: [DEC-067](../../decisions.md#dec-067--capability-spike-routing-coverage-not-the-bottleneck-judgment-unmeasured-above-baseline)
**Scope:** measurement only — no changes to `src/praetor/`
**Judgment path under test:** single-shot GenAI wrapper only. The agentic path (`judgment/agentic/`) is explicitly out of scope.

## Goal

Answer one question with evidence: **does Praetor's judgment layer distinguish malicious from benign telemetry at all?**

Secondarily, and nearly free: **is the model being starved by correlation coverage rather than failing at judgment?**

## Why this does not exist today

Every current eval stipulates the model's answer.

- `evals/scenarios/*.yaml` set `proposed_disposition:` in `setup:` — e.g. `confirmed_malicious_sequence.yaml` sets `auto_contain`.
- `FakeProvider._judgment_with_refs` returns `skeleton_model_judgment(proposed=self.proposed_disposition)`.

The 33 mandatory scenarios therefore measure **authorization**: given a stipulated judgment, does PolicyGate do the right thing? That is the correct test for the deterministic layer and must stay exactly as it is.

`evals/real_provider_adversarial.py` is the only live-model surface. It is non-gating and tests injection survival, with no notion of a correct answer.

**Consequence: there is no ground truth anywhere in the repository.** Judgment quality has never been measured.

## Scoring decision: model layer only

Score `ModelJudgment.proposed_disposition` against the label. Do **not** fold PolicyGate behavior into the capability number.

The gate controls *authority*, not *judgment quality*. Gate-vs-model divergence is already instrumented: `build_progressive_authorization_report` computes `policy_gate_override_rate` per `(target_type, asset_class)` from `policy_gate_evaluations`, written during normal intake, so a spike run populates it for free.

**Refinement:** that report groups only by `target_type`/`asset_class`, so it shows *how often* the gate disagreed, not *whether it disagreed where the model was right*. The spike therefore records each alert's `final_disposition` and `fault_flags` in its own artifact. Recorded, not scored.

## Verified ground truth about the intake path

Confirmed by reading source:

| Fact | Location |
|---|---|
| `AlertEnvelope` carries only `schema_version` + `alert_identity` — **no evidence payload** | `contracts/alert.py` |
| Evidence reaches the model via `sysmon_events`/`security_events` → correlation → bundle, **or** via `evidence_bundle=` directly | `engine/orchestrator.py:265-268` |
| `correlate_telemetry` windows at `anchor ± 300s`, then filters to anchor host | `correlation/window.py:11`, `correlation/__init__.py:46-73` |
| Empty bundle → `correlation_failed`; judgment never runs | `engine/orchestrator.py:130-131` |
| Only Sysmon EventID 1 and Security 4624 are normalized; others silently skipped with a metric | `correlation/sysmon.py:23`, `correlation/security_log.py:19`, `correlation/__init__.py:76-86` |
| `event_field()` already resolves `@timestamp`/`UtcTime`/`TimeCreated`, nested `EventData`, `EventRecordID` | `correlation/_event_fields.py` |
| `EvidenceFact.provenance_path` is a bare `str` — no enum, no validation | `contracts/evidence.py:18` |
| `_build_prompt_fact` emits **one excerpt per `normalized_fields` key**, sorted, arbitrary key names | `judgment/excerpt.py:149-159` |

Two implications drive the design:

1. **The model needs no per-event-type schema.** Whatever lands in `normalized_fields` becomes model-visible text. Normalizers exist for the *deterministic* machinery — `host_id` for DEC-052 targeting, `provenance_path` for corroboration, `ambiguity_flag`, `entity_references` — not for the LLM.
2. **No detection step is needed.** `process_alert_intake` takes raw event dicts. No Sigma, no SPL, no Splunk.

## The two gates apply pressure at different levels

| Gate | Counts | Moved by |
|---|---|---|
| `meets_host_bundle_corroboration` (`provenance.py:76-88`) | distinct `provenance_path` **≥ 2** | more **sources** |
| `meets_host_cited_enrichment` (`provenance.py:91-108`) | distinct `source_event_reference` **≥ 2** | more **events** |

`source_event_reference` is `f"{channel_key}:{event_id}:{record_id}"` (`correlation/ids.py:17-19`), so two distinct EventID 1 records satisfy enrichment. Every Sysmon EventID collapses to one `sysmon_event_log` path, so per-EventID work does **nothing** for corroboration.

**Expected consequence for the spike:** with two sources implemented and a ≥2 floor, host `auto_contain` requires a process-create *and* a 4624 anchoring the same host inside ±300s. Many genuinely malicious anchors will fail corroboration and land on `escalate` regardless of judgment quality. This is expected. Read the gate column as "two sources isn't enough for containment authority," not "judgment failed." If the floor is later dropped to 1, this pressure largely disappears and the gate column becomes less informative — the judgment score is unaffected either way.

`is_attacker_controllable_provenance` (`provenance.py:28-34`) returns `True` for unrecognized paths, so new sources are conservatively classified and cannot silently weaken the gate.

## Design: two paths over one corpus

Same anchors, same labels, same model, same org config, same prompt structure. The only variable is what evidence reaches the bundle.

**Path B — primary.** Harness-built bundle via a generic flattener covering **all** event types. Rich evidence; correlation bypassed via `evidence_bundle=`.

**Path A — control.** Real `correlate_telemetry` via `sysmon_events`/`security_events`. Two event types. Quantifies what the current production path loses.

Everything downstream runs for real on both: prompt construction, provider call, citation validation, PolicyGate, ledger.

### What the delta measures

| | B right | B wrong |
|---|---|---|
| **A right** | Process-create + logon already sufficient. Coverage isn't the bottleneck. | Richer evidence *hurt* — dilution or truncation pressure. |
| **A wrong** | Model can judge; correlation never showed it enough. **Fix = coverage.** | Model can't judge even with full evidence. **Fix = prompt / config / model.** |

The bottom row is the point: both cells look identical in a single-path spike ("judgment is bad") but demand opposite responses. The delta routes the next engineering investment instead of guessing.

### Keeping the delta clean

The flattener MUST reuse `filter_events_in_window` and `filter_events_to_anchor_host` from the correlation module rather than reimplementing them. Otherwise part of the delta is windowing/host-filtering differences masquerading as coverage.

The flattener must stay dumb and mechanical — flatten event fields into `normalized_fields`, set `host_id`, derive `evidence_id` via `derive_evidence_id`, build `source_event_reference` via the existing helper, label `provenance_path` per source. No hand-tuned per-event-type extraction, or a good B result is measuring the flattener rather than Praetor.

Path B's flattener is deliberately a **prototype of a generic normalizer**. It lives in `evals/` and carries zero production risk. Promoting it into `src/` is a separate contracts-level decision, not this spike's job.

## Corpus

Two candidate captures. **Prefer ATLASv2** when local (`atlasv2/`, gitignored): multi-hour attack-day files with per-scenario Security `EventRecordID` groundtruth satisfy the same-file / same-host rule without pulling `data/benign/` (a different capture session). APT29 Day 1 remains an alternate for ancestry-based labeling.

### ATLASv2 (preferred when available)

Local tree: `atlasv2/` (ignored). Attack-day Security XML under `data/attack/h{1,2}/msft-security/` plus `groundtruth/h*_m*|h*_s*` EventRecordID lists. Sysmon has **no** ATLAS groundtruth files (GT can never contain Sysmon EID 1).

**Path A does not consume ground truth.** Runtime anchor is still `(anchor_id, anchor_time, expected_class, rationale)`. Optional manifest `seed_event_id` / `seed_channel` / `seed_event_record_id` exist only for Guard #2 confound features — never as Path A input. Both paths receive the same sysmon/security pools and the same `anchor_time`; `correlate_telemetry` windows ±300s on its own. Path A's empty-bundle rate is the measurement (Guard #3), not a labeling precondition. Do not join GT process paths to Sysmon to bias Path A upward — that shrinks the A/B delta the spike exists to measure.

- **Malicious anchors** — times of **distinct attack actions** evidenced by groundtruth rows (prefer post-exploit `payload.exe` process create/access, not merely `WINWORD.exe` open), not every GT EventRecordID. Same `msft-security-h*-*.xml`, same host. GT membership alone over-labels (handle-close storms on `_MEI*` DLLs) — same failure mode as APT29 window-membership.
- **Benign anchors** — *the same attack-day file and host*, times **outside** groundtruth activity. Seed on **non-GT Security 4688 ordinary app launches** (not 4624 SYSTEM logons) so seed EventID is class-neutral with malicious 4663/4688 seeds — otherwise Path A empty-bundle and corroboration track the label. Spread across the day with a mix of **pre- and post-attack-window** times (≥10m from same-file malicious anchors). Do **not** source scored benign from `data/benign/`.
- **Path B fact cap:** `PATH_B_MAX_FACTS = 64`, nearest-to-anchor first, **identical for every anchor**. Uncapped 4663-dense windows (~thousands of facts) would separate classes by bundle size / prompt budget.
- **`unresolved` / residue** — ATLAS has no plan-step ancestry. Keep the manifest field names; map semantics explicitly:
  - `emulation_steps_total = 10` (scenarios M-1..M-6, S-1..S-4)
  - `unchained_steps` = count of those scenarios with **no usable Path B anchor at all** (no distinct-action GT time that can seed a Path B malicious anchor). This is label quality (Guard #4), not Path A visibility. Zero GT→4624s does **not** make a scenario unchained.

**Label hygiene (required before freeze):** Spot-check chosen malicious times against `atlas_attack_descriptions/`. Spread benign `hour_utc` across each file's span so Guard #2's graded stump does not trip on attack-hour clustering.

### APT29 Day 1 (ancestry path)

OTRF APT29 Day 1 host (`datasets/compound/apt29/day1` → `apt29_evals_day1_manual.zip`). One host JSON capture; do not mix Day 1/Day 2 or host+network for malicious vs benign.

- **15 malicious anchors** — tied to **specific emulation-plan steps** via process ancestry (not whole-window membership). Window-membership over-labels ordinary in-window host noise.
- **15 benign anchors** — from *the same file, same hosts, outside those steps*.
- **`unresolved` anchors** — Day 1 steps that break the ancestry chain (injected/fileless; registry/network whose parent is a legitimate process). Forcing these into malicious inflates FPs; forcing into benign poisons anchors. Third label; **excluded from scoring**.

### The source confound

If malicious came from one capture tree and benign from another, the model could score well by keying on hostnames, agent versions, timestamp formats, or field presence — anything separating the corpora other than maliciousness. Same-file / same-host sourcing eliminates this by construction.

**Limitation to report, not fix (ceiling effect):** lab environments are quiet, so "benign" here is thinner and cleaner than real enterprise activity. A strong Path B score is a **floor test** (rules out gross failure), not proof of discrimination. Verify benign event density before committing to a capture.

**If the capture cannot yield 15 usable malicious anchors,** shrink both scored sides together. A balanced 8+8 is interpretable; 15+6 is not. Do **not** add a second capture to make up a shortfall — that reintroduces the confound. `unresolved` does not participate in the malicious/benign balance.

Path A is additionally bounded to techniques manifesting in process-create or logon. Path B has no such bound; anchors are chosen for Path B and Path A takes whatever subset it can see. **That asymmetry is the measurement, not a flaw.**

### Labels

Each anchor: `(anchor_id, anchor_time, expected_class, rationale)`.

`expected_class ∈ {malicious, benign, unresolved}`:

| Class | Scoring | Meaning |
|---|---|---|
| `malicious` | scored | GT / plan-step ancestry ties the seed to adversary activity |
| `benign` | scored | Same file + host, outside GT / chained steps |
| `unresolved` | **excluded** | Cannot chain without over- or under-labeling |

Manifest top-level (required for live manifests; always printed by the CLI):

- `emulation_steps_total` — APT29: Day 1 plan steps considered; ATLAS: `10` scenarios (M-1..M-6, S-1..S-4)
- `unchained_steps` — APT29: steps that could not be ancestry-labeled; ATLAS: scenarios with no usable Path B anchor (no distinct-action GT time)

**Always emit** `n_unresolved` and `unchained_step_share = unchained_steps / emulation_steps_total` in the summary — including on the happy path (small residue). If residue is large, that is a label-quality finding and caps how hard either path's score can be read.

**Labels are authored from the capture's documented technique ground truth and committed before the first provider call.** Labeling after seeing engine output produces a tautology.

## Harness

New file `evals/capability_spike.py`, separate from `evals/harness.py` so it can never contaminate the gating suite.

Per anchor, per path: call `process_alert_intake` with a real `VertexProvider` (reusing the key resolution in `real_provider_adversarial.py`), recording `proposed_disposition`, citation resolution, **resolved cited `evidence_id`s joined to EventID/Channel**, bundle fact count, `final_disposition`, `fault_flags`.

**Three runs per anchor per path.** Run-to-run variance is itself a finding; ~180 Gemini calls is negligible cost. `unresolved` anchors may be skipped for live provider calls or run and recorded without scoring — either is fine; they never enter the disposition score.

### Join key for citation-mix (required)

Persisting `evidence_id` alone is useless for the mix metric unless each bundle fact still carries **EventID and Channel** keyed by that same `evidence_id`.

- Path B flattener **must pin** `EventID` and `Channel` into `EvidenceFact.normalized_fields` (not text-only excerpts).
- `source_event_reference` (`channel:event_id:record_id`) is a fallback parse, not a substitute for the pin.
- Observation JSONL records `cited_event_ids: tuple[int, ...]` for resolved refs that successfully join.

If IDs validate for grounding but cannot be binned by event type, the A≈B disambiguation is broken.

## Scoring — deliberately crude

**Primary:** does `proposed_disposition` separate the **scored** classes — malicious → `escalate`/`auto_contain`, benign → `standard_review`? `unresolved` and empty-bundle observations are excluded and counted separately.

**Secondary:** citation resolution rate; stability across runs; the A/B delta; Path B citation-mix vs Path A event types.

**Recorded but not scored:** `final_disposition`, `fault_flags`.

### Reading an A≈B null result (pre-registered thresholds)

If Path A ≈ Path B, that is ambiguous between "coverage doesn't matter" and "the model never looked at the added events." Disambiguate with Path B citation mix — thresholds fixed **before** seeing a tie (no post-hoc rationalization):

| Constant | Value | Meaning |
|---|---|---|
| `AB_TIE_SEPARATION_EPSILON` | `0.05` | Absolute difference in separation rates ≤ ε counts as a tie (both sides must have `scored > 0`) |
| `PATH_A_VISIBLE_EVENT_IDS` | `{1, 4624}` | Event types Path A correlation can normalize |
| `PATH_A_CITATION_CONCENTRATION_THRESHOLD` | `0.80` | Share of Path B **resolved** cited EventIDs that are in `{1, 4624}` |

| Path B citation mix on a tie | Investment read |
|---|---|
| Concentration **> 0.80** on `{1, 4624}` | Coverage gap is not the constraint; prompt never pulled richer facts → **prompt / model first** |
| Concentration **≤ 0.80** (material non-1/4624 cites) | Model saw richer evidence and still tied → **coverage not the bottleneck**; do not expand normalizers on this signal |
| No joinable cited EventIDs | Do not route on the tie; report `citations_unavailable` |

Always print the concentration statistic and the tie interpretation (or `not_a_tie`) — including when scores diverge.

Grounding itself remains the existing `cited_evidence_refs` + `validate_evidence_citations` path (`citations_resolved` / `invalid_model_citation`). Do not rebuild a separate grounding harness.

## Three guards against fooling yourself

1. **Labels committed before the first run.**
2. **Confound check (wired into the CLI)** — before and after the live loop, report per-feature:
   - **perfect separation** (boolean): malicious and benign value sets disjoint
   - **graded separation** (float): majority-label-per-value stump accuracy — catches near-perfect separators (e.g. 95%) that the boolean misses
   - Warn when graded ≥ `CONFOUND_GRADED_WARN_THRESHOLD` (0.90) or perfect is True. Features: manifest `seed_event_id` / `seed_channel` (always), plus capture-derived `host_id`, `calendar_day`, `hour_utc`, `path_b_fact_count` when loaded. Never from model output.
3. **Empty-bundle exclusion** — anchors where correlation returns zero facts are excluded from the judgment score and reported separately. That is a correlation finding wearing a judgment costume, and on Path A it will be common.
4. **`unresolved` exclusion** — label-quality residue (APT29 ancestry failures; ATLAS scenarios with no usable Path B anchor); always report. Path A empty bundles are Guard #3 (`excluded_empty_bundle`), not this counter.
5. **Pre-registered A≈B citation-mix thresholds** — fixed before the live run.

## Output

A JSONL artifact plus a summary table read by eye. No gate, no threshold, no pass/fail.

## Explicitly out of scope

Ambiguity tier · CI gating · pass/fail thresholds · formal scoring rubric · Sigma authoring · agentic judgment path · changes to `src/praetor/` · changes to the mandatory harness scenarios · promoting the flattener to production · revisiting the DEC-066 corroboration floor · five-bundle context-sufficiency ablation (follow-on after Path B shows non-trivial signal) · rebuilding citation grounding (already in production intake).

## Amendment 2026-08-03 — Path B extras, spike provider, extras ladder

**Path B construction:** uncapped `{Sysmon EventID 1, Security 4624}` floor (so Path B ⊇ Path A by construction) plus a **constant** `PATH_B_EXTRAS_BUDGET = 256` stratified extras budget. `PATH_B_MAX_FACTS = 512` is a hard safety ceiling that must not bind. Fill-to-ceiling is forbidden — it makes the extras increment anti-correlated with Path A density.

**Spike-local provider** (`evals/capability/spike_vertex_provider.py`, not `src/`): Vertex ADC with `responseSchema=ModelJudgment`, `maxOutputTokens=16384`, `thinkingConfig.thinkingBudget=0`. Non-refusal terminal `finishReason` values (`MAX_TOKENS` / `LENGTH`) are explicit run failures (`output_truncated`), never collapsed into a JSON parse error. Production `vertex_provider.py` still has that bug — file separately.

### Pre-registered extras-budget ladder (infrastructure only)

Run **only if** the primary re-probe at extras=256 on ben-06 fails after the spike-local provider fix.

Rungs: `16, 32, 64, 128, 256`.

Per rung, probe **one malicious and one benign** densest-available Path B anchor at that extras budget (fixed anchors chosen before seeing results: densest malicious and densest benign by Path A fact count from the latest `--bundles-only` report — currently mal-12 and ben-06).

**Selection criterion (fixed before any ladder call):**

> Primary extras budget = the **largest** rung where **all** probes at that rung return a parseable `ModelJudgment` with **≥ 2** resolving citations (`validate_evidence_citations` resolved count).

Rationale for ≥2: DEC-066 enrichment requires ≥2 distinct `source_event_reference` values among target-anchoring cited facts; a budget that systematically returns only one citation starves that gate.

This criterion is infrastructure (parseability + citation resolution), never separation rate. Choosing a budget after seeing which level yields nicer A/B deltas is forbidden.

## Success criterion

A defensible answer to "has judgment earned anything at all" — **including if that answer is no.** A clean negative is a successful spike.
