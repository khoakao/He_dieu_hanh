# -*- coding: utf-8 -*-
"""Configuration (DEFAULT_CFG) + load/save config"""

from __future__ import annotations

import json
from pathlib import Path

APP_NAME = "Task Manager (Linux)"
CFG_PATH = Path.home() / ".config" / "py_task_manager" / "config.json"

DEFAULT_CFG = {
    "refresh_ms": 2000,
    "always_on_top": False,
    "show_system_processes": True,
    "columns": {  # tab Processes
        "pid": True, "name": True, "user": True,
        "cpu": True, "mem": True, "status": True,
        "nice": True, "threads": False, "fds": False,
        "start": False, "cmd": True,
    },
    "details_columns": {  # tab Details
        "pid": True, "name": True, "user": True, "status": True,
        "cpu": True, "mem": True, "nice": True, "threads": True,
        "fds": True, "start": True, "cmd": True,
    },
    "geometry": "1180x720",
}

HISTORY_LEN = 60  # Lưu lịch sử 60 điểm cho biểu đồ

USER_AUTOSTART_DIR = Path.home() / ".config" / "autostart"
SYS_AUTOSTART_DIRS = [Path("/etc/xdg/autostart")]

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

def ensure_cfg_dir() -> None:
    CFG_PATH.parent.mkdir(parents=True, exist_ok=True)

def load_cfg() -> dict:
    """Load config from CFG_PATH, merge into DEFAULT_CFG."""
    ensure_cfg_dir()
    if CFG_PATH.exists():
        try:
            data = json.loads(CFG_PATH.read_text(encoding="utf-8"))
            cfg = dict(DEFAULT_CFG)
            cfg.update({k: v for k, v in data.items() if k in cfg})
            # deep merge for dicts
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
    """Save config to CFG_PATH."""
    ensure_cfg_dir()
    try:
        CFG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
