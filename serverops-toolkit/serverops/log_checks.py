from __future__ import annotations

import os
import re

from .os_compat import default_log_candidates, detect_local_profile
from .common import CheckResult, OK, WARN, INFO

PATTERN = re.compile(r"\b(error|fail(?:ed|ure)?|critical|fatal|panic|segfault|oom)\b", re.IGNORECASE)


def scan_file(path: str, tail_lines: int = 1000, max_matches: int = 30) -> CheckResult:
    if not os.path.isfile(path):
        return CheckResult("logs", path, INFO, "로그 파일이 없거나 읽을 수 없음")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()[-tail_lines:]
    except OSError as exc:
        return CheckResult("logs", path, INFO, "로그를 읽을 수 없음", str(exc))
    matches = [line.rstrip() for line in lines if PATTERN.search(line)]
    status = WARN if matches else OK
    return CheckResult("logs", path, status, f"최근 {len(lines)}줄 중 오류 의심 패턴 {len(matches)}건 발견", "\n".join(matches[-max_matches:]))


def run_log_checks(config: dict) -> list[CheckResult]:
    configured = [str(path) for path in config.get("log_files", [])]
    detected = default_log_candidates(detect_local_profile())
    paths = list(dict.fromkeys(configured + detected))
    return [scan_file(path) for path in paths]
