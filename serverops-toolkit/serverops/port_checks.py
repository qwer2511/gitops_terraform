import socket,time
from .common import CheckResult,OK,FAIL

def check_tcp(host,port,timeout=2.0):
    start=time.monotonic()
    try:
        with socket.create_connection((host,port),timeout=timeout):
            return CheckResult("port",f"{host}:{port}",OK,"TCP connect succeeded",duration_ms=int((time.monotonic()-start)*1000))
    except OSError as exc:
        return CheckResult("port",f"{host}:{port}",FAIL,"TCP connect failed",str(exc),duration_ms=int((time.monotonic()-start)*1000))

def run_port_checks(config):
    out=[]
    for item in config.get("ports",[]):
        try: out.append(check_tcp(str(item.get("host","127.0.0.1")),int(item["port"])))
        except (KeyError,TypeError,ValueError): pass
    return out
