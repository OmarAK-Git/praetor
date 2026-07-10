# Workflow Plan — V2-035 Statute Curation Workflow

**Tier:** T2  
**Goal:** V2-035 — Statute curation workflow: annotation-to-proposed-statute artifact is review-only and not activatable; SOC-lead promotion runs full preflight and records activation audit trail; workflow artifact captures source annotations, proposed edits, reviewer, and activation result.

**Scope:** Statute curation workflow and activation audit only. Do not run V2 Gate 5 exit.

## Verification

```bash
pytest tests/codification/ tests/config/ -q
```
