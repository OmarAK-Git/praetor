# Judgment capability spike — design

**Date:** 2026-08-01
**Status:** approved for planning
**Scope:** measurement only — no changes to `src/praetor/`
**Relates to:** `evals/harness.py` (33 mandatory scenarios), `evals/real_provider_adversarial.py` (DEC-047 probe)

## Goal

Answer one question with evidence: **does Praetor's judgment layer distinguish malicious from benign telemetry at all?**

Nothing else. Not accuracy targets, not ambiguity handling, not gate calibration, not CI integration.

## Why this does not exist today

Every current eval stipulates the model's answer.

- `evals/scenarios/*.yaml` set `proposed_disposition:` in `setup:` — e.g. `confirmed_malicious_sequence.yaml` sets `auto_contain`.
- `FakeProvider._judgment_with_refs` returns `skeleton_model_judgment(proposed=self.proposed_disposition)`.

The 33 mandatory scenarios therefore measure **authorization**: given a stipulated judgment, does PolicyGate do the right thing? That is the correct test for the deterministic layer and it must stay exactly as it is.

The only live-model surface, `evals/real_provider_adversarial.py`, is explicitly non-gating and tests injection survival. It has no notion of a correct answer.

**Consequence: there is no ground truth anywhere in the repository.** Every expectation is "given X, the pipeline does Y", never "given this alert, the right call was Z". Judgment quality has never been measured.

## Scoring decision: model layer only

Score `ModelJudgment.proposed_disposition` against the label. Do **not** fold PolicyGate behavior into the capability number.

Rationale (user-ratified): the gate controls *authority*, not *judgment quality*. Gate-vs-model divergence is already instrumented — `build_progressive_authorization_report` computes `policy_gate_override_rate` per `(target_type, asset_class)` from `policy_gate_evaluations`, and those rows are written during normal intake, so a spike run populates that scoreboard for free.

**Refinement:** that report groups only by `target_type` and `asset_class`. It shows *how often* the gate disagreed, not *whether it disagreed on alerts where the model was right*. A gate overriding mostly-correct judgments is miscalibrated; one overriding mostly-wrong judgments is earning its keep. So the spike records each alert's `final_disposition` and `fault_flags` alongside the scored judgment in its own artifact. Recorded, not scored. No production code changes.

## Verified ground truth about the intake path

Confirmed by reading source, not assumed:

| Fact | Location |
|---|---|
| `AlertEnvelope` carries only `schema_version` + `alert_identity` — **no evidence payload** | `src/praetor/contracts/alert.py` |
| Evidence reaches the model via `sysmon_events` / `security_events` → correlation → `EvidenceBundle` | `src/praetor/engine/orchestrator.py:266-268` |
| `correlate_telemetry` windows internally at `anchor ± 300s` | `src/praetor/correlation/window.py:11` |
| Empty bundle → `correlation_failed`, judgment never runs | `src/praetor/engine/orchestrator.py:130-131` |
| **Only Sysmon EventID 1 (process create) is supported** | `correlation/sysmon.py:23` |
| **Only Security EventID 4624 (successful logon) is supported** | `correlation/security_log.py:19` |
| `event_field()` resolves `@timestamp`/`UtcTime`/`TimeCreated`, nested `EventData`, `EventRecordID` | `correlation/_event_fields.py` |

Two implications drive the design:

1. **Importing `AlertEnvelope`s alone is impossible as an eval.** An envelope is a pointer, not a payload; the model would receive an empty bundle. The corpus unit is `(alert_identity, anchor_time, sysmon_events[], security_events[], label)`.
2. **No detection step is needed.** `process_alert_intake` takes raw event dicts directly. No Sigma rules, no SPL, no Splunk. Correlation performs its own windowing, so **correlation selection is itself under test** — if it drags in noise or misses the pivotal event, judgment degrades and the score catches it.

The OTRF/Mordor JSON shape matches what `event_field()` already parses, so normalization should be near-free. Verify rather than assume.

## Corpus

**One OTRF capture**, selected by verifying it contains both a documented attack window and non-attack activity on the same hosts.

- **15 malicious anchors** — timestamps of events tied to the capture's documented technique.
- **15 benign anchors** — drawn from *the same file, same hosts, outside the attack window*.

### The source confound, and why same-capture sourcing is mandatory

If malicious came from OTRF and benign from a different capture, the model could score well by keying on hostnames, agent versions, timestamp formats, or field presence — anything separating the two corpora other than maliciousness. The result would look excellent and mean nothing.

Same-capture sourcing eliminates this by construction: same environment, same schema, same collection agent, differing only in what happened.

**Known limitation to state in results, not to fix:** lab environments are quiet, so "benign" here is thinner and cleaner than real enterprise activity. Verify actual benign event density in the chosen capture before committing to it.

### Technique selection constraint

Because correlation supports only process-create and logon events, anchors must be chosen from techniques that **manifest in process creation or logon** — command and scripting interpreters, process-based credential access, lateral movement producing 4624. Techniques expressed through network connections, registry, file creation, image load, or WMI events will produce empty or near-empty bundles and are out of scope for this spike.

This bound is itself a finding: judgment capability is capped by correlation coverage.

**If the chosen capture cannot yield 15 usable malicious anchors,** keep the classes balanced and reduce both sides together rather than padding one. Report the achieved count. A balanced 8+8 is interpretable; an unbalanced 15+6 is not. Do not add a second capture to make up the shortfall — that reintroduces the source confound.

### Labels

Each anchor: `(anchor_id, anchor_time, expected_class, rationale)`.

`expected_class` is binary — `malicious` or `benign`. Binary separation deliberately sidesteps escalate-vs-auto_contain labeling arguments, which do not matter until signal is established.

**Labels are authored from the capture's documented technique ground truth and committed before the first provider call.** Labeling after seeing engine output produces a tautology.

## Harness

New file `evals/capability_spike.py`, deliberately separate from `evals/harness.py` so it can never contaminate the gating suite.

Per anchor:

1. Normalize capture events into the shapes `correlation/sysmon.py` and `correlation/security_log.py` expect.
2. Call `process_alert_intake(..., sysmon_events=…, security_events=…, anchor_time=…, judgment_provider=VertexProvider(...))`.
3. Record `proposed_disposition`, `cited_evidence_refs`, citation resolution, bundle fact count, `final_disposition`, `fault_flags`.

**Three runs per anchor.** Run-to-run variance is itself a finding, and 90 Gemini calls is negligible cost.

## Scoring — deliberately crude

**Primary:** does `proposed_disposition` separate the classes?

- malicious → `escalate` or `auto_contain`
- benign → `standard_review`

**Secondary:** citation resolution rate; stability across the three runs.

**Recorded but not scored:** `final_disposition`, `fault_flags`.

## Three guards against fooling yourself

1. **Labels committed before the first run.**
2. **Confound check** — verify a trivial heuristic (hostname, event count, field presence) *cannot* separate the classes. If it can, the corpus is contaminated.
3. **Empty-bundle exclusion** — any anchor where correlation returns zero facts is excluded from the judgment score and reported separately. That is a correlation finding wearing a judgment costume.

## Output

A JSONL artifact plus a summary table read by eye. No gate, no threshold, no pass/fail.

## Explicitly out of scope

Ambiguity tier · CI gating · pass/fail thresholds · formal scoring rubric · Sigma rule authoring · changes to `src/praetor/` · changes to the 33 mandatory scenarios.

All of these are worth building only if the spike returns signal.

## Success criterion

The spike succeeds if it produces a defensible answer to "has judgment earned anything at all" — **including if that answer is no.** A clean negative is a successful spike.
