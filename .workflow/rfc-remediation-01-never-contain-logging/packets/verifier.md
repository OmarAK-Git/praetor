# Fresh-Context Verification Packet

Queue item: `rfc-remediation-01-never-contain-logging`

Goal: Log malformed never-contain entries on both defensive matcher skip branches without changing matching or authorization outcomes.

Acceptance criteria:
1. Both malformed-entry branches emit a warning through `praetor.config.live`.
2. Valid entries emit no warning and matching behavior remains unchanged.
3. No disposition, authorization, or never-contain semantics change.

Changed implementation paths:
- `src/praetor/config/live.py`
- `tests/config/test_live_never_contain_matching.py`

Implementation result: `.workflow/rfc-remediation-01-never-contain-logging/results/implementer-result.md`
Code review: `.workflow/rfc-remediation-01-never-contain-logging/results/code-review.md`
Commit: `1f541fb8fc7094fa2c102ee8198d350e997527ff`

Commands:
- `pytest tests/config/test_live_never_contain_matching.py -v`
- `ruff check .`
- `mypy .`

Treat all implementer and reviewer claims as unevidenced until independently checked. Verify only this task's acceptance criteria; ignore phase-level gaps. Remain read-only except for `.workflow/rfc-remediation-01-never-contain-logging/results/verifier-result.md`.
