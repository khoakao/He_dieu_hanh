# -*- coding: utf-8 -*-
"""
Linux Task Manager (Single File Version)
Yêu cầu: pip install psutil
"""
from __future__ import annotations

import os
import sys
import time
import json
import signal
import shutil
import subprocess
import datetime
from pathlib import Path
from collections import deque, defaultdict
from dataclasses import dataclass

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import psutil

# ============================================================
# 1. CONFIGURATION & CONSTANTS
# ============================================================

APP_NAME = "Task Manager (Linux)"
CFG_PATH = Path.home() / ".config" / "py_task_manager" / "config.json"
HISTORY_LEN = 60
USER_AUTOSTART_DIR = Path.home() / ".config" / "autostart"
SYS_AUTOSTART_DIRS = [Path("/etc/xdg/autostart")]

DEFAULT_CFG = {
    "refresh_ms": 2000,
    "always_on_top": False,
    "show_system_processes": True,
    "columns": {  # Cột cho tab Processes
        "pid": True, "name": True, "user": True,
        "cpu": True, "mem": True, "status": True,
        "nice": True, "threads": False, "fds": False,
        "start": False, "cmd": True,
    },
    "details_columns": {  # Cột cho tab Details
        "pid": True, "name": True, "user": True, "status": True,
        "cpu": True, "mem": True, "nice": True, "threads": True,
        "fds": True, "start": True, "cmd": True,
    },
    "geometry": "1180x720",
}

PROC_STATUS_LABEL = {
    "running": "Running",
    "sleeping": "Sleeping",
    "disk-sleep": "Disk Sleep",
    "stopped": "Stopped",
    "tracing-stop": "Tracing",
    "zombie": "Zombie",
    "dead": "Dead",
    "wake-kill": "Wake Kill",
    "waking": "Waking",
    "parked": "Parked",
    "idle": "Idle",
    "locked": "Locked",
    "waiting": "Waiting",
    "suspended": "Suspended",
}

# ============================================================
# 2. UTILS & MODELS
# ============================================================

@dataclass
class ProcRow:
    pid: int
    name: str
    user: str
    cpu: float
    mem_rss: int
    status: str
    nice: int
    threads: int
    fds: int
    start_time: float
    cmd: str

def ensure_cfg_dir() -> None:
    CFG_PATH.parent.mkdir(parents=True, exist_ok=True)

def load_cfg() -> dict:
    ensure_cfg_dir()
    if CFG_PATH.exists():
        try:
            data = json.loads(CFG_PATH.read_text(encoding="utf-8"))
            cfg = dict(DEFAULT_CFG)
            cfg.update({k: v for k, v in data.items() if k in cfg})
            # Deep merge dicts
            for k in ("columns", "details_columns"):
                if k in data and isinstance(data[k], dict):
                    merged = dict(DEFAULT_CFG[k])
                    merged.update({ck: bool(cv) for ck, cv in data[k].items() if ck in merged})
                    cfg[k] = merged
            return cfg
        except Exception:
            return dict(DEFAULT_CFG)
    return dict(DEFAULT_CFG)

def save_cfg(cfg: dict) -> None:
    ensure_cfg_dir()
    try:
        CFG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

def fmt_bytes(n):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(n) < 1024.0:
            return f"{n:3.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"

def safe_call(cmd_list, timeout=None):
    try:
        subprocess.Popen(cmd_list, start_new_session=True)
    except Exception as e:
        print(f"Error calling {cmd_list}: {e}")

def is_system_process(user):
    if user in ('root', 'daemon', 'bin', 'sys', 'sync', 'games', 'man', 
                'lp', 'mail', 'news', 'uucp', 'proxy', 'www-data', 'backup', 
                'list', 'irc', 'gnats', 'nobody', 'systemd-network', 'messagebus', 'syslog'):
        return True
    return False

def dt_from_ts(ts):
    try:
        return datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
    except:
        return ""

# ============================================================
# 3. MIXINS (LOGIC MODULES)
# ============================================================

class CoreMixin:
    """Quản lý giao diện chính, menu và vòng lặp refresh"""
    def _build_ui(self):
        style = ttk.Style(self)
        try: style.theme_use("clam")
        except: pass

        self._build_menubar()

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

        self.status_var = tk.StringVar(value="")
        bar = ttk.Frame(self)
        bar.pack(fill="x", side="bottom")
        ttk.Label(bar, textvariable=self.status_var, anchor="w").pack(fill="x", padx=10, pady=3)

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
        m_opt.add_checkbutton(label="Always on top", variable=self.var_always_on_top, command=self._toggle_always_on_top)
        m_opt.add_checkbutton(label="Show system processes", variable=self.var_show_system, command=self._toggle_show_system)
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

    def _choose_columns_dialog(self, title, cfg_key, all_cols, apply_cb):
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("360x420")
        win.transient(self)
        
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
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
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

    def _tick(self):
        self.refresh_all(force=False)
        self.after(self.cfg.get("refresh_ms", 2000), self._tick)

    def refresh_all(self, force=False):
        self.refresh_performance()
        self.refresh_statusbar()
        if not self.auto_refresh.get() and not force:
            return
        
        current = self.nb.index("current")
        if current == 0: self.refresh_processes(force=force)
        elif current == 2: self.refresh_users(force=force)
        elif current == 3: self.refresh_details(force=force)
        elif current == 4: self.refresh_services(force=force)
        elif current == 5: self.refresh_startup(force=force)

    def refresh_statusbar(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            vm = psutil.virtual_memory()
            procs = len(psutil.pids())
            self.status_var.set(f"Processes: {procs}    CPU: {cpu:.1f}%    Memory: {vm.percent:.1f}%")
        except: self.status_var.set("")

    def _set_refresh_ms(self, ms):
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
        messagebox.showinfo("About", f"{APP_NAME}\n\nTkinter + psutil\nAll-in-one script.")

    def _on_close(self):
        self.cfg["geometry"] = self.geometry()
        save_cfg(self.cfg)
        self.destroy()

class ProcessesTabMixin:
    """Tab Processes: Liệt kê tiến trình cơ bản"""
    def _build_processes_tab(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="x", padx=10, pady=8)

        ttk.Label(top, text="Search:").pack(side="left")
        ent = ttk.Entry(top, textvariable=self.filter_text, width=35)
        ent.pack(side="left", padx=5)
        ent.bind("<Return>", lambda e: self.refresh_processes(force=True))
        ttk.Checkbutton(top, text="Auto refresh", variable=self.auto_refresh).pack(side="left", padx=10)
        ttk.Button(top, text="Refresh Now", command=lambda: self.refresh_all(force=True)).pack(side="left")

        btns = ttk.Frame(top); btns.pack(side="right")
        ttk.Button(btns, text="End task", command=self.end_task_sigterm).pack(side="right", padx=4)
        ttk.Button(btns, text="Kill", command=self.kill_process).pack(side="right", padx=4)
        ttk.Button(btns, text="Properties", command=self.proc_properties).pack(side="right", padx=4)
        ttk.Button(btns, text="Set priority", command=self.set_priority).pack(side="right", padx=4)

        cols = ("pid", "name", "user", "cpu", "mem", "status", "nice", "threads", "fds", "start", "cmd")
        self.proc_tree = ttk.Treeview(parent, columns=cols, show="headings", height=20)
        self.proc_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        headings = {"pid": "PID", "name": "Name", "user": "User", "cpu": "CPU %", "mem": "Memory", "status": "Status", "nice": "Nice", "threads": "Threads", "fds": "FDs", "start": "Start time", "cmd": "Command"}
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

    def _popup_proc_menu(self, event):
        iid = self.proc_tree.identify_row(event.y)
        if iid:
            self.proc_tree.selection_set(iid)
            self.proc_menu.tk_popup(event.x_root, event.y_root)

    def _sort_processes(self, col):
        if self.sort_col == col: self.sort_desc = not self.sort_desc
        else: self.sort_col = col; self.sort_desc = True
        self.refresh_processes(force=True)

    def _apply_process_columns_visibility(self):
        for c in self.proc_tree["columns"]:
            visible = bool(self.cfg["columns"].get(c, True))
            self.proc_tree.column(c, width=self.proc_tree.column(c, "width"), stretch=True) if visible else self.proc_tree.column(c, width=0, stretch=False)

    def _choose_columns_processes(self):
        self._choose_columns_dialog("Select columns (Processes)", "columns", list(self.proc_tree["columns"]), self._apply_process_columns_visibility)

    def _collect_process_rows(self):
        rows = []
        search = self.filter_text.get().strip().lower()
        show_system = bool(self.cfg.get("show_system_processes", True))

        for p in psutil.process_iter():
            try:
                pid = p.pid
                name = p.name()
                user = p.username() if hasattr(p, "username") else ""
                if (not show_system) and is_system_process(user): continue
                
                cmdline = ""
                try: cmdline = " ".join(p.cmdline()) if p.cmdline() else ""
                except: pass
                
                if search and search not in f"{pid} {name} {user} {cmdline}".lower(): continue

                cpu = 0.0
                try: cpu = float(p.cpu_percent(interval=None) or 0.0)
                except: pass
                
                mem_rss = 0
                try: mem_rss = int(p.memory_info().rss)
                except: pass
                
                status = ""
                try: status = PROC_STATUS_LABEL.get(p.status(), p.status())
                except: pass
                
                nice = 0
                try: nice = int(p.nice())
                except: pass
                
                threads = 0
                try: threads = int(p.num_threads())
                except: pass
                
                fds = 0
                if hasattr(p, "num_fds"):
                    try: fds = int(p.num_fds())
                    except: pass
                
                start_time = 0.0
                try: start_time = float(p.create_time())
                except: pass

                rows.append(ProcRow(pid, name, user, cpu, mem_rss, status, nice, threads, fds, start_time, cmdline))
            except: continue
        return rows

    def refresh_processes(self, force=False):
        rows = self._collect_process_rows()
        rows = self._sort_rows(rows, self.sort_col, self.sort_desc)
        existing = set(self.proc_tree.get_children(""))
        new_ids = set()
        for r in rows:
            iid = str(r.pid)
            new_ids.add(iid)
            vals = (r.pid, r.name, r.user, f"{r.cpu:.1f}", fmt_bytes(r.mem_rss), r.status, str(r.nice), str(r.threads), str(r.fds) if r.fds else "", dt_from_ts(r.start_time) if r.start_time else "", r.cmd)
            if iid in existing: self.proc_tree.item(iid, values=vals)
            else: self.proc_tree.insert("", "end", iid=iid, values=vals)
        for iid in existing - new_ids: self.proc_tree.delete(iid)

    def _sort_rows(self, rows, col, desc):
        reverse = bool(desc)
        colmap = {"pid":"pid", "name":"name", "user":"user", "cpu":"cpu", "mem":"mem_rss", "status":"status", "nice":"nice", "threads":"threads", "fds":"fds", "start":"start_time", "cmd":"cmd"}
        attr = colmap.get(col, col)
        try: return sorted(rows, key=lambda x: getattr(x, attr, ""), reverse=reverse)
        except: return rows

class DetailsTabMixin:
    """Tab Details: Chi tiết hơn, cấu hình cột riêng"""
    def _build_details_tab(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="x", padx=10, pady=8)
        ttk.Label(top, text="Search:").pack(side="left")
        ent = ttk.Entry(top, textvariable=self.filter_text, width=35)
        ent.pack(side="left", padx=5)
        ent.bind("<Return>", lambda e: self.refresh_details(force=True))
        ttk.Button(top, text="Refresh Now", command=lambda: self.refresh_all(force=True)).pack(side="left", padx=8)

        btns = ttk.Frame(top); btns.pack(side="right")
        ttk.Button(btns, text="End task", command=self.end_task_sigterm_details).pack(side="right", padx=4)
        ttk.Button(btns, text="Kill", command=self.kill_process_details).pack(side="right", padx=4)
        ttk.Button(btns, text="Properties", command=self.proc_properties_details).pack(side="right", padx=4)

        cols = ("pid", "name", "user", "status", "cpu", "mem", "nice", "threads", "fds", "start", "cmd")
        self.details_tree = ttk.Treeview(parent, columns=cols, show="headings", height=20)
        self.details_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        headings = {"pid": "PID", "name": "Image Name", "user": "User Name", "status": "Status", "cpu": "CPU %", "mem": "Memory (RSS)", "nice": "Nice", "threads": "Threads", "fds": "FDs", "start": "Start time", "cmd": "Command line"}
        for c in cols:
            self.details_tree.heading(c, text=headings[c], command=lambda cc=c: self._sort_details(cc))
            w = 90
            if c in ("pid", "nice", "threads", "fds"): w = 70
            elif c == "cmd": w = 560
            self.details_tree.column(c, width=w, anchor="w")

        self._apply_details_columns_visibility()
        ysb = ttk.Scrollbar(parent, orient="vertical", command=self.details_tree.yview)
        self.details_tree.configure(yscrollcommand=ysb.set)
        ysb.place(in_=self.details_tree, relx=1.0, rely=0, relheight=1.0, anchor="ne")

        self.details_menu = tk.Menu(self, tearoff=0)
        self.details_menu.add_command(label="End task", command=self.end_task_sigterm_details)
        self.details_menu.add_command(label="Kill", command=self.kill_process_details)
        self.details_menu.add_separator()
        self.details_menu.add_command(label="Set priority", command=self.set_priority_details)
        self.details_menu.add_command(label="Properties", command=self.proc_properties_details)
        self.details_tree.bind("<Button-3>", self._popup_details_menu)
        self.details_tree.bind("<Double-1>", lambda e: self.proc_properties_details())

    def _popup_details_menu(self, event):
        iid = self.details_tree.identify_row(event.y)
        if iid:
            self.details_tree.selection_set(iid)
            self.details_menu.tk_popup(event.x_root, event.y_root)

    def _sort_details(self, col):
        if self.details_sort_col == col: self.details_sort_desc = not self.details_sort_desc
        else: self.details_sort_col = col; self.details_sort_desc = True
        self.refresh_details(force=True)

    def _apply_details_columns_visibility(self):
        for c in self.details_tree["columns"]:
            visible = bool(self.cfg["details_columns"].get(c, True))
            self.details_tree.column(c, width=self.details_tree.column(c, "width"), stretch=True) if visible else self.details_tree.column(c, width=0, stretch=False)

    def _choose_columns_details(self):
        self._choose_columns_dialog("Select columns (Details)", "details_columns", list(self.details_tree["columns"]), self._apply_details_columns_visibility)

    def refresh_details(self, force=False):
        rows = self._collect_process_rows()
        rows = self._sort_rows(rows, self.details_sort_col, self.details_sort_desc)
        existing = set(self.details_tree.get_children(""))
        new_ids = set()
        for r in rows:
            iid = str(r.pid)
            new_ids.add(iid)
            vals = (r.pid, r.name, r.user, r.status, f"{r.cpu:.1f}", fmt_bytes(r.mem_rss), str(r.nice), str(r.threads), str(r.fds) if r.fds else "", dt_from_ts(r.start_time) if r.start_time else "", r.cmd)
            if iid in existing: self.details_tree.item(iid, values=vals)
            else: self.details_tree.insert("", "end", iid=iid, values=vals)
        for iid in existing - new_ids: self.details_tree.delete(iid)

class ActionsMixin:
    """Xử lý hành động: Kill, Nice, Affinity..."""
    def _selected_pid(self, tree):
        sel = tree.selection()
        if not sel: return None
        try: return int(sel[0])
        except: return int(tree.item(sel[0]).get("values", [])[0])

    def end_task_sigterm(self):
        pid = self._selected_pid(self.proc_tree)
        if pid: self._send_signal(pid, signal.SIGTERM, confirm=True)
    def kill_process(self):
        pid = self._selected_pid(self.proc_tree)
        if pid: self._send_signal(pid, signal.SIGKILL, confirm=True)
    def set_priority(self):
        pid = self._selected_pid(self.proc_tree)
        if pid: self._set_nice(pid)
    def set_affinity(self):
        pid = self._selected_pid(self.proc_tree)
        if pid: self._set_cpu_affinity(pid)
    def proc_properties(self):
        pid = self._selected_pid(self.proc_tree)
        if pid: self._show_proc_properties(pid)
    def open_exe_folder(self):
        pid = self._selected_pid(self.proc_tree)
        if pid:
            try:
                p = psutil.Process(pid)
                exe = p.exe()
                if exe: safe_call(["xdg-open", str(Path(exe).parent)])
            except Exception as e: messagebox.showerror("Error", str(e))

    # Details tab actions
    def end_task_sigterm_details(self):
        pid = self._selected_pid(self.details_tree)
        if pid: self._send_signal(pid, signal.SIGTERM, confirm=True)
    def kill_process_details(self):
        pid = self._selected_pid(self.details_tree)
        if pid: self._send_signal(pid, signal.SIGKILL, confirm=True)
    def set_priority_details(self):
        pid = self._selected_pid(self.details_tree)
        if pid: self._set_nice(pid)
    def proc_properties_details(self):
        pid = self._selected_pid(self.details_tree)
        if pid: self._show_proc_properties(pid)

    def _send_signal(self, pid, sig, confirm=False):
        try:
            p = psutil.Process(pid)
            name = p.name()
        except: name = str(pid)
        if confirm and not messagebox.askyesno("Confirm", f"Send signal {sig} to PID {pid} ({name})?"): return
        try:
            os.kill(pid, sig)
        except Exception as e: messagebox.showerror("Error", str(e))
        self.refresh_all(force=True)

    def _set_nice(self, pid):
        try:
            p = psutil.Process(pid)
            cur = int(p.nice())
            new = simpledialog.askinteger("Set Priority", f"PID {pid} current nice={cur}\nRange: -20 (High) .. 19 (Low)", initialvalue=cur, minvalue=-20, maxvalue=19)
            if new is not None:
                p.nice(new)
                self.refresh_all(force=True)
        except Exception as e: messagebox.showerror("Error", str(e))

    def _set_cpu_affinity(self, pid):
        try:
            p = psutil.Process(pid)
            cpus = list(range(psutil.cpu_count(logical=True) or 1))
            cur = p.cpu_affinity() if hasattr(p, "cpu_affinity") else cpus
            s = simpledialog.askstring("Affinity", f"PID {pid}\nAvailable: {cpus}\nCurrent: {cur}\nEnter list (e.g. 0,1) or '*' for all:", initialvalue=",".join(map(str, cur)))
            if s:
                if s.strip() == "*": p.cpu_affinity(cpus)
                else: p.cpu_affinity([int(x) for x in s.split(",") if x.strip()])
                self.refresh_all(force=True)
        except Exception as e: messagebox.showerror("Error", str(e))

    def _show_proc_properties(self, pid):
        try:
            p = psutil.Process(pid)
            info = {"PID": str(pid), "Name": p.name(), "User": p.username(), "Status": p.status()}
            try: info["Exe"] = p.exe()
            except: pass
            try: info["CWD"] = p.cwd()
            except: pass
            try: info["Cmd"] = " ".join(p.cmdline())
            except: pass
            try: info["Mem"] = fmt_bytes(p.memory_info().rss)
            except: pass
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        win = tk.Toplevel(self)
        win.title(f"Properties - PID {pid}")
        win.geometry("600x400")
        tree = ttk.Treeview(win, columns=("k", "v"), show="headings")
        tree.heading("k", text="Field"); tree.column("k", width=150)
        tree.heading("v", text="Value"); tree.column("v", width=400)
        tree.pack(fill="both", expand=True)
        for k, v in info.items(): tree.insert("", "end", values=(k, v))

class OtherTabsMixin:
    """Các tab: Performance, Users, Services, Startup"""
    def _build_performance_tab(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="x", padx=10, pady=8)
        self.perf_summary = tk.StringVar(value="")
        ttk.Label(top, textvariable=self.perf_summary, font=("Consolas", 10)).pack(fill="x")
        
        grid = ttk.Frame(parent)
        grid.pack(fill="both", expand=True, padx=10, pady=10)
        grid.columnconfigure(0, weight=1); grid.columnconfigure(1, weight=1)
        grid.rowconfigure(0, weight=1); grid.rowconfigure(1, weight=1)
        
        self.canvas_cpu = tk.Canvas(grid, height=200, bg="#f0f0f0"); self.canvas_cpu.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.canvas_mem = tk.Canvas(grid, height=200, bg="#f0f0f0"); self.canvas_mem.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.canvas_net = tk.Canvas(grid, height=200, bg="#f0f0f0"); self.canvas_net.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.canvas_swap = tk.Canvas(grid, height=200, bg="#f0f0f0"); self.canvas_swap.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        
        ttk.Label(grid, text="CPU %").grid(row=0, column=0, sticky="nw", padx=8, pady=8)
        ttk.Label(grid, text="Memory %").grid(row=0, column=1, sticky="nw", padx=8, pady=8)
        ttk.Label(grid, text="Network KB/s").grid(row=1, column=0, sticky="nw", padx=8, pady=8)
        ttk.Label(grid, text="Swap %").grid(row=1, column=1, sticky="nw", padx=8, pady=8)

    def refresh_performance(self):
        cpu = psutil.cpu_percent(interval=None)
        vm = psutil.virtual_memory()
        sm = psutil.swap_memory()
        
        self.cpu_hist.append(cpu)
        self.mem_hist.append(vm.percent)
        self.swap_hist.append(sm.percent)
        
        try:
            now = time.time()
            net = psutil.net_io_counters()
            if self._last_net is None:
                self._last_net = net; self._last_net_ts = now
                s_kb = r_kb = 0.0
            else:
                dt = max(1e-6, now - (self._last_net_ts or now))
                s_kb = (net.bytes_sent - self._last_net.bytes_sent)/1024.0/dt
                r_kb = (net.bytes_recv - self._last_net.bytes_recv)/1024.0/dt
                self._last_net = net; self._last_net_ts = now
            self.net_sent_hist.append(s_kb)
            self.net_recv_hist.append(r_kb)
        except:
            self.net_sent_hist.append(0); self.net_recv_hist.append(0)

        self.perf_summary.set(f"CPU: {cpu:.1f}%   Mem: {vm.percent:.1f}% ({fmt_bytes(vm.used)}/{fmt_bytes(vm.total)})   Swap: {sm.percent:.1f}%")
        
        self._draw_chart(self.canvas_cpu, self.cpu_hist, 0, 100, "#0078d7")
        self._draw_chart(self.canvas_mem, self.mem_hist, 0, 100, "#800080")
        self._draw_chart(self.canvas_swap, self.swap_hist, 0, 100, "#ff8c00")
        self._draw_chart(self.canvas_net, self.net_recv_hist, 0, None, "#009900", self.net_sent_hist, "#cc0000")

    def _draw_chart(self, cv, s1, ymin, ymax, c1, s2=None, c2="gray"):
        cv.delete("all")
        w, h = max(1, cv.winfo_width()), max(1, cv.winfo_height())
        if not s1: return
        
        if ymax is None: 
            m1 = max(s1)
            m2 = max(s2) if s2 else 0
            ymax = max(m1, m2, 1.0)
            
        def get_pt(i, val, count):
            x = i * w / max(1, count - 1)
            y = h - ((val - ymin) / max(1e-6, ymax - ymin)) * h
            return x, y

        pts1 = []
        for i, v in enumerate(s1):
            pts1.extend(get_pt(i, max(ymin, min(ymax, float(v))), len(s1)))
        if len(pts1) >= 4: cv.create_line(*pts1, width=2, fill=c1, smooth=True)

        if s2:
            pts2 = []
            for i, v in enumerate(s2):
                pts2.extend(get_pt(i, max(ymin, min(ymax, float(v))), len(s2)))
            if len(pts2) >= 4: cv.create_line(*pts2, width=2, fill=c2, smooth=True, dash=(4,2))

    def _build_users_tab(self, parent):
        top = ttk.Frame(parent); top.pack(fill="x", padx=10, pady=8)
        ttk.Button(top, text="Refresh", command=lambda: self.refresh_users(True)).pack(side="left")
        self.users_tree = ttk.Treeview(parent, columns=("u", "cnt", "cpu", "mem"), show="headings")
        self.users_tree.pack(fill="both", expand=True, padx=10, pady=10)
        for c, t in zip(("u", "cnt", "cpu", "mem"), ("User", "Procs", "CPU", "Mem")):
            self.users_tree.heading(c, text=t)

    def refresh_users(self, force=False):
        rows = self._collect_process_rows()
        agg = defaultdict(lambda: {"c":0, "cpu":0.0, "mem":0})
        for r in rows:
            u = r.user or "unknown"
            agg[u]["c"] += 1; agg[u]["cpu"] += r.cpu; agg[u]["mem"] += r.mem_rss
        self.users_tree.delete(*self.users_tree.get_children())
        for u, d in sorted(agg.items(), key=lambda x: x[1]["cpu"], reverse=True):
            self.users_tree.insert("", "end", values=(u, d["c"], f"{d['cpu']:.1f}", fmt_bytes(d["mem"])))

    def _build_services_tab(self, parent):
        top = ttk.Frame(parent); top.pack(fill="x", padx=10, pady=8)
        ttk.Button(top, text="Refresh", command=lambda: self.refresh_services(True)).pack(side="left")
        ttk.Button(top, text="Restart Service", command=lambda: self._service_action("restart")).pack(side="right")
        self.services_tree = ttk.Treeview(parent, columns=("u", "l", "a", "s", "d"), show="headings")
        self.services_tree.pack(fill="both", expand=True, padx=10, pady=10)
        for c, t, w in zip(("u", "l", "a", "s", "d"), ("Unit", "Load", "Active", "Sub", "Desc"), (200, 80, 80, 80, 400)):
            self.services_tree.heading(c, text=t); self.services_tree.column(c, width=w)
        self.services_tree.bind("<Double-1>", lambda e: self._service_action("restart"))

    def refresh_services(self, force=False):
        sys_cmd = shutil.which("systemctl")
        if not sys_cmd: return
        try:
            out = subprocess.check_output([sys_cmd, "list-units", "--type=service", "--all", "--no-legend", "--plain"], text=True)
            self.services_tree.delete(*self.services_tree.get_children())
            for line in out.splitlines():
                p = line.split(maxsplit=4)
                if len(p) >= 4:
                    self.services_tree.insert("", "end", iid=p[0], values=(p[0], p[1], p[2], p[3], p[4] if len(p)>4 else ""))
        except: pass

    def _service_action(self, act):
        sel = self.services_tree.selection()
        if sel and messagebox.askyesno("Confirm", f"{act} {sel[0]}?"):
            try: subprocess.run(["systemctl", act, sel[0]])
            except Exception as e: messagebox.showerror("Error", str(e))

    def _build_startup_tab(self, parent):
        top = ttk.Frame(parent); top.pack(fill="x", padx=10, pady=8)
        ttk.Button(top, text="Refresh", command=lambda: self.refresh_startup(True)).pack(side="left")
        ttk.Button(top, text="Open Folder", command=self.open_autostart_folder).pack(side="left", padx=5)
        ttk.Button(top, text="Toggle (User)", command=self.toggle_startup_user).pack(side="right")
        self.startup_tree = ttk.Treeview(parent, columns=("n", "e", "s", "c", "p"), show="headings")
        self.startup_tree.pack(fill="both", expand=True, padx=10, pady=10)
        for c, t in zip(("n", "e", "s", "c", "p"), ("Name", "Enabled", "Scope", "Command", "Path")):
            self.startup_tree.heading(c, text=t)

    def refresh_startup(self, force=False):
        ents = []
        def parse(p):
            try:
                txt = p.read_text(errors="ignore")
                d = {}
                for l in txt.splitlines():
                    if l.startswith("Name="): d["Name"]=l[5:]
                    if l.startswith("Exec="): d["Exec"]=l[5:]
                    if l.startswith("Hidden="): d["Hidden"]=l[7:].lower()=="true"
                return d
            except: return None
        
        if USER_AUTOSTART_DIR.exists():
            for p in USER_AUTOSTART_DIR.glob("*.desktop"):
                d = parse(p)
                if d: ents.append((d.get("Name", p.stem), "No" if d.get("Hidden") else "Yes", "User", d.get("Exec",""), str(p)))
        for sd in SYS_AUTOSTART_DIRS:
            if sd.exists():
                for p in sd.glob("*.desktop"):
                    d = parse(p)
                    if d: ents.append((d.get("Name", p.stem), "No" if d.get("Hidden") else "Yes", "System", d.get("Exec",""), str(p)))
        
        self.startup_tree.delete(*self.startup_tree.get_children())
        for e in ents: self.startup_tree.insert("", "end", values=e)

    def open_autostart_folder(self):
        USER_AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        safe_call(["xdg-open", str(USER_AUTOSTART_DIR)])
    
    def toggle_startup_user(self):
        sel = self.startup_tree.selection()
        if not sel: return
        val = self.startup_tree.item(sel[0])["values"]
        if val[2] != "User": return
        p = Path(val[4])
        if not p.exists(): return
        txt = p.read_text().splitlines()
        out = []
        found = False
        for l in txt:
            if l.startswith("Hidden="):
                v = l.split("=")[1].strip().lower() == "true"
                out.append(f"Hidden={'false' if v else 'true'}")
                found = True
            else: out.append(l)
        if not found: out.append("Hidden=true")
        p.write_text("\n".join(out)+"\n")
        self.refresh_startup(True)

# ============================================================
# 4. MAIN APPLICATION
# ============================================================

class TaskManagerApp(tk.Tk, CoreMixin, ProcessesTabMixin, DetailsTabMixin, ActionsMixin, OtherTabsMixin):
    def __init__(self):
        super().__init__()
        self.cfg = load_cfg()
        
        # Fallback if config corrupted
        if "details_columns" not in self.cfg:
             self.cfg["details_columns"] = DEFAULT_CFG["details_columns"]

        self.title(APP_NAME)
        self.geometry(self.cfg.get("geometry", DEFAULT_CFG["geometry"]))
        self.wm_attributes("-topmost", bool(self.cfg.get("always_on_top", False)))

        # State
        self.sort_col = "cpu"
        self.sort_desc = True
        self.details_sort_col = "cpu"
        self.details_sort_desc = True
        self.filter_text = tk.StringVar(value="")
        self.auto_refresh = tk.BooleanVar(value=True)
        self._last_refresh_ts = 0.0

        # Hist buffers
        self.cpu_hist = deque(maxlen=HISTORY_LEN)
        self.mem_hist = deque(maxlen=HISTORY_LEN)
        self.swap_hist = deque(maxlen=HISTORY_LEN)
        self.net_sent_hist = deque(maxlen=HISTORY_LEN)
        self.net_recv_hist = deque(maxlen=HISTORY_LEN)
        self._last_net = None; self._last_net_ts = None

        self._build_ui()
        
        # Bind tab change
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(250, self._tick)

    def _on_tab_changed(self, event):
        try:
            txt = self.nb.tab(self.nb.select(), "text")
            if "Details" in txt: self.refresh_details(True)
            elif "Processes" in txt: self.refresh_processes(True)
            elif "Services" in txt: self.refresh_services(True)
        except: pass

if __name__ == "__main__":
    app = TaskManagerApp()
    app.mainloop()