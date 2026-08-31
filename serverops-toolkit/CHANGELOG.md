# Changelog

## 0.3.0 - 2026-08-31

- SSH Key 기반 원격 서버 진단 추가
- RHEL/Rocky/Alma/CentOS, Ubuntu/Debian 계열 자동 탐지 및 명령 fallback 레이어 추가
- `sshd/ssh`, `httpd/apache2`, `crond/cron` 서비스 별칭 처리
- `ip/ifconfig`, `ss/netstat` 대체 명령 지원
- OS/서비스 관리자/패키지 관리자/방화벽 도구 호환성 점검 추가
- OpenSSH SFTP 업로드/다운로드 GUI 추가
- SSH 전송 압축(`-C`), 폴더 ZIP 묶기, SHA-256 전송 후 무결성 검증 추가
- SSH Jump Host(`-J`) 및 host key 정책(`strict`, `accept-new`) 지원
- 원격 진단 감사 로그(`~/.serverops/audit.jsonl`) 추가
- 원격 IP/문자열 검색 추가
- 테스트 13개로 확장
