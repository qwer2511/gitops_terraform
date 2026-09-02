# Changelog

## 0.4.0 - 2026-09-02

- 원격 TLS/SSL 인증서 안전 교체 GUI 추가
- 기존 인증서를 `YYYYMMDD_HHMMSS.bak` 형식으로 자동 백업
- SFTP 신규 인증서/개인키 업로드와 기존 SHA-256 전송 검증 연동
- OpenSSL 신규 인증서 형식/만료 여부 검사
- 선택적으로 신규 인증서와 개인키 공개키 일치 검증
- 적용 후 기존 파일의 owner/mode 복원 및 SELinux `restorecon` 지원
- Nginx/Apache/HAProxy 설정 검사 후 restart/reload/auto 적용
- service active 확인 및 최종 인증서 재검증
- 주요 단계 실패 시 백업본 자동 롤백과 서비스 복구 시도
- `journalctl` 서비스 로그를 GUI 작업 로그와 함께 표시
- root 비밀번호 저장 없이 root 또는 `sudo -n` 방식 사용
- 인증서 교체 단위 테스트 추가

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
