from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Optional

from .cert_manager import (
    CertificateReplaceRequest,
    planned_steps,
    preflight_certificate,
    replace_certificate,
)
from .gui_v03 import ServerOpsGUI as V03GUI
from .inventory import ServerEntry
from .transfer import upload as sftp_upload

VERSION = "0.4.0"


class ServerOpsGUI(V03GUI):
    def __init__(self, config_path: Optional[str] = None, inventory_path: Optional[str] = None):
        super().__init__(config_path=config_path, inventory_path=inventory_path)
        self.title(f"ServerOps Manager v{VERSION}")

    def _build_main(self, parent: ttk.Frame) -> None:
        super()._build_main(parent)
        toolrow = self.result_title.master
        ttk.Button(
            toolrow,
            text="인증서 교체",
            style="Ghost.TButton",
            command=self._open_certificate_manager,
        ).grid(row=0, column=4, padx=(6, 0))

    def _open_certificate_manager(self) -> None:
        server = self.selected_server
        if not server:
            messagebox.showinfo("인증서 교체", "먼저 원격 서버를 선택하세요.")
            return
        if server.local:
            messagebox.showinfo("인증서 교체", "인증서 자동 교체는 원격 서버에서 사용합니다.")
            return
        CertificateReplaceDialog(self, server)


class CertificateReplaceDialog(tk.Toplevel):
    def __init__(self, parent: ServerOpsGUI, server: ServerEntry):
        super().__init__(parent)
        self.parent = parent
        self.server = server
        self.title(f"TLS 인증서 교체 · {server.name}")
        self.geometry("900x720")
        self.minsize(820, 650)
        self.transient(parent)
        self.grab_set()
        self.queue = queue.Queue()
        self.configure(bg=parent.palette["bg"])
        self._build()
        self.after(100, self._poll)

    def _entry(self, frame: ttk.Frame, row: int, label: str, variable: tk.StringVar, button=None) -> None:
        p = self.parent.palette
        ttk.Label(frame, text=label, style="Section.TLabel").grid(row=row, column=0, sticky="w", pady=5)
        entry = tk.Entry(
            frame,
            textvariable=variable,
            relief="flat",
            bd=0,
            font=("Consolas", 10),
            bg=p["panel2"],
            fg=p["text"],
            insertbackground=p["text"],
        )
        entry.grid(row=row, column=1, sticky="ew", ipady=6, ipadx=7, padx=(8, 6))
        if button:
            ttk.Button(frame, text=button[0], style="Ghost.TButton", command=button[1]).grid(row=row, column=2, sticky="ew")

    def _build(self) -> None:
        frame = ttk.Frame(self, style="Panel.TFrame", padding=20)
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(13, weight=1)

        ttk.Label(frame, text="TLS 인증서 안전 교체", style="Title.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(
            frame,
            text=f"{self.server.display_target} · 백업 → 적용 → 설정검사 → 재기동 → 상태/로그 확인 · 실패 시 자동 롤백",
            style="Muted.TLabel",
            wraplength=800,
            justify="left",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 14))

        self.name_var = tk.StringVar(value=self.server.name)
        self.current_cert_var = tk.StringVar()
        self.new_cert_var = tk.StringVar(value="/tmp/")
        self.current_key_var = tk.StringVar()
        self.new_key_var = tk.StringVar()
        self.service_var = tk.StringVar(value="nginx")
        self.action_var = tk.StringVar(value="restart")
        self.sudo_var = tk.BooleanVar(value=True)

        self._entry(frame, 2, "인증서 이름", self.name_var)
        self._entry(frame, 3, "기존 인증서 경로", self.current_cert_var)
        self._entry(frame, 4, "새 인증서 경로", self.new_cert_var, ("SFTP 업로드", self._upload_certificate))
        self._entry(frame, 5, "기존 개인키 경로 (선택)", self.current_key_var)
        self._entry(frame, 6, "새 개인키 경로 (선택)", self.new_key_var, ("SFTP 업로드", self._upload_key))
        self._entry(frame, 7, "systemd 서비스", self.service_var)

        ttk.Label(frame, text="서비스 적용 방식", style="Section.TLabel").grid(row=8, column=0, sticky="w", pady=5)
        action = ttk.Combobox(frame, textvariable=self.action_var, values=("restart", "reload", "auto"), state="readonly", width=18)
        action.grid(row=8, column=1, sticky="w", padx=(8, 6))
        ttk.Label(frame, text="auto = reload 실패 시 restart", style="Muted.TLabel").grid(row=8, column=2, sticky="w")

        ttk.Checkbutton(
            frame,
            text="root가 아니면 sudo -n 사용 (비밀번호 입력/저장 안 함)",
            variable=self.sudo_var,
        ).grid(row=9, column=0, columnspan=3, sticky="w", pady=(8, 2))
        ttk.Label(
            frame,
            text="백업 파일명은 기존경로.YYYYMMDD_HHMMSS.bak 형식입니다. sudo 비밀번호가 필요한 계정이면 NOPASSWD 정책 또는 root/권한 있는 계정이 필요합니다.",
            style="Muted.TLabel",
            wraplength=800,
            justify="left",
        ).grid(row=10, column=0, columnspan=3, sticky="w", pady=(2, 12))

        buttons = ttk.Frame(frame, style="Panel.TFrame")
        buttons.grid(row=11, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        ttk.Button(buttons, text="작업 순서 보기", style="Action.TButton", command=self._show_plan).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="사전 점검", style="Action.TButton", command=self._preflight).pack(side="left", padx=6)
        ttk.Button(buttons, text="인증서 교체 실행", style="Primary.TButton", command=self._execute).pack(side="left", padx=6)
        ttk.Button(buttons, text="로그 지우기", style="Ghost.TButton", command=lambda: self._set_log("")).pack(side="right")

        ttk.Label(frame, text="작업 로그", style="Section.TLabel").grid(row=12, column=0, columnspan=3, sticky="w", pady=(4, 6))
        logframe = ttk.Frame(frame, style="Card.TFrame")
        logframe.grid(row=13, column=0, columnspan=3, sticky="nsew")
        logframe.columnconfigure(0, weight=1)
        logframe.rowconfigure(0, weight=1)
        p = self.parent.palette
        self.log = tk.Text(
            logframe,
            wrap="word",
            relief="flat",
            bd=0,
            font=("Consolas", 9),
            bg=p["panel2"],
            fg=p["text"],
            insertbackground=p["text"],
            padx=10,
            pady=10,
        )
        scroll = ttk.Scrollbar(logframe, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.status = ttk.Label(frame, text="대기 중", style="Muted.TLabel")
        self.status.grid(row=14, column=0, columnspan=3, sticky="w", pady=(8, 0))

    def _request(self) -> CertificateReplaceRequest:
        return CertificateReplaceRequest(
            name=self.name_var.get(),
            current_cert=self.current_cert_var.get(),
            new_cert=self.new_cert_var.get(),
            service=self.service_var.get(),
            current_key=self.current_key_var.get(),
            new_key=self.new_key_var.get(),
            service_action=self.action_var.get(),
            use_sudo=self.sudo_var.get(),
        )

    def _set_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        if text:
            self.log.insert("end", text)
        self.log.configure(state="disabled")
        self.log.see("end")

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + ("\n" if not text.endswith("\n") else ""))
        self.log.configure(state="disabled")
        self.log.see("end")

    def _show_plan(self) -> None:
        try:
            rows = planned_steps(self._request())
        except ValueError as exc:
            messagebox.showwarning("입력 확인", str(exc), parent=self)
            return
        self._set_log("--- 실행 예정 순서 ---\n" + "\n".join(f"{i}. {row}" for i, row in enumerate(rows, 1)))

    def _preflight(self) -> None:
        try:
            req = self._request()
            planned_steps(req)
        except ValueError as exc:
            messagebox.showwarning("입력 확인", str(exc), parent=self)
            return
        self.status.configure(text="사전 점검 중...")
        self._set_log("사전 점검을 시작합니다...\n")

        def work():
            try:
                self.queue.put(("preflight", preflight_certificate(self.server, req)))
            except Exception as exc:
                self.queue.put(("error", exc))
        threading.Thread(target=work, daemon=True).start()

    def _execute(self) -> None:
        try:
            req = self._request()
            plan = planned_steps(req)
        except ValueError as exc:
            messagebox.showwarning("입력 확인", str(exc), parent=self)
            return
        summary = (
            f"대상: {self.server.display_target}\n"
            f"기존: {req.current_cert}\n"
            f"신규: {req.new_cert}\n"
            f"서비스: {req.service} ({req.service_action})\n\n"
            "실패 시 가능한 단계에서는 백업본으로 자동 롤백합니다.\n"
            "계속하려면 아래 입력창에 '교체'를 입력하세요."
        )
        confirm = simpledialog.askstring("인증서 교체 최종 확인", summary, parent=self)
        if confirm != "교체":
            self.status.configure(text="교체가 취소되었습니다.")
            return
        self.status.configure(text="인증서 교체 작업 중...")
        self._set_log("--- 실행 시작 ---\n" + "\n".join(f"{i}. {row}" for i, row in enumerate(plan, 1)) + "\n\n")

        def work():
            try:
                self.queue.put(("replace", replace_certificate(self.server, req)))
            except Exception as exc:
                self.queue.put(("error", exc))
        threading.Thread(target=work, daemon=True).start()

    def _upload_certificate(self) -> None:
        self._upload_to_remote(self.new_cert_var, "새 인증서 파일 선택")

    def _upload_key(self) -> None:
        self._upload_to_remote(self.new_key_var, "새 개인키 파일 선택")

    def _upload_to_remote(self, variable: tk.StringVar, title: str) -> None:
        local = filedialog.askopenfilename(parent=self, title=title)
        if not local:
            return
        remote = variable.get().strip() or "/tmp/"
        if remote.endswith("/"):
            remote += os.path.basename(local)
            variable.set(remote)
        self.status.configure(text=f"SFTP 업로드 중: {os.path.basename(local)}")

        def work():
            try:
                transfer = sftp_upload(
                    self.server,
                    local,
                    remote,
                    archive=False,
                    ssh_compression=True,
                    verify=True,
                )
                self.queue.put(("upload", transfer))
            except Exception as exc:
                self.queue.put(("error", exc))
        threading.Thread(target=work, daemon=True).start()

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "preflight":
                    self._set_log(payload.text_log())
                    self.status.configure(text="사전 점검 통과" if payload.ok else "사전 점검 실패")
                    if payload.ok:
                        messagebox.showinfo("사전 점검", "새 인증서 기본 검증을 통과했습니다.", parent=self)
                    else:
                        messagebox.showerror("사전 점검 실패", "작업 로그를 확인하세요.", parent=self)
                elif kind == "replace":
                    self._set_log(payload.text_log())
                    if payload.ok:
                        self.status.configure(text="인증서 교체 완료")
                        messagebox.showinfo(
                            "인증서 교체 완료",
                            f"교체가 완료되었습니다.\n\n백업: {payload.backup_cert}\n\n서비스 로그를 아래에서 확인하세요.",
                            parent=self,
                        )
                    else:
                        state = " · 자동 롤백 완료" if payload.rolled_back else ""
                        self.status.configure(text="인증서 교체 실패" + state)
                        messagebox.showerror("인증서 교체 실패", "작업 로그와 롤백 상태를 확인하세요.", parent=self)
                elif kind == "upload":
                    self._append_log(f"[SFTP] {payload.message}\n원격 경로: {payload.remote_path}")
                    self.status.configure(text="SFTP 업로드 완료" if payload.ok else "SFTP 업로드 실패")
                    if not payload.ok:
                        messagebox.showerror("SFTP 업로드 실패", payload.message, parent=self)
                elif kind == "error":
                    self._append_log(f"[ERROR] {payload}")
                    self.status.configure(text="오류 발생")
                    messagebox.showerror("ServerOps 오류", str(payload), parent=self)
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
