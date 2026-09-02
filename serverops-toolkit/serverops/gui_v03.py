from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Optional

from .common import CheckResult, OK
from .gui_base import DARK, LIGHT, STATUS_COLORS, ServerOpsGUI as BaseGUI
from .inventory import ServerEntry
from .ip_scan import scan_ip_references
from .os_compat import compatibility_checks
from .remote_checks import remote_collect, remote_ip_scan
from .transfer import download as sftp_download, upload as sftp_upload

VERSION = "0.3.0"


class ServerOpsGUI(BaseGUI):
    def __init__(self, config_path: Optional[str] = None, inventory_path: Optional[str] = None):
        super().__init__(config_path=config_path, inventory_path=inventory_path)
        self.title(f"ServerOps Manager v{VERSION}")

    def _build_main(self, parent: ttk.Frame) -> None:
        super()._build_main(parent)
        header = self.connection_label.master
        self.connection_label.grid_configure(column=3)
        ttk.Button(header, text="연결 확인", style="Ghost.TButton", command=lambda: self._run_action("connection")).grid(row=0, column=1, rowspan=2, padx=(6, 3))
        ttk.Button(header, text="SFTP 전송", style="Ghost.TButton", command=self._open_sftp).grid(row=0, column=2, rowspan=2, padx=3)
        toolrow = self.result_title.master
        ttk.Button(toolrow, text="호환성", style="Ghost.TButton", command=lambda: self._run_action("compat")).grid(row=0, column=3, padx=(6, 0))

    def _run_action(self, action: str) -> None:
        server = self.selected_server
        if not server:
            messagebox.showinfo("ServerOps", "먼저 서버를 선택하세요.")
            return
        if action == "ip-scan":
            target = simpledialog.askstring("IP / 문자열 검색", "설정 파일에서 찾을 IP 또는 문자열을 입력하세요:", parent=self)
            if not target:
                return
            runner = (lambda: scan_ip_references(target.strip(), self.config_data)) if server.local else (lambda: remote_ip_scan(server, target.strip(), self.config_data))
            title = f"IP 검색 · {target.strip()}"
        elif action == "connection":
            runner = (lambda: [CheckResult("remote", "ssh-connection", OK, "로컬 서버", self._local_identity())]) if server.local else (lambda: remote_collect("connection", server, self.config_data))
            title = "연결 확인"
        elif server.local:
            runner = (lambda: compatibility_checks()) if action == "compat" else (lambda: self._local_collect(action))
            title = {"all":"전체 진단","system":"시스템","network":"네트워크","services":"서비스","mariadb":"MariaDB","ports":"포트","logs":"로그","compat":"호환성"}.get(action, action)
        else:
            runner = lambda: remote_collect(action, server, self.config_data)
            title = {"all":"원격 전체 진단","system":"원격 시스템","network":"원격 네트워크","services":"원격 서비스","mariadb":"원격 MariaDB","ports":"원격 포트","logs":"원격 로그","compat":"원격 호환성"}.get(action, action)
        self.result_title.configure(text=f"진단 결과 · {title}")
        self.status_message.configure(text=f"{title} 실행 중...")
        self._paint_connection("점검 중", "INFO")
        threading.Thread(target=self._worker, args=(runner, title), daemon=True).start()

    def _local_collect(self, action: str):
        from .cli import collect
        return collect(action, self.config_data)

    def _update_summary_cards(self, results):
        super()._update_summary_cards(results)
        os_profile = next((r for r in results if r.name == "os-profile"), None)
        if os_profile:
            self.card_values["host"].configure(text=os_profile.summary[:36])

    def _open_sftp(self) -> None:
        server = self.selected_server
        if not server:
            messagebox.showinfo("SFTP", "먼저 서버를 선택하세요.")
            return
        if server.local:
            messagebox.showinfo("SFTP", "SFTP 전송은 원격 서버에서 사용합니다.")
            return
        SFTPDialog(self, server)


class SFTPDialog(tk.Toplevel):
    def __init__(self, parent: ServerOpsGUI, server: ServerEntry):
        super().__init__(parent)
        self.parent = parent
        self.server = server
        self.title(f"SFTP 전송 · {server.name}")
        self.geometry("620x390")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.queue = queue.Queue()
        self.configure(bg=parent.palette["bg"])
        self._build()
        self.after(100, self._poll)

    def _build(self) -> None:
        p = self.parent.palette
        frame = ttk.Frame(self, style="Panel.TFrame", padding=20)
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        ttk.Label(frame, text="안전한 SFTP 파일 전송", style="Title.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(frame, text=f"{self.server.display_target} · SSH 암호화 전송", style="Muted.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 16))
        ttk.Label(frame, text="원격 경로", style="Section.TLabel").grid(row=2, column=0, sticky="w", pady=6)
        self.remote_var = tk.StringVar(value="/tmp/")
        remote = tk.Entry(frame, textvariable=self.remote_var, relief="flat", bd=0, font=("Consolas", 10), bg=p["panel2"], fg=p["text"], insertbackground=p["text"])
        remote.grid(row=2, column=1, columnspan=2, sticky="ew", ipady=7, ipadx=7)
        frame.columnconfigure(1, weight=1)
        self.compress_var = tk.BooleanVar(value=True)
        self.verify_var = tk.BooleanVar(value=True)
        self.archive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="SSH 전송 압축 (-C)", variable=self.compress_var).grid(row=3, column=0, columnspan=3, sticky="w", pady=(12, 3))
        ttk.Checkbutton(frame, text="SHA-256 무결성 검증", variable=self.verify_var).grid(row=4, column=0, columnspan=3, sticky="w", pady=3)
        ttk.Checkbutton(frame, text="업로드 전에 ZIP로 묶기", variable=self.archive_var).grid(row=5, column=0, columnspan=3, sticky="w", pady=3)
        ttk.Label(frame, text="폴더 업로드는 자동으로 ZIP로 묶습니다. 압축은 전송량을 줄이고, 파일이 동일한지는 SHA-256으로 확인합니다.", style="Muted.TLabel", wraplength=540, justify="left").grid(row=6, column=0, columnspan=3, sticky="w", pady=(10, 16))
        ttk.Button(frame, text="파일 업로드", style="Primary.TButton", command=self._upload_file).grid(row=7, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(frame, text="폴더 업로드", style="Action.TButton", command=self._upload_dir).grid(row=7, column=1, sticky="ew", padx=6)
        ttk.Button(frame, text="파일 다운로드", style="Action.TButton", command=self._download).grid(row=7, column=2, sticky="ew", padx=(6, 0))
        self.status = ttk.Label(frame, text="대기 중", style="Muted.TLabel", wraplength=550)
        self.status.grid(row=8, column=0, columnspan=3, sticky="w", pady=(18, 0))

    def _upload_file(self) -> None:
        path = filedialog.askopenfilename(parent=self, title="업로드할 파일 선택")
        if path:
            self._start_upload(path, self.archive_var.get())

    def _upload_dir(self) -> None:
        path = filedialog.askdirectory(parent=self, title="업로드할 폴더 선택")
        if path:
            self._start_upload(path, True)

    def _start_upload(self, path: str, archive: bool) -> None:
        remote = self.remote_var.get().strip()
        if not remote:
            messagebox.showwarning("SFTP", "원격 경로를 입력하세요.", parent=self); return
        self.status.configure(text="업로드 중...")
        def work():
            try:
                self.queue.put(("done", sftp_upload(self.server, path, remote, archive=archive, ssh_compression=self.compress_var.get(), verify=self.verify_var.get())))
            except Exception as exc:
                self.queue.put(("error", exc))
        threading.Thread(target=work, daemon=True).start()

    def _download(self) -> None:
        remote = self.remote_var.get().strip()
        if not remote or remote.endswith("/"):
            messagebox.showwarning("SFTP", "다운로드할 원격 파일 전체 경로를 입력하세요.", parent=self); return
        local = filedialog.asksaveasfilename(parent=self, title="다운로드 저장 위치", initialfile=os.path.basename(remote) or "download.bin")
        if not local:
            return
        self.status.configure(text="다운로드 중...")
        def work():
            try:
                self.queue.put(("done", sftp_download(self.server, remote, local, ssh_compression=self.compress_var.get(), verify=self.verify_var.get())))
            except Exception as exc:
                self.queue.put(("error", exc))
        threading.Thread(target=work, daemon=True).start()

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "done":
                    suffix = " · SHA-256 일치" if payload.verified else ""
                    self.status.configure(text=payload.message + suffix)
                    (messagebox.showinfo if payload.ok else messagebox.showerror)("SFTP 완료" if payload.ok else "SFTP 검증 실패", payload.message + suffix, parent=self)
                else:
                    self.status.configure(text=f"오류: {payload}")
                    messagebox.showerror("SFTP 오류", str(payload), parent=self)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(100, self._poll)


def launch(config_path: Optional[str] = None, inventory_path: Optional[str] = None) -> int:
    try:
        app = ServerOpsGUI(config_path=config_path, inventory_path=inventory_path)
    except tk.TclError as exc:
        raise RuntimeError(f"GUI를 시작할 수 없습니다: {exc}") from exc
    app.mainloop()
    return 0
