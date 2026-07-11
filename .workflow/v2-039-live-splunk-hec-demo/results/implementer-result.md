# Implementer Result — V2-039 Live Splunk HEC Demo

**Task:** V2-039 / backlog T11  
**Status:** pass (live)  
**Date:** 2026-07-10

## Summary

Live Splunk Free HEC demo completed end-to-end. Env-gated integration test passed once against local Splunk with HEC ingest + management-API SPL verification.

## Live evidence (verbatim)

```
python -m pytest tests/splunk/test_savedsearch_generation.py::test_splunk_demo_integration_with_hec_env -q --override-ini="addopts="
.
1 passed in 21.55s
```

Non-integration regression: `23 passed, 1 deselected`.

## Fixes required for live path

| File | Change |
|------|--------|
| `tools/splunk_ingest_demo.ps1` | Accept `PSCustomObject` from `ConvertFrom-Json`; property access for `@timestamp` |
| `tests/splunk/test_savedsearch_generation.py` | POST form body for `/services/search/jobs/export`; prefer `Splunk` session auth; optional `PRAETOR_SPLUNK_USER`/`PASSWORD` login; convert fixture ISO times to Splunk `MM/DD/YYYY:HH:MM:SS`; default mgmt host to HTTPS when HEC is HTTP |
| `splunk/README.md` | Document HEC base URL, user/password mgmt auth, time-format note |
| `docs/proposals/delivery_backlog.md` | T11 → **Closed (V2-039)** |

## Env used (values not recorded)

- `PRAETOR_SPLUNK_HEC_HOST=http://localhost:8088`
- `PRAETOR_SPLUNK_HEC_TOKEN` (operator-supplied)
- `PRAETOR_SPLUNK_MGMT_HOST=https://localhost:8089`
- `PRAETOR_SPLUNK_USER` / `PRAETOR_SPLUNK_PASSWORD` (operator-supplied)

## Security

Operator pasted HEC token and admin password in chat — recommend rotating both after demo.

## Queue

Do not mark done from implementer; await verifier.
