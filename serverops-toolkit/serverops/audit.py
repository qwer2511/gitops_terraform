from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .common import now_iso


def default_audit_path() -> str:
    return os.path.expanduser(os.environ.get("SERVEROPS_AUDIT_LOG", "~/.serverops/audit.jsonl"))


def write_audit(action: str, target: str, success: bool, *, details: Optional[Dict[str, Any]] = None, path: Optional[str] = None) -> None:
    target_path = Path(path or default_audit_path()).expanduser()
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "time": now_iso(),
            "action": action,
            "target": target,
            "success": bool(success),
            "details": details or {},
        }
        with target_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        try:
            os.chmod(str(target_path), 0o600)
        except OSError:
            pass
    except OSError:
        return
