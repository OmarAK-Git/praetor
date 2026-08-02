# Verifier result — capability-spike-03-bundle

## Verdict

**PASS**

## Claim under review

Path B `build_spike_bundle` reuses production correlation window/host filters, flattens all event types (including non-1/4624), and commit `9cb454a` touches only evals/tests (no `src/praetor`).

## Independent evidence

### Commands (re-run this session)

```
pytest tests/evals/capability/test_bundle.py -q
→ 6 passed in 0.35s (exit 0)

ruff check evals/capability/bundle.py tests/evals/capability/test_bundle.py
→ All checks passed! (exit 0)

mypy evals/capability/bundle.py
→ Success: no issues found in 1 source file (exit 0)
```

### Source: production filter reuse

`evals/capability/bundle.py`:

- Imports `filter_events_to_anchor_host` from `praetor.correlation.host_isolation` (L17).
- Imports `filter_events_in_window` / `DEFAULT_CORRELATION_WINDOW_SECONDS` from `praetor.correlation.window` (L18–21).
- Calls `filter_events_in_window(...)` in `build_spike_bundle` (L44–49).
- Calls `filter_events_to_anchor_host(...)` when `anchor_host_id is not None` (L50–53).

Resolved at runtime to:

- `praetor.correlation.window` → `src/praetor/correlation/window.py`
- `praetor.correlation.host_isolation` → `src/praetor/correlation/host_isolation.py`

No local reimplementation of window/host filtering; `_datable` only drops unparseable timestamps before the production helpers run.

### Acceptance: non-1/4624 events

- `test_includes_event_types_correlation_rejects` keeps EventIDs 3/11/13 (passed).
- Manual parity: EventID 3 on `ws-01` inside window survives host+window filters and appears in the bundle; out-of-window / other-host events excluded.

### Commit `9cb454a` — no `src/praetor`

```
git show --name-only 9cb454a
→ evals/capability/bundle.py
→ tests/evals/capability/test_bundle.py
```

`NO_SRC_PRAETOR_MATCH`. HEAD is `9cb454a`; working tree for those two files matches the commit (`git diff 9cb454a -- …` empty).

## Attack attempts (did not refute)

| Attack | Outcome |
|--------|---------|
| Weakened assertions / not exercising new code | Tests import and call `build_spike_bundle`; window/host/provenance/empty/undatable cases cover the builder path. |
| Reimplemented filters disguised as helpers | `_datable` is timestamp prefilter only; window/host delegated to production symbols. |
| Stale evidence vs latest commit | Fresh pytest/ruff/mypy after confirming HEAD=`9cb454a` and clean diff for scoped files. |
| Commit sneak into `src/praetor` | File list is evals + tests only. |

## Strongest surviving reason

`build_spike_bundle` literally imports and calls `filter_events_in_window` and `filter_events_to_anchor_host` from `praetor.correlation`; independent tests/lint/types pass; commit `9cb454a` contains no `src/praetor` paths.
