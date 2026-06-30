You are running a compaction pass over the Praetor Dream Playbook — a curated
long-term engineering memory that has grown through many per-commit dream cycles.

Your ONLY job is near-duplicate detection. You are NOT synthesising new insights.
You are NOT editing or rewriting entry text. You are identifying pairs of existing
entries where one is redundant given the other, and proposing that the weaker one
be superseded by the stronger one.

## What counts as a near-duplicate

Two entries are a near-duplicate when:
- They describe the same rule, constraint, or hazard
- Reading one makes the other superfluous — the second adds no new fact, scope,
  or consequence that the first does not already cover
- They often arise from the same slug committed across two SHAs, where each
  dream pass re-emitted an overlapping insight rather than superseding the first

## What does NOT count

- Two entries that each add something the other lacks (complementary, not redundant)
- Two entries that cover the same area but with different actionable specifics
- Entries already marked `status=superseded`

## Output contract

Return a `compactions` array. Each element has:
- `superseded_id`: the weaker/redundant entry to retire (must be an active entry ID)
- `canonical_id`: the surviving entry (must be an existing active entry ID)
- `rationale`: one sentence explaining why `superseded_id` is redundant given `canonical_id`

Important constraints:
- Both IDs must already exist in the playbook
- `canonical_id` must be an **active** entry, not already superseded
- Do NOT invent new IDs
- Do NOT propose supersessions where you are uncertain — conservative is correct
- If no clear near-duplicates are found, return an empty `compactions` array

## Known ground-truth pairs (already resolved — use to calibrate your threshold)

These pairs were created by the V2-003 slug being committed across two SHAs, each
firing a dream that re-emitted overlapping insights:

1. AG-0087 superseded by AG-0090: both describe NeverContainSnapshot capture timing;
   AG-0090 is fuller and adds the DEC-060 cross-reference
2. PE-0032 superseded by AG-0088: same content (expired-unrevoked rows as audit
   residue), split across two sections; AG-0088 is the canonical formulation
3. AG-0089 superseded by AG-0091: orphan-directive reconciliation; AG-0091 absorbs
   and extends AG-0089 with the DEC-060 health-audit requirement

A good compaction proposal would have caught all three. Use these as a calibration
floor for your confidence threshold — if you find pairs less similar than these,
skip them.
