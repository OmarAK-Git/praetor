# Review — V2-011

## Notes

- Host corroboration uses `ResolvedEvidenceCitation` metadata from the shared citation validator (AG-0041), applied after citation-anchored target resolution and before never-contain / account branches.
- Default host test/harness/benchmark bundles now carry sysmon+security facts with dual citations so existing auto_contain paths remain valid under the new floor.
- Phase 3 gate: sysmon-only single cite must escalate; corroborated host pass uses sysmon-only noisy bundle plus synthetic host-level security fact (full correlated bundle routes account-first when SID present).

## Gaps

- Worktree branched from commit `d352e45` (pre–V2-006 merge); `tests/splunk/*` fails on committed SPL drift vs compiler on this base — unrelated to V2-011. Full gate excluding splunk: **792 passed**, 1 xfailed.
- `docs/` unchanged per task constraint.
