# Workflow Plan — V2-016 Static Policy Fault-Flag Guard

## Goal

V2-016 — Static policy fault-flag guard: policy/engine literal fault flags are a subset of OutcomeMatrixFaultFlag; DecisionEdict rejects invalid fault flag polarity; harness completeness guard covers new flags.

## Scope

Fault-flag static guards and edict validation only. Do not run V2 Gate 2 exit or full-suite verification.

## Tier

T2

## Verification Commands

```bash
pytest tests/contracts/ tests/policy/ tests/evals/ -q
```
