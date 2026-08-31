from __future__ import annotations
import os, shutil
from .common import CheckResult, OK, WARN, FAIL, INFO, run_command, command_text, safe_read_text

def _load_average():
    cpus=os.cpu_count() or 1
    try: one,five,fifteen=os.getloadavg()
    except (AttributeError,OSError): return CheckResult("system","load-average",INFO,"load average unavailable")
    ratio=one/cpus; status=OK if ratio<0.8 else WARN if ratio<1.5 else FAIL
    return CheckResult("system","load-average",status,f"1m={one:.2f}, 5m={five:.2f}, 15m={fifteen:.2f}, cpu={cpus}",f"1-minute load per CPU: {ratio:.2f}")

def _memory():
    values={}
    for line in safe_read_text("/proc/meminfo").splitlines():
        if ":" not in line: continue
        k,v=line.split(":",1)
        try: values[k]=int(v.strip().split()[0])
        except (ValueError,IndexError): pass
    total=values.get("MemTotal",0); avail=values.get("MemAvailable",0)
    if not total: return CheckResult("system","memory",INFO,"memory information unavailable")
    pct=(1-avail/total)*100; status=OK if pct<80 else WARN if pct<90 else FAIL
    return CheckResult("system","memory",status,f"used={pct:.1f}%",f"total={total/1024/1024:.2f} GiB, available={avail/1024/1024:.2f} GiB")

def _disk(paths):
    out=[]; seen=set()
    for path in paths:
        if not os.path.exists(path): continue
        u=shutil.disk_usage(path); key=(u.total,u.used,u.free)
        if key in seen: continue
        seen.add(key); pct=u.used/u.total*100 if u.total else 0; status=OK if pct<80 else WARN if pct<90 else FAIL
        out.append(CheckResult("system",f"disk:{path}",status,f"used={pct:.1f}%",f"total={u.total/1024**3:.2f} GiB, free={u.free/1024**3:.2f} GiB"))
    return out

def _uptime():
    cmd=["uptime","-p"]; rc,o,e,ms=run_command(cmd,3)
    return CheckResult("system","uptime",OK if rc==0 else INFO,o or "uptime unavailable",e,command_text(cmd),ms)

def _failed_units():
    cmd=["systemctl","--failed","--no-legend","--plain"]; rc,o,e,ms=run_command(cmd,5)
    if rc not in (0,1): return CheckResult("system","failed-units",INFO,"systemd status unavailable",e,command_text(cmd),ms)
    lines=[x for x in o.splitlines() if x.strip()]
    return CheckResult("system","failed-units",OK if not lines else FAIL,"no failed systemd units" if not lines else f"{len(lines)} failed unit(s)","\n".join(lines[:20]),command_text(cmd),ms)

def run_system_checks(config):
    r=[_uptime(),_load_average(),_memory()]; r.extend(_disk(config.get("disk_paths",["/"]))); r.append(_failed_units()); return r
