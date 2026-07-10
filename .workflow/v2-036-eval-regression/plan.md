# Workflow Plan — V2-036 Eval Regression Locking Discipline

**Tier:** T2  
**Goal:** V2-036 — Eval regression locking discipline: workflow template requires every confirmed model error to identify a harness scenario or explicit waiver; eval gate docs define minimum scenario quality and expectation-key validation; CI catches stale or unknown expectation keys.

## Verification

```bash
pytest tests/evals/ -q
```
