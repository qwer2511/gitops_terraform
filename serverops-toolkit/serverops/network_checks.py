from __future__ import annotations
import socket
from .common import CheckResult,OK,WARN,FAIL,INFO,run_command,command_text

def run_network_checks(config):
    results=[]
    for name,cmd in [("interfaces",["ip","-br","addr"]),("default-route",["ip","route","show","default"]),("neighbors",["ip","neigh","show"])]:
        rc,o,e,ms=run_command(cmd,5); status=INFO if rc==127 else (OK if rc==0 else FAIL)
        if name=="default-route" and rc==0 and not o: status=FAIL
        if name=="neighbors" and "FAILED" in o: status=WARN
        results.append(CheckResult("network",name,status,o.splitlines()[0] if o else (e or "unavailable"),o,command_text(cmd),ms))
    target=str(config.get("dns_target", ""))
    if target:
        try:
            addrs=sorted({x[4][0] for x in socket.getaddrinfo(target,443,type=socket.SOCK_STREAM)})
            results.append(CheckResult("network","dns",OK,f"DNS resolution works for {target}",", ".join(addrs[:6])))
        except OSError as exc: results.append(CheckResult("network","dns",FAIL,f"DNS resolution failed for {target}",str(exc)))
    else: results.append(CheckResult("network","dns",INFO,"DNS check not configured"))
    for target in config.get("ping_targets",[]):
        cmd=["ping","-c","1","-W","2",str(target)]; rc,o,e,ms=run_command(cmd,4)
        status=INFO if rc==127 else (OK if rc==0 else FAIL); summary="ping command unavailable" if rc==127 else ("reachable" if rc==0 else "unreachable")
        results.append(CheckResult("network",f"ping:{target}",status,summary,e or o,command_text(cmd),ms))
    return results
