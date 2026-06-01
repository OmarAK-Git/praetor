"""Test doubles for health alert outbox tests (not production API)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FailingJsonlSink:
    """JSONL sink that fails the first ``fail_count`` write attempts."""

    path: Path
    fail_count: int = 1
    channel: str = "jsonl"
    _attempts: int = 0

    def write_line(self, line: str) -> None:
        self._attempts += 1
        if self._attempts <= self.fail_count:
            msg = "simulated jsonl write failure"
            raise OSError(msg)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


@dataclass
class RuntimeErrorStdoutSink:
    """Stdout sink that raises a non-OSError failure."""

    channel: str = "stdout"

    def write_line(self, line: str) -> None:
        msg = "simulated stdout runtime failure"
        raise RuntimeError(msg)


@dataclass
class AppendOnlyJsonlSink:
    """JSONL sink that writes but simulates crash-before-record on first attempt."""

    path: Path
    channel: str = "jsonl"
    crash_before_record: bool = True
    _written_once: bool = field(default=False, init=False)

    def write_line(self, line: str) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        if self.crash_before_record and not self._written_once:
            self._written_once = True
            msg = "simulated crash after jsonl write before status record"
            raise OSError(msg)
