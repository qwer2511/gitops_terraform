import os,re
from .common import CheckResult,OK,WARN,INFO
PATTERN=re.compile(r"\b(error|fail(?:ed|ure)?|critical|fatal|panic|segfault|oom)\b",re.I)

def scan_file(path,tail_lines=1000,max_matches=30):
    if not os.path.isfile(path): return CheckResult("logs",path,INFO,"log file not found or not readable")
    try:
        with open(path,"r",encoding="utf-8",errors="replace") as fh: lines=fh.readlines()[-tail_lines:]
    except OSError as exc: return CheckResult("logs",path,INFO,"unable to read log",str(exc))
    matches=[x.rstrip() for x in lines if PATTERN.search(x)]
    return CheckResult("logs",path,WARN if matches else OK,f"{len(matches)} suspicious line(s) in last {len(lines)} lines","\n".join(matches[-max_matches:]))

def run_log_checks(config): return [scan_file(str(p)) for p in config.get("log_files",[])]
