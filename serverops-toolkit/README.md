# ServerOps Manager

리눅스 서버 운영자가 반복해서 수행하는 상태 점검·장애 진단 작업을 표준화하고, 여러 서버를 한 화면에서 관리하는 방향으로 개발 중인 서버 운영 자동화 도구입니다.

v0.2부터 기존 CLI 진단 엔진에 **한국어 데스크톱 GUI, 다크/라이트 모드, 서버 인벤토리 화면**을 추가했습니다. CLI는 자동화와 장애 대응용으로 계속 유지합니다.

> v0.2는 안전성을 위해 서버 변경보다 조회·진단을 우선합니다. 서비스 재시작, 방화벽 변경, 패키지 설치처럼 서버 상태를 바꾸는 기능은 확인 절차·감사 로그·백업과 함께 후속 버전에서 추가합니다.

## 화면 구성

```text
┌──────────────┬────────────────────────────────────────────────────────┐
│ SERVEROPS    │ DB01                         ● 진단 완료               │
│ 서버 운영자동화│ 10.0.0.21 · 운영 DB                                  │
│              │                                                        │
│ 검색         │ [상태]   [OS/Host]   [CPU]   [메모리]   [디스크]       │
│              │                                                        │
│ ▾ 운영 WEB   │ [전체진단] [시스템] [네트워크] [서비스] [MariaDB] ...   │
│   ○ WEB01    │                                                        │
│   ○ WEB02    │ ┌ 상태 │ 분류 │ 점검 항목 │ 결과                  ┐  │
│ ▾ 운영 DB    │ │ 정상 │ 시스템│ 메모리    │ 사용률=42.1%          │  │
│   ○ DB01     │ │ 주의 │ 시스템│ 디스크 /  │ 사용률=86.2%          │  │
│              │ └──────────────────────────────────────────────────┘  │
│ ☾ 다크 모드  │ 선택한 항목의 상세 명령/로그                           │
└──────────────┴────────────────────────────────────────────────────────┘
```

### UI 원칙

- 기본 다크 모드, 버튼 하나로 라이트 모드 전환
- 초록/주황/빨강은 상태 표시처럼 필요한 곳에만 사용
- 좌측은 서버와 그룹 선택에 집중
- 중앙 위는 서버 상태를 카드 형태로 요약
- 반복 작업은 큰 빠른 작업 버튼으로 제공
- 결과와 원본 로그를 분리해 가독성 확보
- 비밀번호를 일반 JSON 파일에 저장하지 않음

## 현재 기능

### GUI

- 한국어 데스크톱 UI
- 다크/라이트 모드
- 서버 그룹/목록 및 검색
- 로컬 서버 전체 진단
- 시스템 / 네트워크 / 서비스 / MariaDB / 포트 / 로그 개별 진단
- 기존 IP/문자열 잔존 설정 검색
- 정상 / 주의 / 실패 / 정보 / 건너뜀 결과 테이블
- 상세 명령 및 로그 보기
- TXT 리포트 저장
- 상태 요약 카드

### CLI

- 가동 시간, Load Average, 메모리, 디스크, 실패한 systemd 유닛
- 네트워크 인터페이스, 기본 라우트, DNS, ARP/Neighbor, Ping
- systemd 서비스 점검
- TCP 포트 점검
- MariaDB/MySQL 서비스·3306 리스너·mysqladmin ping
- 로그 오류 패턴 검색
- 설정파일의 기존 IP/문자열 검색
- TXT/JSON 리포트 및 종료 코드

## 요구사항

- Python 3.8 이상
- CLI 진단 대상: Linux / systemd 환경 우선
- GUI: Windows 또는 데스크톱 Linux에서 Python Tk 지원 필요
- Linux 진단 명령: `ip`, `ss`, `ping`, `systemctl` 등

GUI는 Python 표준 `tkinter/ttk`를 사용해 외부 GUI 프레임워크 의존성을 추가하지 않았습니다.

## 빠른 시작

```bash
git clone -b serverops-toolkit-v0.2 https://github.com/qwer2511/gitops_terraform.git
cd gitops_terraform/serverops-toolkit
cp serverops.example.json serverops.json
cp servers.example.json servers.json
```

GUI:

```bash
python3 serverops.py -c serverops.json gui --servers servers.json
```

또는:

```bash
python3 serverops_gui.py
```

CLI:

```bash
python3 serverops.py menu
python3 serverops.py all
```

## 서버 목록

`servers.example.json`을 `servers.json`으로 복사한 뒤 실제 환경에 맞게 수정합니다.

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
      "local": false,
      "services": ["sshd", "httpd"]
    }
  ]
}
```

`servers.json`은 Git에서 제외됩니다. 실제 사내 IP나 서버 정보가 공개 저장소에 올라가지 않도록 주의하세요.

## 명령

```text
serverops all       전체 점검
serverops system    시스템 상태 점검
serverops network   네트워크 점검
serverops services  systemd 서비스 점검
serverops ports     TCP 포트 점검
serverops mariadb   MariaDB/MySQL 점검
serverops logs      로그 오류 패턴 검색
serverops ip-scan   설정파일에서 특정 IP/문자열 검색
serverops menu      번호 선택 방식 운영 메뉴
serverops gui       데스크톱 GUI
serverops report    전체 점검 후 리포트 생성
```

## 보안 설계

서버 인벤토리에는 SSH 사용자와 Key 경로를 저장할 수 있지만 SSH 비밀번호 저장 기능은 넣지 않았습니다. 이후 SSH 원격 진단도 키 기반 인증을 우선합니다.

쓰기 작업에는 실행 전 명령 표시, 사용자 확인, 변경 전 백업, dry-run, 허용 작업 목록, 감사 로그를 선행 조건으로 둡니다.

## 로드맵

- **v0.2**: 한국어 GUI, 다크/라이트 모드, 서버 인벤토리, 로컬 진단 연결
- **v0.3**: SSH Key 기반 원격 진단, 여러 서버 일괄 점검, 연결 상태 표시
- **v0.4**: SSH 터미널/SFTP, 프로세스·포트 상세 보기
- **v0.5**: 안전한 서비스 재시작, Apache/Tomcat/Nginx/MariaDB 운영 작업
- **v0.6**: 설정 백업/diff, IP 변경 점검 워크플로, 방화벽 작업
- **v0.7**: 규칙 기반 장애 원인 분석 및 권장 조치
- **v1.0**: 통합 서버 운영 자동화 도구

## 테스트

```bash
python3 -m compileall -q .
python3 -m unittest discover -v
```

로컬 검증 기준 v0.2 단위 테스트 8개를 통과했습니다.

## 라이선스

MIT License
