"""Self-contained Phase 5 production throughput benchmark (Task 35).

Opens a temporary SQLite state DB, activates ``configs/example_org.yaml``, runs
``run_serialized_path_benchmark``, and prints measured sustained rate vs the
active org-config provisional targets. Safe to run on a fresh checkout with no
pre-existing ``state/bench.db``.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from benchmarks.serialized_path import run_serialized_path_benchmark

from praetor.auth.principal import Principal
from praetor.auth.verifier import PrincipalMapVerifier
from praetor.config.activation import activate_org_config

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_CONFIG = REPO_ROOT / "configs" / "example_org.yaml"
SOC_LEAD_TOKEN = "soc-lead-token"


def main(argv: list[str] | None = None) -> int:
    _ = argv
    operations = 30
    verifier = PrincipalMapVerifier(
        {SOC_LEAD_TOKEN: Principal(identity="soc-lead-1", role="soc_lead")}
    )
    with tempfile.TemporaryDirectory(prefix="praetor-phase5-bench-") as tmp:
        db_path = Path(tmp) / "bench.db"
        from praetor.state.store import open_state_store

        store = open_state_store(db_path)
        try:
            activate_org_config(
                store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier
            )
        finally:
            store.close()

        result = run_serialized_path_benchmark(db_path, operations=operations)

    print(f"operations={result.operations}")
    print(f"elapsed_seconds={result.elapsed_seconds:.3f}")
    print(f"sustained_alerts_per_minute={result.sustained_alerts_per_minute:.1f}")
    print(f"target_sustained={result.target_sustained}")
    print(f"target_burst={result.target_burst}")
    print(f"meets_sustained_target={result.meets_sustained_target}")
    print(f"burst_separately_measured={result.burst_separately_measured}")
    print(
        f"meets_burst_target_informational={result.meets_burst_target_informational}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
