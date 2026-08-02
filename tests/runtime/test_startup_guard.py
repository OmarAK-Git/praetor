"""Task 5 startup guard — tests first per docs/plan.md."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from praetor.runtime.singleton import (
    DEFAULT_EXIT_CODE,
    SingletonLock,
    SingletonLockError,
)
from praetor.state.sqlite_guard import (
    StartupGuardError,
    create_guarded_connection,
    critical_transaction,
    init_state_dir,
    run_startup_sqlite_guard,
    verify_connection_isolation,
    verify_journal_mode,
    verify_synchronous,
)
from praetor.state.store import open_state_store


def _wal_db(path: Path) -> None:
    init_state_dir(path)


def _delete_journal_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.close()


class TestSingletonLock:
    def test_acquires_on_empty_state_dir(self, tmp_path: Path) -> None:
        lock = SingletonLock(tmp_path)
        lock.acquire()
        assert lock.is_held
        lock.release()

    def test_second_acquire_in_process_fails(self, tmp_path: Path) -> None:
        first = SingletonLock(tmp_path)
        second = SingletonLock(tmp_path)
        first.acquire()
        try:
            with pytest.raises(SingletonLockError) as exc_info:
                second.acquire()
            assert exc_info.value.exit_code != 0
        finally:
            first.release()

    def test_lock_held_until_released(self, tmp_path: Path) -> None:
        lock = SingletonLock(tmp_path)
        lock.acquire()
        try:
            assert lock.is_held
            blocker = SingletonLock(tmp_path)
            with pytest.raises(SingletonLockError):
                blocker.acquire()
        finally:
            lock.release()

    def test_context_manager_releases(self, tmp_path: Path) -> None:
        with SingletonLock(tmp_path) as lock:
            assert lock.is_held
        follow_up = SingletonLock(tmp_path)
        follow_up.acquire()
        follow_up.release()

    def test_second_process_blocked(self, tmp_path: Path) -> None:
        holder = SingletonLock(tmp_path)
        holder.acquire()
        try:
            script = textwrap.dedent(
                f"""
                import sys
                from pathlib import Path
                from praetor.runtime.singleton import SingletonLock, SingletonLockError
                try:
                    SingletonLock(Path({str(tmp_path)!r})).acquire()
                except SingletonLockError as exc:
                    sys.exit(exc.exit_code)
                sys.exit(0)
                """
            )
            result = subprocess.run(
                [sys.executable, "-c", script],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == DEFAULT_EXIT_CODE
        finally:
            holder.release()

    def test_release_allows_reacquire_in_process(self, tmp_path: Path) -> None:
        lock = SingletonLock(tmp_path)
        lock.acquire()
        lock.release()
        lock.acquire()
        lock.release()

    def test_release_allows_subprocess_reacquire(self, tmp_path: Path) -> None:
        lock = SingletonLock(tmp_path)
        lock.acquire()
        lock.release()
        script = textwrap.dedent(
            f"""
            import sys
            from pathlib import Path
            from praetor.runtime.singleton import SingletonLock, SingletonLockError
            try:
                SingletonLock(Path({str(tmp_path)!r})).acquire()
            except SingletonLockError as exc:
                sys.exit(exc.exit_code)
            sys.exit(0)
            """
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0

    def test_two_subprocesses_race_only_one_wins(self, tmp_path: Path) -> None:
        go_file = tmp_path / "go"
        ready1 = tmp_path / "ready1"
        ready2 = tmp_path / "ready2"
        # Winner must hold the lock long enough that the loser is forced to
        # contend; exiting immediately after acquire lets the OS release the
        # lock before the peer attempts, so both can exit 0 under load.
        script = textwrap.dedent(
            f"""
            import sys
            import time
            from pathlib import Path
            from praetor.runtime.singleton import SingletonLock, SingletonLockError

            state_dir = Path({str(tmp_path)!r})
            go = Path({str(go_file)!r})
            ready = Path(sys.argv[1])
            ready.touch()
            while not go.exists():
                time.sleep(0.001)
            lock = SingletonLock(state_dir)
            try:
                lock.acquire()
            except SingletonLockError as exc:
                sys.exit(exc.exit_code)
            time.sleep(0.5)
            sys.exit(0)
            """
        )
        repo_root = Path(__file__).resolve().parents[2]
        p1 = subprocess.Popen(
            [sys.executable, "-c", script, str(ready1)],
            cwd=repo_root,
        )
        p2 = subprocess.Popen(
            [sys.executable, "-c", script, str(ready2)],
            cwd=repo_root,
        )
        deadline = time.monotonic() + 30
        while not (ready1.exists() and ready2.exists()):
            if time.monotonic() > deadline:
                p1.kill()
                p2.kill()
                raise AssertionError("children did not become ready")
            time.sleep(0.001)
        go_file.touch()
        r1 = p1.wait(timeout=30)
        r2 = p2.wait(timeout=30)
        assert (r1 == 0) ^ (r2 == 0)
        loser = r1 if r2 == 0 else r2
        assert loser == DEFAULT_EXIT_CODE


class TestInitStateDir:
    def test_init_state_dir_sets_wal_persistently(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        init_state_dir(db_path)
        conn = sqlite3.connect(db_path)
        conn.isolation_level = None
        try:
            verify_journal_mode(conn)
        finally:
            conn.close()

    def test_init_state_dir_is_idempotent(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        init_state_dir(db_path)
        init_state_dir(db_path)
        conn = sqlite3.connect(db_path)
        conn.isolation_level = None
        try:
            verify_journal_mode(conn)
            verify_synchronous(conn)
        finally:
            conn.close()

    def test_init_state_dir_restores_guard_after_sync_off(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        conn = sqlite3.connect(db_path)
        conn.isolation_level = None
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=OFF")
        try:
            with pytest.raises(StartupGuardError):
                verify_synchronous(conn)
        finally:
            conn.close()
        init_state_dir(db_path)
        guarded = create_guarded_connection(db_path)
        try:
            verify_journal_mode(guarded)
            verify_synchronous(guarded)
        finally:
            guarded.close()


class TestJournalMode:
    def test_non_wal_rejected(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        _delete_journal_db(db_path)
        conn = sqlite3.connect(db_path)
        conn.isolation_level = None
        try:
            with pytest.raises(StartupGuardError) as exc_info:
                verify_journal_mode(conn)
            assert exc_info.value.exit_code != 0
        finally:
            conn.close()

    def test_wal_accepted(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        _wal_db(db_path)
        conn = sqlite3.connect(db_path)
        conn.isolation_level = None
        try:
            verify_journal_mode(conn)
        finally:
            conn.close()


class TestSynchronous:
    def test_synchronous_off_rejected(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        _wal_db(db_path)
        conn = sqlite3.connect(db_path)
        conn.isolation_level = None
        conn.execute("PRAGMA synchronous=OFF")
        try:
            with pytest.raises(StartupGuardError) as exc_info:
                verify_synchronous(conn)
            assert exc_info.value.exit_code != 0
        finally:
            conn.close()

    def test_synchronous_normal_accepted(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        _wal_db(db_path)
        conn = sqlite3.connect(db_path)
        conn.isolation_level = None
        conn.execute("PRAGMA synchronous=NORMAL")
        try:
            verify_synchronous(conn)
        finally:
            conn.close()

    def test_synchronous_full_accepted(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        _wal_db(db_path)
        conn = sqlite3.connect(db_path)
        conn.isolation_level = None
        try:
            verify_synchronous(conn)
        finally:
            conn.close()


class TestConnectionIsolation:
    def test_default_isolation_rejected(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        _wal_db(db_path)
        conn = sqlite3.connect(db_path)
        try:
            with pytest.raises(StartupGuardError):
                verify_connection_isolation(conn)
        finally:
            conn.close()

    def test_guarded_connection_sets_explicit_isolation(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        _wal_db(db_path)
        conn = create_guarded_connection(db_path)
        try:
            verify_connection_isolation(conn)
        finally:
            conn.close()


class TestCriticalTransaction:
    def test_begin_immediate_used(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        _wal_db(db_path)
        conn = create_guarded_connection(db_path)
        conn.execute("CREATE TABLE probe (id INTEGER PRIMARY KEY)")
        try:
            with critical_transaction(conn):
                conn.execute("INSERT INTO probe (id) VALUES (1)")
            row = conn.execute("SELECT id FROM probe").fetchone()
            assert row == (1,)
        finally:
            conn.close()

    def test_critical_transaction_rolls_back_on_error(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        _wal_db(db_path)
        conn = create_guarded_connection(db_path)
        conn.execute("CREATE TABLE probe (id INTEGER PRIMARY KEY)")
        try:
            with pytest.raises(RuntimeError):
                with critical_transaction(conn):
                    conn.execute("INSERT INTO probe (id) VALUES (1)")
                    raise RuntimeError("abort")
            assert conn.execute("SELECT COUNT(*) FROM probe").fetchone() == (0,)
        finally:
            conn.close()

    def test_nested_critical_transaction_raises(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        _wal_db(db_path)
        conn = create_guarded_connection(db_path)
        conn.execute("CREATE TABLE probe (id INTEGER PRIMARY KEY)")
        try:
            with critical_transaction(conn):
                with pytest.raises(
                    StartupGuardError, match="nested critical_transaction"
                ):
                    with critical_transaction(conn):
                        pass
        finally:
            conn.close()

    def test_sentinel_cleared_after_rollback(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        _wal_db(db_path)
        conn = create_guarded_connection(db_path)
        conn.execute("CREATE TABLE probe (id INTEGER PRIMARY KEY)")
        try:
            with pytest.raises(RuntimeError):
                with critical_transaction(conn):
                    conn.execute("INSERT INTO probe (id) VALUES (1)")
                    raise RuntimeError("abort")
            with critical_transaction(conn):
                conn.execute("INSERT INTO probe (id) VALUES (2)")
            assert conn.execute("SELECT id FROM probe").fetchone() == (2,)
        finally:
            conn.close()


class TestStartupGuard:
    def test_run_startup_guard_opens_wal_db(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        _wal_db(db_path)
        with SingletonLock(tmp_path) as lock:
            conn = run_startup_sqlite_guard(db_path, singleton=lock)
            try:
                verify_journal_mode(conn)
                verify_connection_isolation(conn)
                verify_synchronous(conn)
            finally:
                conn.close()

    def test_run_startup_guard_rejects_non_wal(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        _delete_journal_db(db_path)
        with SingletonLock(tmp_path) as lock:
            with pytest.raises(StartupGuardError):
                run_startup_sqlite_guard(db_path, singleton=lock)

    def test_run_startup_guard_rejects_uninitialized_db(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        with SingletonLock(tmp_path) as lock:
            with pytest.raises(StartupGuardError) as exc_info:
                run_startup_sqlite_guard(db_path, singleton=lock)
            assert exc_info.value.exit_code != 0

    def test_open_state_store_with_unheld_singleton_fails_closed(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "state.db"
        init_state_dir(db_path)
        lock = SingletonLock(tmp_path)

        with pytest.raises(StartupGuardError, match="singleton lock"):
            open_state_store(db_path, singleton=lock)

    def test_open_state_store_with_singleton_rejects_non_wal(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "state.db"
        _delete_journal_db(db_path)

        with SingletonLock(tmp_path) as lock:
            with pytest.raises(StartupGuardError, match="journal_mode"):
                open_state_store(db_path, singleton=lock)
