# Review — V2-014

## Scope adherence

- Correlator drops cross-host in-window events after window filter; anchor host from Security event or Sysmon plurality.
- Strict xfail removed; correlation expected YAML updated for host-scoped bundles.
- PolicyGate citation-anchored targeting unchanged (defense in depth retained).
- No `docs/` edits.

## Findings

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| REVIEW-001 | info | Anchor derivation without Security events uses Sysmon plurality only. | Acceptable for v1 fixtures; explicit `anchor_host_id` param available for intake wiring (V2-015). |
| REVIEW-002 | gap | AG-0080 playbook digest still describes pre-V2-014 behavior. | Deferred to dream consolidate (docs/playbook edit out of scope). |
| REVIEW-003 | fixed | First-Security-event anchor was ordering-dependent. | Replaced with plurality + Sysmon/dual-channel/proximity tie-breaks; regression test for prepended WS2 Security event. |
| REVIEW-004 | fixed | `max()` over a set had hash-order tie hazard. | Ambiguous top rank returns `None` and host filtering is skipped. |

## Anchor resolution order

1. Explicit `anchor_host_id` argument
2. Plurality across in-window Sysmon + Security events
3. Tie-break: higher Sysmon count, then dual-channel presence, then proximity to `anchor_time`

## safe_to_commit

yes — verification green 2026-06-30
