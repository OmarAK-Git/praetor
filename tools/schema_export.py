"""Check or regenerate committed contract JSON Schema artifacts."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from praetor.contracts.schema_export import SCHEMA_EXPORTS, export_schemas

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMAS_DIR = REPO_ROOT / "schemas"


def check_schemas(schemas_dir: Path) -> list[str]:
    """Return drift messages when committed schemas differ from fresh export."""
    mismatches: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        export_schemas(out)
        for _, filename in SCHEMA_EXPORTS:
            expected_path = out / filename
            committed_path = schemas_dir / filename
            if not committed_path.is_file():
                rel = committed_path.relative_to(REPO_ROOT)
                mismatches.append(f"missing committed schema: {rel}")
                continue
            if committed_path.read_bytes() != expected_path.read_bytes():
                rel = committed_path.relative_to(REPO_ROOT)
                mismatches.append(f"schema drift: {rel}")
    return mismatches


def write_schemas(schemas_dir: Path) -> list[Path]:
    """Overwrite committed schema artifacts from current models."""
    return export_schemas(schemas_dir)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check or regenerate committed contract JSON Schema artifacts."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        action="store_true",
        help="Verify committed schemas/ match current model export",
    )
    mode.add_argument(
        "--write",
        action="store_true",
        help="Write current model export to schemas/",
    )
    parser.add_argument(
        "--schemas-dir",
        type=Path,
        default=DEFAULT_SCHEMAS_DIR,
        help="Directory for committed schema artifacts",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.write:
        for path in write_schemas(args.schemas_dir):
            print(path)
        return 0
    mismatches = check_schemas(args.schemas_dir)
    if mismatches:
        for mismatch in mismatches:
            print(mismatch, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
