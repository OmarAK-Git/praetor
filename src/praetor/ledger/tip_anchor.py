"""Optional out-of-band ledger tip anchor verification (AG-0027)."""

from __future__ import annotations

import sqlite3

from praetor.ledger.hash_chain import LedgerChainIntegrityError
from praetor.ledger.store import fetch_ledger_tip_hash


class LedgerTipAnchorMismatchError(LedgerChainIntegrityError):
    """Raised when the live ledger tip hash does not match the operator anchor."""


def verify_ledger_tip_against_anchor(
    conn: sqlite3.Connection,
    *,
    expected_tip_hash: str | None,
) -> None:
    """Compare live tip hash to an operator-supplied anchor.

    When ``expected_tip_hash`` is ``None``, the check is skipped (optional hook).
    """
    if expected_tip_hash is None:
        return
    actual = fetch_ledger_tip_hash(conn)
    if actual != expected_tip_hash:
        msg = "ledger tip hash does not match operator-supplied anchor"
        raise LedgerTipAnchorMismatchError(msg)
