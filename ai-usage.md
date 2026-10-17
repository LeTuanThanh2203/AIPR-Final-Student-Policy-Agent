# BẢNG KHAI BÁO SỬ DỤNG AI (AI USAGE DECLARATION)
**Dự án:** Hệ thống Trợ lý Điểm Rèn luyện & Quản lý Khiếu nại (Đề tài T4 - AIPR Final Project)  
**Nhóm:** 3 Sinh viên

---

## 1. BẢNG TỔNG QUAN THEO THÀNH VIÊN

| STT | Thành viên | Vai trò phụ trách | Công cụ AI | Phạm vi áp dụng chính |
| :---: | :--- | :--- | :--- | :--- |
| 1 | **Ca Ngọc Tân** | **RAG và Data Engineer** | **Antigravity** | **AI hỗ trợ sinh mã nguồn xử lý và phân đoạn văn bản, triển khai Hybrid Search và tích hợp cơ chế Calibration trong RAG Pipeline** |
| 2 | **Lê Tuấn Thành** | **Agent & MCP Architect** | **Claude & GitHub Copilot** | **Hỗ trợ cú pháp Typed Schemas, MCP Server stdio & ReAct Orchestrator** |
| 3 | **Phạm Phước Anh** | **System Integrator & Evaluator** | **Antigravity AI Assistant & ChatGPT** | **Giúp hoàn thiện UI main.py, hỗ trợ hoàn thành unit tests, hỗ trợ cấu trúc đánh giá tự động và chuẩn hóa logger** |


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

#### 📌 Hạng mục 2: Xây dựng MCP Server lưu trữ khiếu nại & Tra cứu quy chế (`src/mcp/server.py`)
* **Tôi hỏi gì:** Cú pháp đăng ký `@mcp.tool()`, kỹ thuật kết nối module RAG vào MCP Server và giữ luồng stdio sạch.
* **AI đã làm gì:** Gợi ý cách khai báo công cụ `lookup_policy(query: str)`, kết nối với VectorStore / RAG Pipeline và cơ chế fallback tìm kiếm BM25 an toàn.
* **Sinh viên tự làm & điều chỉnh:** Đăng ký 3 công cụ (`lookup_policy`, `submit_complaint`, `check_complaint_status`), chuyển hướng toàn bộ log sang `sys.stderr` để giữ sạch luồng stdout cho gói tin JSON-RPC, khởi tạo bộ nhớ đệm `VectorStore` dùng chung, và tự viết logic sinh mã đơn tăng dần `CPL-YYYY-NNNN`.
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

### 🟣 Thành viên C: Phạm Phước Anh — System Integrator & Evaluator

#### 📌 Hạng mục 1: Xây dựng Robust LLM Client & Prompt Loader (`src/llm_client.py`)
* **Tôi hỏi gì:** Hướng dẫn viết hàm Exponential Backoff khi API lỗi mạng và tạo file unit test để kiểm tra tự động mà không tốn chi phí gọi API thật.
* **AI đã làm gì:** 
  * Gợi ý khung thử lại `time.sleep(2 ** attempt)` trong khối `try/except`.
  * **Sinh toàn bộ mã nguồn file kiểm thử `tests/test_llm_client.py`**, sử dụng kỹ thuật giả lập (Mocking với `unittest.mock.MagicMock`) để mô phỏng phản hồi của Groq và tình huống API bị lỗi mạng/rate limit ở lần 1 rồi thành công ở lần 2.
* **Sinh viên tự làm & điều chỉnh:**
  1. Tự thiết kế và cài đặt class `RobustLLMClient` kết nối trực tiếp với Groq API (`from groq import Groq`) và model `openai/gpt-oss-20b` theo đúng kiến thức đã học tại Tuần 2.
  2. Tự viết logic bóc tách token thật (`prompt_tokens`, `completion_tokens`, `total_tokens`) từ đối tượng response của Groq.
  3. Đọc hiểu, làm chủ luồng chạy của file test do AI sinh, chạy lệnh `uv run pytest tests/test_llm_client.py` để xác minh và sẵn sàng giải thích cơ chế Mock khi giảng viên vấn đáp.
  4. Tự bổ sung cơ chế bóc tách mã lỗi HTTP (`status_code`), in log cảnh báo chi tiết theo thời gian thực ở từng lần retry với Exponential Backoff và cấu hình `sys.stdout.reconfigure(encoding="utf-8")` tránh lỗi charmap trên môi trường Windows.
* **Minh chứng:** [`src/llm_client.py`](file:///d:/AIPR-Final-Student-Policy-Agent/src/llm_client.py) và [`tests/test_llm_client.py`](file:///d:/AIPR-Final-Student-Policy-Agent/tests/test_llm_client.py)

---

#### 📌 Hạng mục 2: Xây dựng Session & Usage Logger (`src/utils/logger.py`)
* **Tôi hỏi gì:** Cú pháp sinh file log theo thời gian thực và tạo file unit test để kiểm tra việc ghi log JSON Lines.
* **AI đã làm gì:** 
  * Gợi ý cú pháp định dạng chuỗi `datetime.now().strftime(...)` và cấu trúc lớp `SessionLogger`.
  * **Sinh toàn bộ mã nguồn file kiểm thử `tests/test_logger.py`**, sử dụng thư mục tạm `tempfile.TemporaryDirectory()` để kiểm tra việc ghi, đọc file log JSONL và kiểm tra tính toán chi phí token.
* **Sinh viên tự làm & điều chỉnh:**
  1. Kế thừa trực tiếp bảng giá `PRICING` và công thức tính chi phí từ bài tập Tuần 2, không cần AI sinh phần này.
  2. Bổ sung trường `steps` để lưu vết đầy đủ chuỗi suy luận ReAct theo chuẩn yêu cầu R-01 của đồ án.
  3. Tự đối soát và đồng bộ các tham số của hàm `log_record` để khớp hoàn toàn với lệnh gọi từ bộ điều phối `src/orchestrator.py`.
  4. Đọc hiểu toàn bộ file test do AI sinh, chạy kiểm thử bằng `pytest`, kiểm tra tính toàn vẹn của dữ liệu tiếng Việt UTF-8 và làm chủ mã nguồn để bảo vệ đồ án.
  5. *Bổ sung sửa lỗi (Bug fix):* Khi chạy kiểm thử kết nối với bộ đánh giá, phát hiện lỗi `ImportError: cannot import name 'estimate_cost' from 'src.utils.logger'`. Sinh viên bổ sung thêm hàm `estimate_cost` ở cấp module hỗ trợ linh hoạt cả 2 kiểu đối số truyền vào, giữ nguyên vẹn toàn bộ class `SessionLogger` mà không cần thay thế hay viết lại class.
* **Minh chứng:** [`src/utils/logger.py`](file:///d:/AIPR-Final-Student-Policy-Agent/src/utils/logger.py) và [`tests/test_logger.py`](file:///d:/AIPR-Final-Student-Policy-Agent/tests/test_logger.py)

---

#### 📌 Hạng mục 3: Bộ chạy đánh giá tự động đa tầng (`tests/test_agent.py` cho `make eval` — Mới thêm)
* **Tôi hỏi gì:** Hướng dẫn cấu trúc đánh giá tự động 4 tầng nghiệp vụ (Grounding, Calculation áp trần, Side-Effect Verify R-07, Calibration câu hỏi bẫy) và sinh các test case unit test để kiểm thử logic này.
* **AI đã làm gì:** 
  * Gợi ý cấu trúc bảng tổng kết (Evaluation Summary Table) in ra tỉ lệ phần trăm đạt của từng tầng.
  * **Sinh toàn bộ các hàm kiểm thử đơn vị (`test_evaluate_*`) trong `tests/test_agent.py`** để kiểm tra tự động các kịch bản chấm điểm (khớp trích dẫn Điều, áp trần tính điểm, phát hiện gọi đủ cặp tool nộp và tra cứu đơn, từ chối câu hỏi bẫy).
* **Sinh viên tự làm & điều chỉnh:**
  1. Tự thiết kế và cài đặt logic chấm điểm trong `evaluate_single_query`: kiểm tra trích dẫn số Điều quy chế, số điểm áp trần, đối soát cặp tool theo quy tắc R-07, và tỉ lệ từ chối câu bẫy (mục tiêu >= 80%).
  2. Tự tích hợp `ReActOrchestrator`, `RobustLLMClient` và `SessionLogger` vào hàm `run_evaluation_async` để đọc bộ 16 câu hỏi từ `tests/testset.jsonl`, đo đếm token thực tế và chi phí API.
  3. Trực tiếp chạy và kiểm thử toàn bộ các test cases do AI sinh thông qua `uv run pytest`, chủ động debug xử lý triệt để lỗi môi trường Windows (charmap encoding UTF-8, cấu hình `sys.path`).
* **Minh chứng:** [`tests/test_agent.py`](file:///d:/AIPR-Final-Student-Policy-Agent/tests/test_agent.py)

---

#### 📌 Hạng mục 4: Giao diện dòng lệnh tương tác CLI (`src/main.py` cho `make demo` — Mới thêm)
* **Tôi hỏi gì:** Yêu cầu AI viết hoàn chỉnh mã nguồn giao diện dòng lệnh tương tác (interactive CLI REPL) kết nối toàn bộ hệ thống để chạy lệnh `make demo`.
* **AI đã làm gì:** 
  * **Viết toàn bộ mã nguồn file `src/main.py`**:
    - Khởi tạo và liên kết các module: `RobustLLMClient`, `MCPClientManager` (qua giao thức stdio), `ReActOrchestrator` và `SessionLogger`.
    - Xây dựng vòng lặp REPL `run_interactive_cli()` nhận input từ người dùng, hỗ trợ các lệnh điều khiển phiên (`help`, `tools`, `exit`/`quit`/`q`).
    - Bắt lỗi ngắt chương trình (`KeyboardInterrupt`) để đóng kết nối tiến trình MCP an toàn trước khi thoát.
    - Hiển thị trực quan tiến trình suy luận ReAct từng bước (Think -> Act -> Observe), in câu trả lời cuối cùng, cùng bảng thống kê số bước, lượng token tiêu thụ và chi phí USD ước tính theo thời gian thực.
* **Sinh viên tự làm & điều chỉnh:**
  1. Trực tiếp chạy thử nghiệm tương tác dòng lệnh (`uv run python src/main.py`).
  2. Phát hiện và xử lý lỗi môi trường Windows: giải quyết hiện tượng thư mục `src/mcp` làm che khuất (shadowing) thư viện `mcp` chính thức bằng cách cấu hình lại `sys.path`, đồng thời bổ sung `sys.stdout.reconfigure(encoding="utf-8")` để khắc phục lỗi văng `UnicodeEncodeError (charmap cp1252)`.
* **Minh chứng:** [`src/main.py`](file:///d:/AIPR-Final-Student-Policy-Agent/src/main.py)



---

## 3. CAM KẾT LIÊM CHÍNH HỌC THUẬT

1. Toàn bộ nội dung khai báo trên phản ánh trung thực quá trình làm việc trong dự án.
2. Tự đọc hiểu, làm chủ 100% mã nguồn và sẵn sàng giải thích chi tiết trong buổi vấn đáp.
3. Sử dụng AI làm công cụ hỗ trợ gợi ý cú pháp và tối ưu tốc độ, hoàn toàn làm chủ tư duy thuật toán và logic nghiệp vụ.

