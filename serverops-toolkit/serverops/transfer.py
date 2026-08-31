from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from .inventory import ServerEntry
from .ssh_client import remote_sha256, sftp_available, sftp_options, target
from .audit import write_audit


@dataclass
class TransferResult:
    ok: bool
    message: str
    local_path: str
    remote_path: str
    bytes_transferred: int = 0
    local_sha256: str = ""
    remote_sha256: str = ""
    verified: bool = False
    duration_ms: int = 0


def _audit_transfer(action: str, server: ServerEntry, result: TransferResult) -> TransferResult:
    write_audit(
        f"sftp:{action}",
        server.display_target,
        result.ok,
        details={
            "remote_path": result.remote_path,
            "bytes": result.bytes_transferred,
            "verified": result.verified,
            "duration_ms": result.duration_ms,
            "message": result.message,
        },
    )
    return result


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sftp_quote(value: str) -> str:
    return '"' + value.replace('"', '\\"') + '"'


def _local_sftp_path(value: str) -> str:
    """OpenSSH sftp batch files are more reliable with forward slashes on Windows."""
    return os.path.abspath(value).replace("\\", "/")


def _run_sftp(server: ServerEntry, batch_line: str, timeout: int, compression: bool) -> Tuple[int, str, str, int]:
    if not sftp_available():
        return 127, "", "OpenSSH sftp 클라이언트를 찾을 수 없습니다.", 0
    fd, batch_path = tempfile.mkstemp(prefix="serverops-sftp-", suffix=".txt", text=True)
    os.close(fd)
    Path(batch_path).write_text(batch_line + "\n", encoding="utf-8")
    cmd = ["sftp"] + sftp_options(server, compression=compression) + ["-b", batch_path, target(server)]
    start = time.monotonic()
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout, check=False)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip(), int((time.monotonic() - start) * 1000)
    except subprocess.TimeoutExpired:
        return 124, "", f"{timeout}초 후 전송 시간 초과", int((time.monotonic() - start) * 1000)
    finally:
        try:
            os.unlink(batch_path)
        except OSError:
            pass


def make_zip(source: str, output_dir: Optional[str] = None) -> str:
    source_path = Path(source).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(str(source_path))
    folder = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="serverops-zip-"))
    folder.mkdir(parents=True, exist_ok=True)
    archive = folder / f"{source_path.name}.zip"
    with zipfile.ZipFile(str(archive), "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        if source_path.is_dir():
            for path in source_path.rglob("*"):
                if path.is_file():
                    zf.write(str(path), str(path.relative_to(source_path.parent)))
        else:
            zf.write(str(source_path), source_path.name)
    return str(archive)


def upload(server: ServerEntry, local_path: str, remote_path: str, *, archive: bool = False, ssh_compression: bool = True, verify: bool = True, timeout: int = 300) -> TransferResult:
    original = str(Path(local_path).expanduser())
    temp_archive = ""
    send_path = original
    try:
        if archive or os.path.isdir(original):
            temp_archive = make_zip(original)
            send_path = temp_archive
            if remote_path.endswith("/"):
                remote_path = remote_path + os.path.basename(send_path)
            elif archive and not remote_path.lower().endswith(".zip"):
                remote_path += ".zip"
        if not os.path.isfile(send_path):
            return _audit_transfer("upload", server, TransferResult(False, "업로드할 파일을 찾을 수 없습니다.", original, remote_path))
        local_hash = sha256_file(send_path) if verify else ""
        line = f"put {_sftp_quote(_local_sftp_path(send_path))} {_sftp_quote(remote_path)}"
        rc, out, err, ms = _run_sftp(server, line, timeout, ssh_compression)
        if rc != 0:
            return _audit_transfer("upload", server, TransferResult(False, err or out or "SFTP 업로드 실패", original, remote_path, duration_ms=ms))
        remote_hash = ""
        verified = False
        if verify:
            remote_hash, _ = remote_sha256(server, remote_path)
            verified = bool(remote_hash and remote_hash == local_hash)
            if not remote_hash:
                return _audit_transfer("upload", server, TransferResult(True, "업로드 성공. 원격 SHA-256 도구가 없어 무결성 검증은 생략됨.", original, remote_path, os.path.getsize(send_path), local_hash, "", False, ms))
            if not verified:
                return _audit_transfer("upload", server, TransferResult(False, "업로드는 완료됐지만 SHA-256 값이 일치하지 않습니다.", original, remote_path, os.path.getsize(send_path), local_hash, remote_hash, False, ms))
        return _audit_transfer("upload", server, TransferResult(True, "업로드 및 SHA-256 검증 완료" if verify else "업로드 완료", original, remote_path, os.path.getsize(send_path), local_hash, remote_hash, verified, ms))
    finally:
        if temp_archive:
            try:
                shutil.rmtree(str(Path(temp_archive).parent))
            except OSError:
                pass


def download(server: ServerEntry, remote_path: str, local_path: str, *, ssh_compression: bool = True, verify: bool = True, timeout: int = 300) -> TransferResult:
    local_path = str(Path(local_path).expanduser())
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    remote_hash = ""
    if verify:
        remote_hash, _ = remote_sha256(server, remote_path)
    line = f"get {_sftp_quote(remote_path)} {_sftp_quote(_local_sftp_path(local_path))}"
    rc, out, err, ms = _run_sftp(server, line, timeout, ssh_compression)
    if rc != 0:
        return _audit_transfer("download", server, TransferResult(False, err or out or "SFTP 다운로드 실패", local_path, remote_path, duration_ms=ms))
    if not os.path.isfile(local_path):
        return _audit_transfer("download", server, TransferResult(False, "다운로드 결과 파일을 찾을 수 없습니다.", local_path, remote_path, duration_ms=ms))
    local_hash = sha256_file(local_path) if verify else ""
    verified = bool(verify and remote_hash and local_hash == remote_hash)
    if verify and remote_hash and not verified:
        return _audit_transfer("download", server, TransferResult(False, "다운로드는 완료됐지만 SHA-256 값이 일치하지 않습니다.", local_path, remote_path, os.path.getsize(local_path), local_hash, remote_hash, False, ms))
    message = "다운로드 및 SHA-256 검증 완료" if verified else "다운로드 완료" if not verify else "다운로드 성공. 원격 SHA-256 도구가 없어 무결성 검증은 생략됨."
    return _audit_transfer("download", server, TransferResult(True, message, local_path, remote_path, os.path.getsize(local_path), local_hash, remote_hash, verified, ms))
