# Workflow Plan — V2-026 Org-Config Numeric Rate Ceilings

## Goal

V2-026 — Org-config numeric rate ceilings: org config declares numeric per-scope ceilings with strict integer validation; gate enforces ceilings for host, subnet, and asset-group scopes; missing/invalid ceilings fail preflight or apply documented defaults consistently.

## Scope

Org-config rate ceilings and enforcement only. Do not run V2 Gate 4 exit.

## Tier

T2

## Verification Commands

```bash
pytest tests/config/ tests/policy/test_rate_limits.py -q
```
