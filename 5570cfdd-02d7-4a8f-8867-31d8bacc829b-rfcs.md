# Reverse Spec RFCs

## RFC-as-built-md-001: Reorder critical_transaction to strictly precede external execute_stamp

**Severity:** S1 | **Scope:** behavior | **Personas:** sre_at_3am, hostile_pr_reviewer, attacker, premortem_10x

### Problem
Executing external SOAR stamping before the internal SQLite transaction commits (critical_transaction) creates a fatal race condition. If the internal transaction fails, conflicts, or if an attacker deliberately induces a crash post-stamp, the system recovers by downgrading the state to ESCALATE while the external SOAR remains incorrectly flagged as AUTO_CONTAIN, resulting in an irrevocable and silent desync.

### Evidence
- AS_BUILT.md 3.2: execute_stamp (outbox + backend) happens BEFORE critical_transaction
- AS_BUILT.md 3.3: Deferred persist conflict rebuilds escalate edict in-band
- AS_BUILT.md 3.4: run_engine_startup_recovery forces AUTO_CONTAIN -> ESCALATE

### Traceability
- novel: Static code probes cannot evaluate transactional boundaries across external APIs versus internal SQLite commits, particularly under attacker-induced crash or OOM scenarios.

### Proposed Change
Invert the execution order: commit the internal SQLite critical_transaction first, then attempt execute_stamp. Implement a retry queue or dead-letter queue for SOAR stamping if the external API fails post-commit.

### Acceptance Criteria
- The system never executes SOAR stamps prior to a successful internal SQLite commit.
- Injected crashes between commit and stamp result in successful retry of the stamp upon startup recovery, not a downgrade to ESCALATE.

### Rebuttal Record
CONCEDE

### Conflicts
none

## RFC-as-built-md-002: Implement limits and isolation for JSONL sink to prevent fail-open

**Severity:** S1 | **Scope:** behavior | **Personas:** sre_at_3am, premortem_10x

### Problem
Unbounded JSONL feed growth can lead to disk exhaustion or deliberate I/O saturation by an attacker flooding alerts. If the JSONL health sink fails or export SLOs are missed, the system falls back to a degraded non-actuating mode (disabling automated containment globally) and silently suppresses the health alerts meant to notify operators of the failure.

### Evidence
- DEBT-042: FeedJsonlSink 'v1: no rotation'
- DEBT-027: alerts/system_health.py ~75-87 Catch -> record FAILED delivery
- AS_BUILT.md 3.4: Feed export recovery - if SLO missed, degraded non-actuating mode
- AS_BUILT.md 5.3: Feed unhealthy Block auto_contain only; allow review/escalate

### Traceability
- linked: DEBT-042
- linked: DEBT-027

### Proposed Change
Implement strict log rotation, size limits, and TTLs for the JSONL feed. Separate the system health alert sink from the data feed sink so that JSONL exhaustion does not inherently suppress the I/O of health alerts.

### Acceptance Criteria
- Attacker-induced alert floods trigger load shedding but do not degrade the system to non-actuating mode.
- Health alerts successfully dispatch even when JSONL sinks suffer disk exhaustion.

### Rebuttal Record
KILL; CONCEDE

### Conflicts
none

## RFC-as-built-md-003: Halt on malformed never-contain lists instead of silently skipping

**Severity:** S1 | **Scope:** behavior | **Personas:** hostile_pr_reviewer

### Problem
Silently skipping malformed live never-contain entries (DEBT-023) combined with complex, untested emergency block management (DEBT-062, DEBT-070) creates a fatal fail-closed condition. If an emergency exclusion list is corrupted, the system silently ignores it and auto-contains highly protected assets without any log visibility indicating the list was dropped.

### Evidence
- DEBT-023 — INFO: config/live.py PreflightError → False/continue
- DEBT-062 — S3: config/emergency.py add_emergency_never_contain is 88 LOC function
- DEBT-070 — S2: config.internal.purge_expired_emergency_records_internal has no positive test
- AS_BUILT.md 5.3 — 'Malformed live never-contain entry -> Skip match'

### Traceability
- linked: DEBT-023
- linked: DEBT-062
- linked: DEBT-070

### Proposed Change
Modify the behavior of malformed live never-contain entries: trigger a fatal system fault and transition to ESCALATE for any alerts processed during a configuration error, rather than skipping the exclusion and risking auto-containment of protected assets.

### Acceptance Criteria
- A malformed never-contain entry causes the orchestrator to fail-safe by escalating all containable events until the configuration is repaired.
- Emergency list parsing errors emit explicit telemetry.

### Rebuttal Record
WEAKEN(The finding correctly uses an interaction argument per Rule 2 to challenge an INFO deferral (DEBT-023) using DEBT-062 and DEBT-070. However, it mischaracterizes the result as 'fail-open'. Bypassing a never-contain rule means the containment action proceeds (fail-closed), which is an availability impact, not a security fail-open.)

### Conflicts
none

## RFC-as-built-md-004: Surface explicit metrics for empty correlation schema mismatches

**Severity:** S2 | **Scope:** behavior | **Personas:** sre_at_3am

### Problem
When upstream telemetry schemas change, the correlation engine skips unsupported EventIDs and returns an empty bundle. While the system safely defaults to ESCALATE, the lack of explicit metrics or logging for schema mismatch means operators experience alert fatigue without visibility into the underlying telemetry breakage.

### Evidence
- AS_BUILT.md 5.5: Correlation: unsupported EventIDs skipped; empty bundle returned
- AS_BUILT.md 3.3: Fault short-circuits finish with escalate + Outcome Matrix fault flags

### Traceability
- novel: Design-level silent fallbacks during runtime schema mismatches bypass exception trackers and static complexity probes.

### Proposed Change
Emit a distinct metric and warning log when a correlation bundle returns empty specifically due to unrecognized or unsupported EventIDs, separating it from genuinely empty correlation sets.

### Acceptance Criteria
- A schema change in upstream telemetry triggers a specific schema-mismatch metric rather than just a silent increase in ESCALATE tickets.

### Rebuttal Record
WEAKEN(The finding correctly identifies an observability gap (silent-by-design failure mode) per Rule 4, but overstates the impact. Downgrading to ESCALATE is a deliberate fail-safe mechanism, meaning the system remains secure. The issue is strictly one of missing operational visibility and potential alert fatigue, not a severe processing failure.)

### Conflicts
none

## RFC-as-built-md-005: Secure precedent retrieval and validate exemplars against poisoning

**Severity:** S1 | **Scope:** structure | **Personas:** hostile_pr_reviewer, attacker, premortem_10x

### Problem
The precedent retrieval loop lacks test coverage and fails open by silently skipping validation errors (DEBT-022). This allows attackers to craft payloads that evade retrieval or compromised tokens to inject malicious exemplars. Since the LLM is trusted implicitly for downgrades, poisoned precedents can systematically disable automated containment with zero observability.

### Evidence
- DEBT-074 — S3: No tests/retrieval/ package tree
- DEBT-022 — annotations/precedent.py ~87–88: ValidationError → return None
- AS_BUILT 3.7 — submit_annotation → retrieve_similar_case_exemplars
- AS_BUILT 4 #21 — Judgment quality not machine-gated; Gate can always downgrade

### Traceability
- linked: DEBT-074
- linked: DEBT-022

### Proposed Change
Implement a cryptographic or strict schema-validation boundary for precedent injection, rejecting rather than silently skipping invalid ledger edicts. Introduce a test suite for retrieval and bound the LLM's downgrade authority when precedents are anomalous.

### Acceptance Criteria
- Validation failures in ledger edicts generate critical alerts instead of silently bypassing precedent loading.
- Test suite explicitly covers similar-case ranking and exemplar bounds for prompt injection defense.

### Rebuttal Record
CONCEDE

### Conflicts
none

## RFC-as-built-md-006: Implement direct unit tests for engine.citations to prevent regression

**Severity:** S2 | **Scope:** structure | **Personas:** hostile_pr_reviewer

### Problem
The engine.citations module lacks direct unit tests (DEBT-072), and the orchestrator's massive procedural size (DEBT-050, DEBT-057) means citation evaluation coverage relies entirely on fragile, high-level integration tests, drastically increasing the risk of regressions during routine refactoring.

### Evidence
- DEBT-050 — S3: engine/orchestrator.py is 822 LOC
- DEBT-057 — S3: process_alert_intake is 322 LOC
- DEBT-072 — S3: engine.citations has no direct unit test

### Traceability
- linked: DEBT-050
- linked: DEBT-057
- linked: DEBT-072

### Proposed Change
Extract the citation evaluation logic from the monolithic orchestrator and provide a dedicated, isolated unit test suite for engine.citations to guarantee correct judgment generation.

### Acceptance Criteria
- The engine.citations module has >90% branch coverage via isolated unit tests independent of the orchestrator.

### Rebuttal Record
WEAKEN(The finding relies on hyperbole ('completely blocking', 'guaranteeing regression blindness') while simply aggregating known S3 structural debts. While the lack of isolated unit tests for citations (DEBT-072) nested in a large orchestrator (DEBT-050) does create a testing gap, broader integration tests exist. The claim must be restricted to the specific risk of refactoring without direct unit coverage rather than claiming absolute regression blindness.)

### Conflicts
none
