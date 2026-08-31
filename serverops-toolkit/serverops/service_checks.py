from __future__ import annotations

from .common import CheckResult, OK, WARN, FAIL, INFO, run_command, command_text


def check_service(service: str) -> CheckResult:
    cmd = ["systemctl", "is-active", service]
    rc, out, err, ms = run_command(cmd, timeout=5)
    state = out.strip() or err.strip() or "unknown"
    if state == "active":
        status = OK
    elif state in {"inactive", "deactivating"}:
        status = WARN
    elif state in {"failed", "activating"}:
        status = FAIL
    else:
        status = INFO
    return CheckResult("service", service, status, f"상태={state}", err, command_text(cmd), ms)


def run_service_checks(config: dict) -> list[CheckResult]:
    return [check_service(str(service)) for service in config.get("services", [])]
