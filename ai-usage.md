# BẢNG KHAI BÁO SỬ DỤNG AI (AI USAGE DECLARATION)
**Dự án:** Hệ thống Trợ lý Điểm Rèn luyện & Quản lý Khiếu nại (Đề tài T4 - AIPR Final Project)
**Nhóm:** 3 Sinh viên

---

## 1. BẢNG TỔNG QUAN THEO THÀNH VIÊN

| STT | Thành viên | Vai trò phụ trách | Công cụ AI | Phạm vi áp dụng |
| :---: | :--- | :--- | :--- | :--- |
| 1 | [Họ tên SV 1 - MSSV] | *(Để trống cho SV tự điền)* | *(Để trống cho SV tự điền)* | *(Để trống cho SV tự điền)* |
| 2 | **Lê Tuấn Thành** | **Agent & MCP Architect** | **Claude & GitHub Copilot** | **Schemas, MCP Server & Bộ kiểm thử tự động (45 tests)** |
| 3 | [Họ tên SV 3 - MSSV] | *(Để trống cho SV tự điền)* | *(Để trống cho SV tự điền)* | *(Để trống cho SV tự điền)* |

---

## 2. CHI TIẾT KHAI BÁO SỬ DỤNG AI CỦA TỪNG THÀNH VIÊN

### 🟢 Thành viên A: [Họ tên SV 1 - MSSV]
*(Để trống cho SV tự điền)*

---

### 🔵 Thành viên B: Lê Tuấn Thành — Agent & MCP Architect

#### 📌 Hạng mục 1: Định nghĩa Schemas dữ liệu và xác thực đầu vào (`src/mcp/schemas.py`)
* **Tôi hỏi gì:** Yêu cầu thiết kế các dataclass cho input/output của các MCP tools (`submit_complaint`, `check_complaint_status`, `list_student_complaints`, `calculate_drl`).
* **AI gợi ý gì:** Đề xuất cài thêm thư viện Pydantic để validate dữ liệu tự động.
* **Đã làm những gì:**
  * Từ chối cài thêm Pydantic để giữ code gọn nhẹ, sử dụng thuần Python Standard Library theo bài học W1.
  * Tự viết hàm `__post_init__` để cắt khoảng trắng (`strip()`), chặn chuỗi rỗng và chặn điểm số âm.
  * Xây dựng hàm `to_dict()` và `@classmethod from_dict()` để chuyển đổi dữ liệu hai chiều an toàn.
* **Minh chứng:** [`src/mcp/schemas.py`](file:///c:/Users/LENOVO/Desktop/Study/AIPR%20Project%20Final/src/mcp/schemas.py)

---

#### 📌 Hạng mục 2: Xây dựng MCP Server lưu khiếu nại an toàn (`src/mcp/server.py`)
* **Tôi hỏi gì:** Yêu cầu tạo MCP Server có 3 tool quản lý khiếu nại, lưu dữ liệu thật xuống file JSON và giữ sạch kênh stdio.
* **AI gợi ý gì:** Gợi ý khung cơ bản dùng `json.dump` ghi đè file và quy tắc đặt mã khiếu nại `CPL-YYYY-`.
* **Đã làm những gì:**
  * Áp dụng kỹ thuật Atomic Write: ghi ra file tạm `.tmp` rồi đổi tên bằng `os.replace` để chống hỏng file khi gặp sự cố.
  * Viết logic phát sinh mã đơn tăng dần tự động, đảm bảo không bị trùng ID khi nộp liên tiếp.
  * Chuyển toàn bộ câu lệnh log debug sang `sys.stderr`, giữ kênh `stdout` sạch hoàn toàn cho gói tin JSON-RPC.
  * Xử lý ngoại lệ an toàn khi file chưa tồn tại hoặc dữ liệu JSON bị hỏng.
* **Minh chứng:** [`src/mcp/server.py`](file:///c:/Users/LENOVO/Desktop/Study/AIPR%20Project%20Final/src/mcp/server.py)

---

#### 📌 Hạng mục 3: Xây dựng bộ kiểm thử tự động 45 bài test (`tests/`)
* **Tôi hỏi gì:** Yêu cầu viết unit test toàn diện cho Schemas, Server và Client, đảm bảo không ảnh hưởng file dữ liệu thật.
* **AI gợi ý gì:** Gợi ý khung test cơ bản với một vài trường hợp mẫu.
* **Đã làm những gì:**
  * Xây dựng đầy đủ 45 bài test tự động bao phủ toàn bộ các kịch bản:
    * `test_mcp_schemas.py` (21 tests): Kiểm tra kiểu dữ liệu, chặn dữ liệu sai/rỗng/âm, chuyển đổi roundtrip.
    * `test_mcp_server.py` (15 tests): Kiểm tra lưu thật, đọc lại kiểm chứng, atomic write, xử lý file hỏng.
    * `test_mcp_client.py` (9 tests): Kiểm tra kết nối subprocess qua stdio thật, khám phá tool động, bọc lỗi không để crash app.
  * Sử dụng fixture đổi biến môi trường `AIPR_COMPLAINTS_FILE` sang file tạm khi chạy test để bảo vệ nguyên vẹn `data/complaints.json`.
* **Minh chứng:**
  * [`tests/test_mcp_schemas.py`](file:///c:/Users/LENOVO/Desktop/Study/AIPR%20Project%20Final/tests/test_mcp_schemas.py)
  * [`tests/test_mcp_server.py`](file:///c:/Users/LENOVO/Desktop/Study/AIPR%20Project%20Final/tests/test_mcp_server.py)
  * [`tests/test_mcp_client.py`](file:///c:/Users/LENOVO/Desktop/Study/AIPR%20Project%20Final/tests/test_mcp_client.py)
  * Kết quả: 45/45 tests pass 100%.

---

#### ⚠️ Minh bạch về phần việc chưa làm (ReAct Agent Orchestrator)
* **Thực trạng:** File `src/orchestrator.py` hiện tại là file khung sườn (skeleton stub), chưa có thuật toán ReAct thật.
* **Mức độ dùng AI:** Mới sử dụng AI thảo luận thiết kế luồng ReAct (`MAX_STEPS = 10`) và quy tắc xác minh sau khi nộp đơn.
* **Cam kết:** Sẽ tự tay triển khai mã nguồn và viết test ở Phase 5 kế tiếp.

---

### 🟣 Thành viên C: [Họ tên SV 3 - MSSV]
*(Để trống cho SV tự điền)*

---

## 3. CAM KẾT LIÊM CHÍNH HỌC THUẬT

1. Toàn bộ nội dung khai báo trên phản ánh chính xác 100% quá trình làm việc thực tế trong dự án.
2. Tự đọc hiểu, làm chủ 100% mã nguồn cùng bộ test và sẵn sàng giải thích chi tiết trong buổi vấn đáp.
3. Sử dụng AI làm công cụ hỗ trợ tư vấn và tăng tốc độ, không để AI thay thế tư duy lập trình.
