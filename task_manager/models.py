# -*- coding: utf-8 -*-
"""Data models"""

from __future__ import annotations
from dataclasses import dataclass

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
