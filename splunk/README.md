# Splunk Free demo (TASK-033)

Reproduce Praetor detection portability on Splunk Free using committed OTRF-style fixtures and Sigma-compiled saved searches.

## Prerequisites

- Splunk Free 9.x (local install).
- PowerShell 5.1+ (Windows) for ingest validation/script.
- Python dev env: `pip install -e ".[dev]"` (includes `pysigma` + `pysigma-backend-splunk`).

## 1. Compile or verify SPL

```powershell
python tools/compile_sigma.py --check
```

Regenerate committed artifacts after Sigma rule edits:

```powershell
python tools/compile_sigma.py --write
```

Outputs:

- `detections/spl/*.spl` — plain SPL per rule
- `splunk/savedsearches.conf` — saved search stanzas

## 2. Validate fixtures

```powershell
powershell -ExecutionPolicy Bypass -File tools/splunk_ingest_demo.ps1 -ValidateOnly
```

Checks every path and `sha256` in `tests/fixtures/fixture_manifest.yaml`.

## 3. Install Splunk configuration

Copy into your Splunk instance (adjust `$SPLUNK_HOME`):

```powershell
copy splunk\props.conf "$env:SPLUNK_HOME\etc\apps\praetor_demo\local\props.conf"
copy splunk\savedsearches.conf "$env:SPLUNK_HOME\etc\apps\praetor_demo\local\savedsearches.conf"
```

Create the app folder if needed and restart Splunk.

`props.conf` applies to file/monitor ingest with `source::WinEventLog:...`. The bundled HEC ingest script (step 4) posts `sourcetype=_json` directly; field flattening is handled in Python (`tools/fixture_events.py`) before send.

## 4. Ingest committed fixtures

With HTTP Event Collector (HEC) enabled on index `main`:

```powershell
powershell -ExecutionPolicy Bypass -File tools/splunk_ingest_demo.ps1 `
  -SplunkHost "https://localhost:8088" `
  -HecToken "<your-hec-token>" `
  -Index main
```

The script:

1. Re-validates fixture checksums.
2. Flattens `EventData` fields to top-level keys.
3. Sets `source` to WinEventLog values expected by compiled searches (`EventCode` from `EventID`).

## 5. Run saved searches

In Splunk Search (time range covering fixture timestamps, e.g. `2026-06-08`):

| Saved search | Expected matching `record_id`(s) |
|---|---|
| `Suspicious PowerShell Encoded Command` | `1002` only |
| `Windows Command Shell Execution` | `1001`, `1005`, `1006` |
| `Successful Security Logon (4624)` | `2001` only |
| `Calculator Process Creation` | `9999` only |
| `Notepad Process Creation` | `1003`, `1004` |

Discrimination spot-checks: encoded PowerShell must not match `1001`; 4624 must not match Sysmon records; calc must not match `1001`/`1002`/`1003`.

## Troubleshooting

- **Zero results:** confirm `source` and `EventCode` fields on ingested events (`source="WinEventLog:..."`).
- **Checksum failure:** restore fixture from git; do not ingest tampered files.
- **SPL drift:** run `python tools/compile_sigma.py --write` and recommit, or fix Sigma rules.

## CI scope

Default pytest excludes live Splunk integration (`@pytest.mark.integration`). Compile + manifest validation run in CI.

### Optional live Splunk demo (Phase 5)

Enable HEC on Splunk Free (`Settings → Data inputs → HTTP Event Collector`). For self-signed TLS on localhost, use your Splunk admin cert trust settings or `-SkipCertificateCheck` in custom scripts.

Set environment variables before running the env-gated integration marker:

```powershell
$env:PRAETOR_SPLUNK_HEC_HOST = "https://localhost:8088"
$env:PRAETOR_SPLUNK_HEC_TOKEN = "<hec-token>"
pytest -m integration tests/splunk/test_savedsearch_generation.py::test_splunk_demo_integration_with_hec_env
```

Ingest uses `sourcetype=_json` with flattened `EventData` fields (`tools/splunk_ingest_demo.ps1`); `props.conf` applies to file/monitor ingest with `source::WinEventLog:...` — see step 3 above.
