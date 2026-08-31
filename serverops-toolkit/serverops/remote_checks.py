from __future__ import annotations

from typing import Dict, List

from .common import CheckResult, FAIL, INFO, OK, SKIP, WARN
from .inventory import ServerEntry
from .os_compat import OSProfile, family_from_release, parse_os_release, service_candidates
from .ssh_client import SSHClientError, run_ssh, shell_quote
from .audit import write_audit


def _result(category: str, name: str, command: str, server: ServerEntry, *, timeout: int = 15, ok_rc=(0,)) -> CheckResult:
    res = run_ssh(server, command, timeout=timeout)
    if res.returncode == 124:
        return CheckResult(category, name, FAIL, "SSH 명령 시간 초과", res.stderr, res.command_display, res.duration_ms)
    status = OK if res.returncode in ok_rc else FAIL
    summary = res.stdout.splitlines()[0][:180] if res.stdout else (res.stderr.splitlines()[0][:180] if res.stderr else f"exit={res.returncode}")
    return CheckResult(category, name, status, summary, res.stdout or res.stderr, res.command_display, res.duration_ms)


def probe_remote_os(server: ServerEntry) -> OSProfile:
    res = run_ssh(server, "cat /etc/os-release 2>/dev/null || true", timeout=10)
    data = parse_os_release(res.stdout)
    family = family_from_release(data)
    tools = run_ssh(server, "for x in systemctl service dnf yum apt-get zypper apk firewall-cmd ufw nft ip ifconfig ss netstat; do command -v $x >/dev/null 2>&1 && echo $x; done", timeout=10)
    present = set(tools.stdout.split())
    init = "systemd" if "systemctl" in present else "sysv" if "service" in present else "unknown"
    package = next((x for x in ("dnf", "yum", "apt-get", "zypper", "apk") if x in present), "unknown")
    firewall = next((x for x in ("firewall-cmd", "ufw", "nft") if x in present), "unknown")
    return OSProfile(os_id=data.get("ID", "unknown").lower(), name=data.get("PRETTY_NAME") or data.get("NAME") or "Linux", version_id=data.get("VERSION_ID", ""), id_like=data.get("ID_LIKE", "").split(), family=family, init_system=init, package_manager=package, firewall_tool=firewall)


def connection_check(server: ServerEntry) -> List[CheckResult]:
    res = run_ssh(server, "printf 'SERVEROPS_OK\\n'; hostname; uname -sr", timeout=10)
    if res.returncode != 0 or "SERVEROPS_OK" not in res.stdout:
        return [CheckResult("remote", "ssh-connection", FAIL, "SSH 연결 실패", res.stderr or res.stdout, res.command_display, res.duration_ms)]
    profile = probe_remote_os(server)
    lines = res.stdout.splitlines()
    identity = " · ".join(lines[1:3]) if len(lines) > 1 else server.host
    return [CheckResult("remote", "ssh-connection", OK, "SSH 연결 성공", identity, res.command_display, res.duration_ms), CheckResult("compat", "os-profile", OK, profile.display_name, f"family={profile.family}, init={profile.init_system}, pkg={profile.package_manager}, firewall={profile.firewall_tool}")]


def remote_compat(server: ServerEntry, config: Dict = None) -> List[CheckResult]:
    profile = probe_remote_os(server)
    checks = [CheckResult("compat", "os-profile", OK, profile.display_name, f"family={profile.family}, id={profile.os_id}"), CheckResult("compat", "init-system", OK if profile.init_system != "unknown" else WARN, f"init={profile.init_system}"), CheckResult("compat", "package-manager", OK if profile.package_manager != "unknown" else INFO, f"패키지 관리자={profile.package_manager}"), CheckResult("compat", "firewall-tool", OK if profile.firewall_tool != "unknown" else INFO, f"방화벽 도구={profile.firewall_tool}")]
    tool_res = run_ssh(server, "for x in ip ifconfig ss netstat ping journalctl tar gzip sha256sum shasum; do command -v $x >/dev/null 2>&1 && printf '%s ' $x; done", timeout=10)
    present = set(tool_res.stdout.split())
    requirements = {"network-ip": ("ip", "ifconfig"), "socket-list": ("ss", "netstat"), "ping": ("ping",), "archive": ("tar", "gzip"), "checksum": ("sha256sum", "shasum")}
    for label, alternatives in requirements.items():
        found = next((x for x in alternatives if x in present), "")
        checks.append(CheckResult("compat", label, OK if found else INFO, f"사용 도구={found}" if found else "대체 도구를 찾지 못함"))
    return checks


def remote_system(server: ServerEntry, config: Dict) -> List[CheckResult]:
    results: List[CheckResult] = [_result("system", "uptime", "uptime -p 2>/dev/null || uptime", server)]
    load = run_ssh(server, "cat /proc/loadavg 2>/dev/null | awk '{print $1,$2,$3}'", timeout=8)
    results.append(CheckResult("system", "load-average", OK if load.returncode == 0 and load.stdout else INFO, f"load={load.stdout}" if load.stdout else "Load Average 확인 불가", load.stderr, load.command_display, load.duration_ms))
    mem_cmd = "awk '/MemTotal:/{t=$2}/MemAvailable:/{a=$2}END{if(t>0) printf \"사용률=%.1f%%\\n\",(1-a/t)*100}' /proc/meminfo"
    results.append(_result("system", "memory", mem_cmd, server))
    for path in config.get("disk_paths", ["/"]):
        res = run_ssh(server, f"df -P {shell_quote(str(path))} 2>/dev/null | tail -1", timeout=8)
        if res.returncode == 0 and res.stdout:
            used = next((p for p in res.stdout.split() if p.endswith("%")), "?")
            try:
                pct = int(used.rstrip("%")); status = OK if pct < 80 else WARN if pct < 90 else FAIL
            except ValueError:
                status = INFO
            results.append(CheckResult("system", f"disk:{path}", status, f"사용률={used}", res.stdout, res.command_display, res.duration_ms))
    failed = run_ssh(server, "command -v systemctl >/dev/null 2>&1 && systemctl --failed --no-legend --plain || true", timeout=10)
    lines = [x for x in failed.stdout.splitlines() if x.strip()]
    results.append(CheckResult("system", "failed-units", OK if not lines else FAIL, "실패한 systemd 유닛 없음" if not lines else f"실패한 systemd 유닛 {len(lines)}개", "\n".join(lines[:20]), failed.command_display, failed.duration_ms))
    return results


def remote_network(server: ServerEntry, config: Dict) -> List[CheckResult]:
    cmds = [("interfaces", "(command -v ip >/dev/null 2>&1 && ip -br addr) || (command -v ifconfig >/dev/null 2>&1 && ifconfig -a)"), ("default-route", "(command -v ip >/dev/null 2>&1 && ip route show default) || (command -v route >/dev/null 2>&1 && route -n | awk '$1==\"0.0.0.0\"{print}')"), ("neighbors", "(command -v ip >/dev/null 2>&1 && ip neigh show) || (command -v arp >/dev/null 2>&1 && arp -an) || true")]
    results = [_result("network", name, cmd, server) for name, cmd in cmds]
    for target in config.get("ping_targets", []):
        ping = run_ssh(server, f"ping -c 1 -W 2 {shell_quote(str(target))}", timeout=5)
        results.append(CheckResult("network", f"ping:{target}", OK if ping.returncode == 0 else FAIL, "응답 성공" if ping.returncode == 0 else "응답 실패", ping.stdout or ping.stderr, ping.command_display, ping.duration_ms))
    return results


def _remote_service_one(server: ServerEntry, service: str, profile: OSProfile) -> CheckResult:
    candidates = service_candidates(service, profile)
    quoted = " ".join(shell_quote(x) for x in candidates)
    command = "for s in " + quoted + "; do if command -v systemctl >/dev/null 2>&1; then state=$(systemctl is-active \"$s\" 2>/dev/null); [ \"$state\" = active ] && echo \"$s active\" && exit 0; elif command -v service >/dev/null 2>&1; then service \"$s\" status >/dev/null 2>&1 && echo \"$s active\" && exit 0; fi; done; exit 3"
    res = run_ssh(server, command, timeout=10)
    if res.returncode == 0:
        return CheckResult("service", service, OK, res.stdout or "active", command=res.command_display, duration_ms=res.duration_ms)
    return CheckResult("service", service, WARN, f"서비스 실행 상태를 확인하지 못함 ({'/'.join(candidates)})", res.stderr, res.command_display, res.duration_ms)


def remote_services(server: ServerEntry, config: Dict) -> List[CheckResult]:
    profile = probe_remote_os(server)
    return [_remote_service_one(server, str(name), profile) for name in (server.services or config.get("services", []))]


def remote_mariadb(server: ServerEntry, config: Dict) -> List[CheckResult]:
    profile = probe_remote_os(server)
    results = [_remote_service_one(server, "mariadb", profile)]
    listener = run_ssh(server, "((ss -lnt 2>/dev/null || netstat -lnt 2>/dev/null) | grep -E '[:.]3306[[:space:]]' | head -10) || true", timeout=8)
    matches = [x for x in listener.stdout.splitlines() if x.strip()]
    results.append(CheckResult("mariadb", "listener", OK if matches else WARN, "3306 포트 리스너 확인됨" if matches else "3306 포트 리스너가 확인되지 않음", "\n".join(matches), listener.command_display, listener.duration_ms))
    if not config.get("mariadb", {}).get("admin_ping", True):
        results.append(CheckResult("mariadb", "admin-ping", SKIP, "설정에서 비활성화됨"))
    else:
        ping = run_ssh(server, "command -v mysqladmin >/dev/null 2>&1 && mysqladmin ping --connect-timeout=3 2>&1", timeout=8)
        status = OK if ping.returncode == 0 and "alive" in ping.stdout.lower() else INFO if ping.returncode == 127 else FAIL
        results.append(CheckResult("mariadb", "admin-ping", status, ping.stdout or ping.stderr or "mysqladmin ping 실패", command=ping.command_display, duration_ms=ping.duration_ms))
    return results


def remote_logs(server: ServerEntry, config: Dict) -> List[CheckResult]:
    pattern = r"error|fail(ed|ure)?|critical|fatal|panic|segfault|oom"
    results: List[CheckResult] = []
    for path in config.get("log_files", []):
        cmd = f"test -r {shell_quote(str(path))} || exit 4; tail -n 1000 {shell_quote(str(path))} | grep -Ein '{pattern}' | tail -30 || true"
        res = run_ssh(server, cmd, timeout=12)
        if res.returncode == 4:
            results.append(CheckResult("logs", str(path), INFO, "로그 파일이 없거나 읽을 수 없음", res.stderr, res.command_display, res.duration_ms)); continue
        matches = [x for x in res.stdout.splitlines() if x.strip()]
        results.append(CheckResult("logs", str(path), WARN if matches else OK, f"오류 패턴 {len(matches)}건" if matches else "최근 오류 패턴 없음", "\n".join(matches), res.command_display, res.duration_ms))
    return results


def remote_ports(server: ServerEntry, config: Dict) -> List[CheckResult]:
    res = run_ssh(server, "ss -lntp 2>/dev/null || netstat -lntp 2>/dev/null || ss -lnt 2>/dev/null || netstat -lnt 2>/dev/null", timeout=10)
    if res.returncode != 0:
        return [CheckResult("ports", "listeners", INFO, "리스닝 포트 목록을 확인할 수 없음", res.stderr, res.command_display, res.duration_ms)]
    return [CheckResult("ports", "listeners", OK, f"리스닝 소켓 {len(res.stdout.splitlines())}줄", res.stdout[:12000], res.command_display, res.duration_ms)]


def remote_ip_scan(server: ServerEntry, needle: str, config: Dict) -> List[CheckResult]:
    roots = [str(x) for x in config.get("ip_scan_roots", ["/etc"])][:6]
    if not roots:
        return [CheckResult("ip-scan", needle, INFO, "검색 경로가 설정되지 않음")]
    excludes = []
    for path in config.get("ip_scan_excludes", []):
        name = str(path).rstrip("/").split("/")[-1]
        if name:
            excludes.append(f"--exclude-dir={shell_quote(name)}")
    command = "grep -RFn --binary-files=without-match " + " ".join(excludes) + f" -- {shell_quote(needle)} {' '.join(shell_quote(x) for x in roots)} 2>/dev/null | head -50 || true"
    res = run_ssh(server, command, timeout=30)
    lines = [x for x in res.stdout.splitlines() if x.strip()]
    if lines:
        return [CheckResult("ip-scan", needle, WARN, f"원격 서버에서 {len(lines)}건 발견 (최대 50건)", "\n".join(lines), res.command_display, res.duration_ms)]
    return [CheckResult("ip-scan", needle, OK, "원격 검색 경로에서 일치 항목 없음", command=res.command_display, duration_ms=res.duration_ms)]


def remote_collect(action: str, server: ServerEntry, config: Dict) -> List[CheckResult]:
    mapping = {"compat": remote_compat, "system": remote_system, "network": remote_network, "services": remote_services, "mariadb": remote_mariadb, "ports": remote_ports, "logs": remote_logs}
    if action == "connection":
        output = connection_check(server)
    elif action == "all":
        output = connection_check(server)
        for name in ("compat", "system", "network", "services", "mariadb", "ports", "logs"):
            output.extend(mapping[name](server, config))
    else:
        if action not in mapping:
            raise SSHClientError(f"지원하지 않는 원격 점검: {action}")
        output = mapping[action](server, config)
    write_audit("remote-check:" + action, server.display_target, not any(item.status == FAIL for item in output), details={"checks": len(output)})
    return output
