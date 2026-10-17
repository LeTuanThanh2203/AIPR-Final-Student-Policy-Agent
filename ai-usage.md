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

### Thành viên: [Ca Ngọc Tân - 24110127] — Member A (RAG & Data Engineer) 
* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).
  **Vị trí áp dụng:** Hàm parse_and_chunk_documents trong `src/rag/doc_parser.py`.
* **Prompt chính đã dùng:**
  > *Dựa trên cấu trúc văn bản Quy định đánh giá kết quả rèn luyện của sinh viên Trường Đại học Sư phạm Kỹ thuật TP.HCM (HCMUTE), gồm 19 Điều và Phụ lục 1 là bảng khung điểm các hoạt động, hãy viết hàm Python parse_and_chunk_documents để đọc trực tiếp nội dung từ file HTRL.txt, không khai báo nội dung văn bản trực tiếp trong code và không cần hàm đọc nhiều định dạng file extract_text_from_file. Cuối cùng, lưu toàn bộ chunks vào file `data/processed/chunks.json` để phục vụ hệ thống RAG.*

* **Đoạn code do AI hỗ trợ sinh:**
  ```python

  source_path = Path(source_file)
  if not source_path.is_file():
      raise FileNotFoundError(
          f"Không tìm thấy file dữ liệu: {source_path.resolve()}"
      )
  text = source_path.read_text(encoding="utf-8")

  if not text.strip():
      raise ValueError(
          f"File {source_path} không có nội dung."
      )

  dieu_matches = list(
      re.finditer(
          r"(Điều\s+(\d+)[\.: \t]+([^\n]*))",
          text,
      )
  )

  for i, match in enumerate(dieu_matches):
      dieu_num = match.group(2)
      dieu_title = match.group(1).strip()
      start_pos = match.start()

      if i + 1 < len(dieu_matches):
          end_pos = dieu_matches[i + 1].start()
      else:
          appendix_pos = text.find("Phụ lục 1", start_pos)
          end_pos = (
              appendix_pos
              if appendix_pos != -1
              else len(text)
          )

      dieu_content = text[start_pos:end_pos].strip()
      chunk = DocumentChunk(
          chunk_id=f"{doc_id}_D{dieu_num.zfill(2)}",
          doc_id=doc_id,
          chunk_index=chunk_counter,
          content=dieu_content,
          metadata={
              "doc_id": doc_id,
              "dieu": dieu_num,
              "title": dieu_title,
              "source": source_path.name,
              "type": "dieu_khoan",
          },
      )

* **Tinh chỉnh và hoàn thiện của sinh viên:**
  1. Bổ sung kiểm tra dữ liệu đầu vào: Kiểm tra sự tồn tại của file nguồn và nội dung rỗng trước khi thực hiện phân tách, giúp phát hiện lỗi dữ liệu sớm.
  2. Hoàn thiện phân đoạn logic: Phân tách từng Điều dựa trên tiêu đề Điều tiếp theo, đồng thời xác định điểm kết thúc phần thân quy định để không đưa nội dung Phụ lục 1 vào chunk của Điều cuối cùng.
  3. Tách riêng các tiêu chí trong phụ lục: Bổ sung biểu thức chính quy để nhận diện 5 khối TIÊU CHÍ I đến TIÊU CHÍ V, giúp nội dung bảng điểm được truy xuất độc lập và chính xác hơn
  4. Ánh xạ tiêu chí với Điều tương ứng: Gán metadata theo quy ước I → Điều 5, II → Điều 6, III → Điều 7, IV → Điều 8, V → Điều 9. Việc ánh xạ này hỗ trợ hệ thống truy xuất thông tin và xác định căn cứ quy định liên quan khi trả lời câu hỏi về điểm rèn luyện.
  5. Chuẩn hóa dữ liệu đầu ra: Gán chunk_id, chunk_index và metadata cho từng chunk; lưu kết quả thành JSON bằng ensure_ascii=False để giữ nguyên tiếng Việt, phục vụ các bước embedding, lập chỉ mục và truy xuất trong hệ thống RAG.


* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).
  **Vị trí áp dụng:** Các hàm normalise_scores và hybrid_search
* **Prompt chính đã dùng:**
  > *"Viết hàm Hybrid Search kết hợp BM25Okapi và Cosine Similarity bằng NumPy theo bài học Tuần 4.2 với trọng số 0.3×BM25+0.7×Cosine. Chuẩn hóa mảng điểm về đoạn [0, 1] và xử lý các trường hợp mảng điểm rỗng hoặc min == max."*

* **Đoạn code do AI hỗ trợ sinh:**
  ```python
  def normalise_scores(scores: List[float]) -> List[float]:
    if not scores: return []
    min_s, max_s = min(scores), max(scores)
    if max_s == min_s:
        return [1.0 if max_s > 0 else 0.0 for _ in scores]
    return [(s - min_s) / (max_s - min_s) for s in scores]
  def hybrid_search(...):
      bm25_norm = normalise_scores(bm25_raw_scores)
      cosine_norm = normalise_scores(cosine_raw_scores)
      combined = [(chunks[i], 0.3 * bm25_norm[i] + 0.7 * cosine_norm[i]) for i in range(len(chunks))]

* **Tinh chỉnh và hoàn thiện của sinh viên:** Đảm bảo type hints nghiêm ngặt và xử lý trường hợp chunk.embedding is None để không bị lỗi runtime.


* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).
  **Vị trí áp dụng:** Hàm rag_pipeline
* **Prompt chính đã dùng:**
  > *"Tích hợp cơ chế Calibration (ngưỡng tương đồng tối thiểu CALIBRATION_THRESHOLD = 0.25) vào RAG Pipeline để khi gặp các câu hỏi bẫy ngoài quy chế (chơi game, xem phim Marvel...) hệ thống lập tức từ chối và trả về đúng câu: 'Thông tin này không có trong quy chế điểm rèn luyện được cung cấp.' thay vì bịa đặt."*

* **Đoạn code do AI hỗ trợ sinh:**
  ```python
  if not results or (results[0][1] < CALIBRATION_THRESHOLD):
    return "Thông tin này không có trong quy chế điểm rèn luyện được cung cấp.", results

* **Tinh chỉnh và hoàn thiện của sinh viên:** Đồng bộ giá trị ngưỡng với hằng số CALIBRATION_THRESHOLD trong `src/utils/config.py` và liên kết với template prompt ngoài tại `prompts/rag_grounding.txt`.






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

#### 📌 Hạng mục 1: Xây dựng Robust LLM Client & Prompt Loader (`src/llm_client.py`)
* **Tôi hỏi gì:** Hỗ trợ cú pháp đóng gói lớp `RobustLLMClient` kết nối Groq API theo phong cách Tuần 2, thuật toán Exponential Backoff tự động thử lại khi nghẽn mạng và cú pháp Mock test trong `unittest.mock`.
* **AI đã làm gì:** Gợi ý khung try/except với `time.sleep(2 ** attempt)`, hàm `load_prompt` an toàn với Pathlib, và cấu trúc hàm test giả lập đối tượng phản hồi của Groq.
* **Sinh viên tự làm & điều chỉnh:**
  1. Cấu hình kết nối trực tiếp với Groq API (`from groq import Groq`) và model `openai/gpt-oss-20b` đúng như bài tập đã học tại Tuần 2.
  2. Bóc tách chính xác số liệu `usage` thật từ Groq (`prompt_tokens`, `completion_tokens`, `total_tokens`) để đáp ứng tiêu chí đo token thật của R-01.
  3. Tự viết bộ kiểm thử trong `tests/test_llm_client.py` kiểm tra cả trường hợp thành công và trường hợp giả lập lỗi mạng để chứng minh cơ chế retry hoạt động độc lập.
* **Minh chứng:** [`src/llm_client.py`](file:///d:/AIPR-Final-Student-Policy-Agent/src/llm_client.py) và [`tests/test_llm_client.py`](file:///d:/AIPR-Final-Student-Policy-Agent/tests/test_llm_client.py)



---

## 3. CAM KẾT LIÊM CHÍNH HỌC THUẬT

1. Toàn bộ nội dung khai báo trên phản ánh trung thực quá trình làm việc trong dự án.
2. Tự đọc hiểu, làm chủ 100% mã nguồn và sẵn sàng giải thích chi tiết trong buổi vấn đáp.
3. Sử dụng AI làm công cụ hỗ trợ gợi ý cú pháp và tối ưu tốc độ, hoàn toàn làm chủ tư duy thuật toán và logic nghiệp vụ.
