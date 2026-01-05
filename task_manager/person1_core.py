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
# PERSON 1 — CORE / APP SHELL
#   - UI shell: notebook, status bar, menu
#   - Refresh loop: tick -> refresh_all -> refresh_<tab>
#   - App settings hooks: refresh interval, always-on-top, show-system
# Deliverable: app start flow + list of persisted settings
# ============================================================



class CoreMixin:
    # ------------------------------------------------------------
    # [P1][UI] App shell layout (Notebook + Status bar)
    # ------------------------------------------------------------
    def _build_ui(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        self._build_menubar()

        # Notebook
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)

        self.tab_processes = ttk.Frame(self.nb)
        self.tab_performance = ttk.Frame(self.nb)
        self.tab_users = ttk.Frame(self.nb)
        self.tab_details = ttk.Frame(self.nb)
        self.tab_services = ttk.Frame(self.nb)
        self.tab_startup = ttk.Frame(self.nb)

        self.nb.add(self.tab_processes, text="Processes")
        self.nb.add(self.tab_performance, text="Performance")
        self.nb.add(self.tab_users, text="Users")
        self.nb.add(self.tab_details, text="Details")
        self.nb.add(self.tab_services, text="Services")
        self.nb.add(self.tab_startup, text="Startup")

        self._build_processes_tab(self.tab_processes)
        self._build_performance_tab(self.tab_performance)
        self._build_users_tab(self.tab_users)
        self._build_details_tab(self.tab_details)
        self._build_services_tab(self.tab_services)
        self._build_startup_tab(self.tab_startup)

        # Status bar
        self.status_var = tk.StringVar(value="")
        bar = ttk.Frame(self)
        bar.pack(fill="x", side="bottom")
        ttk.Label(bar, textvariable=self.status_var, anchor="w").pack(fill="x", padx=10, pady=3)
    # ------------------------------------------------------------
    # [P1][UI] Menu bar + Settings entry points
    # ------------------------------------------------------------


    def _build_menubar(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File
        m_file = tk.Menu(menubar, tearoff=0)
        m_file.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=m_file)

        # Options
        m_opt = tk.Menu(menubar, tearoff=0)
        self.var_always_on_top = tk.BooleanVar(value=bool(self.cfg.get("always_on_top", False)))
        self.var_show_system = tk.BooleanVar(value=bool(self.cfg.get("show_system_processes", True)))

        m_opt.add_checkbutton(
            label="Always on top",
            variable=self.var_always_on_top,
            command=self._toggle_always_on_top
        )
        m_opt.add_checkbutton(
            label="Show system processes",
            variable=self.var_show_system,
            command=self._toggle_show_system
        )
        menubar.add_cascade(label="Options", menu=m_opt)

        # View
        m_view = tk.Menu(menubar, tearoff=0)
        m_speed = tk.Menu(m_view, tearoff=0)
        m_speed.add_command(label="High (0.5s)", command=lambda: self._set_refresh_ms(500))
        m_speed.add_command(label="Normal (2s)", command=lambda: self._set_refresh_ms(2000))
        m_speed.add_command(label="Low (5s)", command=lambda: self._set_refresh_ms(5000))
        m_speed.add_command(label="Paused", command=lambda: self.auto_refresh.set(False))
        m_view.add_cascade(label="Update speed", menu=m_speed)
        m_view.add_separator()
        m_view.add_command(label="Select columns (Processes)...", command=self._choose_columns_processes)
        m_view.add_command(label="Select columns (Details)...", command=self._choose_columns_details)
        menubar.add_cascade(label="View", menu=m_view)

        # Help
        m_help = tk.Menu(menubar, tearoff=0)
        m_help.add_command(label="About", command=self._about)
        menubar.add_cascade(label="Help", menu=m_help)

    # -------------------------
    # Tabs: Processes
    # -------------------------

    def _choose_columns_dialog(self, title: str, cfg_key: str, all_cols: list, apply_cb):
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("360x420")
        win.transient(self)
        win.grab_set()

        vars_map = {}
        frm = ttk.Frame(win)
        frm.pack(fill="both", expand=True, padx=12, pady=12)

        ttk.Label(frm, text="Tick các cột muốn hiển thị:").pack(anchor="w", pady=(0, 8))

        canvas = tk.Canvas(frm)
        canvas.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(frm, orient="vertical", command=canvas.yview)
        sb.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=sb.set)

        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
    # ------------------------------------------------------------
    # [P1][CONFIG] Open config dialog / update runtime cfg
    # ------------------------------------------------------------

        def _on_config(e=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        inner.bind("<Configure>", _on_config)

        for c in all_cols:
            v = tk.BooleanVar(value=bool(self.cfg[cfg_key].get(c, True)))
            vars_map[c] = v
            ttk.Checkbutton(inner, text=c, variable=v).pack(anchor="w")

        btns = ttk.Frame(win)
        btns.pack(fill="x", padx=12, pady=12)

        def save_and_close():
            for c, v in vars_map.items():
                self.cfg[cfg_key][c] = bool(v.get())
            save_cfg(self.cfg)
            apply_cb()
            win.destroy()

        ttk.Button(btns, text="OK", command=save_and_close).pack(side="right", padx=6)
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="right")

    # -------------------------
    # Main loop tick
    # -------------------------
    # ------------------------------------------------------------
    # [P1][REFRESH LOOP] Tkinter after() tick scheduler
    # ------------------------------------------------------------

    def _tick(self):
        self.refresh_all(force=False)
        self.after(self.cfg.get("refresh_ms", 2000), self._tick)
    # ------------------------------------------------------------
    # [P1][REFRESH] Refresh current tab / all tabs (manual/auto)
    # ------------------------------------------------------------


    def refresh_all(self, force=False):
        # cập nhật tab đang xem trước để mượt hơn, nhưng vẫn có status + perf
        self.refresh_performance()
        self.refresh_statusbar()

        if not self.auto_refresh.get() and not force:
            return

        current = self.nb.index("current")
        # 0: Processes, 1: Perf, 2: Users, 3: Details, 4: Services, 5: Startup
        if current == 0:
            self.refresh_processes(force=force)
        elif current == 2:
            self.refresh_users(force=force)
        elif current == 3:
            self.refresh_details(force=force)
        elif current == 4:
            self.refresh_services(force=force)
        elif current == 5:
            self.refresh_startup(force=force)
        else:
            # perf tab already refreshed
            pass

    # -------------------------
    # Collect processes
    # -------------------------
    # ------------------------------------------------------------
    # [P1][UI] Status bar update
    # ------------------------------------------------------------

    def refresh_statusbar(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            vm = psutil.virtual_memory()
            procs = len(psutil.pids())
            self.status_var.set(f"Processes: {procs}    CPU: {cpu:.1f}%    Memory: {vm.percent:.1f}%")
        except Exception:
            self.status_var.set("")

    # -------------------------
    # Menu callbacks
    # -------------------------

    def _set_refresh_ms(self, ms: int):
        self.cfg["refresh_ms"] = int(ms)
        save_cfg(self.cfg)


    def _toggle_always_on_top(self):
        self.cfg["always_on_top"] = bool(self.var_always_on_top.get())
        self.wm_attributes("-topmost", bool(self.cfg["always_on_top"]))
        save_cfg(self.cfg)


    def _toggle_show_system(self):
        self.cfg["show_system_processes"] = bool(self.var_show_system.get())
        save_cfg(self.cfg)
        self.refresh_processes(force=True)
        self.refresh_details(force=True)
        self.refresh_users(force=True)


    def _about(self):
        messagebox.showinfo(
            "About",
            f"{APP_NAME}\n\n"
            "Tkinter + psutil\n"
            "Tabs: Processes, Performance, Users, Details, Services, Startup\n"
            "Mục tiêu: giống Task Manager Windows nhất có thể trên Linux."
        )


    def _on_close(self):
        try:
            self.cfg["geometry"] = self.geometry()
        except Exception:
            pass
        save_cfg(self.cfg)
        self.destroy()


if __name__ == "__main__":
    app = TaskManagerApp()
    app.mainloop()

