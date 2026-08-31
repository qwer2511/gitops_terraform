from __future__ import annotations

STATUS_LABELS = {
    "OK": "정상",
    "WARN": "주의",
    "FAIL": "실패",
    "INFO": "정보",
    "SKIP": "건너뜀",
}

CATEGORY_LABELS = {
    "system": "시스템",
    "network": "네트워크",
    "service": "서비스",
    "port": "포트",
    "mariadb": "MariaDB",
    "logs": "로그",
    "ip-scan": "IP검색",
}

NAME_LABELS = {
    "load-average": "시스템 부하",
    "memory": "메모리",
    "uptime": "가동 시간",
    "failed-units": "실패한 systemd 유닛",
    "interfaces": "네트워크 인터페이스",
    "default-route": "기본 라우트",
    "dns": "DNS",
    "neighbors": "ARP/Neighbor",
    "service": "서비스 상태",
    "admin-ping": "DB 응답 확인",
    "listener": "3306 리스너",
}


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def category_label(category: str) -> str:
    return CATEGORY_LABELS.get(category, category)


def name_label(name: str) -> str:
    if name in NAME_LABELS:
        return NAME_LABELS[name]
    if name.startswith("disk:"):
        return f"디스크 {name.split(':', 1)[1]}"
    if name.startswith("ping:"):
        return f"Ping {name.split(':', 1)[1]}"
    return name
