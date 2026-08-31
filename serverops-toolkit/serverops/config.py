from __future__ import annotations

import json
import os
from typing import Optional

DEFAULT_CONFIG = {
    "disk_paths": ["/", "/var", "/home"],
    "ping_targets": [],
    "dns_target": "",
    "services": [],
    "ports": [],
    "log_files": ["/var/log/messages", "/var/log/syslog"],
    "ip_scan_roots": ["/etc"],
    "ip_scan_excludes": ["/etc/ssl", "/etc/pki"],
    "ip_scan_max_file_bytes": 2000000,
    "mariadb": {"admin_ping": True, "host": "127.0.0.1", "user": "root"}
}


def deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: Optional[str]) -> dict:
    if not path:
        candidates = [os.environ.get("SERVEROPS_CONFIG", ""), "./serverops.json", "/etc/serverops/serverops.json"]
        path = next((p for p in candidates if p and os.path.isfile(p)), None)
    if not path:
        return dict(DEFAULT_CONFIG)
    with open(path, "r", encoding="utf-8") as fh:
        return deep_merge(DEFAULT_CONFIG, json.load(fh))
