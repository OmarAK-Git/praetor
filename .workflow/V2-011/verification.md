# Verification — V2-011

## Commands (VS-0001)

```text
pip install -e ".[dev]"
python -m pytest -q --ignore=tests/splunk
python -m mypy src evals consumer_sdk
python -m ruff check src tests evals consumer_sdk
python -m evals.harness
```

## Results

| Check | Command | Result | Evidence time |
|---|---|---|---|
| pytest (core) | `python -m pytest -q --ignore=tests/splunk` | **792 passed**, 1 deselected, 1 xfailed | 2026-06-29 |
| pytest (full) | `python -m pytest -q` | **811 passed**, 2 splunk failures (baseline) | 2026-06-29 |
| mypy | `python -m mypy src evals consumer_sdk` | clean | 2026-06-29 |
| ruff | `python -m ruff check src tests evals consumer_sdk` | clean | 2026-06-29 |
| harness | `python -m evals.harness` | all scenarios PASS | 2026-06-29 |
