# Judgment capability spike — design

**Date:** 2026-08-01
**Status:** approved for planning
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

**One OTRF capture**, verified to contain both a documented attack window and non-attack activity on the same hosts.

- **15 malicious anchors** — timestamps tied to the documented technique.
- **15 benign anchors** — from *the same file, same hosts, outside the attack window*.

### The source confound

If malicious came from OTRF and benign from a different capture, the model could score well by keying on hostnames, agent versions, timestamp formats, or field presence — anything separating the corpora other than maliciousness. Same-capture sourcing eliminates this by construction.

**Limitation to report, not fix:** lab environments are quiet, so "benign" here is thinner and cleaner than real enterprise activity. Verify benign event density before committing to a capture.

**If the capture cannot yield 15 usable malicious anchors,** shrink both sides together. A balanced 8+8 is interpretable; 15+6 is not. Do **not** add a second capture to make up a shortfall — that reintroduces the confound.

Path A is additionally bounded to techniques manifesting in process-create or logon. Path B has no such bound; anchors are chosen for Path B and Path A takes whatever subset it can see. **That asymmetry is the measurement, not a flaw.**

### Labels

Each anchor: `(anchor_id, anchor_time, expected_class, rationale)`. `expected_class` is binary — `malicious` or `benign` — which sidesteps escalate-vs-`auto_contain` labeling arguments that don't matter until signal is established.

**Labels are authored from the capture's documented technique ground truth and committed before the first provider call.** Labeling after seeing engine output produces a tautology.

## Harness

New file `evals/capability_spike.py`, separate from `evals/harness.py` so it can never contaminate the gating suite.

Per anchor, per path: call `process_alert_intake` with a real `VertexProvider` (reusing the key resolution in `real_provider_adversarial.py`), recording `proposed_disposition`, `cited_evidence_refs`, citation resolution, bundle fact count, `final_disposition`, `fault_flags`.

**Three runs per anchor per path.** Run-to-run variance is itself a finding; ~180 Gemini calls is negligible cost.

## Scoring — deliberately crude

**Primary:** does `proposed_disposition` separate the classes — malicious → `escalate`/`auto_contain`, benign → `standard_review`?

**Secondary:** citation resolution rate; stability across runs; the A/B delta.

**Recorded but not scored:** `final_disposition`, `fault_flags`.

## Three guards against fooling yourself

1. **Labels committed before the first run.**
2. **Confound check** — verify a trivial heuristic (hostname, event count, field presence) *cannot* separate the classes.
3. **Empty-bundle exclusion** — anchors where correlation returns zero facts are excluded from the judgment score and reported separately. That is a correlation finding wearing a judgment costume, and on Path A it will be common.

## Output

A JSONL artifact plus a summary table read by eye. No gate, no threshold, no pass/fail.

## Explicitly out of scope

Ambiguity tier · CI gating · pass/fail thresholds · formal scoring rubric · Sigma authoring · agentic judgment path · changes to `src/praetor/` · changes to the 33 mandatory scenarios · promoting the flattener to production · revisiting the DEC-066 corroboration floor.

## Success criterion

A defensible answer to "has judgment earned anything at all" — **including if that answer is no.** A clean negative is a successful spike.
