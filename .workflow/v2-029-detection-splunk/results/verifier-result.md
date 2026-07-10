# Verifier Result — V2-029 Detection and Splunk Demo Durability

**Verdict:** SURVIVES (task-scoped acceptance verified)
**Scope:** V2-029 acceptance criteria only. V2 Gate 4 exit NOT assessed (per packet + queue).
**Verifier:** skeptic-verifier (fresh context, did not produce the work)

## Claim under test

Implementer claims V2-029 complete: Sigma↔SPL matcher parity pinned, Splunk saved
searches use a fixture-stable dispatch window, live Splunk Free demo test is env-gated,
and `tools/` mypy exclusion is documented. Claimed evidence: `41 passed, 1 deselected`.

## Fresh verification command

```text
python -m pytest tests/detections/ tests/splunk/ -q
→ 41 passed, 1 deselected in 4.58s   (exit 0)

python -m pytest tests/detections/ tests/splunk/ -rs
→ 42 collected / 1 deselected / 41 selected; 41 passed, 1 deselected, 0 skipped
```

Reproduced the implementer's exact count independently. No hidden skips masking
failures; the single deselected item is the env-gated `@pytest.mark.integration`
live demo test (see AC3). All Windows-only PowerShell ingest tests ran and passed
on this win32 host.

## Acceptance criteria — adversarial review

| AC | Verdict | Evidence gathered |
|---|---|---|
| Sigma matcher set == SPL matcher set per rule over manifest fixtures | **PASS** | `test_sigma_spl_matcher_sets_equal_per_rule` (`tests/splunk/test_savedsearch_generation.py:188`) compares the Sigma-side `_event_matches_rule` (imported from `tests/detections/test_sigma_rules.py`) against the SPL-side `matching_record_ids` (`tools/spl_match.py:102`) for every loaded rule. Confirmed the two matchers are **genuinely independent** implementations: `spl_match.py` is a standalone regex-based SPL predicate parser/evaluator, not a wrapper over the Sigma evaluator. |
| — non-vacuous check | **PASS** | Guarded against vacuous equality: `test_committed_spl_semantic_match_and_discrimination` pins non-empty expected match sets per SPL (e.g. `powershell→{1002}`, `cmd→{1001,1005,1006}`); `test_each_fixture_event_matches_at_least_one_rule` and `test_sigma_rule_discrimination` enforce non-empty matches; `test_sigma_rules_parse_without_errors` asserts ≥5 rules. The equivalence therefore compares non-empty, discriminating sets, not empty==empty. |
| Splunk saved searches use fixture-stable window or documented override | **PASS** | `splunk/savedsearches.conf:1-3` `[default]` pins `dispatch.earliest_time = 2026-06-08T00:00:00` / `dispatch.latest_time = 2026-06-08T23:59:59`, matching `FIXTURE_DISPATCH_EARLIEST`/`FIXTURE_DISPATCH_LATEST` (`tools/compile_sigma.py:27-28`). `test_savedsearches_use_fixture_stable_dispatch_window` asserts both constants present and that `-30d` / `dispatch.latest_time = now` are absent. |
| Live Splunk Free demo test env-gated and executable when HEC settings exist | **PASS** | `test_splunk_demo_integration_with_hec_env` (`:423`) is `@pytest.mark.integration`, skips without `PRAETOR_SPLUNK_HEC_HOST`/`PRAETOR_SPLUNK_HEC_TOKEN`, and is deselected by default `addopts`. When env is set it ingests fixtures via the PowerShell HEC script and validates SPL match sets via the Splunk management API (`services/search/jobs/export`) with Bearer/Splunk auth fallback. Executable path is present and coherent (not stubbed). |
| `tools/` in mypy gate or exclusion documented | **PASS** | `pyproject.toml:47-49` `[tool.mypy] exclude` includes `'^tools/'`; `docs/eval_gates.md:100-102` documents the exclusion, its rationale (operator/demo scripting, pySigma untyped noise), that ruff still lints `tools/**`, and the advisory explicit-typecheck command. |

## Refutation attempts that failed to refute

- **Vacuous parity**: attempted — refuted by non-empty pinned expectation tests above.
- **Matcher self-comparison**: attempted — `spl_match.py` read in full; it is an independent SPL parser, so parity is a real cross-implementation check, not a tautology.
- **Stale evidence**: re-ran the suite from a fresh process; count reproduced (41 passed, 1 deselected, 0 skipped).
- **Hidden skips hiding failures**: `-rs` run shows 0 skipped; only 1 deselected (the intended integration gate).
- **AC4 unverifiable by test command**: AC4 is a documentation/config requirement, correctly satisfied outside the pytest command by `pyproject.toml` + `docs/eval_gates.md`, both confirmed by direct read.

## Notes / boundaries

- Live HEC integration path was not executed (no Splunk instance / env vars); AC3 requires env-gated + executable structure, which is satisfied. Live behavior is out of scope for a deterministic task-scoped run.
- Per packet and queue: queue entry left as-is; this verifier does NOT mark V2-029 done and does NOT assess V2 Gate 4 exit.
