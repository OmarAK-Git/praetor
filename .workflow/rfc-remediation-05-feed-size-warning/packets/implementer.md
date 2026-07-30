# Implementer Packet

Implement source plan Task 5 with TDD.

Read this run plan, source plan Task 5, current exporter/startup tests, `docs/contracts.md` feed boundaries, and the feed/startup/outbox entries in the playbook digest.

Boundaries:
- Modify only the three allowed files, plus result artifact and exact task commit.
- Use the existing `SystemHealthAlert` + `write_pending_health_alert` path.
- Do not rotate, truncate, segment, rewrite, or otherwise modify the feed file.
- Do not change JSONL format, sequence/checksum behavior, `is_feed_actuation_blocked`, disposition, authorization, or DEC-053 ordering.
- Do not add dependencies, fault flags, tables, or unrelated cleanup.
- Preserve unrelated working-tree changes; do not edit the queue.

Use the source plan's threshold constant and defaulted signatures, adapting only to current repository APIs. Demonstrate red tests, implement helper and startup wiring, run the full exporter test file plus ruff/mypy, self-review, and commit only allowed files with the plan's Task 5 commit message.

The tests must cover above-threshold, below-threshold, and default startup-hook wiring (not just direct helper behavior).

Write `.workflow/rfc-remediation-05-feed-size-warning/results/implementer-result.md`; return status, commit, checks, and concerns.
