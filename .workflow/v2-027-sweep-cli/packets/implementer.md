# Implementer Packet — V2-027 Org-Config Sweep CLI

**implementation_model:** composer-2.5-fast

## Objective
CLI runs org-config sweep, writes proposed YAML + markdown report, exits non-zero on invalid inputs; proposed artifacts fail activation preflight; docs state sweep does not infer never-contain/subnet/containment policy.

## Verification
pytest tests/codification/ -q

Allowed: src/praetor/codification/, docs/operator_runbook.md, tests/codification/, specs/, IMPLEMENTATION_PLAN.md, memory-bank/

Write .workflow/v2-027-sweep-cli/results/implementer-result.md. Do NOT mark queue done.
