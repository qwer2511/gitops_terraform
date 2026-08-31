# ServerOps Manager

**ServerOps Manager**는 반복적인 Linux 서버 운영 점검을 한국어 GUI/CLI에서 실행하고, 여러 배포판의 차이를 흡수하면서 SSH/SFTP 기반 원격 관리까지 확장하는 서버 운영 자동화 프로젝트입니다.

v0.3의 핵심은 **원격 SSH 진단, OS 호환성 레이어, 안전한 SFTP 전송**입니다. 서버 상태를 변경하는 작업보다 조회·진단 기능을 먼저 구현하고 있습니다.

## v0.3 주요 기능

- 시스템: Uptime, Load, Memory, Disk, 실패한 systemd unit
- 네트워크: Interface, Default Route, DNS, Neighbor/ARP, Ping
- 서비스 상태 점검
- MariaDB/MySQL 서비스, 3306 Listener, `mysqladmin ping`
- Listening Port 조회
- 로그 오류 패턴 검색
- 설정 파일의 기존 IP/문자열 검색
- TXT/JSON 리포트
- 한국어 GUI / 다크·라이트 모드
- SSH Key 기반 원격 진단
- Jump Host(`ssh -J`) 지원
- OpenSSH SFTP 업로드/다운로드
- 선택적 SSH 전송 압축(`-C`)
- 폴더/파일 ZIP 묶기
- 전송 전후 SHA-256 무결성 확인
- 원격 진단 감사 로그 `~/.serverops/audit.jsonl`

## OS 호환성 처리

서버 버전별 코드를 복사하지 않고 **환경 탐지 → 공통 기능 → 대체 명령** 구조로 처리합니다.

1. `/etc/os-release`로 배포판 family 탐지
2. `systemctl`, `service`, `dnf`, `yum`, `apt-get`, `zypper`, `apk` 등의 존재 여부 확인
3. 배포판별 서비스명 alias 적용
4. 주 명령이 없으면 fallback 사용

| 기능 | 우선 | fallback |
|---|---|---|
| 인터페이스 | `ip` | `ifconfig` |
| 라우팅 | `ip route` | `route -n` |
| 소켓/포트 | `ss` | `netstat` |
| 서비스 | `systemctl` | `service` |
| SSH 서비스 | RHEL `sshd` | Debian `ssh` |
| Apache | RHEL `httpd` | Debian `apache2` |
| Cron | RHEL `crond` | Debian `cron` |
| 시스템 로그 | RHEL `/var/log/messages` | Debian `/var/log/syslog` |

우선 지원 대상은 RHEL/Rocky/Alma/CentOS 계열과 Ubuntu/Debian 계열입니다. SUSE/Alpine은 배포판 탐지는 하지만 실제 운영 호환성 검증이 더 필요합니다.

> 코드에 호환 로직이 있다는 것과 모든 OS/버전에서 검증이 끝났다는 것은 다릅니다. 실제 지원 표시는 테스트 VM/컨테이너에서 회귀 테스트 후 확정해야 합니다.

호환성 점검:

```bash
python3 serverops.py compat
python3 serverops.py remote WEB01 compat --servers servers.json
```

## SSH 원격 진단

`servers.example.json`을 `servers.json`으로 복사하고 실제 서버에 맞게 수정합니다.

```json
{
  "servers": [
    {
      "name": "WEB01",
      "host": "10.0.0.11",
      "port": 22,
      "user": "serverops",
      "group": "운영 WEB",
      "key_file": "~/.ssh/id_ed25519",
      "jump_host": "",
      "host_key_policy": "strict",
      "services": ["sshd", "httpd"]
    }
  ]
}
```

CLI 예시:

```bash
python3 serverops.py remote WEB01 connection --servers servers.json
python3 serverops.py remote WEB01 all --servers servers.json
python3 serverops.py remote DB01 mariadb --servers servers.json
```

`host_key_policy` 기본값은 `strict`입니다. 처음 보는 서버를 자동 신뢰하지 않습니다. `accept-new`를 사용하면 신규 host key만 등록하며 변경된 key는 거부합니다.

## SFTP와 압축 전송

GUI에서 원격 서버를 선택한 뒤 **SFTP 전송**을 누릅니다.

```text
파일/폴더
   │
   ├─ 폴더 또는 선택 시 ZIP 생성
   │
   ├─ OpenSSH SFTP
   │    └─ SSH 암호화 + 선택적 -C 전송 압축
   │
   └─ SHA-256
        로컬 hash ↔ 원격 hash 비교
```

### 압축과 파일 깨짐

압축 자체가 파일 손상을 방지하는 핵심 기능은 아닙니다.

- SSH/SFTP는 암호화된 전송 채널과 데이터 무결성 보호를 제공합니다.
- ZIP로 묶으면 많은 작은 파일을 하나로 전송하기 쉬워집니다.
- `sftp -C`는 전송량을 줄일 수 있지만 ZIP/JPG/MP4처럼 이미 압축된 파일에는 효과가 작을 수 있습니다.
- **원본과 전송 결과가 같은지 확인하는 가장 명확한 방법은 SHA-256 비교**입니다.

ServerOps는 가능하면 전송 전후 SHA-256을 비교합니다. 원격 서버에 `sha256sum` 또는 `shasum`이 없으면 전송은 가능하지만 검증이 생략됐다고 표시합니다.

GUI 실행 PC에는 OpenSSH의 `ssh`, `sftp` 명령이 필요합니다.

Windows PowerShell 확인 예:

```powershell
ssh -V
sftp -h
```

## GUI 실행

```bash
python3 serverops.py -c serverops.json gui --servers servers.json
```

또는:

```bash
python3 serverops_gui.py
```

## CLI

```text
serverops all        로컬 전체 점검
serverops compat     로컬 OS/도구 호환성 점검
serverops system     시스템 상태
serverops network    네트워크
serverops services   서비스
serverops ports      TCP 포트
serverops mariadb    MariaDB/MySQL
serverops logs       로그 분석
serverops ip-scan    설정 파일 문자열/IP 검색
serverops remote     SSH 원격 서버 진단
serverops menu       대화형 메뉴
serverops gui        GUI
serverops report     리포트 생성
```

## 안전 설계

현재는 조회/진단 중심입니다. 향후 서버를 변경하는 기능에는 다음 안전장치를 적용할 예정입니다.

- 실행 전 대상/명령 표시
- 명시적 사용자 확인
- dry-run
- 변경 전 설정 백업
- 변경 전/후 diff
- 허용 명령 allow-list
- 감사 로그
- 가능한 작업의 rollback

실제 사내 IP/사용자명/key 경로가 들어가는 `servers.json`은 Git에 올리지 마세요.

## 테스트

```bash
python3 -m compileall -q .
python3 -m unittest discover -v
```

자동 테스트에는 OS family 파싱, 서비스 alias, Jump Host SSH 옵션, ZIP 생성/SHA-256 검증 등이 포함됩니다. 실제 SSH/SFTP end-to-end 테스트는 접속 가능한 Linux 테스트 서버에서 별도로 수행해야 합니다.

## 로드맵

- **v0.3**: SSH 원격 진단, OS 호환성, SFTP/압축/SHA-256, Jump Host
- **v0.4**: 여러 서버 병렬 일괄 점검, 원격 파일 브라우저, SSH 터미널
- **v0.5**: Process/Port 상세 뷰, 안전한 서비스 restart/start/stop
- **v0.6**: 설정 백업/diff/rollback, Apache/Tomcat/Nginx/MariaDB 운영 작업
- **v0.7**: 규칙 기반 장애 원인 분석 및 권장 조치
- **v1.0**: 통합 운영 자동화 도구

## 라이선스

MIT License
