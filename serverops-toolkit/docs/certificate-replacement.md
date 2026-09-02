# TLS 인증서 교체 기능 (v0.4)

ServerOps v0.4의 인증서 교체 기능은 사내 운영에서 흔히 사용하는 **SFTP 업로드 → 기존 인증서 백업 → 신규 인증서 적용 → 서비스 재기동 → 로그 확인** 절차를 안전장치와 함께 자동화합니다.

## GUI 입력값

- 인증서 이름: 작업을 식별하기 위한 이름
- 기존 인증서 경로: 현재 서비스가 참조하는 원격 서버의 절대경로
- 새 인증서 경로: SFTP로 업로드했거나 이미 서버에 존재하는 신규 인증서 절대경로
- 기존 개인키 경로: 선택 입력. 신규 인증서와 현재 키가 일치하는지 검사할 때 사용
- 새 개인키 경로: 선택 입력. 인증서와 키를 함께 교체할 때 사용
- systemd 서비스: 예) `nginx`, `httpd`, `apache2`, `haproxy`
- 적용 방식: `restart`, `reload`, `auto`

## 실제 실행 순서

1. 기존/신규 파일 존재 여부 확인
2. `openssl x509`로 신규 인증서 형식과 만료 여부 확인
3. 개인키 경로가 입력된 경우 인증서/키 공개키 일치 여부 확인
4. 원격 서버 시간으로 `YYYYMMDD_HHMMSS` 백업 suffix 생성
5. `cp -a`로 기존 인증서 백업
6. 키도 교체하는 경우 기존 개인키 백업
7. 신규 인증서를 기존 인증서 경로에 적용
8. 기존 백업본 기준으로 owner/mode 복원
9. SELinux 환경에서는 `restorecon` 실행 가능 시 컨텍스트 복구
10. Nginx/Apache/HAProxy는 알려진 설정 검사 명령 실행
11. 선택한 방식으로 systemd reload/restart
12. `systemctl is-active` 확인
13. 기존 경로의 인증서를 OpenSSL로 재확인
14. `journalctl -u <service>` 최근 로그 수집
15. ServerOps GUI에 작업 단계 로그 + 서비스 로그 표시

백업 예시:

```text
/etc/pki/tls/certs/example.crt
→ /etc/pki/tls/certs/example.crt.20260902_101530.bak
```

같은 날 여러 번 작업해도 백업 파일끼리 충돌하지 않도록 날짜뿐 아니라 시각도 붙입니다.

## SFTP 연동

`새 인증서 경로` 또는 `새 개인키 경로` 옆의 **SFTP 업로드** 버튼을 누르면 로컬 파일을 선택해 서버에 업로드할 수 있습니다. 기존 ServerOps SFTP 모듈을 사용하므로 SSH 암호화 전송과 SHA-256 검증을 그대로 사용합니다.

업로드 위치를 `/tmp/`로 두면 선택한 파일명이 자동으로 붙습니다.

```text
/tmp/ + example.crt
→ /tmp/example.crt
```

## 실패 시 롤백

다음 주요 단계가 실패하면 백업본으로 원래 인증서를 복구하도록 설계했습니다.

- 신규 파일 적용 실패
- Nginx/Apache/HAProxy 설정 검사 실패
- 서비스 reload/restart 실패
- 서비스가 active 상태가 아님
- 최종 인증서 재확인 실패

롤백 후에는 기존 인증서 기준으로 서비스를 다시 기동하는 복구도 시도하고, 결과를 작업 로그에 표시합니다.

## 권한 정책

ServerOps는 root 비밀번호를 저장하지 않습니다.

GUI의 `sudo -n 사용` 옵션이 켜져 있으면:

- SSH 계정이 root이면 그대로 실행
- root가 아니면 `sudo -n` 사용
- sudo가 비밀번호를 요구하면 즉시 실패하고 작업을 중단

따라서 운영 서버에서는 회사 정책에 맞는 제한된 NOPASSWD 명령 정책 또는 별도 운영 계정을 사용하는 것을 권장합니다.

## 서비스별 설정 검사

| 서비스 | 교체 후 설정 검사 |
|---|---|
| nginx | `nginx -t` |
| httpd | `apachectl configtest` 또는 `httpd -t` |
| apache2 | `apache2ctl configtest` 또는 `apachectl configtest` |
| haproxy | `haproxy -c -f /etc/haproxy/haproxy.cfg` |
| 그 외 | 전용 검사 없음 표시 후 service action 진행 |

Tomcat의 JKS/PKCS#12와 같은 Java keystore 교체는 이 PEM 교체 기능과 별도 기능으로 다루는 것이 안전합니다.

## 지원 형식

v0.4 자동 교체는 우선 PEM 계열 인증서(`.crt`, `.pem`)를 대상으로 합니다. `.p12`, `.pfx`, JKS는 후속 keystore 관리 기능에서 별도로 지원할 예정입니다.

## 운영 전 필수 테스트

처음에는 운영 서버가 아니라 테스트 서버에서 다음을 확인하세요.

```text
1. SFTP 신규 인증서 업로드
2. 사전 점검
3. 인증서 교체 실행
4. 백업 파일 생성 확인
5. 서비스 정상 상태 확인
6. HTTPS 실제 접속 확인
7. journalctl 로그 확인
8. 테스트용 잘못된 인증서로 롤백 동작 확인
```

실제 HTTPS endpoint의 443 인증서까지 원격에서 자동 검증하는 기능은 후속 버전에 추가할 예정입니다.
