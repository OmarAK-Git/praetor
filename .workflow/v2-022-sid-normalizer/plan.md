# Workflow Plan — V2-022 SID and Normalizer Conformance

## Goal

V2-022 — SID and normalizer conformance: SID validation vectors or documented waiver; malformed domain-separator accounts set ambiguity_flag=true in test helpers.

## Scope

SID/normalizer conformance only. Do not run V2 Gate 3 exit.

## Tier

T2

## Verification Commands

```bash
pytest tests/evidence/ tests/correlation/ -q
```
