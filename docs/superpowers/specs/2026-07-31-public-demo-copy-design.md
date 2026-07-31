# Public-facing demo copy design

## Goal

Make `demo/index.html` (and the shared scenario registry behind it) readable to a
security leader / SOC manager who knows SOC concepts but not Praetor internals.

## Audience

Security leader / SOC manager. Allowed: containment, alert, analyst, allowlist,
rate limit, circuit breaker. Disallowed in panel prose: PolicyGate, edict,
preflight, provenance_path, system_fault_escalation, "seeded evaluation rows".

## Approach

Rewrite shared scenario copy in `notebooks/walkthrough_scenarios.py`. Rename the
three panel headings from Architecture / Wiring / Gotcha to:

- **What happens**
- **Setup**
- **Why it matters**

Keep real engine output under a clearer title (**What the engine printed**). Do
not change scenario keys or assertions — only public-facing strings and labels.

## Success

Someone who built Praetor should not need to re-decode a panel they already
understand. A SOC manager should get the decision and the constraint in one
screen.
