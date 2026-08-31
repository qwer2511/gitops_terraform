from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

from .common import CheckResult, OK, WARN, FAIL, INFO, SKIP
from .config import load_config
from .system_checks import run_system_checks
from .network_checks import run_network_checks
from .service_checks import run_service_checks
from .port_checks import run_port_checks
from .mariadb_checks import run_mariadb_checks
from .log_checks import run_log_checks
from .ip_scan import scan_ip_references
from .report import write_json, write_text
from .i18n import status_label, category_label, name_label

VERSION = "0.2.0"
COLORS = {OK:"\033[32m", WARN:"\033[33m", FAIL:"\033[31m", INFO:"\033[36m", SKIP:"\033[90m", "RESET":"\033[0m"}


def colorize(text: str, status: str, enabled: bool) -> str:
    if not enabled:
        return text
    return f"{COLORS.get(status, '')}{text}{COLORS['RESET']}"


def print_results(results: list[CheckResult], verbose: bool, color: bool) -> None:
    for item in results:
        label = status_label(item.status)
        prefix = colorize(f"[{label:4}]", item.status, color)
        print(f"{prefix} {category_label(item.category):10} {name_label(item.name):28} {item.summary}")
        if verbose and item.details:
            for line in item.details.splitlines():
                print(f"       {line}")


def collect(category: str, config: dict) -> list[CheckResult]:
    mapping = {"system":run_system_checks,"network":run_network_checks,"services":run_service_checks,"ports":run_port_checks,"mariadb":run_mariadb_checks,"logs":run_log_checks}
    if category == "all":
        results = []
        for name in ("system","network","services","ports","mariadb","logs"):
            results.extend(mapping[name](config))
        return results
    return mapping[category](config)


def exit_code(results: list[CheckResult]) -> int:
    if any(r.status == FAIL for r in results):
        return 2
    if any(r.status == WARN for r in results):
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="serverops", description="리눅스 서버 상태 점검 및 장애 진단 도구")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument("-c","--config", help="JSON 설정 파일 경로")
    parser.add_argument("-v","--verbose", action="store_true", help="상세 점검 결과 표시")
    parser.add_argument("--no-color", action="store_true", help="터미널 색상 비활성화")
    sub = parser.add_subparsers(dest="command", required=True)
    helps = {"all":"전체 점검 실행","system":"시스템 상태 점검","network":"네트워크 점검","services":"systemd 서비스 점검","ports":"TCP 포트 점검","mariadb":"MariaDB/MySQL 점검","logs":"로그 오류 패턴 검색"}
    for name, help_text in helps.items():
        sub.add_parser(name, help=help_text)
    ip_scan = sub.add_parser("ip-scan", help="설정된 경로에서 특정 IP/문자열 검색")
    ip_scan.add_argument("ip", help="검색할 IP 주소 또는 문자열")
    sub.add_parser("menu", help="번호 선택 방식의 대화형 운영 메뉴")
    gui = sub.add_parser("gui", help="ServerOps 데스크톱 GUI 실행")
    gui.add_argument("--servers", help="서버 인벤토리 JSON 파일 경로")
    report = sub.add_parser("report", help="전체 점검 후 리포트 파일 생성")
    report.add_argument("--format", choices=("text","json"), default="text", help="리포트 형식")
    report.add_argument("-o","--output", help="출력 파일 경로")
    return parser


def interactive_menu(config: dict, args) -> int:
    options = {"1":("시스템 상태 점검","system"),"2":("네트워크 진단","network"),"3":("서비스 상태 점검","services"),"4":("포트 점검","ports"),"5":("MariaDB 점검","mariadb"),"6":("로그 오류 검색","logs"),"7":("전체 장애 진단","all"),"8":("텍스트 리포트 생성","report"),"9":("기존 IP/문자열 잔존 설정 검색","ip-scan")}
    color = not args.no_color and sys.stdout.isatty()
    while True:
        print("\n" + "="*58)
        print(" ServerOps Toolkit - 서버 운영 메뉴")
        print("="*58)
        for key,(label,_) in options.items():
            print(f" {key}. {label}")
        print(" 0. 종료")
        choice = input("\n선택 > ").strip()
        if choice == "0":
            return 0
        if choice not in options:
            print("잘못된 번호입니다. 다시 선택해주세요.")
            continue
        action = options[choice][1]
        if action == "ip-scan":
            target = input("찾을 IP 또는 문자열 > ").strip()
            if not target:
                continue
            results = scan_ip_references(target, config)
        elif action == "report":
            results = collect("all", config)
            output = f"serverops_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            write_text(results, output)
            print_results(results, args.verbose, color)
            print(f"\n리포트 저장 완료: {os.path.abspath(output)}")
            input("\n계속하려면 Enter를 누르세요...")
            continue
        else:
            results = collect(action, config)
        print_results(results, args.verbose, color)
        input("\n계속하려면 Enter를 누르세요...")


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
    except (OSError, ValueError) as exc:
        print(f"설정 파일 오류: {exc}", file=sys.stderr)
        return 64
    if args.command == "gui":
        try:
            from .gui import launch
            return launch(config_path=args.config, inventory_path=args.servers)
        except (RuntimeError, ImportError) as exc:
            print(f"GUI 실행 오류: {exc}", file=sys.stderr)
            return 70
    if args.command == "ip-scan":
        results = scan_ip_references(args.ip, config)
        print_results(results, args.verbose, not args.no_color and sys.stdout.isatty())
        return exit_code(results)
    if args.command == "menu":
        return interactive_menu(config, args)
    if args.command == "report":
        results = collect("all", config)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = args.output or f"serverops_report_{stamp}.{'json' if args.format == 'json' else 'txt'}"
        write_json(results, output) if args.format == "json" else write_text(results, output)
        print_results(results, args.verbose, not args.no_color and sys.stdout.isatty())
        print(f"\n리포트 저장 완료: {os.path.abspath(output)}")
        return exit_code(results)
    results = collect(args.command, config)
    print_results(results, args.verbose, not args.no_color and sys.stdout.isatty())
    return exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
