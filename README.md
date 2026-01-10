# Linux Task Manager (Python + Tkinter)

Một ứng dụng **Task Manager** dành cho Linux được viết bằng **Python** và thư viện giao diện **Tkinter**, sử dụng **psutil** để thu thập thông tin hệ thống. Ứng dụng này mô phỏng giao diện và chức năng của Windows Task Manager, giúp người dùng quản lý tiến trình, hiệu năng và dịch vụ hệ thống một cách trực quan.

![Linux Task Manager](https://img.shields.io/badge/Platform-Linux-linux)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📋 Tính năng chính

Ứng dụng bao gồm các nhóm chức năng chính:

1.  **Quản lý tiến trình (Processes/Details):**
    * Hiển thị danh sách PID, Tên, User, CPU%, RAM, Trạng thái, Command line...
    * Hỗ trợ **Search/Lọc**, **Sort** theo cột, **Ẩn/Hiện cột**.
    * Tự động làm mới (Auto refresh) có thể cấu hình.
2.  **Thao tác với Process:**
    * **End task** (Gửi tín hiệu SIGTERM).
    * **Kill process** (Gửi tín hiệu SIGKILL - buộc dừng).
    * Thay đổi độ ưu tiên (**Set Priority/Nice**).
    * Thiết lập **CPU Affinity** (gán CPU cụ thể cho tiến trình).
    * Xem **Properties** chi tiết và mở thư mục chứa file chạy (`xdg-open`).
3.  **Giám sát hiệu năng (Performance):**
    * Biểu đồ thời gian thực cho **CPU, RAM, Swap, Network**.
    * Lưu lịch sử hiển thị (History graph).
4.  **Thống kê người dùng (Users):**
    * Tổng hợp tài nguyên (CPU/RAM/Số tiến trình) đang sử dụng bởi từng User.
5.  **Dịch vụ hệ thống (Services):**
    * Liệt kê các Systemd Service.
    * Thao tác **Start/Stop/Restart** (Lưu ý: Cần quyền root/sudo cho các thao tác này).
6.  **Startup Apps:**
    * Quản lý các file `.desktop` trong thư mục autostart (User & System).
    * **Enable/Disable** ứng dụng khởi động cùng hệ thống (User scope).
7.  **Cấu hình:**
    * Lưu trạng thái (kích thước cửa sổ, cột hiển thị, tốc độ update...) vào file JSON.

---

## 👥 Phân công nhiệm vụ (Team Roles)

Dự án được phát triển theo mô hình module hóa, với sự phân công cụ thể như sau:

| Thành viên | Module / File | Nhiệm vụ chi tiết |
| :--- | :--- | :--- |
| **Đặng Thị Bích Phượng** | `person1_core.py` | **Core / App Shell**<br>- Thiết kế khung ứng dụng (Notebook 6 tab, Status bar).<br>- Xây dựng Menu bar (Options, View, Help).<br>- Xử lý luồng Refresh Loop (`_tick`) toàn bộ ứng dụng.<br>- Quản lý lưu/đọc cấu hình (`config.json`) và trạng thái cửa sổ. |
| **Vũ Thị Hải Anh** | `person2_processes.py` | **Processes Tab**<br>- UI & Logic tab Processes.<br>- Thu thập dữ liệu từ `psutil`, format CPU/RAM.<br>- Xử lý Search/Filter và ẩn process hệ thống.<br>- Sort dữ liệu theo cột.<br>- Context menu và các binding sự kiện. |
| **Nguyễn Thị Nhật Lệ** | `person3_details.py` | **Details Tab**<br>- UI & Logic tab Details (TreeView độc lập).<br>- Cơ chế Sort riêng biệt cho tab Details.<br>- Quản lý ẩn/hiện cột chi tiết theo cấu hình.<br>- Refresh dữ liệu sử dụng collector chung. |
| **Trần Bảo Nam** | `person4_actions.py` | **Actions & Properties**<br>- Xử lý logic End Task (SIGTERM), Kill (SIGKILL).<br>- Logic Set Priority (Nice) và CPU Affinity.<br>- Dialog hiển thị Properties chi tiết.<br>- Xử lý các ngoại lệ (Permission Denied, NoSuchProcess). |
| **Cao Hữu Hà Khoa** | `person5_other_tabs.py` | **Performance, Users, Services, Startup**<br>- **Perf:** Vẽ biểu đồ Canvas (CPU/RAM/Net) + Lịch sử.<br>- **Users:** Thống kê tài nguyên theo User.<br>- **Services:** Quản lý Systemd units (Start/Stop/Restart).<br>- **Startup:** Quản lý file `.desktop`, toggle enable/disable. |

---

## 🛠️ Hướng dẫn Cài đặt & Chạy (Development)

### 1. Yêu cầu hệ thống
* Hệ điều hành: Linux (Ubuntu, Debian, Fedora, Arch, etc.)
* Python: 3.6 trở lên.

### 2. Cài đặt thư viện giao diện Tkinter (Bắt buộc)
Trên Linux, thư viện giao diện Tkinter thường không được cài mặc định cùng Python. Bạn cần cài nó thủ công qua Terminal tùy theo bản phân phối Linux đang sử dụng:

* **Ubuntu / Debian / Linux Mint / Kali:**
  ```bash
  sudo apt-get update
  sudo apt-get install python3-tk

### Cài đặt thư viện Python
Sử dụng `pip` để cài đặt thư viện phụ thuộc (`psutil`):

  ```bash
  sudo pip install psutil

