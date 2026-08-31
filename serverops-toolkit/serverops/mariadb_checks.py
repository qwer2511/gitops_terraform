from .common import CheckResult,OK,WARN,FAIL,INFO,SKIP,run_command,command_text

def run_mariadb_checks(config):
    results=[]
    active=None
    for candidate in ("mariadb","mysql","mysqld"):
        cmd=["systemctl","is-active",candidate]; rc,o,e,ms=run_command(cmd,4)
        if o.strip()=="active": active=candidate; break
    results.append(CheckResult("mariadb","service",OK if active else WARN,f"{active}=active" if active else "MariaDB/MySQL systemd service not active or not found"))
    cmd=["ss","-lntp"]; rc,o,e,ms=run_command(cmd,5); matches=[x for x in o.splitlines() if ":3306" in x]
    if rc!=0: results.append(CheckResult("mariadb","listener",INFO,"socket inspection unavailable",e,command_text(cmd),ms))
    else: results.append(CheckResult("mariadb","listener",OK if matches else WARN,"3306 listener found" if matches else "no listener detected on 3306","\n".join(matches[:10]),command_text(cmd),ms))
    m=config.get("mariadb",{})
    if not m.get("admin_ping",True): results.append(CheckResult("mariadb","admin-ping",SKIP,"disabled in config")); return results
    cmd=["mysqladmin","ping","--connect-timeout=3"]
    if m.get("host"): cmd += ["--host",str(m["host"])]
    if m.get("user"): cmd += ["--user",str(m["user"])]
    if m.get("socket"): cmd += ["--socket",str(m["socket"])]
    rc,o,e,ms=run_command(cmd,5)
    status=INFO if rc==127 else (OK if rc==0 and "alive" in o.lower() else FAIL)
    results.append(CheckResult("mariadb","admin-ping",status,"mysqladmin not installed" if rc==127 else (o or "mysqladmin ping failed"),e,command_text(cmd),ms))
    return results
