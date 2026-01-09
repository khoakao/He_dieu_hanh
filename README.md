
## Tóm tắt chức năng

Ứng dụng **Task Manager cho Linux** (Python + Tkinter + psutil) mô phỏng Task Manager Windows, gồm các nhóm chức năng chính:

* **Quản lý tiến trình (Processes/Details):** hiển thị danh sách process (PID/Name/User/CPU/RAM/Status/Command…), hỗ trợ **search/lọc**, **sort theo cột**, **ẩn/hiện cột**, **auto refresh**, và **context menu**.
* **Thao tác với process:** **End task (SIGTERM)**, **Kill (SIGKILL)**, **đổi priority (nice)**, **set CPU affinity**, xem **Properties** và **mở thư mục executable**.
* **Giám sát hiệu năng (Performance):** theo dõi **CPU/RAM/Swap/Network** theo thời gian thực (kèm đồ thị lịch sử).
* **Thống kê người dùng (Users):** tổng hợp **số process/CPU/RAM** theo từng user.
* **Dịch vụ hệ thống (Services):** liệt kê service (systemd) và thao tác **Start/Stop/Restart** (một số thao tác cần quyền sudo).
* **Startup apps:** đọc `.desktop` từ autostart (user/system), hỗ trợ **enable/disable** (user scope), mở file/thư mục.
* **Cấu hình & lưu trạng thái:** lưu `config.json` (refresh interval, always on top, show system processes, cấu hình cột, kích thước cửa sổ…).

---

## Phân công nhiệm vụ của từng thành viên

### Đặng Thị Bích Phượng — Core / App Shell (`person1_core.py`)

* Thiết kế **khung ứng dụng** (Notebook 6 tab + status bar).
* Xây dựng **menu** và luồng cấu hình:

  * Always on top, Show system processes, Update speed.
  * Dialog chọn cột hiển thị.
* Xây dựng **refresh loop** (`_tick`, `refresh_all`) và cập nhật status bar.
* Lưu/đọc cấu hình và trạng thái cửa sổ khi thoát.

### Vũ Thị Hải Anh — Processes Tab (`person2_processes.py`)

* UI tab Processes: Search, Auto refresh, Refresh Now, bảng TreeView.
* Logic:

  * Collect process từ `psutil.process_iter()`
  * Format dữ liệu (CPU%, RSS, start time…)
  * Lọc theo keyword và ẩn process hệ thống (theo config)
  * Sort theo cột
* Context menu + binding double click.

### Nguyễn Thị Nhật Lệ — Details Tab (`person3_details.py`)

* UI tab Details + TreeView riêng.
* Cơ chế:

  * Sort theo cột (độc lập tab Processes)
  * Ẩn/hiện cột Details theo config riêng
* Refresh danh sách Details dựa trên collector dùng chung.

### Trần Bảo Nam — Actions & Properties (`person4_actions.py`)

* Xử lý thao tác trên tiến trình:

  * End task (SIGTERM), Kill (SIGKILL)
  * Set nice/priority
  * Set CPU affinity
  * Open executable folder
* Thiết kế và hiển thị **Properties dialog** + copy nhanh thông tin.
* Xử lý lỗi quyền (Permission denied), process biến mất (NoSuchProcess)…

### Cao Hữu Hà Khoa — Performance + Users + Services + Startup (`person5_other_tabs.py`)

* Tab Performance:

  * Thu thập CPU/RAM/Swap/Network
  * Vẽ biểu đồ line chart bằng Canvas + lưu lịch sử
* Tab Users:
  
  * Gom nhóm thống kê CPU/RAM/process count theo user
* Tab Services:

  * Liệt kê services bằng systemctl
  * Start/Stop/Restart
* Tab Startup:

  * Đọc `.desktop` trong autostart dirs
  * Bật/tắt startup user bằng `Hidden=true/false`
  * Mở folder/file bằng `xdg-open`

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
