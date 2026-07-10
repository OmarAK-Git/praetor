# Implementer Packet — V2-026 Org-Config Numeric Rate Ceilings

**implementation_model:** composer-2.5-fast

## Objective

Replace fixed DEC-029 rate ceiling with org-configurable per-scope numeric ceilings (host, subnet, asset-group) with strict integer preflight validation and PolicyGate enforcement.

## Original User Goal

V2-026 — Org-config numeric rate ceilings: org config declares numeric per-scope ceilings with strict integer validation; gate enforces ceilings for host, subnet, and asset-group scopes; missing/invalid ceilings fail preflight or apply documented defaults consistently.

## Allowed Files

- src/praetor/contracts/org_config_sections.py
- src/praetor/config/preflight.py
- src/praetor/policy/rate_limit.py
- tests/config/
- tests/policy/test_rate_limits.py
- specs/, IMPLEMENTATION_PLAN.md, memory-bank/

## Do-Not-Touch

- Do not mark queue done; do not run V2 Gate 4 exit

## Verification

pytest tests/config/ tests/policy/test_rate_limits.py -q

Write result to .workflow/v2-026-rate-ceilings/results/implementer-result.md
