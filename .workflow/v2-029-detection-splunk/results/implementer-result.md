# Implementer Result — V2-029 Detection and Splunk Demo Durability

**Status:** Complete (queue not marked done per packet)

## Acceptance criteria

| AC | Status | Evidence |
|---|---|---|
| Sigma matcher set equals SPL matcher set per rule over manifest fixtures | **PASS** | `test_sigma_spl_matcher_sets_equal_per_rule` compares `_event_matches_rule` vs `matching_record_ids` for every Sigma rule |
| Splunk saved searches use fixture-stable time window or docs require explicit override | **PASS** | `compile_sigma.py` post-processes `[default]` dispatch to `2026-06-08T00:00:00`–`2026-06-08T23:59:59`; `test_savedsearches_use_fixture_stable_dispatch_window`; `splunk/README.md` documents override when timestamps differ |
| Live Splunk Free demo test env-gated and executable when HEC settings exist | **PASS** | `test_splunk_demo_integration_with_hec_env` skips without `PRAETOR_SPLUNK_HEC_HOST`/`PRAETOR_SPLUNK_HEC_TOKEN`; when set, ingests via HEC and validates SPL match sets via management API |
| `tools/` in mypy gate or exclusion documented | **PASS** | `docs/eval_gates.md` Phase 4 section documents `pyproject.toml` `exclude = ['^tools/']` rationale and advisory mypy command |

## Files changed

| File | Rationale |
|---|---|
| `tools/compile_sigma.py` | Post-process pySigma `savedsearches.conf` output to fixture-stable dispatch window constants |
| `splunk/savedsearches.conf` | Regenerated via `compile_sigma.py --write` with absolute `2026-06-08` bounds |
| `tests/splunk/test_savedsearch_generation.py` | Sigma↔SPL equivalence pin, dispatch-window test, env-gated live HEC integration |
| `splunk/README.md` | Document fixture-stable default window, mgmt-token override, integration test behavior |
| `docs/eval_gates.md` | Document `tools/` mypy exclusion; update Phase 4/5 Splunk gate wording |

## Verification commands

```text
python -m pytest tests/detections/ tests/splunk/ -q
→ 41 passed, 1 deselected in 4.68s

python tools/compile_sigma.py --check
→ exit 0
```

## Unresolved / operator notes

- Live integration test (`@pytest.mark.integration`) is deselected in default CI (`addopts` excludes integration). Requires Windows PowerShell, running Splunk with HEC enabled, and optionally `PRAETOR_SPLUNK_MGMT_TOKEN` when HEC token cannot query port 8089.
- Queue entry intentionally **not** marked done per implementer packet.
