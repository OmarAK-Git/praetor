"""OS-level process singleton lock for single-writer Praetor instances."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import TracebackType

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

LOCK_FILENAME = ".praetor.lock"
DEFAULT_EXIT_CODE = 1


class SingletonLockError(Exception):
    """Raised when the singleton file lock cannot be acquired."""

    def __init__(self, message: str, *, exit_code: int = DEFAULT_EXIT_CODE) -> None:
        super().__init__(message)
        self.exit_code = exit_code


class SingletonLock:
    """Exclusive file lock held for process lifetime."""

    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir
        self._lock_path = state_dir / LOCK_FILENAME
        self._fd: int | None = None

    @property
    def is_held(self) -> bool:
        return self._fd is not None

    def acquire(self) -> None:
        if self._fd is not None:
            msg = f"singleton lock already held: {self._lock_path}"
            raise SingletonLockError(msg)

        self._state_dir.mkdir(parents=True, exist_ok=True)
        fd = os.open(self._lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            if os.fstat(fd).st_size == 0:
                try:
                    os.write(fd, b"\x00")
                except OSError as err:
                    msg = f"cannot acquire singleton lock: {self._lock_path}"
                    raise SingletonLockError(msg) from err
            os.lseek(fd, 0, os.SEEK_SET)
            self._try_exclusive_lock(fd)
        except SingletonLockError:
            os.close(fd)
            raise
        self._fd = fd

    def release(self) -> None:
        if self._fd is None:
            return
        fd = self._fd
        self._fd = None
        try:
            self._unlock(fd)
        finally:
            os.close(fd)

    def __enter__(self) -> SingletonLock:
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()

    def _try_exclusive_lock(self, fd: int) -> None:
        if sys.platform == "win32":
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError as err:
                msg = f"cannot acquire singleton lock: {self._lock_path}"
                raise SingletonLockError(msg) from err
            return

        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[name-defined]
        except BlockingIOError as err:
            msg = f"cannot acquire singleton lock: {self._lock_path}"
            raise SingletonLockError(msg) from err

    def _unlock(self, fd: int) -> None:
        if sys.platform == "win32":
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            return
        fcntl.flock(fd, fcntl.LOCK_UN)  # type: ignore[name-defined]
