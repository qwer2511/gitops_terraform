from .common import CheckResult,OK,WARN,FAIL,INFO,run_command,command_text

def run_service_checks(config):
    out=[]
    for service in config.get("services",[]):
        cmd=["systemctl","is-active",str(service)]; rc,o,e,ms=run_command(cmd,5); state=o.strip() or e.strip() or "unknown"
        status=OK if state=="active" else WARN if state in {"inactive","deactivating"} else FAIL if state in {"failed","activating"} else INFO
        out.append(CheckResult("service",str(service),status,f"state={state}",e,command_text(cmd),ms))
    return out
