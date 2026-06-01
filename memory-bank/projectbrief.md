# Project Brief

## What this project does

**Praetor** is a post-detection disposition-policy engine for a SOC. Upstream detection has already fired; Praetor decides what happens next: correlate local telemetry, get structured LLM judgment against org config, run deterministic **PolicyGate**, emit disposition + audit record (and optional containment directive).

Core thesis (from `docs/prd.md`, `docs/spec.md`): model judgment is useful only when constrained by contracts, schema-enforced citations, deterministic safety controls, and a reviewable audit trail. **The model recommends; the system authorizes.**

Three dispositions only: `standard_review`, `escalate`, `auto_contain`. No `auto_close`.

**Authoritative docs** (do not duplicate; read these for detail):

| Doc | Role |
|-----|------|
| `docs/prd.md` | Why — product thesis, decisions, success criteria, non-goals summary |
| `docs/spec.md` | What — architecture, contracts behavior, acceptance criteria, risks |
| `docs/plan.md` | How — 35 tasks, sprints, phase gates |
| `docs/contracts.md` | Hashing, IDs, Outcome Matrix, consumer pre-actuation (hard prerequisite for Task 3) |

## Tech stack

From `docs/spec.md` (planned v1):

- Python, Pydantic v2 (versioned contracts, JSON Schema export)
- YAML/JSON org config
- LLM provider Protocol (Vertex AI Gemini initially; FakeProvider for tests)
- SQLite (WAL, single-process/single-writer, OS singleton lock)
- Hash-chained append-only ledger; durable outboxes (stamp, health alerts, revocation feed)
- Append-only JSONL revocation feed projection
- Sigma / pysigma, OTRF/Mordor fixtures, Splunk Free (detection spine / demo)

Referenced but not yet in repo: `docs/operator_runbook.md`, `docs/architecture.md`, `docs/eval_gates.md` (Task 35).

## Main commands

After Task 1–2:

- Install: `pip install -e ".[dev]"`
- Test: `pytest` from repo root
- Export schemas: `python -m praetor.contracts.schema_export`
- Run: TODO (application entrypoint not yet defined)
- Build: `pip install -e .` (hatchling wheel)

Benchmarks planned: `benchmarks/smoke_serialized_path.py` (Task 11), `benchmarks/serialized_path.py` (Task 35).

## Important constraints

- **Docs are source of truth** — Memory Bank summarizes; do not invent fields or behavior not in docs.
- **Single writer** — OS singleton + SQLite WAL; `docs/contracts.md` fixes all hash domain constants before hashing code.
- **Idempotency** — One completed edict per `(alert_id, evidence_bundle_hash, org_config_snapshot_hash)`; `decision_id` is per-attempt (includes attempt identity).
- **No auto_close**; uncertainty flows to `standard_review`.
- **`auto_contain`** only after all deterministic gates (citations, never-contain, rate limits, breakers, revocation-feed health, etc.).
- **Consumer** owns receipt-to-actuation; Praetor owns honest emission + revocation feed signals.
- **Ledger** tamper-evident, not immutable; feed is projection, chain is audit authority.
- **Account auto-contain** production-disabled until Phase 3 identity gates + `account_auto_contain_enabled`.

## Out of scope (v1)

Per `docs/prd.md` / `docs/spec.md`: detection engine, severity scorer, live enforcer, external enrichment, self-learning, suppressor, computational LLM replay, IdP, subnet/asset-group containment, feed rotation machinery, direct SOAR/EDR actuation, analyst UI beyond annotations. See spec **Deferred Work** for roadmap items.
