"""Export the hash-chained audit ledger as newline-delimited JSON.

Read-only dump of ``ledger_chain`` for external ingestion (e.g. Azure Data
Explorer's native JSON/NDJSON ingest). One JSON object per line; each object
carries the chain-lineage fields (``chain_sequence``, ``ledger_previous_hash``,
``ledger_current_hash``) alongside the decoded record fields so a Kusto table
can index on either.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from praetor.ledger.store import fetch_ledger_rows


def export_ledger_jsonl(db_path: Path, out: Path | None) -> int:
    """Write ledger_chain rows as JSONL to ``out`` (or stdout). Returns row count."""
    uri = f"file:{db_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = fetch_ledger_rows(conn)
    finally:
        conn.close()

    handle = out.open("w", encoding="utf-8") if out is not None else sys.stdout
    try:
        for row in rows:
            record = json.loads(row.record_json)
            line = {
                "chain_sequence": row.chain_sequence,
                "ledger_previous_hash": row.ledger_previous_hash,
                "ledger_current_hash": row.ledger_current_hash,
                **record,
            }
            handle.write(json.dumps(line, sort_keys=True) + "\n")
    finally:
        if out is not None:
            handle.close()
    return len(rows)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the ledger_chain table as JSONL for external ingestion."
    )
    parser.add_argument(
        "--db",
        type=Path,
        required=True,
        help="Path to the SQLite state database (e.g. state/production.db)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output .jsonl path (default: stdout)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    count = export_ledger_jsonl(args.db, args.out)
    print(f"exported {count} ledger records", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
