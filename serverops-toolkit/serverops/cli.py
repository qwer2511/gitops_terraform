import argparse,os,sys
from datetime import datetime
from .common import OK,WARN,FAIL,INFO,SKIP
from .config import load_config
from .system_checks import run_system_checks
from .network_checks import run_network_checks
from .service_checks import run_service_checks
from .port_checks import run_port_checks
from .mariadb_checks import run_mariadb_checks
from .log_checks import run_log_checks
from .ip_scan import scan_ip_references
from .report import write_json,write_text
VERSION="0.1.0"
COLORS={OK:"\033[32m",WARN:"\033[33m",FAIL:"\033[31m",INFO:"\033[36m",SKIP:"\033[90m","RESET":"\033[0m"}

def collect(category,config):
    m={"system":run_system_checks,"network":run_network_checks,"services":run_service_checks,"ports":run_port_checks,"mariadb":run_mariadb_checks,"logs":run_log_checks}
    if category=="all":
        out=[]
        for name in ("system","network","services","ports","mariadb","logs"): out.extend(m[name](config))
        return out
    return m[category](config)

def print_results(results,verbose=False,color=False):
    for x in results:
        tag=f"[{x.status:4}]"; tag=f"{COLORS.get(x.status,'')}{tag}{COLORS['RESET']}" if color else tag
        print(f"{tag} {x.category:8} {x.name:24} {x.summary}")
        if verbose and x.details:
            for line in x.details.splitlines(): print(f"       {line}")

def code(results):
    return 2 if any(x.status==FAIL for x in results) else 1 if any(x.status==WARN for x in results) else 0

def menu(config,args):
    opts={"1":("System health","system"),"2":("Network diagnostics","network"),"3":("Service status","services"),"4":("Port checks","ports"),"5":("MariaDB checks","mariadb"),"6":("Log scan","logs"),"7":("Full diagnosis","all"),"8":("Create text report","report"),"9":("Find old IP references","ip-scan")}
    while True:
        print("\n"+"="*52+"\n ServerOps Toolkit - Operations Menu\n"+"="*52)
        for k,(label,_) in opts.items(): print(f" {k}. {label}")
        print(" 0. Exit"); choice=input("\nSelect > ").strip()
        if choice=="0": return 0
        if choice not in opts: print("Invalid selection."); continue
        action=opts[choice][1]
        if action=="ip-scan": results=scan_ip_references(input("IP/text to find > ").strip(),config)
        else: results=collect("all" if action=="report" else action,config)
        print_results(results,args.verbose,not args.no_color and sys.stdout.isatty())
        if action=="report":
            path=f"serverops_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"; write_text(results,path); print(f"Report written: {os.path.abspath(path)}")
        input("\nPress Enter to continue...")

def main(argv=None):
    p=argparse.ArgumentParser(prog="serverops",description="Linux server health-check and troubleshooting toolkit"); p.add_argument("--version",action="version",version=f"%(prog)s {VERSION}"); p.add_argument("-c","--config"); p.add_argument("-v","--verbose",action="store_true"); p.add_argument("--no-color",action="store_true"); sub=p.add_subparsers(dest="command",required=True)
    for name in ("all","system","network","services","ports","mariadb","logs"): sub.add_parser(name)
    ip=sub.add_parser("ip-scan"); ip.add_argument("ip"); sub.add_parser("menu"); rep=sub.add_parser("report"); rep.add_argument("--format",choices=("text","json"),default="text"); rep.add_argument("-o","--output")
    args=p.parse_args(argv)
    try: config=load_config(args.config)
    except (OSError,ValueError) as exc: print(f"configuration error: {exc}",file=sys.stderr); return 64
    if args.command=="menu": return menu(config,args)
    if args.command=="ip-scan": results=scan_ip_references(args.ip,config)
    else: results=collect("all" if args.command=="report" else args.command,config)
    print_results(results,args.verbose,not args.no_color and sys.stdout.isatty())
    if args.command=="report":
        ext="json" if args.format=="json" else "txt"; output=args.output or f"serverops_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        write_json(results,output) if args.format=="json" else write_text(results,output); print(f"\nReport written: {os.path.abspath(output)}")
    return code(results)
