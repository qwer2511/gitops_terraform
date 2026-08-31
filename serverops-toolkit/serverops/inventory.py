from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ServerEntry:
    name: str
    host: str = "127.0.0.1"
    port: int = 22
    user: str = ""
    group: str = "기본"
    key_file: str = ""
    local: bool = False
    services: List[str] = field(default_factory=list)
    notes: str = ""
    jump_host: str = ""
    host_key_policy: str = "strict"

    @property
    def display_target(self) -> str:
        if self.local:
            return "이 PC"
        if self.user:
            return f"{self.user}@{self.host}:{self.port}"
        return f"{self.host}:{self.port}"


def _default_entries() -> List[ServerEntry]:
    return [ServerEntry(name="로컬 서버", host="127.0.0.1", group="내 서버", local=True, notes="ServerOps가 실행 중인 현재 서버")]


def _candidate_path(path: Optional[str]) -> Optional[str]:
    if path:
        return path
    candidates = [os.environ.get("SERVEROPS_SERVERS", ""), "./servers.json", os.path.expanduser("~/.serverops/servers.json")]
    return next((p for p in candidates if p and os.path.isfile(p)), None)


def load_inventory(path: Optional[str] = None) -> List[ServerEntry]:
    source = _candidate_path(path)
    if not source:
        return _default_entries()
    with open(source, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    rows = payload.get("servers", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("서버 목록은 배열 형식이어야 합니다.")
    entries: List[ServerEntry] = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f"서버 #{index} 항목이 객체가 아닙니다.")
        name = str(row.get("name", "")).strip()
        if not name:
            raise ValueError(f"서버 #{index}의 name이 비어 있습니다.")
        port = int(row.get("port", 22))
        if port < 1 or port > 65535:
            raise ValueError(f"{name}: SSH 포트 범위가 올바르지 않습니다.")
        policy = str(row.get("host_key_policy", "strict")).strip().lower() or "strict"
        if policy not in {"strict", "accept-new"}:
            raise ValueError(f"{name}: host_key_policy는 strict 또는 accept-new만 사용할 수 있습니다.")
        entries.append(ServerEntry(name=name, host=str(row.get("host", "127.0.0.1")).strip() or "127.0.0.1", port=port, user=str(row.get("user", "")).strip(), group=str(row.get("group", "기본")).strip() or "기본", key_file=os.path.expanduser(str(row.get("key_file", "")).strip()), local=bool(row.get("local", False)), services=[str(x).strip() for x in row.get("services", []) if str(x).strip()], notes=str(row.get("notes", "")), jump_host=str(row.get("jump_host", "")).strip(), host_key_policy=policy))
    return entries or _default_entries()


def save_inventory(entries: List[ServerEntry], path: str) -> str:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"servers": [asdict(item) for item in entries]}
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(target)
