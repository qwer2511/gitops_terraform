from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from .inventory import ServerEntry


@dataclass
class SSHResult:
    returncode: int
    stdout: str
    stderr: str
    duration_ms: int
    command_display: str


class SSHClientError(RuntimeError):
    pass


def openssh_available() -> bool:
    return shutil.which("ssh") is not None


def sftp_available() -> bool:
    return shutil.which("sftp") is not None


def _policy(server: ServerEntry) -> str:
    """Map our friendly policy names to OpenSSH StrictHostKeyChecking values."""
    value = (server.host_key_policy or "strict").lower()
    if value == "accept-new":
        return "accept-new"
    return "yes"


def ssh_options(server: ServerEntry, connect_timeout: int = 7) -> List[str]:
    opts = [
        "-p", str(server.port),
        "-o", "BatchMode=yes",
        "-o", f"ConnectTimeout={connect_timeout}",
        "-o", f"StrictHostKeyChecking={_policy(server)}",
    ]
    if server.key_file:
        opts += ["-i", os.path.expanduser(server.key_file)]
    if server.jump_host:
        opts += ["-J", server.jump_host]
    return opts


def sftp_options(server: ServerEntry, connect_timeout: int = 7, compression: bool = True) -> List[str]:
    opts = [
        "-P", str(server.port),
        "-o", "BatchMode=yes",
        "-o", f"ConnectTimeout={connect_timeout}",
        "-o", f"StrictHostKeyChecking={_policy(server)}",
    ]
    if compression:
        opts.append("-C")
    if server.key_file:
        opts += ["-i", os.path.expanduser(server.key_file)]
    if server.jump_host:
        opts += ["-J", server.jump_host]
    return opts


def target(server: ServerEntry) -> str:
    if server.local:
        raise SSHClientError("로컬 서버에는 SSH 원격 실행을 사용하지 않습니다.")
    if not server.host:
        raise SSHClientError("서버 host가 비어 있습니다.")
    return f"{server.user}@{server.host}" if server.user else server.host


def run_ssh(server: ServerEntry, remote_command: str, timeout: int = 15) -> SSHResult:
    if not openssh_available():
        raise SSHClientError("OpenSSH ssh 클라이언트를 찾을 수 없습니다. Windows 선택적 기능 또는 openssh-client 설치를 확인하세요.")
    cmd = ["ssh"] + ssh_options(server) + [target(server), remote_command]
    start = time.monotonic()
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout, check=False)
        elapsed = int((time.monotonic() - start) * 1000)
        display = "ssh " + " ".join(shlex.quote(x) for x in cmd[1:-1]) + " <remote-command>"
        return SSHResult(proc.returncode, proc.stdout.strip(), proc.stderr.strip(), elapsed, display)
    except subprocess.TimeoutExpired as exc:
        elapsed = int((time.monotonic() - start) * 1000)
        out = exc.stdout if isinstance(exc.stdout, str) else ""
        err = exc.stderr if isinstance(exc.stderr, str) else ""
        return SSHResult(124, (out or "").strip(), (err or f"{timeout}초 후 시간 초과").strip(), elapsed, "ssh <timeout>")


def shell_quote(value: str) -> str:
    return shlex.quote(value)


def remote_sha256(server: ServerEntry, remote_path: str) -> Tuple[str, SSHResult]:
    path = shell_quote(remote_path)
    command = f"(command -v sha256sum >/dev/null 2>&1 && sha256sum {path}) || (command -v shasum >/dev/null 2>&1 && shasum -a 256 {path})"
    result = run_ssh(server, command, timeout=30)
    digest = result.stdout.split()[0].lower() if result.returncode == 0 and result.stdout else ""
    if len(digest) != 64:
        digest = ""
    return digest, result
