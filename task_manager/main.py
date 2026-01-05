# -*- coding: utf-8 -*-
from __future__ import annotations

from .app import TaskManagerApp

def main() -> None:
    app = TaskManagerApp()
    app.mainloop()

if __name__ == "__main__":
    main()
