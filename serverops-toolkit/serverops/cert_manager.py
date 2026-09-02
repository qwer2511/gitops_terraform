from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional

from .audit import write_audit
from .inventory import ServerEntry
from .ssh_client import SSHResult, run_ssh

SERVICE_RE = re.compile(r"^[A-Za-z0-9@_.-]+$")


@dataclass
class CertificateReplaceRequest:
    name: str
    current_cert: str
    new_cert: str
    service: str
    current_key: str = ""
    new_key: str = ""
    service_action: str = "restart"
    use_sudo: bool = True
    log_lines: int = 80


@dataclass
class CertificateStep:
    name: str
    ok: bool
    message: str
    details: str = ""


@dataclass
class CertificateReplaceResult:
    ok: bool
    name: str
    backup_cert: str = ""
    backup_key: str = ""
    rolled_back: bool = False
    steps: List[CertificateStep] = field(default_factory=list)
    service_log: str = ""
    final_certificate: str = ""

    def text_log(self) -> str:
        rows = []
        for index, step in enumerate(self.steps, 1):
            mark = "OK" if step.ok else "FAIL"
            rows.append(f"[{index:02d}] [{mark}] {step.name} - {step.message}")
            if step.details:
                rows.extend(f"     {line}" for line in step.details.splitlines())
        if self.service_log:
            rows.append("\n--- 서비스 로그 ---")
            rows.append(self.service_log)
        if self.final_certificate:
            rows.append("\n--- 적용 인증서 ---")
            rows.append(self.final_certificate)
        return "\n".join(rows)


def _validate_path(path: str, label: str, *, optional: bool = False) -> str:
    value = (path or "").strip()
    if optional and not value:
        return ""
    if not value:
        raise ValueError(f"{label} 경로가 비어 있습니다.")
    if "\n" in value or "\r" in value or "\x00" in value:
        raise ValueError(f"{label} 경로에 사용할 수 없는 문자가 있습니다.")
    if not value.startswith("/"):
        raise ValueError(f"{label} 경로는 원격 서버의 절대경로로 입력하세요: {value}")
    return value


def validate_request(req: CertificateReplaceRequest) -> CertificateReplaceRequest:
    req.name = (req.name or "인증서").strip() or "인증서"
    req.current_cert = _validate_path(req.current_cert, "기존 인증서")
    req.new_cert = _validate_path(req.new_cert, "새 인증서")
    req.current_key = _validate_path(req.current_key, "기존 개인키", optional=True)
    req.new_key = _validate_path(req.new_key, "새 개인키", optional=True)
    if req.current_cert == req.new_cert:
        raise ValueError("기존 인증서 경로와 새 인증서 경로는 달라야 합니다.")
    req.service = (req.service or "").strip()
    if not req.service or not SERVICE_RE.fullmatch(req.service):
        raise ValueError("서비스 이름은 영문/숫자와 @ _ . - 만 사용할 수 있습니다.")
    req.service_action = (req.service_action or "restart").strip().lower()
    if req.service_action not in {"restart", "reload", "auto"}:
        raise ValueError("service_action은 restart, reload, auto 중 하나여야 합니다.")
    if bool(req.current_key) != bool(req.new_key):
        if req.current_key and not req.new_key:
            pass
        else:
            raise ValueError("새 개인키를 교체하려면 기존 개인키 경로도 입력해야 합니다.")
    req.log_lines = max(10, min(int(req.log_lines or 80), 500))
    return req


def planned_steps(req: CertificateReplaceRequest) -> List[str]:
    validate_request(req)
    steps = [
        "새 인증서 파일 존재 여부 확인",
        "OpenSSL로 새 인증서 형식/만료일 확인",
    ]
    if req.current_key:
        steps.append("새 인증서와 개인키의 공개키 일치 여부 확인")
    steps += [
        "원격 서버 시간 기준 YYYYMMDD_HHMMSS 백업명 생성",
        "기존 인증서를 cp -a로 백업",
    ]
    if req.current_key and req.new_key:
        steps.append("기존 개인키를 cp -a로 백업")
    steps.append("새 인증서를 기존 경로에 적용하고 기존 소유권/권한 복원")
    if req.current_key and req.new_key:
        steps.append("새 개인키를 기존 경로에 적용하고 기존 소유권/권한 복원")
    steps += [
        "Nginx/Apache/HAProxy 등 알려진 서비스이면 설정 검사",
        f"systemd 서비스 {req.service_action} 실행",
        "systemctl is-active로 서비스 상태 확인",
        "실패 시 백업본 자동 롤백",
        f"journalctl 최근 {req.log_lines}줄 수집",
        "최종 적용 인증서 정보 다시 확인",
    ]
    return steps


def _quote(value: str) -> str:
    return shlex.quote(value)


def _root_command(command: str, use_sudo: bool) -> str:
    if not use_sudo:
        return command
    quoted = shlex.quote(command)
    return (
        'if [ "$(id -u)" -eq 0 ]; then sh -c ' + quoted +
        '; elif command -v sudo >/dev/null 2>&1; then sudo -n sh -c ' + quoted +
        '; else echo "root 권한이 필요하지만 sudo를 찾을 수 없습니다." >&2; exit 126; fi'
    )


def _run(server: ServerEntry, command: str, *, timeout: int = 30,
         runner: Callable[[ServerEntry, str, int], SSHResult] = run_ssh) -> SSHResult:
    return runner(server, command, timeout)


def _step(result: CertificateReplaceResult, name: str, ssh: SSHResult, success_message: str) -> bool:
    ok = ssh.returncode == 0
    details = ssh.stdout or ssh.stderr
    result.steps.append(CertificateStep(
        name,
        ok,
        success_message if ok else (ssh.stderr or ssh.stdout or "명령 실패"),
        details if ok else "",
    ))
    return ok


def _cert_info_command(path: str) -> str:
    p = _quote(path)
    return f"openssl x509 -in {p} -noout -subject -issuer -serial -startdate -enddate -fingerprint -sha256"


def _key_match_command(cert: str, key: str) -> str:
    c = _quote(cert)
    k = _quote(key)
    return (
        "set -eu; "
        f"c=$(openssl x509 -in {c} -pubkey -noout 2>/dev/null | openssl pkey -pubin -outform DER 2>/dev/null | openssl dgst -sha256 | awk '{{print $NF}}'); "
        f"k=$(openssl pkey -in {k} -pubout -outform DER 2>/dev/null | openssl dgst -sha256 | awk '{{print $NF}}'); "
        '[ -n "$c" ] && [ "$c" = "$k" ] && echo "certificate/key public key match"'
    )


def _config_test_command(service: str) -> Optional[str]:
    base = service.lower()
    if base.endswith(".service"):
        base = base[:-8]
    base = base.split("@")[0]
    if base == "nginx":
        return "nginx -t"
    if base in {"httpd", "apache"}:
        return "(command -v apachectl >/dev/null 2>&1 && apachectl configtest) || httpd -t"
    if base == "apache2":
        return "(command -v apache2ctl >/dev/null 2>&1 && apache2ctl configtest) || apachectl configtest"
    if base == "haproxy":
        return "haproxy -c -f /etc/haproxy/haproxy.cfg"
    return None


def _service_command(service: str, action: str) -> str:
    svc = _quote(service)
    if action == "auto":
        return f"systemctl reload {svc} || systemctl restart {svc}"
    return f"systemctl {action} {svc}"


def preflight_certificate(server: ServerEntry, req: CertificateReplaceRequest, *,
                          runner: Callable[[ServerEntry, str, int], SSHResult] = run_ssh) -> CertificateReplaceResult:
    validate_request(req)
    result = CertificateReplaceResult(False, req.name)

    exists = _run(server, f"test -f {_quote(req.new_cert)} && test -f {_quote(req.current_cert)}", runner=runner)
    if not _step(result, "파일 확인", exists, "기존/새 인증서 파일 확인 완료"):
        return result

    info_command = _cert_info_command(req.new_cert) + f" && openssl x509 -in {_quote(req.new_cert)} -checkend 0 -noout"
    info = _run(server, info_command, runner=runner)
    if not _step(result, "새 인증서 검사", info, "OpenSSL 인증서 검사 통과"):
        return result

    if req.current_key:
        key_to_check = req.new_key or req.current_key
        key_exists = _run(server, f"test -f {_quote(key_to_check)}", runner=runner)
        if not _step(result, "개인키 파일 확인", key_exists, "개인키 파일 확인 완료"):
            return result
        match = _run(server, _key_match_command(req.new_cert, key_to_check), runner=runner)
        if not _step(result, "인증서/개인키 일치", match, "인증서와 개인키가 일치합니다."):
            return result

    service_check = (
        f"command -v systemctl >/dev/null 2>&1 && "
        f"state=$(systemctl show {_quote(req.service)} -p LoadState --value 2>/dev/null) && "
        '[ -n "$state" ] && [ "$state" != "not-found" ]'
    )
    svc = _run(server, service_check, runner=runner)
    if not _step(result, "서비스 확인", svc, f"{req.service} 서비스를 확인했습니다."):
        return result

    result.ok = True
    result.final_certificate = info.stdout
    return result


def replace_certificate(server: ServerEntry, req: CertificateReplaceRequest, *,
                        runner: Callable[[ServerEntry, str, int], SSHResult] = run_ssh) -> CertificateReplaceResult:
    validate_request(req)
    result = preflight_certificate(server, req, runner=runner)
    if not result.ok:
        write_audit("certificate:replace", server.display_target, False,
                    details={"name": req.name, "stage": "preflight"})
        return result

    result.ok = False
    stamp_res = _run(server, "date +%Y%m%d_%H%M%S", runner=runner)
    stamp = stamp_res.stdout.strip() if stamp_res.returncode == 0 and stamp_res.stdout.strip() else datetime.now().strftime("%Y%m%d_%H%M%S")
    if not re.fullmatch(r"\d{8}_\d{6}", stamp):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result.backup_cert = f"{req.current_cert}.{stamp}.bak"
    result.backup_key = f"{req.current_key}.{stamp}.bak" if req.current_key and req.new_key else ""
    result.steps.append(CertificateStep("백업 이름 생성", True, stamp))

    backup = _run(server, _root_command(
        f"cp -a -- {_quote(req.current_cert)} {_quote(result.backup_cert)}", req.use_sudo), runner=runner)
    if not _step(result, "기존 인증서 백업", backup, result.backup_cert):
        return result

    if req.current_key and req.new_key:
        key_backup = _run(server, _root_command(
            f"cp -a -- {_quote(req.current_key)} {_quote(result.backup_key)}", req.use_sudo), runner=runner)
        if not _step(result, "기존 개인키 백업", key_backup, result.backup_key):
            return result

    def rollback(reason: str) -> None:
        commands = [f"cp -pf -- {_quote(result.backup_cert)} {_quote(req.current_cert)}"]
        if result.backup_key:
            commands.append(f"cp -pf -- {_quote(result.backup_key)} {_quote(req.current_key)}")
        commands.append(f"command -v restorecon >/dev/null 2>&1 && restorecon -F {_quote(req.current_cert)} || true")
        if req.current_key:
            commands.append(f"command -v restorecon >/dev/null 2>&1 && restorecon -F {_quote(req.current_key)} || true")
        rb = _run(server, _root_command("; ".join(commands), req.use_sudo), timeout=45, runner=runner)
        result.rolled_back = rb.returncode == 0
        result.steps.append(CertificateStep(
            "자동 롤백", result.rolled_back,
            reason if result.rolled_back else "롤백 실패", rb.stderr or rb.stdout))
        if result.rolled_back:
            recover = _run(server, _root_command(
                f"systemctl restart {_quote(req.service)}", req.use_sudo), timeout=60, runner=runner)
            result.steps.append(CertificateStep(
                "롤백 후 서비스 복구", recover.returncode == 0,
                "서비스 재기동 완료" if recover.returncode == 0 else "서비스 복구 재기동 실패",
                recover.stderr or recover.stdout))

    apply_commands = [
        f"cp -f -- {_quote(req.new_cert)} {_quote(req.current_cert)}",
        f"chown --reference={_quote(result.backup_cert)} {_quote(req.current_cert)}",
        f"chmod --reference={_quote(result.backup_cert)} {_quote(req.current_cert)}",
        f"command -v restorecon >/dev/null 2>&1 && restorecon -F {_quote(req.current_cert)} || true",
    ]
    if req.current_key and req.new_key:
        apply_commands += [
            f"cp -f -- {_quote(req.new_key)} {_quote(req.current_key)}",
            f"chown --reference={_quote(result.backup_key)} {_quote(req.current_key)}",
            f"chmod --reference={_quote(result.backup_key)} {_quote(req.current_key)}",
            f"command -v restorecon >/dev/null 2>&1 && restorecon -F {_quote(req.current_key)} || true",
        ]
    apply_res = _run(server, _root_command("set -e; " + "; ".join(apply_commands), req.use_sudo),
                     timeout=45, runner=runner)
    if not _step(result, "새 인증서 적용", apply_res, "기존 경로에 새 인증서를 적용했습니다."):
        rollback("인증서 적용 실패로 백업본을 복원했습니다.")
        return result

    config_test = _config_test_command(req.service)
    if config_test:
        test_res = _run(server, _root_command(config_test, req.use_sudo), timeout=45, runner=runner)
        if not _step(result, "서비스 설정 검사", test_res, "서비스 설정 검사를 통과했습니다."):
            rollback("설정 검사 실패로 백업본을 복원했습니다.")
            return result
    else:
        result.steps.append(CertificateStep(
            "서비스 설정 검사", True, "알려진 전용 검사 명령이 없어 건너뜁니다."))

    action_res = _run(server, _root_command(
        _service_command(req.service, req.service_action), req.use_sudo), timeout=90, runner=runner)
    if not _step(result, "서비스 재적용", action_res, f"{req.service} {req.service_action} 완료"):
        rollback("서비스 재적용 실패로 백업본을 복원했습니다.")
        return result

    active = _run(server, f"systemctl is-active {_quote(req.service)}", timeout=20, runner=runner)
    if not _step(result, "서비스 상태 확인", active, "서비스가 active 상태입니다."):
        rollback("서비스가 active 상태가 아니어서 백업본을 복원했습니다.")
        return result

    final = _run(server, _cert_info_command(req.current_cert), runner=runner)
    if not _step(result, "적용 인증서 재확인", final, "적용된 인증서 정보를 확인했습니다."):
        rollback("최종 인증서 확인 실패로 백업본을 복원했습니다.")
        write_audit("certificate:replace", server.display_target, False,
                    details={"name": req.name, "stage": "final-verify", "rolled_back": result.rolled_back})
        return result
    result.final_certificate = final.stdout

    log_cmd = f"journalctl -u {_quote(req.service)} -n {req.log_lines} --no-pager --output=short-iso 2>&1 || true"
    logs = _run(server, _root_command(log_cmd, req.use_sudo), timeout=30, runner=runner)
    result.service_log = logs.stdout or logs.stderr
    result.steps.append(CertificateStep("서비스 로그 수집", True, f"journalctl 최근 {req.log_lines}줄 수집"))

    result.ok = True
    write_audit("certificate:replace", server.display_target, True, details={
        "name": req.name,
        "current_cert": req.current_cert,
        "backup_cert": result.backup_cert,
        "service": req.service,
        "service_action": req.service_action,
        "key_replaced": bool(req.current_key and req.new_key),
    })
    return result
