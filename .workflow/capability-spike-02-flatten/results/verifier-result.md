# Verifier result — capability-spike-02-flatten

## Verdict

**PASS**

## Claim under review

Queue item `capability-spike-02-flatten` is complete: generic mechanical flattener in `evals/capability/flatten.py` with tests, commit `41eae19`, acceptance criteria met, no window/host filter reimplementation, no `src/praetor/` edits.

Implementer result treated as unevidenced; all checks re-run and source inspected independently.

## Fresh verification commands

| Command | Result |
|---------|--------|
| `pytest tests/evals/capability/test_flatten.py -q` | `8 passed in 0.33s` (exit 0) |
| `ruff check evals/capability/flatten.py tests/evals/capability/test_flatten.py` | `All checks passed!` (exit 0) |
| `mypy evals/capability/flatten.py` | `Success: no issues found in 1 source file` (exit 0) |

## Acceptance criteria

| Criterion | Evidence | Status |
|-----------|----------|--------|
| `flatten_event_to_fact` emits `EvidenceFact` with flattened `normalized_fields` | Tests assert EventData keys (`DestinationIp`, `DestinationPort`, `Image`) land in `normalized_fields`; ad-hoc probe with EventID 99 nested `Foo` → `normalized_fields['Foo']=='bar'`. Implementation `_flatten_fields` (`evals/capability/flatten.py:49-61`) copies top-level + EventData keys without schema. | Met |
| `resolve_provenance_path` labels known sources; unknown → `SPIKE_UNKNOWN_SOURCE` | `test_resolve_provenance_path_by_channel`; probe: Sysmon channel → `sysmon_event_log`, unknown channel → `spike_unknown_source`. Channel-only branching (`flatten.py:40-46`). | Met |
| Flattener stays mechanical (no per-EventID hand extraction) | No `EventID == …` / allowlist branches in extraction. `EventID` used only for `source_event_reference` (`flatten.py:71-77`). EventID 3 and EventID 99 both flatten generically. | Met |

## Manual checks

### No correlation window/host filter reimplementation

- Grep of `evals/capability/flatten.py`: **no** matches for `filter_events_in_window`, `filter_events_to_anchor_host`, `timedelta`, `window_seconds`, or `anchor_host`.
- `event_host_id` is used only to **set** `normalized_fields["host_id"]` (`flatten.py:80`), not to drop events — field extraction, not host filtering. Window/host filtering belongs to Task 3 bundle builder per plan.

### No `src/praetor/` edits in `41eae19`

```
git diff-tree --no-commit-id --name-only -r 41eae19
evals/capability/flatten.py
tests/evals/capability/test_flatten.py
```

`Select-String` / `findstr` for `src/praetor`: no matches. Commit message: "Add generic event flattener for capability spike Path B." Full hash: `41eae190faf618ebdd65d70be66afe65ca80c112`.

Working tree for those two files matches the commit (`git diff 41eae19 -- evals/capability/flatten.py tests/evals/capability/test_flatten.py` empty).

## Refutation attempts (failed to refute)

1. **Gamed tests / dead code:** Tests import and call live `evals.capability.flatten` APIs; fresh pytest 8/8; independent EventID-99 probe confirms mechanical flatten + provenance without using fixtures alone.
2. **Hidden EventID allowlist:** Source read — only Channel substring for provenance; EventID not gated.
3. **Filter logic smuggled via helpers:** Imports are field/id helpers + `EvidenceFact` constructors; no window/host filter imports.
4. **Scope creep into `src/praetor/`:** Commit file list is evals + tests only.

## Strongest surviving reason

Fresh command evidence (pytest/ruff/mypy exit 0) plus code and commit inspection show a mechanical Channel-based flattener scoped to the two allowed files, with no window/host filter reimplementation and no `src/praetor/` changes in `41eae19`.
