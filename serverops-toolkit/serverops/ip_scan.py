from __future__ import annotations

import os
from typing import Iterable

from .common import CheckResult, OK, WARN, INFO

DEFAULT_EXCLUDE_DIRS = {".git", "proc", "sys", "dev", "run", "tmp", "var/cache", "var/lib"}


def _is_excluded(path: str, excludes: Iterable[str]) -> bool:
    normalized = os.path.abspath(path)
    for item in excludes:
        item = item.strip()
        if not item:
            continue
        candidate = os.path.abspath(item)
        if normalized == candidate or normalized.startswith(candidate + os.sep):
            return True
    return False


def scan_ip_references(target: str, config: dict) -> list[CheckResult]:
    roots = config.get("ip_scan_roots", ["/etc"])
    excludes = config.get("ip_scan_excludes", ["/etc/ssl", "/etc/pki"])
    max_bytes = int(config.get("ip_scan_max_file_bytes", 2_000_000))
    matches = []
    errors = 0
    needle = target.encode("utf-8")
    for root in roots:
        root = os.path.abspath(str(root))
        if not os.path.exists(root):
            continue
        if os.path.isfile(root):
            paths = [root]
        else:
            paths = []
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [name for name in dirnames if not _is_excluded(os.path.join(dirpath, name), excludes)]
                paths.extend(os.path.join(dirpath, name) for name in filenames)
        for path in paths:
            if _is_excluded(path, excludes):
                continue
            try:
                if os.path.getsize(path) > max_bytes:
                    continue
                with open(path, "rb") as fh:
                    data = fh.read(max_bytes + 1)
                if b"\x00" in data[:4096] or needle not in data:
                    continue
                text = data.decode("utf-8", errors="replace")
                line_hits = []
                for lineno, line in enumerate(text.splitlines(), 1):
                    if target in line:
                        clean = line.strip()
                        if len(clean) > 220:
                            clean = clean[:217] + "..."
                        line_hits.append(f"{lineno}: {clean}")
                        if len(line_hits) >= 8:
                            break
                matches.append(CheckResult("ip-scan", path, WARN, f"{target} 문자열이 발견됨", "\n".join(line_hits)))
            except (OSError, PermissionError):
                errors += 1
    if not matches:
        matches.append(CheckResult("ip-scan", target, OK, f"검색 경로에서 {target} 문자열을 찾지 못함: {', '.join(map(str, roots))}", f"읽지 못해 건너뛴 파일: {errors}개" if errors else ""))
    else:
        matches.insert(0, CheckResult("ip-scan", target, INFO, f"대상 문자열이 포함된 파일 {len(matches)}개 발견", f"읽지 못해 건너뛴 파일: {errors}개" if errors else ""))
    return matches
