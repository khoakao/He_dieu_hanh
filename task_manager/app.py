# -*- coding: utf-8 -*-
"""Task Manager (Linux) - Tkinter + psutil (split modules)

Run:
  python -m task_manager.main
"""
# ============================================================
# APP ENTRY CLASS — TaskManagerApp
#   This class composes feature mixins by "person" modules.
#   Keep __init__ here to initialize shared state & call _build_ui().
# ============================================================


from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import psutil

from .config import APP_NAME, DEFAULT_CFG, load_cfg, save_cfg
from .person1_core import CoreMixin
from .person2_processes import ProcessesTabMixin
from .person3_details import DetailsTabMixin
from .person4_actions import ActionsMixin
from .person5_other_tabs import OtherTabsMixin


class TaskManagerApp(CoreMixin, ProcessesTabMixin, DetailsTabMixin, ActionsMixin, OtherTabsMixin, tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_cfg()
        self.title(APP_NAME)
        self.geometry(self.cfg.get("geometry", DEFAULT_CFG["geometry"]))
        self.wm_attributes("-topmost", bool(self.cfg.get("always_on_top", False)))

        # state
        self.sort_col = "cpu"
        self.sort_desc = True
        self.details_sort_col = "cpu"
        self.details_sort_desc = True

        self.filter_text = tk.StringVar(value="")
        self.auto_refresh = tk.BooleanVar(value=True)

        self._last_refresh_ts = 0.0

        # --- PERFORMANCE DATA HISTORY ---
        self.cpu_hist = deque(maxlen=HISTORY_LEN)
        self.mem_hist = deque(maxlen=HISTORY_LEN)
        self.swap_hist = deque(maxlen=HISTORY_LEN)
        self.net_sent_hist = deque(maxlen=HISTORY_LEN)
        self.net_recv_hist = deque(maxlen=HISTORY_LEN)

        self._last_net = None
        self._last_net_ts = None

        self._build_ui()

        # prime CPU measurements (psutil cần 1 vòng trước)
        try:
            psutil.cpu_percent(interval=None)
            for p in psutil.process_iter():
                try:
                    p.cpu_percent(interval=None)
                except Exception:
                    pass
        except Exception:
            pass

        self.after(250, self._tick)

        # close hook
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -------------------------
    # UI
    # -------------------------
