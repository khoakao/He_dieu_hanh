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
cài đặt thư viện phụ thuộc (`psutil`):
  ```bash
  sudo apt install python3-pip
  sudo apt-get install python3-psutil

```
### 3.Chay ung dung:
Để chạy ứng dụng từ mã nguồn python:<br>
Di chuyển đến thư mục chứa mã nguồn
```bash
    cd <thư mục chứa mã nguồn>
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

#### 1.Các thanh công cụ:
* **Tìm kiếm:** Nhập tên (vd: `chrome`) hoặc PID vào ô Search rồi nhấn Enter.
* **Sắp xếp:** Click vào tiêu đề cột (ví dụ click `CPU %` , `PID` , `Memory`) để sắp xếp cao -> thấp.
* **Menu chuột phải:** Click phải vào một dòng để:
    * *Set priority:* Thay đổi độ ưu tiên của tiến trình (liên quan đến cột Nice).
    * *Kill(SIGKILL):* Ép buộc tắt ngay lập tức (dùng khi bị treo).
    * *End task:* Yêu cầu phần mềm tắt một cách bình thường (an toàn hơn Kill).
    * *Properties:* Xem thông tin chi tiết về tiến trình đó.
* **Auto Refresh:** Bỏ tích ô này nếu muốn danh sách đứng yên để dễ soi.
* **Refresh Now:** Nhấn để cập nhật danh sách thủ công ngay lập tức
#### 2. thông tin các cột:

* **PID:** Mã số định danh duy nhất của tiến trình
* **Name** Cho biết tên của tiến trình
* **User** cho biết ai chạy ứng dụng này
* **CPU %** Mức độ sử dụng vi xử lý
* **Memory** dung lượng RAM bị chiếm dụng
* **Command** Câu lệnh thực tế hoặc đường dẫn file đang chạy



### Tab 2: Performance (Hiệu năng)
Giám sát sức khỏe phần cứng theo thời gian thực (Real-time).

* **CPU:** Biểu đồ đường màu xanh dương.
* **Memory (RAM):** Biểu đồ màu tím.
* **Network:**
    * Màu đỏ: Tốc độ Gửi (Sent).
    * Màu xanh lá: Tốc độ Nhận (Received).
* *Lưu ý:* Biểu đồ lưu lại lịch sử 60 giây gần nhất.
* **Swap:** Bộ nhớ ảo (lấy từ ổ cứng) đang được sử dụng khi RAM thật bị đầy

###  Tab 3: Users
Thống kê tài nguyên theo người dùng.

#### 1.Các nút chức năng:
* Hữu ích khi máy có nhiều user đăng nhập cùng lúc.
* **Hiển thị:** Tổng số Process, Tổng % CPU, Tổng lượng RAM mà user đó chiếm dụng.
* **refresh now** Nhấn nút này để cập nhật lại số liệu thống kê mới nhất (vì tab này có thể không tự nhảy số liên tục như tab Performance)

#### 2.Các cột thông tin

* **User:** Tên tài khoản
* **Processes:** Tổng số lượng tiến trình mà tài khoản đó đang chạy
* **CPU %:** Tổng phần trăm sức mạnh xử lý mà tài khoản đó đã chiếm dụng
* **Memory:** Tổng dung lượng RAM mà tài khoản đó đã dùng 

### Tab 4: Details (Chi tiết)
Giống tab Processes nhưng hiển thị chi tiết kỹ thuật hơn.

#### 1.Các nút chức năng:
* **Search:** Nhập tên (vd: `chrome`) hoặc PID vào ô Search rồi nhấn Enter
* **refresh now:** nhấn nút này để cập nhật số liệu mới nhất
* **properties:** xem thuộc tính kỹ thuật
* **Kill** Ép buộc tiến trình dừng ngay lập tức
* **End task** Yêu cầu tiến trình tắt một cách an toàn

#### 2.Thông tin các cột:
* **PID:** Định danh duy nhất của tiến trình
* **Image Name:** Tên của tệp thực thi hoặc tên tiến trình
* **User Name** Tên tài khoản của người dùng
* **Status:** Trạng thái hiện tại của tiến trình
* **Running:** Đang xử lý tính toán
* **Sleeping:** Đang chờ tài nguyên hoặc tín hiệu 
* **Idle:** Nhàn rỗi
* **CPU %** Phần trăm CPU mà tiến trình đang chiếm dụng
* **Memory(RSS):** Lượng bộ nhớ RAM vật lý thực tế mà tiến trình đang sử dụng
* **Nice:** Giá trị ưu tiên của tiến trình
* **threads** Số lượng luồng xử lý mà tiến trình đó đang mở
* **FDs** số lượng files , socket hoặc kết nối mà tiến trình đang mở
* **Start time** Thời gian cụ thể tiến trình đó bắt đầu đang chạy
* **Command line** Câu lệnh đầy đủ dùng để khởi chạy tiến trình bao gồm cả đường dẫn file và các tham số (arguments)

### Tab 5: Services (Dịch vụ)
Quản lý các dịch vụ nền (Systemd Daemons).

#### 1.Các nút chức năng:
* **refresh now:** Cập nhật lại trạng thái của tất cả các dịch vụ
* **Start** Bắt đầu một dịch vụ đang tắt
* **Restart** Khởi động lại 1 dịch vụ
* **NOTE** có thể Click đúp (Double click) vào một dòng để thực hiện lệnh Restart ngay lập tức (theo hướng dẫn ở thanh trạng thái dưới cùng).

#### 2.Ý nghĩa các cột trạng thái:

* **Services:** Tên kỹ thuật của dịch vụ
* **Load:** Trạng thái nạp cấu hình
* **Active hoặc inactive:** hoạt động hoặc không hoạt động
* **Sub:** Trạng thái chi tiết
* **Description** Mô tả ngắn gọn chức năng của dịch vụ đó

###  Tab 6: Startup (Khởi động)
Quản lý ứng dụng chạy cùng hệ thống.

#### 1.Thanh công cụ chức năng:

* **Refresh now:** Cập nhật lại danh sách nếu bạn vừa cài đặt hoặc gỡ bỏ phần mềm.
* **Open auto start folder:** Mở nhanh thư mục chứa các file cấu hình khởi động trên máy
* **Open file:** Mở file nội dung cấu hình của ứng dụng đang chọn để xem hoặc chỉnh sửa thủ công

* **Enable/disable(user):** dùng để bật hoặc tắt quyền tự khởi tạo của ứng dụng
* **Lưu ý:**Dòng chữ nhỏ dưới đáy cửa sổ ghi rõ "Enable/Disable chỉ áp dụng cho user scope". Nghĩa là bạn chỉ tắt được các app do bạn cài (ví dụ: Zalo, Unikey...), còn các dịch vụ cốt lõi của hệ thống (Scope: System) thì nút này có thể không hoạt động để đảm bảo an toàn.

#### 2.Các cột thông tin:

* **Name:** tên ứng dụng dịch vụ
* **Enabled:** Trạng thái hiện tại
* **Scope:** Phạm vi ảnh hưởng
* **System:** dịch vụ của toàn hệ thống
* **User** Ứng dụng riêng của người dùng 
* **Exec:** Đường dẫn lệnh thực tế mà máy sẽ chạy

## 6.Mức độ hoàn thành:

### 1.Giao diện(GUI) : hoàn thành được 90% cần bổ sung Dark Mode 
### 2.Giám sát CPU /RAM : hoàn thành được 100% ổn định được realtime
### 3.Quản lý Process: Hoàn thành 85% đã có kill và renice cần bổ sung Tree View và Disk I/O per process
### 4.Quản lý service: đã tích hợp systemd nhưng cần xử lý bất đồng bộ để tránh lag UI
### 5.Kiến trúc phần mềm: hoàn thành 70% cần cải thiện multi-threading cho các tác vụ nặng




