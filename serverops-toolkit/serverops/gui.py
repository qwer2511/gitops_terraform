from __future__ import annotations

import os
import platform
import queue
import socket
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Dict, List, Optional

from .cli import collect
from .common import CheckResult, FAIL, INFO, OK, SKIP, WARN
from .config import load_config
from .i18n import category_label, name_label, status_label
from .inventory import ServerEntry, load_inventory
from .ip_scan import scan_ip_references
from .report import write_text

VERSION = "0.2.0"

DARK = {"bg":"#0b1220","panel":"#111827","panel2":"#172033","border":"#263247","text":"#e5e7eb","muted":"#94a3b8","accent":"#3b82f6","accent_hover":"#2563eb","ok":"#22c55e","warn":"#f59e0b","fail":"#ef4444","info":"#38bdf8","skip":"#64748b","select":"#1e3a5f"}
LIGHT = {"bg":"#f4f7fb","panel":"#ffffff","panel2":"#f8fafc","border":"#dbe3ee","text":"#172033","muted":"#64748b","accent":"#2563eb","accent_hover":"#1d4ed8","ok":"#16a34a","warn":"#d97706","fail":"#dc2626","info":"#0284c7","skip":"#64748b","select":"#dbeafe"}
STATUS_COLORS = {OK:"ok", WARN:"warn", FAIL:"fail", INFO:"info", SKIP:"skip"}


class ServerOpsGUI(tk.Tk):
    def __init__(self, config_path: Optional[str] = None, inventory_path: Optional[str] = None):
        super().__init__()
        self.title(f"ServerOps Manager v{VERSION}")
        self.geometry("1320x820")
        self.minsize(1080, 680)
        self.config_path = config_path
        self.inventory_path = inventory_path
        self.config_data = load_config(config_path)
        self.servers = load_inventory(inventory_path)
        self.selected_server: Optional[ServerEntry] = None
        self.server_by_iid: Dict[str, ServerEntry] = {}
        self.last_results: List[CheckResult] = []
        self._worker_queue = queue.Queue()
        self.dark_mode = True
        self.palette = DARK
        self._build_style()
        self._build_layout()
        self._populate_servers()
        self.after(100, self._poll_worker)

    def _build_style(self) -> None:
        p = self.palette
        self.configure(bg=p["bg"])
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("App.TFrame", background=p["bg"])
        style.configure("Panel.TFrame", background=p["panel"])
        style.configure("Card.TFrame", background=p["panel2"], relief="flat")
        style.configure("TLabel", background=p["panel"], foreground=p["text"], font=("Malgun Gothic", 10))
        style.configure("Title.TLabel", background=p["panel"], foreground=p["text"], font=("Malgun Gothic", 18, "bold"))
        style.configure("Section.TLabel", background=p["panel"], foreground=p["text"], font=("Malgun Gothic", 11, "bold"))
        style.configure("Muted.TLabel", background=p["panel"], foreground=p["muted"], font=("Malgun Gothic", 9))
        style.configure("CardTitle.TLabel", background=p["panel2"], foreground=p["muted"], font=("Malgun Gothic", 9))
        style.configure("CardValue.TLabel", background=p["panel2"], foreground=p["text"], font=("Malgun Gothic", 14, "bold"))
        style.configure("Primary.TButton", background=p["accent"], foreground="#ffffff", padding=(16,10), font=("Malgun Gothic",10,"bold"), borderwidth=0)
        style.map("Primary.TButton", background=[("active",p["accent_hover"]),("pressed",p["accent_hover"])])
        style.configure("Action.TButton", background=p["panel2"], foreground=p["text"], padding=(14,10), font=("Malgun Gothic",9), borderwidth=1, relief="solid")
        style.map("Action.TButton", background=[("active",p["select"])])
        style.configure("Ghost.TButton", background=p["panel"], foreground=p["muted"], padding=(10,7), borderwidth=0)
        style.map("Ghost.TButton", foreground=[("active",p["text"])], background=[("active",p["panel2"])])
        style.configure("Treeview", background=p["panel"], fieldbackground=p["panel"], foreground=p["text"], rowheight=30, borderwidth=0, font=("Malgun Gothic",9))
        style.configure("Treeview.Heading", background=p["panel2"], foreground=p["muted"], font=("Malgun Gothic",9,"bold"), relief="flat")
        style.map("Treeview", background=[("selected",p["select"])], foreground=[("selected",p["text"])])

    def _build_layout(self) -> None:
        for child in self.winfo_children():
            child.destroy()
        root = ttk.Frame(self, style="App.TFrame", padding=12)
        root.pack(fill="both", expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)
        self.sidebar = ttk.Frame(root, style="Panel.TFrame", width=255, padding=14)
        self.sidebar.grid(row=0,column=0,sticky="nsew",padx=(0,10))
        self.sidebar.grid_propagate(False)
        self.sidebar.rowconfigure(3,weight=1)
        self._build_sidebar(self.sidebar)
        self.main = ttk.Frame(root, style="Panel.TFrame", padding=18)
        self.main.grid(row=0,column=1,sticky="nsew")
        self.main.columnconfigure(0,weight=1)
        self.main.rowconfigure(4,weight=1)
        self._build_main(self.main)

    def _build_sidebar(self, parent) -> None:
        ttk.Label(parent,text="SERVEROPS",style="Title.TLabel").grid(row=0,column=0,sticky="w")
        ttk.Label(parent,text="서버 운영 자동화",style="Muted.TLabel").grid(row=1,column=0,sticky="w",pady=(0,14))
        search_wrap = ttk.Frame(parent,style="Panel.TFrame")
        search_wrap.grid(row=2,column=0,sticky="ew",pady=(0,10))
        search_wrap.columnconfigure(0,weight=1)
        self.server_search = tk.StringVar()
        entry = tk.Entry(search_wrap,textvariable=self.server_search,relief="flat",bd=0,font=("Malgun Gothic",10),bg=self.palette["panel2"],fg=self.palette["text"],insertbackground=self.palette["text"])
        entry.grid(row=0,column=0,sticky="ew",ipady=8,ipadx=8)
        self.server_search.trace_add("write",lambda *_: self._populate_servers())
        tree_wrap = ttk.Frame(parent,style="Panel.TFrame")
        tree_wrap.grid(row=3,column=0,sticky="nsew")
        tree_wrap.rowconfigure(0,weight=1); tree_wrap.columnconfigure(0,weight=1)
        self.server_tree = ttk.Treeview(tree_wrap,show="tree",selectmode="browse")
        self.server_tree.grid(row=0,column=0,sticky="nsew")
        self.server_tree.bind("<<TreeviewSelect>>",self._on_server_select)
        scroll = ttk.Scrollbar(tree_wrap,orient="vertical",command=self.server_tree.yview)
        scroll.grid(row=0,column=1,sticky="ns"); self.server_tree.configure(yscrollcommand=scroll.set)
        bottom = ttk.Frame(parent,style="Panel.TFrame")
        bottom.grid(row=4,column=0,sticky="ew",pady=(12,0)); bottom.columnconfigure(0,weight=1)
        self.theme_button = ttk.Button(bottom,text="☾  다크 모드",style="Ghost.TButton",command=self._toggle_theme)
        self.theme_button.grid(row=0,column=0,sticky="w")
        ttk.Label(bottom,text=f"v{VERSION}",style="Muted.TLabel").grid(row=0,column=1,sticky="e")

    def _build_main(self, parent) -> None:
        header = ttk.Frame(parent,style="Panel.TFrame")
        header.grid(row=0,column=0,sticky="ew"); header.columnconfigure(0,weight=1)
        self.server_name_label = ttk.Label(header,text="서버를 선택하세요",style="Title.TLabel")
        self.server_name_label.grid(row=0,column=0,sticky="w")
        self.target_label = ttk.Label(header,text="",style="Muted.TLabel")
        self.target_label.grid(row=1,column=0,sticky="w",pady=(2,0))
        self.connection_label = tk.Label(header,text="● 대기",font=("Malgun Gothic",10,"bold"),bd=0,padx=12,pady=6)
        self.connection_label.grid(row=0,column=1,rowspan=2,sticky="e")
        self._paint_connection("대기",INFO)
        cards = ttk.Frame(parent,style="Panel.TFrame")
        cards.grid(row=1,column=0,sticky="ew",pady=(18,12))
        for c in range(5): cards.columnconfigure(c,weight=1,uniform="cards")
        self.card_values = {}
        specs=[("상태","status"),("OS / Host","host"),("CPU / Load","cpu"),("메모리","memory"),("디스크","disk")]
        for col,(title,key) in enumerate(specs):
            card=ttk.Frame(cards,style="Card.TFrame",padding=(14,12)); card.grid(row=0,column=col,sticky="nsew",padx=(0 if col==0 else 5,0 if col==4 else 5))
            ttk.Label(card,text=title,style="CardTitle.TLabel").pack(anchor="w")
            value=ttk.Label(card,text="—",style="CardValue.TLabel"); value.pack(anchor="w",pady=(6,0)); self.card_values[key]=value
        actions=ttk.Frame(parent,style="Panel.TFrame"); actions.grid(row=2,column=0,sticky="ew",pady=(2,12))
        ttk.Label(actions,text="빠른 작업",style="Section.TLabel").pack(anchor="w",pady=(0,8))
        grid=ttk.Frame(actions,style="Panel.TFrame"); grid.pack(fill="x")
        for c in range(8): grid.columnconfigure(c,weight=1,uniform="actions")
        buttons=[("전체 진단","all","Primary.TButton"),("시스템","system","Action.TButton"),("네트워크","network","Action.TButton"),("서비스","services","Action.TButton"),("MariaDB","mariadb","Action.TButton"),("포트","ports","Action.TButton"),("로그","logs","Action.TButton"),("IP 검색","ip-scan","Action.TButton")]
        for i,(label,action,style) in enumerate(buttons):
            ttk.Button(grid,text=label,style=style,command=lambda a=action:self._run_action(a)).grid(row=0,column=i,sticky="ew",padx=(0 if i==0 else 4,0 if i==len(buttons)-1 else 4))
        toolrow=ttk.Frame(parent,style="Panel.TFrame"); toolrow.grid(row=3,column=0,sticky="ew",pady=(0,8)); toolrow.columnconfigure(0,weight=1)
        self.result_title=ttk.Label(toolrow,text="진단 결과",style="Section.TLabel"); self.result_title.grid(row=0,column=0,sticky="w")
        ttk.Button(toolrow,text="리포트 저장",style="Ghost.TButton",command=self._save_report).grid(row=0,column=1,padx=(6,0))
        ttk.Button(toolrow,text="결과 지우기",style="Ghost.TButton",command=self._clear_results).grid(row=0,column=2,padx=(6,0))
        result_area=ttk.Frame(parent,style="Panel.TFrame"); result_area.grid(row=4,column=0,sticky="nsew"); result_area.rowconfigure(0,weight=3); result_area.rowconfigure(1,weight=1); result_area.columnconfigure(0,weight=1)
        columns=("status","category","name","summary")
        self.results_tree=ttk.Treeview(result_area,columns=columns,show="headings",selectmode="browse")
        for key,text in (("status","상태"),("category","분류"),("name","점검 항목"),("summary","결과")): self.results_tree.heading(key,text=text)
        self.results_tree.column("status",width=80,minwidth=70,stretch=False,anchor="center"); self.results_tree.column("category",width=100,minwidth=90,stretch=False); self.results_tree.column("name",width=220,minwidth=150); self.results_tree.column("summary",width=500,minwidth=250)
        self.results_tree.grid(row=0,column=0,sticky="nsew"); self.results_tree.bind("<<TreeviewSelect>>",self._show_result_detail)
        ybar=ttk.Scrollbar(result_area,orient="vertical",command=self.results_tree.yview); ybar.grid(row=0,column=1,sticky="ns"); self.results_tree.configure(yscrollcommand=ybar.set)
        self.detail_text=tk.Text(result_area,height=8,relief="flat",wrap="word",font=("Consolas",9),padx=12,pady=10,state="disabled")
        self.detail_text.grid(row=1,column=0,columnspan=2,sticky="nsew",pady=(8,0)); self._style_text_widgets()
        statusbar=ttk.Frame(parent,style="Panel.TFrame"); statusbar.grid(row=5,column=0,sticky="ew",pady=(8,0)); statusbar.columnconfigure(0,weight=1)
        self.status_message=ttk.Label(statusbar,text="준비됨",style="Muted.TLabel"); self.status_message.grid(row=0,column=0,sticky="w")
        self.clock_label=ttk.Label(statusbar,text="",style="Muted.TLabel"); self.clock_label.grid(row=0,column=1,sticky="e"); self._tick_clock()

    def _style_text_widgets(self):
        p=self.palette
        if hasattr(self,"detail_text"): self.detail_text.configure(bg=p["panel2"],fg=p["text"],insertbackground=p["text"],selectbackground=p["select"])

    def _populate_servers(self):
        if not hasattr(self,"server_tree"): return
        self.server_tree.delete(*self.server_tree.get_children()); self.server_by_iid={}
        query=self.server_search.get().strip().lower() if hasattr(self,"server_search") else ""
        grouped={}
        for server in self.servers:
            hay=f"{server.name} {server.host} {server.group} {server.user}".lower()
            if query and query not in hay: continue
            grouped.setdefault(server.group,[]).append(server)
        for group in sorted(grouped):
            gid=self.server_tree.insert("","end",text=f"▾  {group}",open=True)
            for server in grouped[group]:
                icon="●" if server.local else "○"
                iid=self.server_tree.insert(gid,"end",text=f"  {icon}  {server.name}"); self.server_by_iid[iid]=server
        roots=self.server_tree.get_children()
        if roots:
            children=self.server_tree.get_children(roots[0])
            if children:
                self.server_tree.selection_set(children[0]); self.server_tree.focus(children[0]); self._on_server_select()

    def _on_server_select(self,_event=None):
        selection=self.server_tree.selection()
        if not selection: return
        item=selection[0]
        if not self.server_tree.parent(item): return
        server=self.server_by_iid.get(item)
        if not server: return
        self.selected_server=server; self.server_name_label.configure(text=server.name); self.target_label.configure(text=f"{server.display_target}   ·   {server.group}")
        if server.local:
            self._paint_connection("로컬",OK); self.card_values["host"].configure(text=self._local_identity())
        else:
            self._paint_connection("미확인",INFO); self.card_values["host"].configure(text=server.host)
        for key in ("status","cpu","memory","disk"): self.card_values[key].configure(text="—")
        self.status_message.configure(text=f"{server.name} 선택됨")

    def _local_identity(self):
        host=socket.gethostname(); os_name=platform.system(); release=platform.release()
        try:
            if os.path.isfile("/etc/os-release"):
                data={}
                with open("/etc/os-release","r",encoding="utf-8",errors="replace") as fh:
                    for line in fh:
                        if "=" in line:
                            key,value=line.rstrip().split("=",1); data[key]=value.strip().strip('"')
                os_name=data.get("PRETTY_NAME",os_name); return f"{host} · {os_name}"[:36]
        except OSError: pass
        return f"{host} · {os_name} {release}"[:36]

    def _run_action(self,action):
        server=self.selected_server
        if not server:
            messagebox.showinfo("ServerOps","먼저 서버를 선택하세요."); return
        if not server.local:
            messagebox.showinfo("원격 SSH 준비 중","v0.2 GUI에서는 로컬 진단 엔진을 먼저 연결했습니다.\n원격 서버 SSH 진단은 다음 단계에서 이 화면에 그대로 연결합니다.\n\n비밀번호를 파일에 저장하지 않는 SSH Key 방식으로 구현할 예정입니다."); return
        if action=="ip-scan":
            target=simpledialog.askstring("IP / 문자열 검색","설정 파일에서 찾을 IP 또는 문자열을 입력하세요:",parent=self)
            if not target: return
            runner=lambda:scan_ip_references(target.strip(),self.config_data); title=f"IP 검색 · {target.strip()}"
        else:
            runner=lambda:collect(action,self.config_data); labels={"all":"전체 진단","system":"시스템","network":"네트워크","services":"서비스","mariadb":"MariaDB","ports":"포트","logs":"로그"}; title=labels.get(action,action)
        self.result_title.configure(text=f"진단 결과 · {title}"); self.status_message.configure(text=f"{title} 실행 중..."); self._paint_connection("점검 중",INFO)
        threading.Thread(target=self._worker,args=(runner,title),daemon=True).start()

    def _worker(self,runner,title):
        try: self._worker_queue.put(("ok",title,runner()))
        except Exception as exc: self._worker_queue.put(("error",title,exc))

    def _poll_worker(self):
        try:
            while True:
                kind,title,payload=self._worker_queue.get_nowait()
                if kind=="ok": self._render_results(payload); self.status_message.configure(text=f"{title} 완료 · {len(payload)}개 항목")
                else: self._paint_connection("오류",FAIL); self.status_message.configure(text=f"{title} 실행 오류"); messagebox.showerror("ServerOps 오류",str(payload))
        except queue.Empty: pass
        self.after(100,self._poll_worker)

    def _render_results(self,results):
        self.last_results=results; self.results_tree.delete(*self.results_tree.get_children()); counts={OK:0,WARN:0,FAIL:0,INFO:0,SKIP:0}
        for index,item in enumerate(results):
            counts[item.status]=counts.get(item.status,0)+1
            iid=self.results_tree.insert("","end",values=(status_label(item.status),category_label(item.category),name_label(item.name),item.summary)); self.results_tree.item(iid,tags=(item.status,str(index)))
        for status,color_key in STATUS_COLORS.items(): self.results_tree.tag_configure(status,foreground=self.palette[color_key])
        overall=FAIL if counts[FAIL] else WARN if counts[WARN] else OK; label="장애" if overall==FAIL else "주의" if overall==WARN else "정상"
        self.card_values["status"].configure(text=f"{label}  {counts[FAIL]}/{counts[WARN]}"); self._paint_connection("진단 완료",overall); self._update_summary_cards(results)
        if results:
            first=self.results_tree.get_children()[0]; self.results_tree.selection_set(first); self._show_result_detail()

    def _update_summary_cards(self,results):
        cpu=next((r for r in results if r.name=="load-average"),None); memory=next((r for r in results if r.name=="memory"),None); disk=next((r for r in results if r.name.startswith("disk:")),None)
        if cpu: self.card_values["cpu"].configure(text=cpu.summary.split(",")[0])
        if memory: self.card_values["memory"].configure(text=memory.summary.replace("사용률=",""))
        if disk: self.card_values["disk"].configure(text=disk.summary.replace("사용률=",""))

    def _show_result_detail(self,_event=None):
        selected=self.results_tree.selection()
        if not selected:return
        iid=selected[0]; tags=self.results_tree.item(iid,"tags"); index=next((int(t) for t in tags if str(t).isdigit()),None)
        if index is None or index>=len(self.last_results):return
        item=self.last_results[index]; lines=[f"[{status_label(item.status)}] {category_label(item.category)} / {name_label(item.name)}",item.summary]
        if item.command: lines.extend(["",f"실행 명령: {item.command}"])
        if item.details: lines.extend(["",item.details])
        self.detail_text.configure(state="normal"); self.detail_text.delete("1.0","end"); self.detail_text.insert("1.0","\n".join(lines)); self.detail_text.configure(state="disabled")

    def _paint_connection(self,text,status):
        key=STATUS_COLORS.get(status,"info"); p=self.palette; self.connection_label.configure(text=f"●  {text}",bg=p["panel"],fg=p[key])

    def _save_report(self):
        if not self.last_results:
            messagebox.showinfo("리포트","저장할 진단 결과가 없습니다."); return
        server_name=self.selected_server.name if self.selected_server else "server"; default=f"serverops_{server_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path=filedialog.asksaveasfilename(parent=self,title="진단 리포트 저장",defaultextension=".txt",initialfile=default,filetypes=[("텍스트","*.txt"),("모든 파일","*.*")])
        if path: write_text(self.last_results,path); self.status_message.configure(text=f"리포트 저장 완료: {os.path.basename(path)}")

    def _clear_results(self):
        self.last_results=[]; self.results_tree.delete(*self.results_tree.get_children()); self.detail_text.configure(state="normal"); self.detail_text.delete("1.0","end"); self.detail_text.configure(state="disabled")
        for key in ("status","cpu","memory","disk"): self.card_values[key].configure(text="—")
        self.result_title.configure(text="진단 결과"); self.status_message.configure(text="결과를 지웠습니다.")

    def _toggle_theme(self):
        selected=self.selected_server.name if self.selected_server else None; self.dark_mode=not self.dark_mode; self.palette=DARK if self.dark_mode else LIGHT
        self._build_style(); self._build_layout(); self._populate_servers()
        if selected:
            for root in self.server_tree.get_children():
                for child in self.server_tree.get_children(root):
                    mapped=self.server_by_iid.get(child)
                    if mapped and mapped.name==selected:
                        self.server_tree.selection_set(child); self.server_tree.focus(child); self._on_server_select(); break
        self.theme_button.configure(text="☾  다크 모드" if self.dark_mode else "☀  라이트 모드")
        if self.last_results:self._render_results(self.last_results)

    def _tick_clock(self):
        if hasattr(self,"clock_label"): self.clock_label.configure(text=datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
        self.after(1000,self._tick_clock)


def launch(config_path: Optional[str] = None, inventory_path: Optional[str] = None) -> int:
    try: app=ServerOpsGUI(config_path=config_path,inventory_path=inventory_path)
    except tk.TclError as exc: raise RuntimeError(f"GUI를 시작할 수 없습니다: {exc}") from exc
    app.mainloop(); return 0
