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
# PERSON 5 — PERFORMANCE + USERS + SERVICES + STARTUP
#   - Performance: charts + refresh
#   - Users: list sessions/users
#   - Services: systemctl list + actions
#   - Startup: .desktop parsing + enable/disable (user scope)
# Deliverable: data sources (psutil/systemctl/.desktop) + limitations
# ============================================================



class OtherTabsMixin:
    # ------------------------------------------------------------
    # [P5][UI] Build Performance tab (charts area)
    # ------------------------------------------------------------
    def _build_performance_tab(self, parent):
        # summary top
        top = ttk.Frame(parent)
        top.pack(fill="x", padx=10, pady=8)

        self.perf_summary = tk.StringVar(value="")
        ttk.Label(top, textvariable=self.perf_summary, anchor="w", font=("Consolas", 10)).pack(fill="x")

        # charts area
        grid = ttk.Frame(parent)
        grid.pack(fill="both", expand=True, padx=10, pady=10)

        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.rowconfigure(0, weight=1)
        grid.rowconfigure(1, weight=1)

        self.canvas_cpu = tk.Canvas(grid, height=220, bg="#f0f0f0", highlightthickness=1, highlightbackground="#cccccc")
        self.canvas_mem = tk.Canvas(grid, height=220, bg="#f0f0f0", highlightthickness=1, highlightbackground="#cccccc")
        self.canvas_net = tk.Canvas(grid, height=220, bg="#f0f0f0", highlightthickness=1, highlightbackground="#cccccc")
        self.canvas_swap = tk.Canvas(grid, height=220, bg="#f0f0f0", highlightthickness=1, highlightbackground="#cccccc")

        ttk.Label(grid, text="CPU Usage", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.canvas_cpu.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(20, 8))

        ttk.Label(grid, text="Memory Usage", font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="w")
        self.canvas_mem.grid(row=0, column=1, sticky="nsew", pady=(20, 8))

        ttk.Label(grid, text="Network (KB/s)", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w")
        self.canvas_net.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(20, 0))

        ttk.Label(grid, text="Swap Usage", font=("Arial", 10, "bold")).grid(row=1, column=1, sticky="w")
        self.canvas_swap.grid(row=1, column=1, sticky="nsew", pady=(20, 0))

    # -------------------------
    # Tabs: Users
    # -------------------------
    # ------------------------------------------------------------
    # [P5][UI] Build Users tab
    # ------------------------------------------------------------

    def _build_users_tab(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="x", padx=10, pady=8)

        ttk.Button(top, text="Refresh Now", command=lambda: self.refresh_all(force=True)).pack(side="left")

        cols = ("user", "processes", "cpu", "mem")
        self.users_tree = ttk.Treeview(parent, columns=cols, show="headings", height=20)
        self.users_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        headings = {"user": "User", "processes": "Processes", "cpu": "CPU %", "mem": "Memory"}
        widths = {"user": 220, "processes": 110, "cpu": 110, "mem": 140}

        for c in cols:
            self.users_tree.heading(c, text=headings[c])
            self.users_tree.column(c, width=widths[c], anchor="w")

        ysb = ttk.Scrollbar(parent, orient="vertical", command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=ysb.set)
        ysb.place(in_=self.users_tree, relx=1.0, rely=0, relheight=1.0, anchor="ne")

    # -------------------------
    # Tabs: Services
    # -------------------------
    # ------------------------------------------------------------
    # [P5][UI] Build Services tab
    # ------------------------------------------------------------

    def _build_services_tab(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="x", padx=10, pady=8)

        ttk.Button(top, text="Refresh Now", command=lambda: self.refresh_services(force=True)).pack(side="left")

        btns = ttk.Frame(top)
        btns.pack(side="right")
        ttk.Button(btns, text="Start", command=lambda: self._service_action("start")).pack(side="right", padx=4)
        ttk.Button(btns, text="Stop", command=lambda: self._service_action("stop")).pack(side="right", padx=4)
        ttk.Button(btns, text="Restart", command=lambda: self._service_action("restart")).pack(side="right", padx=4)

        cols = ("unit", "load", "active", "sub", "description")
        self.services_tree = ttk.Treeview(parent, columns=cols, show="headings", height=20)
        self.services_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        headings = {
            "unit": "Service", "load": "Load", "active": "Active",
            "sub": "Sub", "description": "Description",
        }
        widths = {"unit": 280, "load": 80, "active": 90, "sub": 120, "description": 560}
        for c in cols:
            self.services_tree.heading(c, text=headings[c])
            self.services_tree.column(c, width=widths[c], anchor="w")

        ysb = ttk.Scrollbar(parent, orient="vertical", command=self.services_tree.yview)
        self.services_tree.configure(yscrollcommand=ysb.set)
        ysb.place(in_=self.services_tree, relx=1.0, rely=0, relheight=1.0, anchor="ne")

        self.services_hint = tk.StringVar(
            value="Tip: Services tab uses systemctl (systemd). Một số thao tác cần quyền root."
        )
        ttk.Label(parent, textvariable=self.services_hint, anchor="w").pack(fill="x", padx=10, pady=(0, 6))

    # -------------------------
    # Tabs: Startup
    # -------------------------
    # ------------------------------------------------------------
    # [P5][UI] Build Startup tab
    # ------------------------------------------------------------

    def _build_startup_tab(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="x", padx=10, pady=8)

        ttk.Button(top, text="Refresh Now", command=lambda: self.refresh_startup(force=True)).pack(side="left")
        ttk.Button(top, text="Open autostart folder", command=self.open_autostart_folder).pack(side="left", padx=8)

        btns = ttk.Frame(top)
        btns.pack(side="right")
        ttk.Button(btns, text="Enable/Disable (user)", command=self.toggle_startup_user).pack(side="right", padx=4)
        ttk.Button(btns, text="Open file", command=self.open_startup_file).pack(side="right", padx=4)

        cols = ("name", "enabled", "scope", "exec", "path")
        self.startup_tree = ttk.Treeview(parent, columns=cols, show="headings", height=20)
        self.startup_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        headings = {"name": "Name", "enabled": "Enabled", "scope": "Scope", "exec": "Exec", "path": "File"}
        widths = {"name": 220, "enabled": 90, "scope": 90, "exec": 520, "path": 520}
        for c in cols:
            self.startup_tree.heading(c, text=headings[c])
            self.startup_tree.column(c, width=widths[c], anchor="w")

        ysb = ttk.Scrollbar(parent, orient="vertical", command=self.startup_tree.yview)
        self.startup_tree.configure(yscrollcommand=ysb.set)
        ysb.place(in_=self.startup_tree, relx=1.0, rely=0, relheight=1.0, anchor="ne")

        self.startup_hint = tk.StringVar(
            value="Startup: đọc ~/.config/autostart và /etc/xdg/autostart. Enable/Disable chỉ áp dụng cho user scope."
        )
        ttk.Label(parent, textvariable=self.startup_hint, anchor="w").pack(fill="x", padx=10, pady=(0, 6))

    # -------------------------
    # Generic: choose columns dialog
    # -------------------------
    # ------------------------------------------------------------
    # [P5][LOGIC] Refresh performance metrics + chart buffers
    # ------------------------------------------------------------

    def refresh_performance(self):
        # CPU
        cpu = psutil.cpu_percent(interval=None)
        vm = psutil.virtual_memory()
        sm = psutil.swap_memory()

        self.cpu_hist.append(cpu)
        self.mem_hist.append(vm.percent)
        self.swap_hist.append(sm.percent)

        # network KB/s
        try:
            now = time.time()
            net = psutil.net_io_counters()
            if self._last_net is None:
                self._last_net = net
                self._last_net_ts = now
                sent_kbs = recv_kbs = 0.0
            else:
                dt = max(1e-6, now - (self._last_net_ts or now))
                sent_kbs = (net.bytes_sent - self._last_net.bytes_sent) / 1024.0 / dt
                recv_kbs = (net.bytes_recv - self._last_net.bytes_recv) / 1024.0 / dt
                self._last_net = net
                self._last_net_ts = now
            self.net_sent_hist.append(sent_kbs)
            self.net_recv_hist.append(recv_kbs)
        except Exception:
            self.net_sent_hist.append(0.0)
            self.net_recv_hist.append(0.0)

        # summary text
        self.perf_summary.set(
            f"CPU: {cpu:.1f}%    "
            f"Memory: {vm.percent:.1f}% ({fmt_bytes(vm.used)} / {fmt_bytes(vm.total)})    "
            f"Swap: {sm.percent:.1f}% ({fmt_bytes(sm.used)} / {fmt_bytes(sm.total)})"
        )

        # Draw charts with colors
        # CPU: Blue (#0078d7 or similar), Memory: Purple/Pink, Swap: Orange, Net: Green
        self._draw_line_chart(self.canvas_cpu, list(self.cpu_hist), 0, 100, suffix="%", dual=False, line_color="#0078d7")
        self._draw_line_chart(self.canvas_mem, list(self.mem_hist), 0, 100, suffix="%", dual=False, line_color="#800080")
        self._draw_line_chart(self.canvas_swap, list(self.swap_hist), 0, 100, suffix="%", dual=False, line_color="#ff8c00")
        self._draw_line_chart(self.canvas_net, list(self.net_recv_hist), 0, None, suffix=" KB/s",
                              dual=True, series2=list(self.net_sent_hist), label1="Recv", label2="Sent",
                              line_color="#009900", line_color2="#cc0000")


    def _draw_line_chart(self, canvas: tk.Canvas, series, y_min, y_max, suffix="", dual=False,
                         series2=None, label1="A", label2="B", line_color="black", line_color2="gray"):
        canvas.delete("all")
        w = max(1, int(canvas.winfo_width()))
        h = max(1, int(canvas.winfo_height()))
        pad = 10

        # background grid
        for i in range(6):
            y = pad + i * (h - 2 * pad) / 5
            canvas.create_line(pad, y, w - pad, y, dash=(2, 2), fill="#d0d0d0")

        if not series:
            return

        if y_max is None:
            max_s1 = max(series) if series else 0.0
            max_s2 = max(series2) if (dual and series2) else 0.0
            y_max = max(max_s1, max_s2, 1.0)

        def to_xy(i, v, n):
            x = pad + i * (w - 2 * pad) / max(1, n - 1)
            # invert y
            yy = (v - y_min) / max(1e-6, (y_max - y_min))
            y = (h - pad) - yy * (h - 2 * pad)
            return x, y

        n = len(series)
        pts = []
        for i, v in enumerate(series):
            v = max(y_min, min(y_max, float(v)))
            pts.extend(to_xy(i, v, n))
        
        if len(pts) >= 4:
            canvas.create_line(*pts, smooth=True, width=2, fill=line_color)

        if dual and series2:
            n2 = len(series2)
            m = min(n, n2)
            pts2 = []
            for i in range(m):
                v = max(y_min, min(y_max, float(series2[i])))
                pts2.extend(to_xy(i, v, m))
            if len(pts2) >= 4:
                canvas.create_line(*pts2, smooth=True, width=2, dash=(4, 2), fill=line_color2)

        # label max
        canvas.create_text(pad + 2, pad + 2, anchor="nw", text=f"max {y_max:.1f}{suffix}", fill="#333333", font=("Arial", 9))
        if dual:
            canvas.create_text(w - pad - 2, pad + 2, anchor="ne", 
                               text=f"{label1}: solid, {label2}: dash", fill="#333333", font=("Arial", 9))

    # -------------------------
    # Users refresh
    # -------------------------
    # ------------------------------------------------------------
    # [P5][LOGIC] Refresh users list (psutil.users)
    # ------------------------------------------------------------

    def refresh_users(self, force=False):
        rows = self._collect_process_rows()

        agg = defaultdict(lambda: {"cpu": 0.0, "mem": 0, "count": 0})
        for r in rows:
            u = r.user or "(unknown)"
            agg[u]["cpu"] += float(r.cpu)
            agg[u]["mem"] += int(r.mem_rss)
            agg[u]["count"] += 1

        for iid in self.users_tree.get_children(""):
            self.users_tree.delete(iid)

        for user, d in sorted(agg.items(), key=lambda kv: kv[1]["cpu"], reverse=True):
            self.users_tree.insert("", "end", values=(
                user, d["count"], f"{d['cpu']:.1f}", fmt_bytes(d["mem"])
            ))

    # -------------------------
    # Services refresh + action
    # -------------------------
    # ------------------------------------------------------------
    # [P5][LOGIC] Refresh services list (systemctl)
    # ------------------------------------------------------------

    def refresh_services(self, force=False):
        # detect systemctl
        rc, out, err = safe_call(["which", "systemctl"], timeout=2)
        if rc != 0:
            self.services_hint.set("systemctl không có trên máy này (không dùng systemd).")
            for iid in self.services_tree.get_children(""):
                self.services_tree.delete(iid)
            return

        rc, out, err = safe_call(["systemctl", "list-units", "--type=service", "--all", "--no-legend", "--no-pager"], timeout=5)
        if rc != 0:
            self.services_hint.set(f"Không đọc được services: {err.strip() or out.strip()}")
            return
        self.services_hint.set("Tip: Start/Stop/Restart có thể cần quyền root (sudo).")

        for iid in self.services_tree.get_children(""):
            self.services_tree.delete(iid)

        for line in out.splitlines():
            line = line.rstrip()
            if not line:
                continue
            parts = line.split(None, 4)
            if len(parts) < 5:
                continue
            unit, load, active, sub, desc = parts
            self.services_tree.insert("", "end", iid=unit, values=(unit, load, active, sub, desc))


    def _selected_service(self):
        sel = self.services_tree.selection()
        if not sel:
            return None
        return sel[0]
    # ------------------------------------------------------------
    # [P5][ACTION] Service start/stop/restart (systemctl)
    # ------------------------------------------------------------


    def _service_action(self, action: str):
        unit = self._selected_service()
        if not unit:
            return
        if not messagebox.askyesno("Confirm", f"{action.title()} service {unit}?"):
            return
        # best-effort: try systemctl directly
        rc, out, err = safe_call(["systemctl", action, unit], timeout=8)
        if rc != 0:
            messagebox.showerror("Service action failed", (err or out or "").strip() + "\n\nTip: thử chạy app với sudo.")
        self.refresh_services(force=True)

    # -------------------------
    # Startup refresh + actions
    # -------------------------
    # ------------------------------------------------------------
    # [P5][LOGIC] Refresh startup entries (.desktop in autostart dirs)
    # ------------------------------------------------------------

    def refresh_startup(self, force=False):
        entries = []

        def parse_desktop(path: Path):
            data = {}
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                return None
            cur_section = None
            for raw in text.splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    cur_section = line[1:-1].strip()
                    continue
                if "=" in line and cur_section == "Desktop Entry":
                    k, v = line.split("=", 1)
                    data[k.strip()] = v.strip()
            if not data:
                return None
            return data

        if USER_AUTOSTART_DIR.exists():
            for p in USER_AUTOSTART_DIR.glob("*.desktop"):
                d = parse_desktop(p)
                if not d:
                    continue
                hidden = d.get("Hidden", "false").lower() == "true"
                enabled = (not hidden)
                name = d.get("Name", p.stem)
                exe = d.get("Exec", "")
                entries.append((name, "Yes" if enabled else "No", "User", exe, str(p)))

        for ddir in SYS_AUTOSTART_DIRS:
            if ddir.exists():
                for p in ddir.glob("*.desktop"):
                    d = parse_desktop(p)
                    if not d:
                        continue
                    hidden = d.get("Hidden", "false").lower() == "true"
                    enabled = (not hidden)
                    name = d.get("Name", p.stem)
                    exe = d.get("Exec", "")
                    entries.append((name, "Yes" if enabled else "No", "System", exe, str(p)))

        for iid in self.startup_tree.get_children(""):
            self.startup_tree.delete(iid)

        for i, row in enumerate(entries):
            self.startup_tree.insert("", "end", iid=str(i), values=row)


    def _selected_startup_row(self):
        sel = self.startup_tree.selection()
        if not sel:
            return None
        return self.startup_tree.item(sel[0]).get("values", None)


    def open_autostart_folder(self):
        USER_AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        safe_call(["xdg-open", str(USER_AUTOSTART_DIR)], timeout=2)


    def open_startup_file(self):
        row = self._selected_startup_row()
        if not row:
            return
        path = row[4]
        try:
            safe_call(["xdg-open", path], timeout=2)
        except Exception as e:
            messagebox.showerror("Open file", str(e))
    # ------------------------------------------------------------
    # [P5][ACTION] Enable/disable startup (user scope)
    # ------------------------------------------------------------


    def toggle_startup_user(self):
        row = self._selected_startup_row()
        if not row:
            return
        scope = row[2]
        if scope != "User":
            messagebox.showinfo("Startup", "Chỉ bật/tắt được entry ở User scope.")
            return
        path = Path(row[4])
        if not path.exists():
            messagebox.showwarning("Startup", "File không tồn tại.")
            return
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            out_lines = []
            in_de = False
            hidden_line_written = False
            cur_hidden = False

            for ln in text:
                if ln.strip() == "[Desktop Entry]":
                    in_de = True
                if in_de and ln.strip().startswith("Hidden="):
                    cur_hidden = ln.strip().split("=", 1)[1].strip().lower() == "true"

            new_hidden = not cur_hidden

            for ln in text:
                if ln.strip() == "[Desktop Entry]":
                    in_de = True
                    out_lines.append(ln)
                    continue
                if in_de and ln.strip().startswith("Hidden="):
                    out_lines.append(f"Hidden={'true' if new_hidden else 'false'}")
                    hidden_line_written = True
                else:
                    out_lines.append(ln)

            if in_de and not hidden_line_written:
                out_lines.append(f"Hidden={'true' if new_hidden else 'false'}")

            path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
            self.refresh_startup(force=True)
        except Exception as e:
            messagebox.showerror("Startup", str(e))

    # -------------------------
    # Status bar update
    # -------------------------

