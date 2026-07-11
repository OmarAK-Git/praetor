# Verifier Packet — V2-039 Live Splunk HEC Demo

**verification_model:** claude-opus-4-8-thinking-high
**readonly:** true

## Original goal

V2-039 — Live Splunk Free HEC demo end-to-end (T11): env-gated integration test passes once against a live Splunk instance; five saved searches return expected record_ids; README/runbook reconciled for HEC/cert/props.conf.

## Acceptance criteria

1. With HEC env set: pytest integration test for live Splunk demo passes.
2. Without HEC env: would be human_needed — not applicable (live pass claimed).
3. splunk/README.md documents HEC enablement / mgmt auth / props vs _json.
4. delivery_backlog T11 Closed only after real live pass.

## Implementer result

`.workflow/v2-039-live-splunk-hec-demo/results/implementer-result.md`

## Instructions

- Re-run non-integration splunk tests (do not require live HEC for verifier if env absent — but inspect code fixes and implementer live evidence).
- If HEC env is present in the environment, optionally re-run the integration test; otherwise accept implementer's verbatim `1 passed in 21.55s` only after confirming the code path changes make that result plausible (POST body, time format, login helper).
- Confirm T11 is Closed (V2-039) in delivery_backlog.
- Confirm session key / debug credential files are not left in the repo.
- Write `.workflow/v2-039-live-splunk-hec-demo/results/verifier-result.md`.
- Do not update the queue.
