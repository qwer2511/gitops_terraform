from __future__ import annotations

import os
import shlex
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Iterable, Tuple


@dataclass
class CheckResult:
    category: str
    name: str
    status: str
    summary: str
    details: str = ""
    command: str = ""
    duration_ms: int = 0

    def to_dict(self):
        return asdict(self)


OK = "OK"
WARN = "WARN"
FAIL = "FAIL"
INFO = "INFO"
SKIP = "SKIP"


def run_command(command: Iterable[str], timeout: int = 8) -> Tuple[int, str, str, int]:
    args = list(command)
    start = time.monotonic()
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout, check=False)
        elapsed = int((time.monotonic() - start) * 1000)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip(), elapsed
    except FileNotFoundError:
        elapsed = int((time.monotonic() - start) * 1000)
        return 127, "", f"command not found: {args[0]}", elapsed
    except subprocess.TimeoutExpired as exc:
        elapsed = int((time.monotonic() - start) * 1000)
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        return 124, stdout.strip(), (stderr.strip() or f"timeout after {timeout}s"), elapsed


def command_text(command: Iterable[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def safe_read_text(path: str, limit: int = 100_000) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except OSError:
        return ""


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def is_root() -> bool:
    return hasattr(os, "geteuid") and os.geteuid() == 0
