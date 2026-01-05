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
# PERSON 2 — PROCESSES TAB
#   - UI: treeview, filter/search, column chooser, context menu
#   - Logic: collect rows from psutil, refresh, sort/filter
# Deliverable: explain 1 process row source + filter + columns
# ============================================================



class ProcessesTabMixin:
    # ------------------------------------------------------------
    # [P2][UI] Build Processes tab (widgets + bindings)
    # ------------------------------------------------------------
    def _build_processes_tab(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="x", padx=10, pady=8)

        ttk.Label(top, text="Search:").pack(side="left")
        ent = ttk.Entry(top, textvariable=self.filter_text, width=35)
        ent.pack(side="left", padx=5)
        ent.bind("<Return>", lambda e: self.refresh_processes(force=True))

        ttk.Checkbutton(top, text="Auto refresh", variable=self.auto_refresh).pack(side="left", padx=10)
        ttk.Button(top, text="Refresh Now", command=lambda: self.refresh_all(force=True)).pack(side="left")

        btns = ttk.Frame(top)
        btns.pack(side="right")
        ttk.Button(btns, text="End task", command=self.end_task_sigterm).pack(side="right", padx=4)
        ttk.Button(btns, text="Kill (SIGKILL)", command=self.kill_process).pack(side="right", padx=4)
        ttk.Button(btns, text="Properties", command=self.proc_properties).pack(side="right", padx=4)
        ttk.Button(btns, text="Set priority", command=self.set_priority).pack(side="right", padx=4)

        cols = ("pid", "name", "user", "cpu", "mem", "status", "nice", "threads", "fds", "start", "cmd")
        self.proc_tree = ttk.Treeview(parent, columns=cols, show="headings", height=20)
        self.proc_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        headings = {
            "pid": "PID", "name": "Name", "user": "User", "cpu": "CPU %",
            "mem": "Memory", "status": "Status", "nice": "Nice",
            "threads": "Threads", "fds": "FDs", "start": "Start time", "cmd": "Command",
        }

        for c in cols:
            self.proc_tree.heading(c, text=headings[c], command=lambda cc=c: self._sort_processes(cc))
            w = 90
            if c in ("pid", "nice", "threads", "fds"): w = 70
            if c == "cpu": w = 80
            if c == "mem": w = 110
            if c in ("name", "user", "status"): w = 140
            if c == "start": w = 160
            if c == "cmd": w = 520
            self.proc_tree.column(c, width=w, anchor="w")

        self._apply_process_columns_visibility()

        ysb = ttk.Scrollbar(parent, orient="vertical", command=self.proc_tree.yview)
        self.proc_tree.configure(yscrollcommand=ysb.set)
        ysb.place(in_=self.proc_tree, relx=1.0, rely=0, relheight=1.0, anchor="ne")

        # right-click menu
        self.proc_menu = tk.Menu(self, tearoff=0)
        self.proc_menu.add_command(label="End task (SIGTERM)", command=self.end_task_sigterm)
        self.proc_menu.add_command(label="Kill (SIGKILL)", command=self.kill_process)
        self.proc_menu.add_separator()
        self.proc_menu.add_command(label="Set priority (nice)", command=self.set_priority)
        self.proc_menu.add_command(label="Set CPU affinity", command=self.set_affinity)
        self.proc_menu.add_separator()
        self.proc_menu.add_command(label="Properties", command=self.proc_properties)
        self.proc_menu.add_command(label="Open exe folder", command=self.open_exe_folder)

        self.proc_tree.bind("<Button-3>", self._popup_proc_menu)
        self.proc_tree.bind("<Double-1>", lambda e: self.proc_properties())
    # ------------------------------------------------------------
    # [P2][UI] Right-click context menu (Processes)
    # ------------------------------------------------------------


    def _popup_proc_menu(self, event):
        iid = self.proc_tree.identify_row(event.y)
        if iid:
            self.proc_tree.selection_set(iid)
            try:
                self.proc_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.proc_menu.grab_release()
    # ------------------------------------------------------------
    # [P2][UI->LOGIC] Click column header to sort
    # ------------------------------------------------------------


    def _sort_processes(self, col):
        if self.sort_col == col:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = col
            self.sort_desc = True
        self.refresh_processes(force=True)


    def _apply_process_columns_visibility(self):
        cols = list(self.proc_tree["columns"])
        for c in cols:
            visible = bool(self.cfg["columns"].get(c, True))
            if visible:
                self.proc_tree.column(c, width=self.proc_tree.column(c, "width"), stretch=True)
            else:
                self.proc_tree.column(c, width=0, stretch=False)


    def _choose_columns_processes(self):
        self._choose_columns_dialog(title="Select columns (Processes)", cfg_key="columns",
                                    all_cols=list(self.proc_tree["columns"]),
                                    apply_cb=self._apply_process_columns_visibility)

    # -------------------------
    # Tabs: Details
    # -------------------------
    # ------------------------------------------------------------
    # [P2][LOGIC] Collect process rows from psutil
    #   - This is the canonical source for Processes + Details tables
    # ------------------------------------------------------------

    def _collect_process_rows(self):
        rows = []
        search = self.filter_text.get().strip().lower()
        show_system = bool(self.cfg.get("show_system_processes", True))

        for p in psutil.process_iter():
            try:
                pid = p.pid
                name = p.name()
                user = p.username() if hasattr(p, "username") else ""
                if (not show_system) and is_system_process(user):
                    continue

                # filter (name/cmd/user/pid)
                cmdline = ""
                try:
                    cmdline = " ".join(p.cmdline()) if p.cmdline() else ""
                except Exception:
                    cmdline = ""
                if search:
                    hay = f"{pid} {name} {user} {cmdline}".lower()
                    if search not in hay:
                        continue

                cpu = 0.0
                try:
                    cpu = float(p.cpu_percent(interval=None) or 0.0)
                except Exception:
                    cpu = 0.0

                mem_rss = 0
                try:
                    mem_rss = int(p.memory_info().rss)
                except Exception:
                    mem_rss = 0

                status = ""
                try:
                    st = p.status()
                    status = PROC_STATUS_LABEL.get(st, st)
                except Exception:
                    status = ""

                nice = 0
                try:
                    nice = int(p.nice())
                except Exception:
                    nice = 0

                threads = 0
                try:
                    threads = int(p.num_threads())
                except Exception:
                    threads = 0

                fds = 0
                if hasattr(p, "num_fds"):
                    try:
                        fds = int(p.num_fds())
                    except Exception:
                        fds = 0

                start_time = 0.0
                try:
                    start_time = float(p.create_time())
                except Exception:
                    start_time = 0.0

                rows.append(ProcRow(
                    pid=pid, name=name, user=user or "",
                    cpu=cpu, mem_rss=mem_rss, status=status, nice=nice,
                    threads=threads, fds=fds, start_time=start_time, cmd=cmdline
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception:
                continue
        return rows

    # -------------------------
    # Refresh: Processes tree
    # -------------------------
    # ------------------------------------------------------------
    # [P2][LOGIC] Refresh table rows (apply filter + format + insert)
    # ------------------------------------------------------------

    def refresh_processes(self, force=False):
        rows = self._collect_process_rows()
        rows = self._sort_rows(rows, self.sort_col, self.sort_desc)

        existing = set(self.proc_tree.get_children(""))
        new_ids = set()

        for r in rows:
            iid = str(r.pid)
            new_ids.add(iid)
            values = (
                r.pid,
                r.name,
                r.user,
                f"{r.cpu:.1f}",
                fmt_bytes(r.mem_rss),
                r.status,
                str(r.nice),
                str(r.threads),
                str(r.fds) if r.fds else "",
                dt_from_ts(r.start_time) if r.start_time else "",
                r.cmd
            )
            if iid in existing:
                self.proc_tree.item(iid, values=values)
            else:
                self.proc_tree.insert("", "end", iid=iid, values=values)

        for iid in existing - new_ids:
            self.proc_tree.delete(iid)

    # -------------------------
    # Refresh: Details tree
    # -------------------------
    # ------------------------------------------------------------
    # [P2][LOGIC] Generic row sorter used by Processes/Details
    # ------------------------------------------------------------

    def _sort_rows(self, rows, col, desc: bool):
        reverse = bool(desc)
        colmap = {
            "pid": "pid", "name": "name", "user": "user", "cpu": "cpu", "mem": "mem_rss",
            "status": "status", "nice": "nice", "threads": "threads", "fds": "fds",
            "start": "start_time", "cmd": "cmd"
        }
        attr = colmap.get(col, col)
        def key_func(x):
            v = getattr(x, attr, "")
            return v
        try:
            return sorted(rows, key=key_func, reverse=reverse)
        except Exception:
            return rows

    # -------------------------
    # Actions (Processes)
    # -------------------------

