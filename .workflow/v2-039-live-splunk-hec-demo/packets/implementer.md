# Implementer Packet — V2-039 Live Splunk HEC Demo

**implementation_model:** composer-2.5-fast

## Objective

Run the live Splunk Free HEC demo end-to-end (backlog T11). Pass the env-gated integration test once. Reconcile README/runbook for HEC/cert/props.conf if gaps remain.

## Original goal

V2-039 — Live Splunk Free HEC demo end-to-end (T11): env-gated integration test passes once against a live Splunk instance; five saved searches return expected record_ids; README/runbook reconciled for HEC/cert/props.conf.

## Hard stop — human_needed

Before claiming any pass, check env:

- `PRAETOR_SPLUNK_HEC_HOST` (e.g. `https://localhost:8088`)
- `PRAETOR_SPLUNK_HEC_TOKEN`
- Optional: `PRAETOR_SPLUNK_HEC_INDEX` (default `main`)
- Optional: `PRAETOR_SPLUNK_MGMT_HOST` (default host with `:8089`)
- Optional: `PRAETOR_SPLUNK_MGMT_TOKEN` (if HEC token cannot query management API)

If HEC host/token missing: write implementer-result with `status: human_needed`, list exact vars + Splunk Free setup steps from `splunk/README.md`, and **stop**. Do not mark done. Do not fake green.

## When env is present

1. Ensure Splunk app config installed per README (props + savedsearches) if needed for the test path.
2. Run: `pytest tests/splunk/test_savedsearch_generation.py -q -m integration` (or the specific `test_splunk_demo_integration_with_hec_env`).
3. Fix only minimal bugs blocking a real live pass (cert handling, auth fallback, README clarity) within files_allowed.
4. On pass: update `delivery_backlog.md` T11 → **Closed (V2-039)** with evidence note.
5. Capture verbatim pytest output in implementer-result.

## Allowed files (strict)

- tests/splunk/
- splunk/
- tools/splunk_ingest_demo.ps1
- tools/fixture_events.py
- tools/compile_sigma.py
- docs/operator_runbook.md
- docs/proposals/delivery_backlog.md
- docs/eval_gates.md
- memory-bank/tasks.md, progress.md, activeContext.md
- .workflow/v2-039-live-splunk-hec-demo/

## Do-not-touch

- Do not remove `@pytest.mark.integration` or force the test into default CI.
- Do not mark queue done.
- Do not install Splunk itself without approval_gates (external install).
- Do not invent a pass without live HEC evidence.

## Expected result

Write `.workflow/v2-039-live-splunk-hec-demo/results/implementer-result.md` with either:
- live pass evidence + files changed, or
- `human_needed` + env checklist
