# Reverse-Spec RFC Disposition (2026-07-30)

Source: [`docs/archive/reverse_spec_rfcs.md`](../archive/reverse_spec_rfcs.md), a reverse-spec review
generated from [`docs/archive/as_built.md`](../archive/as_built.md) and
[`docs/archive/debt_ledger.md`](../archive/debt_ledger.md). Each RFC's cited evidence
was checked against current source and against `docs/decisions.md`, which the
generating tool did not appear to cross-reference. Full rationale for each
verdict is in `docs/superpowers/plans/2026-07-30-reverse-spec-rfc-remediation.md`
("Verification Notes").

| RFC | Original severity | Verdict | Disposition |
|---|---|---|---|
| RFC-001 (invert stamp/ledger order) | S1, tool CONCEDEd | **Rejected** | Contradicts DEC-053 (docs/decisions.md, docs/spec.md:149, docs/architecture.md:56/74, docs/contracts.md:312/644). Do not implement without an explicit DEC-053 supersession decided by a project owner. |
| RFC-002 (JSONL sink limits/isolation) | S1 | **Rejected framing; narrow fix shipped** | "Health alerts silently suppressed" is false — separate sink, already durable (`alerts/system_health.py`). Real kernel (DEBT-042, no size bound) closed via an operator size-warning alert only; rotation stays out of scope (frozen v1 non-goal, `tests/docs/test_docs.py`). |
| RFC-003 (halt on malformed never-contain) | S1, tool WEAKENed | **Accepted, rescoped tighter than the tool's own WEAKEN** | Skip branches are defensive dead code on the production read path (entries are pre-validated by `read_live_never_contain_entries`). Made observable via logging rather than a system-wide halt, which would itself be a denial-of-automation vector. |
| RFC-004 (correlation schema-mismatch metric) | S2, tool WEAKENed | **Accepted as scoped** | Real, low-risk observability gap. Implemented as-is. |
| RFC-005 (precedent poisoning) | S1, tool CONCEDEd | **Rejected S1 severity; narrow fix shipped** | Exemplars are advisory-only; PolicyGate independently re-authorizes every containment decision (as-built invariant #21), so poisoning cannot itself authorize unauthorized `auto_contain`. Real annotation-auth gap is DEBT-041, tracked separately. Only the malformed-edict silent-drop (DEBT-022) was fixed. |
| RFC-006 (citations unit tests) | S2, tool WEAKENed | **Accepted, rescoped tighter than the tool's own WEAKEN** | `engine/citations.py` is a 15-line adapter; the actual citation logic already has direct tests in `tests/evidence/test_citation_validation.py`. Added one direct test file for the adapter itself; no orchestrator extraction needed. |

**Process note:** this reverse-spec tool's automated rebuttal pass reached
CONCEDE on two S1 findings (RFC-001, RFC-005) that manual verification against
`docs/decisions.md` and the actual authorization flow rejected outright. Future
runs of this tool should be checked against `docs/decisions.md` before any S1
finding is acted on.
