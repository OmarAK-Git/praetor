# Workflow Plan — V2-018 Revocation Supersession and Feed Verifiability

## Goal

V2-018 — Revocation supersession and feed verifiability: expired directive re-issue matches owner decision; feed supports consumer supersession verification or documents limitation.

## Scope

Revocation, feed projection, and consumer verification only. Do not run V2 Gate 3 exit.

## Tier

T2

## Verification Commands

```bash
pytest tests/containment/ tests/consumer_sdk/ -q
```
