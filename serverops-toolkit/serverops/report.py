import json
from collections import Counter
from pathlib import Path
from .common import now_iso

def summarize(results):
    counts=Counter(x.status for x in results)
    return {"generated_at":now_iso(),"total":len(results),"counts":dict(counts)}

def write_json(results,path):
    Path(path).write_text(json.dumps({"summary":summarize(results),"results":[x.to_dict() for x in results]},indent=2,ensure_ascii=False)+"\n",encoding="utf-8"); return path

def write_text(results,path):
    s=summarize(results); lines=["ServerOps Diagnostic Report","="*80,f"Generated: {s['generated_at']}",f"Total checks: {s['total']}",f"Counts: {s['counts']}",""]
    for x in results:
        lines.append(f"[{x.status}] {x.category}/{x.name} - {x.summary}")
        if x.command: lines.append(f"  command: {x.command}")
        if x.details:
            lines.append("  details:"); lines.extend(f"    {line}" for line in x.details.splitlines())
        lines.append("")
    Path(path).write_text("\n".join(lines),encoding="utf-8"); return path
