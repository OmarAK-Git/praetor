# Plan — V2-038 Delivery Backlog Reconcile

**Tier:** T2  
**Goal:** V2-038 — Reconcile docs/proposals/delivery_backlog.md Open/Partial rows against V2 completion evidence (Gates 0–5 + V2-037); update banner; leave true residual Open / Accepted Deferral / Future rows honest.

## Acceptance criteria

1. Banner no longer lists Gate 5 intake wiring as residual; reflects post-V2-037 state.
2. Every row closed by a V2 task/gate is marked Closed with closing task id.
3. True residuals remain Open/Partial/Accepted Deferral with accurate notes.
4. No product/source code changes outside docs and memory-bank.

## Verification

Manual spot-check + banner sanity. Prefer evidence from `.workflow/v2-*-exit/` and task verifiers.
