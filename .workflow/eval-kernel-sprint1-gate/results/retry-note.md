# Gate retry

Attempt 1 outcome: **gaps** — `mypy src evals consumer_sdk` exit 1 on two pre-existing capability-spike files identical to `master`.

T1 unblock (outside gate implementation; not src/tests):
- `evals/capability/spike_vertex_provider.py` — narrow `result["judgment"]` with `isinstance(..., ModelJudgment)`
- `evals/capability_spike.py` — remove unused `# type: ignore[arg-type]`

Fresh `mypy src evals consumer_sdk` after the fix: exit 0 (155 source files).
