from __future__ import annotations

import os
import shutil

from .common import CheckResult, OK, WARN, FAIL, INFO, run_command, command_text, safe_read_text


def _load_average() -> CheckResult:
    cpus = os.cpu_count() or 1
    try:
        one, five, fifteen = os.getloadavg()
    except (AttributeError, OSError):
        return CheckResult("system", "load-average", INFO, "시스템 부하 정보를 확인할 수 없음")
    ratio = one / cpus
    status = OK if ratio < 0.8 else WARN if ratio < 1.5 else FAIL
    return CheckResult("system", "load-average", status, f"1m={one:.2f}, 5m={five:.2f}, 15m={fifteen:.2f}, cpu={cpus}", f"CPU 1개당 1분 부하: {ratio:.2f}")


def _memory() -> CheckResult:
    data = safe_read_text("/proc/meminfo")
    values = {}
    for line in data.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        try:
            values[key] = int(value.strip().split()[0])
        except (ValueError, IndexError):
            continue
    total = values.get("MemTotal", 0)
    avail = values.get("MemAvailable", 0)
    if not total:
        return CheckResult("system", "memory", INFO, "메모리 정보를 확인할 수 없음")
    used_pct = (1 - (avail / total)) * 100
    status = OK if used_pct < 80 else WARN if used_pct < 90 else FAIL
    return CheckResult("system", "memory", status, f"사용률={used_pct:.1f}%", f"전체={total/1024/1024:.2f} GiB, 사용 가능={avail/1024/1024:.2f} GiB")


def _disk(paths):
    results = []
    seen = set()
    for path in paths:
        if not os.path.exists(path):
            continue
        usage = shutil.disk_usage(path)
        key = (usage.total, usage.used, usage.free)
        if key in seen:
            continue
        seen.add(key)
        used_pct = usage.used / usage.total * 100 if usage.total else 0
        status = OK if used_pct < 80 else WARN if used_pct < 90 else FAIL
        results.append(CheckResult("system", f"disk:{path}", status, f"사용률={used_pct:.1f}%", f"전체={usage.total/1024**3:.2f} GiB, 여유={usage.free/1024**3:.2f} GiB"))
    return results


def _uptime() -> CheckResult:
    cmd = ["uptime", "-p"]
    rc, out, err, ms = run_command(cmd, timeout=3)
    return CheckResult("system", "uptime", OK if rc == 0 else INFO, out or "가동 시간 정보를 확인할 수 없음", err, command_text(cmd), ms)


def _failed_systemd_units() -> CheckResult:
    cmd = ["systemctl", "--failed", "--no-legend", "--plain"]
    rc, out, err, ms = run_command(cmd, timeout=5)
    if rc not in (0, 1):
        return CheckResult("system", "failed-units", INFO, "systemd 상태를 확인할 수 없음", err, command_text(cmd), ms)
    lines = [line for line in out.splitlines() if line.strip()]
    status = OK if not lines else FAIL
    return CheckResult("system", "failed-units", status, "실패한 systemd 유닛 없음" if not lines else f"실패한 systemd 유닛 {len(lines)}개", "\n".join(lines[:20]), command_text(cmd), ms)


def run_system_checks(config: dict) -> list[CheckResult]:
    paths = config.get("disk_paths", ["/", "/var", "/home"])
    results = [_uptime(), _load_average(), _memory()]
    results.extend(_disk(paths))
    results.append(_failed_systemd_units())
    return results
