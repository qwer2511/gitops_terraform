import os
from .common import CheckResult,OK,WARN,INFO

def _excluded(path,excludes):
    p=os.path.abspath(path)
    return any(p==os.path.abspath(x) or p.startswith(os.path.abspath(x)+os.sep) for x in excludes if x)

def scan_ip_references(target,config):
    roots=config.get("ip_scan_roots",["/etc"]); excludes=config.get("ip_scan_excludes",[]); max_bytes=int(config.get("ip_scan_max_file_bytes",2000000)); matches=[]; errors=0; needle=target.encode()
    for root in roots:
        root=os.path.abspath(str(root)); paths=[]
        if os.path.isfile(root): paths=[root]
        elif os.path.isdir(root):
            for dirpath,dirnames,filenames in os.walk(root):
                dirnames[:]=[d for d in dirnames if not _excluded(os.path.join(dirpath,d),excludes)]
                paths.extend(os.path.join(dirpath,n) for n in filenames)
        for path in paths:
            if _excluded(path,excludes): continue
            try:
                if os.path.getsize(path)>max_bytes: continue
                data=open(path,"rb").read(max_bytes+1)
                if b"\x00" in data[:4096] or needle not in data: continue
                text=data.decode("utf-8",errors="replace"); hits=[]
                for lineno,line in enumerate(text.splitlines(),1):
                    if target in line:
                        clean=line.strip(); clean=clean if len(clean)<=220 else clean[:217]+"..."; hits.append(f"{lineno}: {clean}")
                        if len(hits)>=8: break
                matches.append(CheckResult("ip-scan",path,WARN,f"reference to {target} found","\n".join(hits)))
            except OSError: errors+=1
    if matches: matches.insert(0,CheckResult("ip-scan",target,INFO,f"{len(matches)} file(s) contain the target IP",f"unreadable files skipped: {errors}" if errors else ""))
    else: matches=[CheckResult("ip-scan",target,OK,f"no references found under {', '.join(map(str,roots))}",f"unreadable files skipped: {errors}" if errors else "")]
    return matches
