# -*- coding: utf-8 -*-
"""Task Manager (Linux) - Tkinter + psutil (split modules)
Run: python -m task_manager.main
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from collections import deque
import psutil
import os

from .config import APP_NAME, DEFAULT_CFG, load_cfg, save_cfg
from .person1_core import CoreMixin
from .person2_processes import ProcessesTabMixin
from .person3_details import DetailsTabMixin
from .person4_actions import ActionsMixin
from .person5_other_tabs import OtherTabsMixin

HISTORY_LEN = 60

class TaskManagerApp(CoreMixin, ProcessesTabMixin, DetailsTabMixin, ActionsMixin, OtherTabsMixin, tk.Tk):
    def __init__(self):
        super().__init__()
        
        # --- [FIX QUAN TRỌNG] RESET CẤU HÌNH CỘT ---
        # Load cấu hình cũ
        self.cfg = load_cfg()
        
        # SỬA LỖI MÀN HÌNH TRẮNG:
        # Nếu cấu hình bị lỗi, ta ép buộc reset lại phần hiển thị cột của tab Details
        self.cfg["details_columns"] = {
            "pid": True, "name": True, "user": True, "status": True,
            "cpu": True, "mem": True, "nice": True, "threads": True,
            "fds": True, "start": True, "cmd": True
        }
        # -------------------------------------------

        self.title(APP_NAME)
        
        # Fix lỗi geometry
        geo = self.cfg.get("geometry", DEFAULT_CFG["geometry"])
        self.geometry(geo)
        
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

        # Xây dựng giao diện
        self._build_ui()

        # --- GẮN SỰ KIỆN CHUYỂN TAB ---
        self.notebook_widget = None
        if hasattr(self, 'notebook') and isinstance(self.notebook, ttk.Notebook):
            self.notebook_widget = self.notebook
        else:
            for widget in self.winfo_children():
                if isinstance(widget, ttk.Notebook):
                    self.notebook_widget = widget
                    break
        
        if self.notebook_widget:
            self.notebook_widget.bind("<<NotebookTabChanged>>", self._on_tab_changed)
            print(">>> Đã gắn sự kiện chuyển tab thành công!")
        # -------------------------------

        try:
            psutil.cpu_percent(interval=None)
            for p in psutil.process_iter():
                try: p.cpu_percent(interval=None)
                except: pass
        except: pass

        self.after(250, self._tick)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_tab_changed(self, event):
        """Hàm xử lý khi chuyển tab"""
        try:
            nb = event.widget
            current_tab_id = nb.select()
            current_tab_text = nb.tab(current_tab_id, "text")

            if "Details" in current_tab_text:
                # Ép hiển thị lại các cột (đề phòng bị ẩn do bug)
                if hasattr(self, 'details_tree'):
                    cols = self.details_tree["columns"]
                    for c in cols:
                        # Nếu cột nào đang bị độ rộng = 0 (bị ẩn), mở nó ra
                        if self.details_tree.column(c, "width") < 5:
                            self.details_tree.column(c, width=80)
                
                # Tải dữ liệu
                self.refresh_details(force=True)
                
            elif "Processes" in current_tab_text:
                if hasattr(self, 'refresh_processes'):
                    self.refresh_processes(force=True)
                    
        except Exception as e:
            print(f"Lỗi tab: {e}")

    def _on_close(self):
        self.cfg["geometry"] = self.winfo_geometry()
        save_cfg(self.cfg)
        self.destroy()

if __name__ == "__main__":
    app = TaskManagerApp()
    app.mainloop()