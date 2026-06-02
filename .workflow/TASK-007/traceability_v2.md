# Traceability: TASK-007

Map requirements → tasks → code → verification. Update as work proceeds.

| Req ID | Requirement (summary) | Task ID | Code / artifact | Verification |
|--------|-------------------------|---------|-----------------|--------------|
| REQ-001 | Pending before external call | T-003 | `stamp.py` `execute_stamp`, `outbox.py` `write_pending_stamp` | V-003 |
| REQ-002 | Durable success/failure | T-003 | `outbox.py` `record_stamp_outcome` | V-004, V-007b |
| REQ-003 | Timeout/ambiguous → `unknown` | T-003 | `stamp.py` `_is_backend_ambiguity` | V-005, V-005b, V-005c |
| REQ-004 | Recovery same `stamp_id` | T-003 | `stamp.py` `execute_stamp` recovery path | V-006, V-006b, V-006c, V-011 |
| REQ-005 | Idempotent ticket backend | T-002/T-003 | fake backends + recovery replay test | V-007, V-006c |
| REQ-006 | Non-idempotent risk documented | T-003 | `stamp.py` module doc / constant | V-008 |
| REQ-007 | `unknown` ≠ `failed` | T-003 | `StampStatus` enum | V-009 |
| REQ-008 | `critical_transaction` for writes | T-003 | `outbox.py` | V-010 (implicit) |
| REQ-009 | No docs changes | — | scope guard | V-002 |
| REQ-010 | Payload authority on retry | reopen | `execute_stamp` uses `existing.ticket_payload` | V-012 |
| REQ-011 | DEC-022 additive schema | reopen | `init_stamp_outbox_schema` + open hook | V-013 |
| REQ-012 | PENDING outcome guard | reopen | `record_stamp_outcome` ValueError | V-014 |
| REQ-013 | `processing_attempt_identity` semantics | reopen | first-writer, no update on retry | V-015, DEC-023 |

## Orphan / unmapped

- Requirements with no task: none
- Tasks with no requirement: none
- **Deferred TASK-023:** attempt FSM `pending_stamp`, PolicyGate stamp sequencing, edict append — not mapped (intentionally out of scope)

## Reopen gap resolution

| Gap # | Topic | Resolution |
|-------|-------|------------|
| G-1 | Generic backend ambiguity | Fixed — `_is_backend_ambiguity`; tests for ConnectionError + programmer error |
| G-2 | PENDING-on-restart | Fixed — restart test |
| G-3 | EMPTY_BUNDLE path | Fixed — dedicated test |
| G-4 | FAILED terminal cache | Fixed — symmetric test |
| G-5 | Payload divergence | Fixed — payload authority test |
| G-6 | DEC-022 regression | Fixed — Task 6 DB fixture test |
| G-7 | Recovery idempotent backend | Fixed — StampThenLoseResponseBackend test |
| G-8 | PENDING record guard | Fixed — negative test |
| G-9 | processing_attempt_identity | Fixed — explicit test + DEC-023 |
| G-10 | Timestamp canonical format | **Open — TASK-023 hazard** (documented, not fixed) |
| G-11 | Repeated schema ensure | **Mitigated** — cache + table-exists validation |
| G-12 | Artifact overclaim | Fixed — this verification.md / review.md update |
