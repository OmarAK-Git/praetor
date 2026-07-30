# Fresh-Context Verification Packet

Goal: Emit an operator health warning when the append-only revocation feed exceeds a configured size threshold.

Acceptance:
- Above threshold queues `revocation_feed_file_size_warning` via the existing health outbox.
- Missing/below threshold emits no warning.
- Default database startup hook checks the configured default threshold.
- No rotation, truncation, segmentation, format, sequence, checksum, or actuation changes.

Changed paths are the three allowed paths in this run plan.
Implementation result and code review are under `results/`.
Commit: `03f62cb`

Run:
- `pytest tests/revocation/test_feed_exporter.py -v`
- `ruff check .`
- `mypy .`

Treat prior claims as unevidenced. Inspect the lazy-import reason and startup wiring independently. Verify task scope only. Remain read-only except for the verifier result.
