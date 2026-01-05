# Task Manager (Linux) - Split by 5 people

This is your original `hdh (1).py` split into modules following the 5-person plan:

- person1_core.py: App shell + config + refresh + menu + status bar
- person2_processes.py: Processes tab (UI + list + filter + sort + columns)
- person3_details.py: Details tab (UI + sort + columns)
- person4_actions.py: Process actions & properties (kill/nice/affinity/properties/open folder)
- person5_other_tabs.py: Performance + Users + Services + Startup

## Run

Install deps:
```bash
pip install psutil
```

Run:
```bash
python run.py
# or
python -m task_manager.main
```

Config is saved at:
`~/.config/py_task_manager/config.json`
