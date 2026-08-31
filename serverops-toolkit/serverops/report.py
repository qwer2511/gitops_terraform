from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .common import CheckResult, now_iso
from .i18n import status_label, category_label, name_label


def summarize(results: list[CheckResult]) -> dict:
    counts = Counter(item.status for item in results)
    return {"generated_at": now_iso(), "total": len(results), "counts": dict(counts)}


def write_json(results: list[CheckResult], path: str) -> str:
    payload = {"summary": summarize(results), "results": [item.to_dict() for item in results]}
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_text(results: list[CheckResult], path: str) -> str:
    summary = summarize(results)
    korean_counts = {status_label(k): v for k, v in summary["counts"].items()}
    lines = ["ServerOps 서버 진단 리포트", "=" * 80, f"생성 시각: {summary['generated_at']}", f"전체 점검 수: {summary['total']}", f"상태별 개수: {korean_counts}", ""]
    for item in results:
        lines.append(f"[{status_label(item.status)}] {category_label(item.category)}/{name_label(item.name)} - {item.summary}")
        if item.command:
            lines.append(f"  실행 명령: {item.command}")
        if item.details:
            lines.append("  상세 내용:")
            lines.extend(f"    {line}" for line in item.details.splitlines())
        lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")
    return path
