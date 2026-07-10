# Verifier Result — V2-027 Org-Config Sweep CLI

**Verdict:** `survives` (task-scoped)

**Scope:** V2-027 only. Verification command `pytest tests/codification/ -q` re-run independently.

## Claim restated

The org-config sweep CLI (1) writes a proposed YAML artifact + markdown report and exits non-zero on invalid inputs, (2) produces artifacts that fail activation preflight, and (3) is documented as not inferring never-contain / subnet / containment policy.

## Independent evidence

### Verification command (re-run, not trusted from transcript)

```
python -m pytest tests/codification/ -q
.........................
25 passed in 3.01s   (exit 0, 0 skipped)
```

Confirms the implementer's reported "25 passed". No skips, so the new tests actually execute.

### AC1 — CLI writes YAML+report, non-zero on invalid

- Write path: `src/praetor/codification/cli.py:106-128` (`run_sweep_cli`) renders YAML + report and writes both files; test `test_sweep_cli_writes_yaml_and_report` (`tests/codification/test_sweep_cli.py:44-72`) asserts both files exist and parses YAML/report content via a real subprocess (`python -m praetor.codification`).
- Non-zero path: `main` returns 1 on `SweepInputError` (`cli.py:142-145`); argparse errors (missing required `--org-id`/`--output-*`) exit 2 uncaught. Five subprocess tests cover missing/blank org-id, missing telemetry file, invalid JSON, and malformed fixture shape (`test_sweep_cli.py:101-187`), each asserting `returncode != 0` **and** a matching stderr message — not just a non-zero code.

### AC2 — Proposed artifacts fail preflight (not gamed)

- Rejection is genuine, not a weakened fixture: `run_preflight` calls `_reject_proposed_sweep_artifact` first (`src/praetor/config/preflight.py:143,361-366`), which raises `proposed_artifact_not_activatable` whenever `is_proposed_org_config_artifact` is true.
- That predicate keys on `version_metadata.artifact_kind == "proposed_org_config"` (`placeholders.py:16-21`, constant `models.py:9`), and the CLI's builder always stamps that kind on both the evidence and zero-evidence artifacts (`sweep.py:121,175`).
- `test_sweep_cli_output_fails_preflight` (`test_sweep_cli.py:75-98`) feeds the CLI-generated YAML into the **real** `run_preflight` and asserts the error code equals `proposed_artifact_not_activatable`. This exercises the actual production preflight, not a stub. Defense-in-depth placeholder sentinels (`UNOBSERVED-REQUIRES-HUMAN-REVIEW`, `REPLACE-BEFORE-ACTIVATION`) provide a second rejection path (`preflight.py:369-376`).

### AC3 — Docs state no never-contain / subnet / containment inference

- `docs/operator_runbook.md:234-238` — "Sweep does not infer policy" with explicit bullets for never-contain exclusions, subnet membership, and containment policy statute; runbook example command (`:223-230`) matches actual CLI flags.
- CLI `--help` epilog `SWEEP_LIMITATIONS_EPILOG` (`cli.py:18-27`) restates the same three, verified by `test_sweep_cli_help_documents_limitations` (`test_sweep_cli.py:34-41`).

## Refutation attempts (all failed)

- Preflight rejection tautological? No — it is the intended contract (proposed artifacts must be non-activatable) and the test asserts the specific error code against the real preflight, using YAML actually emitted by the CLI subprocess.
- Non-zero tests passing without real failure? No — each also asserts a specific stderr substring, so a spurious crash would not satisfy them.
- Stale evidence? No — re-ran the suite; 25 passed, 0 skipped.

## Notes

- Out of task scope (not blocking): full-repo lint/typecheck/other suites were not run; verification limited to the specified `tests/codification/` command per "task-scoped only".
