from __future__ import annotations

import socket
import time

from .common import CheckResult, OK, FAIL


def check_tcp(host: str, port: int, timeout: float = 2.0) -> CheckResult:
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            elapsed = int((time.monotonic() - start) * 1000)
            return CheckResult("port", f"{host}:{port}", OK, "TCP 연결 성공", duration_ms=elapsed)
    except OSError as exc:
        elapsed = int((time.monotonic() - start) * 1000)
        return CheckResult("port", f"{host}:{port}", FAIL, "TCP 연결 실패", str(exc), duration_ms=elapsed)


def run_port_checks(config: dict) -> list[CheckResult]:
    results = []
    for item in config.get("ports", []):
        try:
            host = str(item.get("host", "127.0.0.1"))
            port = int(item["port"])
        except (KeyError, TypeError, ValueError):
            continue
        results.append(check_tcp(host, port))
    return results
