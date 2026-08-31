from __future__ import annotations

from .common import CheckResult, OK, WARN, FAIL, INFO, SKIP, run_command, command_text


def _service() -> CheckResult:
    for candidate in ("mariadb", "mysql", "mysqld"):
        cmd = ["systemctl", "is-active", candidate]
        rc, out, err, ms = run_command(cmd, timeout=4)
        if out.strip() == "active":
            return CheckResult("mariadb", "service", OK, f"{candidate}=active (실행 중)", command=command_text(cmd), duration_ms=ms)
    return CheckResult("mariadb", "service", WARN, "MariaDB/MySQL systemd 서비스가 실행 중이 아니거나 찾을 수 없음")


def _admin_ping(config: dict) -> CheckResult:
    enabled = bool(config.get("mariadb", {}).get("admin_ping", True))
    if not enabled:
        return CheckResult("mariadb", "admin-ping", SKIP, "설정에서 비활성화됨")
    cmd = ["mysqladmin", "ping", "--connect-timeout=3"]
    host = config.get("mariadb", {}).get("host")
    user = config.get("mariadb", {}).get("user")
    socket_path = config.get("mariadb", {}).get("socket")
    if host:
        cmd += ["--host", str(host)]
    if user:
        cmd += ["--user", str(user)]
    if socket_path:
        cmd += ["--socket", str(socket_path)]
    rc, out, err, ms = run_command(cmd, timeout=5)
    if rc == 127:
        return CheckResult("mariadb", "admin-ping", INFO, "mysqladmin이 설치되어 있지 않음", err, command_text(cmd), ms)
    status = OK if rc == 0 and "alive" in out.lower() else FAIL
    return CheckResult("mariadb", "admin-ping", status, out or "mysqladmin ping 실패", err, command_text(cmd), ms)


def _listener() -> CheckResult:
    cmd = ["ss", "-lntp"]
    rc, out, err, ms = run_command(cmd, timeout=5)
    if rc != 0:
        return CheckResult("mariadb", "listener", INFO, "소켓 정보를 확인할 수 없음", err, command_text(cmd), ms)
    matches = [line for line in out.splitlines() if ":3306" in line]
    return CheckResult("mariadb", "listener", OK if matches else WARN, "3306 포트 리스너 확인됨" if matches else "3306 포트 리스너가 확인되지 않음", "\n".join(matches[:10]), command_text(cmd), ms)


def run_mariadb_checks(config: dict) -> list[CheckResult]:
    return [_service(), _listener(), _admin_ping(config)]
