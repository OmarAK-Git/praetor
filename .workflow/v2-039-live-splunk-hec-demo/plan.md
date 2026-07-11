# Plan — V2-039 Live Splunk HEC Demo

**Tier:** T2  
**Goal:** V2-039 — Live Splunk Free HEC demo end-to-end (T11): env-gated integration test passes once against a live Splunk instance; five saved searches return expected record_ids; README/runbook reconciled for HEC/cert/props.conf.

## Stop condition

If `PRAETOR_SPLUNK_HEC_HOST` / `PRAETOR_SPLUNK_HEC_TOKEN` are unset, set queue item `human_needed` and list exact env vars — do not claim done.
