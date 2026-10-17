# BẢNG KHAI BÁO SỬ DỤNG AI (AI USAGE DECLARATION)
**Dự án:** Hệ thống Trợ lý Điểm Rèn luyện & Quản lý Khiếu nại (Đề tài T4 - AIPR Final Project)  
**Nhóm:** 3 Sinh viên

---

## 1. BẢNG TỔNG QUAN THEO THÀNH VIÊN

| STT | Thành viên | Vai trò phụ trách | Công cụ AI | Phạm vi áp dụng chính |
| :---: | :--- | :--- | :--- | :--- |
| 1 | [Họ tên SV 1 - MSSV] | *(Để trống cho SV tự điền)* | *(Để trống cho SV tự điền)* | *(Để trống cho SV tự điền)* |
| 2 | **Lê Tuấn Thành** | **Agent & MCP Architect** | **Claude & GitHub Copilot** | **Hỗ trợ cú pháp Typed Schemas, MCP Server stdio & ReAct Orchestrator** |
| 3 | [Họ tên SV 3 - MSSV] | *(Để trống cho SV tự điền)* | *(Để trống cho SV tự điền)* | *(Để trống cho SV tự điền)* |

---

## 2. CHI TIẾT KHAI BÁO SỬ DỤNG AI CỦA TỪNG THÀNH VIÊN

### 🟢 Thành viên A: [Họ tên SV 1 - MSSV]
*(Để trống cho SV tự điền)*

---

### 🔵 Thành viên B: Lê Tuấn Thành — Agent & MCP Architect

#### 📌 Hạng mục 1: Khai báo Typed Schemas (`src/mcp/schemas.py`)
* **Tôi hỏi gì:** Gợi ý cú pháp khai báo `@dataclass` chuẩn Python cho các schema nộp và tra cứu khiếu nại.
* **AI đã làm gì:** Gợi ý khung dataclass mẫu có type hint và cách xuất dictionary dùng hàm `asdict()`.
* **Sinh viên tự làm & điều chỉnh:** Tự định nghĩa đúng các trường nghiệp vụ (`student_id`, `category`, `reason`), viết hàm validate dữ liệu rỗng và tinh gọn bỏ các class thừa để giữ code gọn gàng, đúng trọng tâm.
* **Minh chứng:** [`src/mcp/schemas.py`](file:///c:/Users/LENOVO/Desktop/Study/AIPR%20Project%20Final/src/mcp/schemas.py)

---

#### 📌 Hạng mục 2: Xây dựng MCP Server lưu trữ khiếu nại (`src/mcp/server.py`)
* **Tôi hỏi gì:** Cú pháp đăng ký `@mcp.tool()` và kỹ thuật lưu file JSON an toàn trên tiến trình stdio.
* **AI đã làm gì:** Gợi ý cấu trúc server FastMCP/MCPServer và kỹ thuật atomic write (ghi file tạm `.tmp` rồi đổi tên).
* **Sinh viên tự làm & điều chỉnh:** Giới hạn đúng 2 công cụ cốt lõi (`submit_complaint`, `check_complaint_status`), chuyển hướng toàn bộ log sang `sys.stderr` để giữ sạch luồng stdout cho gói tin JSON-RPC, và tự viết logic sinh mã đơn tăng dần `CPL-YYYY-NNNN`.
* **Minh chứng:** [`src/mcp/server.py`](file:///c:/Users/LENOVO/Desktop/Study/AIPR%20Project%20Final/src/mcp/server.py)

---

#### 📌 Hạng mục 3: Vòng lặp ReAct Orchestrator & Xác minh dữ liệu (`src/orchestrator.py`)
* **Tôi hỏi gì:** Hỗ trợ biểu thức chính quy (regex) bóc tách JSON và khung vòng lặp ReAct (Think - Act - Observe).
* **AI đã làm gì:** Gợi ý regex trích xuất khối JSON từ phản hồi của LLM và cấu trúc vòng lặp `for step in range(MAX_STEPS)`.
* **Sinh viên tự làm & điều chỉnh:** 
  * Tự lập trình logic kiểm soát xác minh: Khi gọi tool nộp khiếu nại, bắt buộc phải gọi tool đọc để đối soát dữ liệu thật trong CSDL trước khi đưa ra câu trả lời cuối.
  * Tự cài đặt cơ chế xử lý lỗi mềm để phản hồi lại ngữ cảnh cho LLM tự sửa sai nếu sinh JSON lỗi, tránh crash chương trình.
  * Tinh gọn toàn bộ mã nguồn để dễ theo dõi và thuận tiện giải thích khi bảo vệ trực tiếp.
* **Minh chứng:** [`src/orchestrator.py`](file:///c:/Users/LENOVO/Desktop/Study/AIPR%20Project%20Final/src/orchestrator.py)

---

### 🟣 Thành viên C: [Họ tên SV 3 - MSSV]
*(Để trống cho SV tự điền)*

---

## 3. CAM KẾT LIÊM CHÍNH HỌC THUẬT

1. Toàn bộ nội dung khai báo trên phản ánh trung thực quá trình làm việc trong dự án.
2. Tự đọc hiểu, làm chủ 100% mã nguồn và sẵn sàng giải thích chi tiết trong buổi vấn đáp.
3. Sử dụng AI làm công cụ hỗ trợ gợi ý cú pháp và tối ưu tốc độ, hoàn toàn làm chủ tư duy thuật toán và logic nghiệp vụ.
