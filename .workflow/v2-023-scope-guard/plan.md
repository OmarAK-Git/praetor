# Workflow Plan — V2-023 Contract Scope Guard and Generated Artifact Hygiene

## Goal

V2-023 — Contract scope guard and generated artifact hygiene: scope guard allowlist strict; generators expose `--check` and `--write`.

## Scope

Scope guard and artifact hygiene only. Do not run V2 Gate 3 exit.

## Tier

T2

## Verification Commands

```bash
pytest tests/contracts/test_scope_guard.py -q
```
