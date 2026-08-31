from __future__ import annotations

import socket

from .common import CheckResult, OK, WARN, FAIL, INFO, run_command, command_text


def _interfaces() -> CheckResult:
    cmd = ["ip", "-br", "addr"]
    rc, out, err, ms = run_command(cmd, timeout=5)
    if rc != 0:
        return CheckResult("network", "interfaces", INFO, "ip 명령어를 사용할 수 없음", err, command_text(cmd), ms)
    down = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].upper() == "DOWN" and parts[0] != "lo":
            down.append(parts[0])
    status = WARN if down else OK
    summary = f"DOWN 인터페이스: {', '.join(down)}" if down else "인터페이스 상태 확인 완료"
    return CheckResult("network", "interfaces", status, summary, out, command_text(cmd), ms)


def _default_route() -> CheckResult:
    cmd = ["ip", "route", "show", "default"]
    rc, out, err, ms = run_command(cmd, timeout=5)
    if rc != 0:
        return CheckResult("network", "default-route", INFO, "라우팅 정보를 확인할 수 없음", err, command_text(cmd), ms)
    status = OK if out else FAIL
    return CheckResult("network", "default-route", status, out or "기본 라우트 없음", out, command_text(cmd), ms)


def _dns(target: str) -> CheckResult:
    if not target:
        return CheckResult("network", "dns", INFO, "DNS 점검 대상이 설정되지 않음")
    try:
        addresses = sorted({item[4][0] for item in socket.getaddrinfo(target, 443, type=socket.SOCK_STREAM)})
        return CheckResult("network", "dns", OK, f"{target} DNS 조회 성공", ", ".join(addresses[:6]))
    except OSError as exc:
        return CheckResult("network", "dns", FAIL, f"{target} DNS 조회 실패", str(exc))


def _ping(target: str) -> CheckResult:
    cmd = ["ping", "-c", "1", "-W", "2", target]
    rc, out, err, ms = run_command(cmd, timeout=4)
    status = INFO if rc == 127 else (OK if rc == 0 else FAIL)
    detail = out.splitlines()[-2] if rc == 0 and len(out.splitlines()) >= 2 else (err or out)
    summary = "ping 명령어를 사용할 수 없음" if rc == 127 else ("응답 성공" if rc == 0 else "응답 실패")
    return CheckResult("network", f"ping:{target}", status, summary, detail, command_text(cmd), ms)


def _neighbors() -> CheckResult:
    cmd = ["ip", "neigh", "show"]
    rc, out, err, ms = run_command(cmd, timeout=5)
    if rc != 0:
        return CheckResult("network", "neighbors", INFO, "Neighbor 테이블을 확인할 수 없음", err, command_text(cmd), ms)
    failed = [line for line in out.splitlines() if "FAILED" in line]
    status = WARN if failed else OK
    return CheckResult("network", "neighbors", status, f"FAILED Neighbor 항목 {len(failed)}개", out[:6000], command_text(cmd), ms)


def run_network_checks(config: dict) -> list[CheckResult]:
    results = [_interfaces(), _default_route(), _dns(str(config.get("dns_target", ""))), _neighbors()]
    for target in config.get("ping_targets", []):
        results.append(_ping(str(target)))
    return results
