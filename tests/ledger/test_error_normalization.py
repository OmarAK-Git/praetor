"""Task 10 — ledger verification error normalization."""

from __future__ import annotations

import sqlite3

import pytest

from praetor.ledger.hash_chain import LedgerChainIntegrityError, verify_ledger_chain


def test_malformed_record_json_surfaces_integrity_error(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        INSERT INTO ledger_chain (
            record_type, record_json, ledger_previous_hash, ledger_current_hash
        ) VALUES ('decision_edict', '{not-json', NULL, 'abc')
        """
    )
    conn.commit()

    with pytest.raises(LedgerChainIntegrityError, match="malformed"):
        verify_ledger_chain(conn)


def test_missing_record_type_in_json_surfaces_integrity_error(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        INSERT INTO ledger_chain (
            record_type, record_json, ledger_previous_hash, ledger_current_hash
        ) VALUES ('decision_edict', '{"schema_version":"1"}', NULL, 'abc')
        """
    )
    conn.commit()

    with pytest.raises(LedgerChainIntegrityError, match="record_type"):
        verify_ledger_chain(conn)


def test_unknown_record_type_surfaces_integrity_error(
    conn: sqlite3.Connection,
) -> None:
    bogus_json = '{"schema_version":"1","record_type":"bogus_type"}'
    conn.execute(
        """
        INSERT INTO ledger_chain (
            record_type, record_json, ledger_previous_hash, ledger_current_hash
        ) VALUES ('bogus_type', ?, NULL, 'abc')
        """,
        (bogus_json,),
    )
    conn.commit()

    with pytest.raises(LedgerChainIntegrityError, match="bogus_type"):
        verify_ledger_chain(conn)


def test_missing_current_hash_surfaces_integrity_error(
    conn: sqlite3.Connection,
) -> None:
    partial_json = '{"schema_version":"1","record_type":"directive_revocation"}'
    conn.execute(
        """
        INSERT INTO ledger_chain (
            record_type, record_json, ledger_previous_hash, ledger_current_hash
        ) VALUES ('directive_revocation', ?, NULL, '')
        """,
        (partial_json,),
    )
    conn.commit()

    with pytest.raises(LedgerChainIntegrityError, match="contract validation"):
        verify_ledger_chain(conn)
