# Verifier Result — V2-039 Live Splunk HEC Demo

**verification_model:** claude-opus-4-8-thinking-high
**readonly:** true (only this file written)
**Date:** 2026-07-10
**Verdict:** PASS (conditional live acceptance — see caveat)

## Claim under test

Implementer claims T11 is done: env-gated integration test passed once live
(`1 passed in 21.55s`), non-integration regression `23 passed, 1 deselected`,
code fixes to ingest PS + integration test, README reconciled, backlog T11
Closed. Treated as unevidenced until independently checked.

## Evidence gathered

### 1. Non-integration regression (re-run by verifier)

```
python -m pytest tests/splunk/test_savedsearch_generation.py -q -m "not integration"
.......................
23 passed, 1 deselected in 4.39s
```

Matches the implementer's `23 passed, 1 deselected` claim. ✓

### 2. Code-fix inspection (make live pass plausible)

- **Ingest PS (`tools/splunk_ingest_demo.ps1`):** `ConvertTo-SplunkEvent`
  accepts `[object]$Event`, re-serializes, flattens via Python, returns
  `ConvertFrom-Json` (PSCustomObject). `Send-SplunkEvents` reads
  `$splunkEvent.'@timestamp'` (property access) and posts to
  `/services/collector/event` with `Splunk $Token` auth. ✓ (matches claim)
- **POST body for search (`test`:512-522):** `_run_oneshot_search` form-encodes
  `search`/`output_mode=json`/`exec_mode=oneshot` and POSTs to
  `/services/search/jobs/export`. ✓
- **Auth preference (`test`:526-535):** tries `Splunk <key>` before
  `Bearer <key>`. ✓
- **Login helper (`test`:424-445):** `_splunk_login_session_key` POSTs
  urlencoded user/password to `/services/auth/login`, parses `sessionKey`
  from XML. Used only when `PRAETOR_SPLUNK_USER`/`PASSWORD` set and no mgmt
  token. ✓
- **Time format (`test`:448-456):** `_splunk_time_bound` converts ISO
  `2026-06-08T00:00:00` → `06/08/2026:00:00:00` (and latest →
  `06/08/2026:23:59:59`); `FIXTURE_DISPATCH_*` confirmed ISO in
  `tools/compile_sigma.py:27-28`. Splunk `MM/DD/YYYY:HH:MM:SS` form correct. ✓
- **mgmt host default (`test`:474-478):** rewrites `:8088`→`:8089` and forces
  HTTPS when HEC is HTTP. ✓
- Integration test remains `@pytest.mark.integration` and skips without HEC
  env (`test`:459-468); not forced into default CI. ✓

All code paths are internally coherent and consistent with a real live pass.

### 3. Backlog T11 status

`docs/proposals/delivery_backlog.md:221` — status column reads
**`Closed (V2-039)` — live HEC ingest + SPL record_id assertions passed
2026-07-10**. Header note (line 6) also reflects closure. ✓

### 4. Leftover secret / debug files

`.session_key` and `_debug_time.py` (present as untracked at session start per
git snapshot) are **gone**:
- `Read` of both paths → `File not found`.
- Run-dir glob returns only `plan.md`, `packets/{implementer,verifier}.md`,
  `results/implementer-result.md`.
- `git status --porcelain` shows no `.session_key`/`_debug_time`/password
  artifacts.
Only `session_key`/`password` string hits in the run dir are env-var *names*
in `implementer-result.md` (documentation), not secret values. ✓

### 5. Secrets hygiene

Verifier checked HEC env presence only (not values): `HEC_HOST_set=False`,
`HEC_TOKEN_set=False`. No secrets printed. `implementer-result.md` records
"values not recorded" and recommends rotating the operator-pasted HEC token +
admin password — that recommendation stands.

## Caveat (honest limitation)

HEC env is **absent** in the verifier environment, so the live
`1 passed in 21.55s` could not be independently re-executed. Per verifier
packet instruction, the verbatim live result is accepted because the code-path
changes (POST body, auth order, time format, login helper, mgmt-host default)
are present and make that pass plausible, and the non-integration suite was
re-run green. This is conditional acceptance of the implementer's live
evidence, not an independent live re-verification.

## Queue

Not modified (per hard rules; `autopilot-queue.json` left untouched).

## Verdict: PASS
