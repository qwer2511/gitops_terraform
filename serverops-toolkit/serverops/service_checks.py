from __future__ import annotations

from .common import CheckResult, OK, WARN, FAIL, INFO, run_command, command_text
from .os_compat import detect_local_profile, service_candidates


def _systemd_state(service: str):
    cmd = ["systemctl", "is-active", service]
    rc, out, err, ms = run_command(cmd, timeout=5)
    return rc, out.strip(), err.strip(), ms, cmd


def _sysv_state(service: str):
    cmd = ["service", service, "status"]
    rc, out, err, ms = run_command(cmd, timeout=5)
    state = "active" if rc == 0 else "inactive"
    return rc, state, err.strip() or out.strip(), ms, cmd


def check_service(service: str) -> CheckResult:
    profile = detect_local_profile()
    attempts = []
    for candidate in service_candidates(service, profile):
        if profile.init_system == "systemd":
            rc, state, err, ms, cmd = _systemd_state(candidate)
        elif profile.init_system == "sysv":
            rc, state, err, ms, cmd = _sysv_state(candidate)
        else:
            return CheckResult("service", service, INFO, "지원되는 서비스 관리 도구를 찾을 수 없음")
        attempts.append(f"{candidate}={state or 'unknown'}")
        if state == "active":
            return CheckResult("service", service, OK, f"{candidate}=active", err, command_text(cmd), ms)
        if state in {"failed", "activating"}:
            return CheckResult("service", service, FAIL, f"{candidate}={state}", err, command_text(cmd), ms)
    return CheckResult("service", service, WARN, " / ".join(attempts) or "서비스 상태 확인 불가")


def run_service_checks(config: dict) -> list[CheckResult]:
    return [check_service(str(service)) for service in config.get("services", [])]
