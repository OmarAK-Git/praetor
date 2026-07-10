# Workflow Plan — V2-021 Evidence ID Contract Pin

## Goal

V2-021 — Evidence ID contract pin: docs/contracts.md defines evidence_id preimage; exact test vector pins one known evidence_id.

## Scope

Evidence ID contract and hashing only. Do not run V2 Gate 3 exit.

## Tier

T2

## Verification Commands

```bash
pytest tests/hashing/ tests/correlation/ -q
```
