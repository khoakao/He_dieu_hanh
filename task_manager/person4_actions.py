# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
import time
import signal
import subprocess
from collections import deque, defaultdict
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

import psutil

from .config import DEFAULT_CFG, HISTORY_LEN, USER_AUTOSTART_DIR, SYS_AUTOSTART_DIRS, PROC_STATUS_LABEL
from .utils import fmt_bytes, safe_call, is_system_process, dt_from_ts, readlink_exe, run_cmd
from .models import ProcRow
# ============================================================
# PERSON 4 — PROCESS ACTIONS & PROPERTIES
#   - End/Kill/Signal
#   - Nice/Priority
#   - CPU Affinity
#   - Open executable folder / Properties dialog
# Deliverable: mapping actions <-> Windows Task Manager + permission denied cases
# ============================================================



class ActionsMixin:
    # ------------------------------------------------------------
    # [P4][HELPER] Resolve selected PID from current tree
    # ------------------------------------------------------------
    def _selected_pid(self, tree: ttk.Treeview):
        sel = tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except Exception:
            try:
                vals = tree.item(sel[0]).get("values", [])
                return int(vals[0])
            except Exception:
                return None
    # ------------------------------------------------------------
    # [P4][ACTION] End task (SIGTERM)
    # ------------------------------------------------------------


    def end_task_sigterm(self):
        pid = self._selected_pid(self.proc_tree)
        if pid is None:
            return
        self._send_signal(pid, signal.SIGTERM, confirm=True)
    # ------------------------------------------------------------
    # [P4][ACTION] Kill process (SIGKILL)
    # ------------------------------------------------------------


    def kill_process(self):
        pid = self._selected_pid(self.proc_tree)
        if pid is None:
            return
        self._send_signal(pid, signal.SIGKILL, confirm=True)
    # ------------------------------------------------------------
    # [P4][ACTION] Set priority (nice)
    # ------------------------------------------------------------


    def set_priority(self):
        pid = self._selected_pid(self.proc_tree)
        if pid is None:
            return
        self._set_nice(pid)
    # ------------------------------------------------------------
    # [P4][ACTION] Set CPU affinity
    # ------------------------------------------------------------


    def set_affinity(self):
        pid = self._selected_pid(self.proc_tree)
        if pid is None:
            return
        self._set_cpu_affinity(pid)
    # ------------------------------------------------------------
    # [P4][ACTION] Show Properties dialog
    # ------------------------------------------------------------


    def proc_properties(self):
        pid = self._selected_pid(self.proc_tree)
        if pid is None:
            return
        self._show_proc_properties(pid)
    # ------------------------------------------------------------
    # [P4][ACTION] Open executable folder (xdg-open)
    # ------------------------------------------------------------


    def open_exe_folder(self):
        pid = self._selected_pid(self.proc_tree)
        if pid is None:
            return
        try:
            p = psutil.Process(pid)
            exe = p.exe()
            if not exe:
                raise RuntimeError("Không tìm được đường dẫn executable.")
            folder = str(Path(exe).parent)
            safe_call(["xdg-open", folder], timeout=2)
        except Exception as e:
            messagebox.showerror("Open folder", str(e))

    # -------------------------
    # Actions (Details)
    # -------------------------

    def end_task_sigterm_details(self):
        pid = self._selected_pid(self.details_tree)
        if pid is None:
            return
        self._send_signal(pid, signal.SIGTERM, confirm=True)


    def kill_process_details(self):
        pid = self._selected_pid(self.details_tree)
        if pid is None:
            return
        self._send_signal(pid, signal.SIGKILL, confirm=True)


    def set_priority_details(self):
        pid = self._selected_pid(self.details_tree)
        if pid is None:
            return
        self._set_nice(pid)


    def proc_properties_details(self):
        pid = self._selected_pid(self.details_tree)
        if pid is None:
            return
        self._show_proc_properties(pid)

    # -------------------------
    # Signal / priority helpers
    # -------------------------

    def _send_signal(self, pid: int, sig: int, confirm=False):
        try:
            p = psutil.Process(pid)
            name = p.name()
        except Exception:
            name = str(pid)

        if confirm:
            if not messagebox.askyesno("Confirm", f"Send signal {sig} to PID {pid} ({name})?"):
                return

        try:
            os.kill(pid, sig)
        except PermissionError:
            messagebox.showerror("Permission denied", "Bạn không đủ quyền. Thử chạy với sudo hoặc chọn process của user.")
        except ProcessLookupError:
            messagebox.showwarning("Not found", "Process không còn tồn tại.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            self.refresh_processes(force=True)
            self.refresh_details(force=True)


    def _set_nice(self, pid: int):
        try:
            p = psutil.Process(pid)
            cur = int(p.nice())
            new = simpledialog.askinteger("Set priority (nice)",
                                          f"PID {pid} - current nice = {cur}\n"
                                          "Nice range thường: -20 (high) .. 19 (low)\n"
                                          "Nhập nice mới:",
                                          initialvalue=cur, minvalue=-20, maxvalue=19)
            if new is None:
                return
            p.nice(int(new))
            self.refresh_processes(force=True)
            self.refresh_details(force=True)
        except psutil.AccessDenied:
            messagebox.showerror("Permission denied", "Đổi priority cần quyền (đặc biệt nếu giảm nice).")
        except Exception as e:
            messagebox.showerror("Error", str(e))


    def _set_cpu_affinity(self, pid: int):
        try:
            p = psutil.Process(pid)
            cpus = list(range(psutil.cpu_count(logical=True) or 1))
            cur = p.cpu_affinity() if hasattr(p, "cpu_affinity") else cpus
            prompt = (
                f"PID {pid}\n"
                f"CPU khả dụng: {cpus}\n"
                f"Affinity hiện tại: {cur}\n\n"
                "Nhập danh sách CPU mới (vd: 0,1,2) hoặc '*' để all:"
            )
            s = simpledialog.askstring("Set CPU affinity", prompt, initialvalue=",".join(map(str, cur)))
            if s is None:
                return
            s = s.strip()
            if s == "*":
                p.cpu_affinity(cpus)
            else:
                new = [int(x.strip()) for x in s.split(",") if x.strip() != ""]
                p.cpu_affinity(new)
            self.refresh_processes(force=True)
            self.refresh_details(force=True)
        except psutil.AccessDenied:
            messagebox.showerror("Permission denied", "Set affinity có thể cần quyền tùy process.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # -------------------------
    # Properties dialog
    # -------------------------

    def _show_proc_properties(self, pid: int):
        try:
            p = psutil.Process(pid)
            # gather info (best-effort)
            info = {}
            info["PID"] = str(pid)
            info["Name"] = p.name()
            try: info["Executable"] = p.exe()
            except Exception: info["Executable"] = ""
            try: info["CWD"] = p.cwd()
            except Exception: info["CWD"] = ""
            try: info["User"] = p.username()
            except Exception: info["User"] = ""
            try: info["Status"] = PROC_STATUS_LABEL.get(p.status(), p.status())
            except Exception: info["Status"] = ""
            try: info["Started"] = dt_from_ts(p.create_time())
            except Exception: info["Started"] = ""
            try: info["Nice"] = str(p.nice())
            except Exception: info["Nice"] = ""
            try: info["CPU %"] = f"{p.cpu_percent(interval=None):.1f}"
            except Exception: info["CPU %"] = ""
            try: info["Memory (RSS)"] = fmt_bytes(p.memory_info().rss)
            except Exception: info["Memory (RSS)"] = ""
            try: info["Threads"] = str(p.num_threads())
            except Exception: info["Threads"] = ""
            if hasattr(p, "num_fds"):
                try: info["FDs"] = str(p.num_fds())
                except Exception: info["FDs"] = ""
            try:
                cmd = p.cmdline()
                info["Command line"] = " ".join(cmd) if cmd else ""
            except Exception:
                info["Command line"] = ""

            try:
                files = p.open_files()
                info["Open files (count)"] = str(len(files))
            except Exception:
                info["Open files (count)"] = ""
            try:
                conns = p.connections(kind="inet") if hasattr(p, "connections") else []
                info["Connections (count)"] = str(len(conns))
            except Exception:
                info["Connections (count)"] = ""

        except psutil.NoSuchProcess:
            messagebox.showwarning("Not found", "Process không còn tồn tại.")
            return
        except psutil.AccessDenied:
            messagebox.showerror("Access denied", "Không đủ quyền để xem properties process này.")
            return
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        win = tk.Toplevel(self)
        win.title(f"Properties - PID {pid}")
        win.geometry("760x520")
        win.transient(self)

        frm = ttk.Frame(win)
        frm.pack(fill="both", expand=True, padx=12, pady=12)

        tree = ttk.Treeview(frm, columns=("k", "v"), show="headings")
        tree.heading("k", text="Field")
        tree.heading("v", text="Value")
        tree.column("k", width=180, anchor="w")
        tree.column("v", width=540, anchor="w")
        tree.pack(fill="both", expand=True)

        for k, v in info.items():
            tree.insert("", "end", values=(k, v))

        btns = ttk.Frame(win)
        btns.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Button(btns, text="Copy selected", command=lambda: self._copy_tree_selection(tree)).pack(side="right")
        ttk.Button(btns, text="Close", command=win.destroy).pack(side="right", padx=8)


    def _copy_tree_selection(self, tree: ttk.Treeview):
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0]).get("values", [])
        if not vals:
            return
        text = f"{vals[0]}: {vals[1]}"
        self.clipboard_clear()
        self.clipboard_append(text)

    # -------------------------
    # Performance refresh + draw
    # -------------------------

