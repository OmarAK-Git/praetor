# RFC Remediation 05 — Feed Size Warning

Goal: Emit an operator health warning when the append-only revocation feed exceeds a configured size threshold.

Allowed files:
- `src/praetor/config/constants.py`
- `src/praetor/revocation/exporter.py`
- `tests/revocation/test_feed_exporter.py`

Acceptance:
1. Above-threshold feed queues `revocation_feed_file_size_warning` through the existing health-alert outbox.
2. Missing or below-threshold feed emits no warning.
3. Default database startup hook checks the configured threshold.
4. No rotation, truncation, segmentation, feed-format, sequence, checksum, or actuation-state changes.

Verification:
- `pytest tests/revocation/test_feed_exporter.py -v`
- `ruff check .`
- `mypy .`

Source plan: Task 5 of the reverse-spec RFC remediation plan.

Research decision: no researcher dispatch; the approved design mandates the existing durable health-alert outbox and explicitly forbids alternate rotation designs.
