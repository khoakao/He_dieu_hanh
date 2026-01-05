# -*- coding: utf-8 -*-
"""Shared helpers (formatting, safe calls, etc.)"""

from __future__ import annotations

import os
import re
import time
import subprocess
from datetime import datetime

import psutil

def fmt_bytes(n: int) -> str:
    if n is None:
        return ""
    units = ["B", "KB", "MB", "GB", "TB"]
    x = float(n)
    i = 0
    while x >= 1024 and i < len(units) - 1:
        x /= 1024.0
        i += 1
    if i == 0:
        return f"{int(x)} {units[i]}"
    return f"{x:.1f} {units[i]}"

def safe_call(fn, default=None):
    try:
        return fn()
    except Exception:
        return default

def is_system_process(p: psutil.Process) -> bool:
    """Heuristic: system process if username is root or pid < 100."""
    try:
        if p.pid < 100:
            return True
        u = p.username()
        return u in ("root", "systemd+", "messagebus")
    except Exception:
        return False

def dt_from_ts(ts: float) -> str:
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""

def readlink_exe(pid: int) -> str:
    """Try to get executable path for a PID."""
    try:
        return os.readlink(f"/proc/{pid}/exe")
    except Exception:
        return ""

def run_cmd(cmd: list[str], timeout: float = 2.0) -> tuple[int, str, str]:
    """Run subprocess command and return (returncode, stdout, stderr)."""
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        return 1, "", str(e)
