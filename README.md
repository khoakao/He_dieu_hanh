# Linux Task Manager (Python + Tkinter)

Một ứng dụng **Task Manager** dành cho Linux được viết bằng **Python** và thư viện giao diện **Tkinter**, sử dụng **psutil** để thu thập thông tin hệ thống. Ứng dụng này mô phỏng giao diện và chức năng của Windows Task Manager, giúp người dùng quản lý tiến trình, hiệu năng và dịch vụ hệ thống một cách trực quan.

![Linux Task Manager](https://img.shields.io/badge/Platform-Linux-linux)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

##  Tính năng chính

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

##  Phân công nhiệm vụ (Team Roles)

Dự án được phát triển theo mô hình module hóa, với sự phân công cụ thể như sau:

| Thành viên | Module / File | Nhiệm vụ chi tiết |
| :--- | :--- | :--- |
| **Đặng Thị Bích Phượng** | `person1_core.py` | **Core / App Shell**<br>- Thiết kế khung ứng dụng (Notebook 6 tab, Status bar).<br>- Xây dựng Menu bar (Options, View, Help).<br>- Xử lý luồng Refresh Loop (`_tick`) toàn bộ ứng dụng.<br>- Quản lý lưu/đọc cấu hình (`config.json`) và trạng thái cửa sổ. |
| **Vũ Thị Hải Anh** | `person2_processes.py` | **Processes Tab**<br>- UI & Logic tab Processes.<br>- Thu thập dữ liệu từ `psutil`, format CPU/RAM.<br>- Xử lý Search/Filter và ẩn process hệ thống.<br>- Sort dữ liệu theo cột.<br>- Context menu và các binding sự kiện. |
| **Nguyễn Thị Nhật Lệ** | `person3_details.py` | **Details Tab**<br>- UI & Logic tab Details (TreeView độc lập).<br>- Cơ chế Sort riêng biệt cho tab Details.<br>- Quản lý ẩn/hiện cột chi tiết theo cấu hình.<br>- Refresh dữ liệu sử dụng collector chung. |
| **Trần Bảo Nam** | `person4_actions.py` | **Actions & Properties**<br>- Xử lý logic End Task (SIGTERM), Kill (SIGKILL).<br>- Logic Set Priority (Nice) và CPU Affinity.<br>- Dialog hiển thị Properties chi tiết.<br>- Xử lý các ngoại lệ (Permission Denied, NoSuchProcess). |
| **Cao Hữu Hà Khoa** | `person5_other_tabs.py` | **Performance, Users, Services, Startup**<br>- **Perf:** Vẽ biểu đồ Canvas (CPU/RAM/Net) + Lịch sử.<br>- **Users:** Thống kê tài nguyên theo User.<br>- **Services:** Quản lý Systemd units (Start/Stop/Restart).<br>- **Startup:** Quản lý file `.desktop`, toggle enable/disable. |

---

##  Hướng dẫn Cài đặt & Chạy (Development)

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

```
### 3.Chay ung dung:
Để chạy ứng dụng từ mã nguồn python:<br>
Di chuyển đến thư mục "HE_DIEU_HANH"
```bash
    cd HE_DIEU_HANH
    python3 run.py
```
Note: 

##  4.Hướng dẫn Dịch (Đóng gói thành file chạy exe/binary)

Để tạo ra một file chạy duy nhất (không cần cài Python mỗi lần chạy), bạn có thể sử dụng **PyInstaller**.

### 1. Cài đặt PyInstaller

```bash
pip install pyinstaller
```

### 2.Thực hiện đóng gói:

Chạy lệnh sau tại thư mục gốc của dự án:
```bash
  pyinstaller --noconfirm --onefile --windowed --name "TaskManagerLinux" --clean run.py
```
Giải thích tham số:

* --onefile: Gom tất cả vào 1 file duy nhất
* --windowed: Chạy chế độ cửa sổ (không hiện màn hình đen terminal phía sau)
* --name: "TaskManagerLinux": Đặt tên file đầu ra

### 3.Kết quả:

Sau khi chạy xong, file thực thi sẽ nằm trong thư mục dist/.
```bash
  ./dist/TaskManagerLinux
```
Thầy và các bạn có thể copy file TaskManagerLinux này sang máy Linux khác để chạy mà không cần cài đặt lại môi trường Python

## Note:

### 1.Quyền root:Một số tính năng như Restart Service (tab Services) hoặc Kill các tiến trình hệ thống sẽ yêu cầu bạn chạy ứng dụng với quyền sudo:

```bash
  sudo python3 run.py
# Hoặc
sudo ./dist/TaskManagerLinux
```
### 2.Config: Cấu hình ứng dụng được lưu tại ~/.config/py_task_manager/config.json. Nếu gặp lỗi giao diện, bạn có thể xóa file này để ứng dụng tạo lại cấu hình mặc định

## 5. Hướng dẫn Sử dụng chi tiết

Giao diện chia làm 6 Tab chính. Dưới đây là cách sử dụng từng Tab:

### Tab 1: Processes (Tiến trình)
Quản lý các phần mềm đang chạy.

* **Tìm kiếm:** Nhập tên (vd: `chrome`) hoặc PID vào ô Search rồi nhấn Enter.
* **Sắp xếp:** Click vào tiêu đề cột (ví dụ click `CPU %`) để sắp xếp cao -> thấp.
* **Menu chuột phải:** Click phải vào một dòng để:
    * *End Task:* Yêu cầu tắt phần mềm.
    * *Kill:* Ép buộc tắt ngay lập tức (dùng khi bị treo).
    * *Set Priority:* Chỉnh độ ưu tiên (Số càng nhỏ ưu tiên càng cao).
    * *Set Affinity:* Chọn CPU cụ thể cho ứng dụng chạy.
* **Auto Refresh:** Bỏ tích ô này nếu muốn danh sách đứng yên để dễ soi.

### 📈 Tab 2: Performance (Hiệu năng)
Giám sát sức khỏe phần cứng theo thời gian thực (Real-time).

* **CPU:** Biểu đồ đường màu xanh dương.
* **Memory (RAM):** Biểu đồ màu tím.
* **Network:**
    * Màu đỏ: Tốc độ Gửi (Sent).
    * Màu xanh lá: Tốc độ Nhận (Received).
* *Lưu ý:* Biểu đồ lưu lại lịch sử 60 giây gần nhất.

###  Tab 3: Users
Thống kê tài nguyên theo người dùng.

* Hữu ích khi máy có nhiều user đăng nhập cùng lúc.
* **Hiển thị:** Tổng số Process, Tổng % CPU, Tổng lượng RAM mà user đó chiếm dụng.

### Tab 4: Details (Chi tiết)
Giống tab Processes nhưng hiển thị chi tiết kỹ thuật hơn.

* Hiển thị **Command Line** đầy đủ (đường dẫn file chạy và các tham số khởi động).
* Cột riêng biệt, có thể cấu hình hiển thị trong Menu `View` -> `Select columns`.

### Tab 5: Services (Dịch vụ)
Quản lý các dịch vụ nền (Systemd Daemons).

* **Các cột:** Unit (Tên), Load (Trạng thái nạp), Active (Đang chạy hay không), Sub (Trạng thái con).
* **Thao tác:** Chọn service -> Bấm nút **Restart Service**.
* **Yêu cầu:** Cần chạy app bằng `sudo` mới thao tác được.

###  Tab 6: Startup (Khởi động)
Quản lý ứng dụng chạy cùng hệ thống.

* **User Scope:** Ứng dụng cài riêng cho user hiện tại (`~/.config/autostart`).
* **System Scope:** Ứng dụng toàn hệ thống (`/etc/xdg/autostart`).
* **Toggle (User):** Chọn dòng thuộc User Scope -> Bấm nút để Bật/Tắt (Enable/Disable).
* **Open Folder:** Mở nhanh thư mục chứa file cấu hình khởi động.


