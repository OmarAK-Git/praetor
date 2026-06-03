"""Internal outstanding-directive lifecycle (not a public API)."""

from __future__ import annotations

import sqlite3

from praetor.contracts.containment import ContainmentDirective
from praetor.state.sqlite_guard import critical_transaction


def commit_outstanding_directive(
    conn: sqlite3.Connection,
    directive: ContainmentDirective,
) -> None:
    """Record a committed directive for reconciliation scans (internal/tests)."""
    with critical_transaction(conn):
        conn.execute(
            """
            INSERT INTO outstanding_containment_directives (
                directive_id, directive_json, issued_at, expires_at,
                target_type, target_id, revoked
            ) VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (
                directive.directive_id,
                directive.model_dump_json(),
                directive.issued_at.isoformat(),
                directive.expires_at.isoformat(),
                directive.target_type.value,
                directive.target_id,
            ),
        )
