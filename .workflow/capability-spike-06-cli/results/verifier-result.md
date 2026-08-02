# Verifier result — capability-spike-06-cli

## Verdict

**PASS** (claim survives)

## Claim under test

Commit `2450e66` adds an offline-safe capability spike CLI (`evals/capability_spike.py`), tests, and a non-gating section in `docs/eval_gates.md`. Acceptance: unset env → exit 0 skip; enabled without API key still skips (no network); JSONL loader skips blank/malformed lines; harness does not import the spike; no `src/praetor/**`, `evals/harness.py`, or `evals/scenarios/**` edits.

## Fresh evidence (re-run this session)

| Command | Result |
|---------|--------|
| `pytest tests/evals/capability/test_cli.py -q` | `6 passed in 0.34s` (exit 0) |
| `ruff check evals/capability_spike.py tests/evals/capability/test_cli.py` | All checks passed (exit 0) |
| `mypy evals/capability_spike.py` | Success: no issues found (exit 0) |
| `python -m evals.capability_spike` | prints `capability spike skipped: PRAETOR_CAPABILITY_SPIKE not enabled`; exit 0 |

Live probe (enabled, no keys):

```
PRAETOR_CAPABILITY_SPIKE=1
# PRAETOR_GEMINI_API_KEY / GOOGLE_API_KEY unset
python -m evals.capability_spike
# → capability spike skipped: no API key in PRAETOR_GEMINI_API_KEY or GOOGLE_API_KEY
# exit 0
```

Working tree for the three product files matches `2450e66` (`git diff 2450e66 --` empty for those paths).

## Acceptance criteria

| Criterion | Evidence | Status |
|-----------|----------|--------|
| `main()` exits 0 with skip when env unset | Fresh CLI run + `test_main_exits_zero_when_disabled`; early return before argparse/`VertexProvider` (`capability_spike.py:119–129`) | met |
| Enabled without API key still skips (no network) | Live probe exit 0; `resolve_spike_provider` returns `None` before `VertexProvider(...)` (`:58–68`); `test_enabled_without_key_still_skips` | met |
| `load_capture_events` reads JSONL; skips blank/malformed | `test_load_capture_events_reads_jsonl`; `test_load_capture_events_skips_blank_and_malformed_lines`; impl `:71–85` | met |
| Harness does not import spike | Source + AST import walk of `evals/harness.py`: no `capability_spike` / `evals.capability`; ripgrep across `evals/` only self-ref in CLI; `test_harness_does_not_import_the_spike` | met |
| Non-gating section in `docs/eval_gates.md` | `## Non-gating: judgment capability spike` at `:192–205`; states not a CI gate + env/key requirement | met |

## Manual checks

### Commit `2450e66` has no `src/praetor` / harness / scenarios edits

`git show 2450e66 --name-status`:

- `A  .workflow/capability-spike-06-cli/results/implementer-result.md`
- `M  docs/eval_gates.md`
- `A  evals/capability_spike.py`
- `A  tests/evals/capability/test_cli.py`

Forbidden path search on commit file list: none. Diffstat: 4 files, +311 only.

### Spike remains opt-in / not a CI gate

Docs section + CLI gate on `PRAETOR_CAPABILITY_SPIKE` and API key; default path never constructs provider.

## Adversarial checks attempted

- **Stale evidence:** re-ran all packet commands this session; product files match commit.
- **Weakened “no network” test:** unit test only asserts `resolve_spike_provider() is None`, not `main()`. Refutation attempt failed — live `main()` under flag-without-key still exits 0 with skip message, and provider is never constructed on that path.
- **Harness isolation gamed by string-only assert:** AST import walk confirms no capability imports; broader `evals/` grep finds no harness/scenario import of the spike module.
- **Scope creep via commit:** only allowed paths; no `src/praetor/**`, `evals/harness.py`, or `evals/scenarios/**`.
- **Forbidden agentic import:** no `praetor.judgment.agentic` in `capability_spike.py`.

## Strongest reason for PASS

Fresh green pytest/ruff/mypy plus both offline CLI skip paths (unset env and enabled-without-key), with commit `2450e66` limited to allowed files and harness AST/source free of spike imports.
