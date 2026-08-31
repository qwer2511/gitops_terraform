from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from typing import Dict, List

from .common import CheckResult, INFO, OK, WARN, command_text, run_command, safe_read_text


@dataclass
class OSProfile:
    os_id: str = "unknown"
    name: str = "Unknown Linux"
    version_id: str = ""
    id_like: List[str] = field(default_factory=list)
    family: str = "linux"
    init_system: str = "unknown"
    package_manager: str = "unknown"
    firewall_tool: str = "unknown"

    @property
    def display_name(self) -> str:
        return f"{self.name} {self.version_id}".strip()


def parse_os_release(text: str) -> Dict[str, str]:
    data: Dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key] = value.strip().strip('"').strip("'")
    return data


def family_from_release(data: Dict[str, str]) -> str:
    os_id = data.get("ID", "").lower()
    likes = data.get("ID_LIKE", "").lower().split()
    tokens = {os_id, *likes}
    if tokens & {"rhel", "fedora", "centos", "rocky", "almalinux", "ol", "amzn"}:
        return "rhel"
    if tokens & {"debian", "ubuntu", "linuxmint"}:
        return "debian"
    if tokens & {"suse", "opensuse", "sles"}:
        return "suse"
    if "alpine" in tokens:
        return "alpine"
    return "linux"


def _which_first(names: List[str]) -> str:
    for name in names:
        if shutil.which(name):
            return name
    return "unknown"


def detect_local_profile() -> OSProfile:
    data = parse_os_release(safe_read_text("/etc/os-release"))
    os_id = data.get("ID", "unknown").lower()
    family = family_from_release(data)
    init_system = "systemd" if shutil.which("systemctl") else "sysv" if shutil.which("service") else "unknown"
    package_manager = _which_first(["dnf", "yum", "apt-get", "zypper", "apk"])
    firewall_tool = _which_first(["firewall-cmd", "ufw", "nft", "iptables"])
    return OSProfile(
        os_id=os_id,
        name=data.get("PRETTY_NAME") or data.get("NAME") or "Linux",
        version_id=data.get("VERSION_ID", ""),
        id_like=data.get("ID_LIKE", "").split(),
        family=family,
        init_system=init_system,
        package_manager=package_manager,
        firewall_tool=firewall_tool,
    )


SERVICE_ALIASES = {
    "sshd": {"rhel": ["sshd", "ssh"], "debian": ["ssh", "sshd"], "default": ["sshd", "ssh"]},
    "ssh": {"rhel": ["sshd", "ssh"], "debian": ["ssh", "sshd"], "default": ["ssh", "sshd"]},
    "httpd": {"rhel": ["httpd", "apache2"], "debian": ["apache2", "httpd"], "default": ["httpd", "apache2"]},
    "apache2": {"rhel": ["httpd", "apache2"], "debian": ["apache2", "httpd"], "default": ["apache2", "httpd"]},
    "mariadb": {"default": ["mariadb", "mysql", "mysqld"]},
    "mysql": {"default": ["mysql", "mariadb", "mysqld"]},
    "crond": {"rhel": ["crond", "cron"], "debian": ["cron", "crond"], "default": ["crond", "cron"]},
    "cron": {"rhel": ["crond", "cron"], "debian": ["cron", "crond"], "default": ["cron", "crond"]},
}


def service_candidates(name: str, profile: OSProfile) -> List[str]:
    normalized = name.strip()
    mapping = SERVICE_ALIASES.get(normalized)
    if not mapping:
        return [normalized]
    result = mapping.get(profile.family) or mapping.get("default") or [normalized]
    return list(dict.fromkeys(result))


def default_log_candidates(profile: OSProfile) -> List[str]:
    common = ["/var/log/auth.log", "/var/log/secure", "/var/log/mariadb/mariadb.log", "/var/log/mysql/error.log"]
    if profile.family == "debian":
        return ["/var/log/syslog"] + common
    if profile.family == "rhel":
        return ["/var/log/messages"] + common
    return ["/var/log/messages", "/var/log/syslog"] + common


def compatibility_checks() -> List[CheckResult]:
    profile = detect_local_profile()
    results = [
        CheckResult("compat", "os-profile", OK, profile.display_name, f"family={profile.family}, id={profile.os_id}"),
        CheckResult("compat", "init-system", OK if profile.init_system != "unknown" else WARN, f"init={profile.init_system}"),
        CheckResult("compat", "package-manager", INFO if profile.package_manager == "unknown" else OK, f"패키지 관리자={profile.package_manager}"),
        CheckResult("compat", "firewall-tool", INFO if profile.firewall_tool == "unknown" else OK, f"방화벽 도구={profile.firewall_tool}"),
    ]
    tools = {
        "network-ip": ["ip", "ifconfig"],
        "socket-list": ["ss", "netstat"],
        "ping": ["ping"],
        "ssh-client": ["ssh"],
        "sftp-client": ["sftp"],
        "archive": ["tar", "zip"],
        "checksum": ["sha256sum", "shasum"],
    }
    for label, candidates in tools.items():
        found = _which_first(candidates)
        status = OK if found != "unknown" else INFO
        results.append(CheckResult("compat", label, status, f"사용 도구={found}" if found != "unknown" else "사용 가능한 도구를 찾지 못함"))
    return results
