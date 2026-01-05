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
# PERSON 3 — DETAILS TAB
#   - UI: treeview, column chooser, context menu
#   - Logic: refresh + sort (shares collector/sorter with Processes)
# Deliverable: compare Details vs Processes (headers/default columns/shared collector)
# ============================================================



class DetailsTabMixin:
    # ------------------------------------------------------------
    # [P3][UI] Build Details tab (widgets + bindings)
    # ------------------------------------------------------------
    def _build_details_tab(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="x", padx=10, pady=8)

        ttk.Label(top, text="Search:").pack(side="left")
        ent = ttk.Entry(top, textvariable=self.filter_text, width=35)
        ent.pack(side="left", padx=5)
        ent.bind("<Return>", lambda e: self.refresh_details(force=True))

        ttk.Button(top, text="Refresh Now", command=lambda: self.refresh_all(force=True)).pack(side="left", padx=8)

        btns = ttk.Frame(top)
        btns.pack(side="right")
        ttk.Button(btns, text="End task", command=self.end_task_sigterm_details).pack(side="right", padx=4)
        ttk.Button(btns, text="Kill", command=self.kill_process_details).pack(side="right", padx=4)
        ttk.Button(btns, text="Properties", command=self.proc_properties_details).pack(side="right", padx=4)

        cols = ("pid", "name", "user", "status", "cpu", "mem", "nice", "threads", "fds", "start", "cmd")
        self.details_tree = ttk.Treeview(parent, columns=cols, show="headings", height=20)
        self.details_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        headings = {
            "pid": "PID", "name": "Image Name", "user": "User Name", "status": "Status",
            "cpu": "CPU %", "mem": "Memory (RSS)", "nice": "Nice",
            "threads": "Threads", "fds": "FDs", "start": "Start time", "cmd": "Command line",
        }
        for c in cols:
            self.details_tree.heading(c, text=headings[c], command=lambda cc=c: self._sort_details(cc))
            w = 90
            if c in ("pid", "nice", "threads", "fds"): w = 70
            if c == "cpu": w = 80
            if c == "mem": w = 120
            if c in ("name", "user", "status"): w = 160
            if c == "start": w = 160
            if c == "cmd": w = 560
            self.details_tree.column(c, width=w, anchor="w")

        self._apply_details_columns_visibility()

        ysb = ttk.Scrollbar(parent, orient="vertical", command=self.details_tree.yview)
        self.details_tree.configure(yscrollcommand=ysb.set)
        ysb.place(in_=self.details_tree, relx=1.0, rely=0, relheight=1.0, anchor="ne")

        self.details_menu = tk.Menu(self, tearoff=0)
        self.details_menu.add_command(label="End task (SIGTERM)", command=self.end_task_sigterm_details)
        self.details_menu.add_command(label="Kill (SIGKILL)", command=self.kill_process_details)
        self.details_menu.add_separator()
        self.details_menu.add_command(label="Set priority (nice)", command=self.set_priority_details)
        self.details_menu.add_command(label="Properties", command=self.proc_properties_details)

        self.details_tree.bind("<Button-3>", self._popup_details_menu)
        self.details_tree.bind("<Double-1>", lambda e: self.proc_properties_details())
    # ------------------------------------------------------------
    # [P3][UI] Right-click context menu (Details)
    # ------------------------------------------------------------


    def _popup_details_menu(self, event):
        iid = self.details_tree.identify_row(event.y)
        if iid:
            self.details_tree.selection_set(iid)
            try:
                self.details_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.details_menu.grab_release()
    # ------------------------------------------------------------
    # [P3][UI->LOGIC] Click column header to sort (Details)
    # ------------------------------------------------------------


    def _sort_details(self, col):
        if self.details_sort_col == col:
            self.details_sort_desc = not self.details_sort_desc
        else:
            self.details_sort_col = col
            self.details_sort_desc = True
        self.refresh_details(force=True)


    def _apply_details_columns_visibility(self):
        cols = list(self.details_tree["columns"])
        for c in cols:
            visible = bool(self.cfg["details_columns"].get(c, True))
            if visible:
                self.details_tree.column(c, width=self.details_tree.column(c, "width"), stretch=True)
            else:
                self.details_tree.column(c, width=0, stretch=False)


    def _choose_columns_details(self):
        self._choose_columns_dialog(title="Select columns (Details)", cfg_key="details_columns",
                                    all_cols=list(self.details_tree["columns"]),
                                    apply_cb=self._apply_details_columns_visibility)

    # -------------------------
    # Tabs: Performance (Real-time Charts)
    # -------------------------
    # ------------------------------------------------------------
    # [P3][LOGIC] Refresh Details rows (uses shared collector)
    # ------------------------------------------------------------

    def refresh_details(self, force=False):
        rows = self._collect_process_rows()
        rows = self._sort_rows(rows, self.details_sort_col, self.details_sort_desc)

        existing = set(self.details_tree.get_children(""))
        new_ids = set()
        for r in rows:
            iid = str(r.pid)
            new_ids.add(iid)
            values = (
                r.pid,
                r.name,
                r.user,
                r.status,
                f"{r.cpu:.1f}",
                fmt_bytes(r.mem_rss),
                str(r.nice),
                str(r.threads),
                str(r.fds) if r.fds else "",
                dt_from_ts(r.start_time) if r.start_time else "",
                r.cmd
            )
            if iid in existing:
                self.details_tree.item(iid, values=values)
            else:
                self.details_tree.insert("", "end", iid=iid, values=values)

        for iid in existing - new_ids:
            self.details_tree.delete(iid)


