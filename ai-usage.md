# BẢNG KHAI BÁO SỬ DỤNG AI (AI USAGE DECLARATION)
**Dự án:** Hệ thống Trợ lý Điểm Rèn luyện & Quản lý Khiếu nại (Đề tài T4 - AIPR Final Project)  
**Nhóm:** 3 Sinh viên

---

## 1. BẢNG TỔNG QUAN THEO THÀNH VIÊN

| STT | Thành viên | Vai trò phụ trách | Công cụ AI | Phạm vi áp dụng chính |
| :---: | :--- | :--- | :--- | :--- |
| 1 | **Ca Ngọc Tân** | **RAG và Data Engineer** | **Antigravity** | **AI hỗ trợ sinh mã nguồn xử lý và phân đoạn văn bản, triển khai Hybrid Search và tích hợp cơ chế Calibration trong RAG Pipeline** |
| 2 | **Lê Tuấn Thành** | **Agent & MCP Architect** | **Antigravity AI Assistant (Gemini 3.8 Flash High)** | **Typed Schemas (@dataclass) hỗ trợ Policy Versioning (2022 vs 2024), MCP Server stdio (stdout sạch 100%), Dynamic Tool Discovery (mcp SDK), Tool lookup_policy lọc version & Fallback BM25 Okapi, cơ chế cưỡng chế Verify Tầng c (pending_verification_cid), bộ parse Action an toàn 2 tầng (R-06) và ThreadPool async bridge (run_sync). *Vòng lặp ReAct tự viết tay 100%.* |
| 3 | **Phạm Phước Anh** | **System Integrator & Evaluator** | **ChatGPT & Antigravity AI Assistant** | **4 câu hỏi đánh đố bổ sung (Q11-Q14) trong testset và nội dung phản biện thêm vào Prompt do sinh viên tự lên ý tưởng, tự viết và dùng ChatGPT tinh chỉnh câu chữ; AI hỗ trợ sinh mã nguồn kịch bản đánh giá tự động đa tầng (tests/test_agent.py), Exponential Backoff (src/llm_client.py, tests/test_llm_client.py), Session Logger & chi phí USD (src/utils/logger.py, tests/test_logger.py), giao diện CLI Rich tương tác (src/main.py).** |


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

### Thành viên: [Lê Tuấn Thành] — Member B (Agent & MCP Architect)



* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).
  **Vị trí áp dụng:** Toàn bộ file [src/mcp/schemas.py](file:///c:/Users/LENOVO/Desktop/Study/AIPR/AIPR%20Project%20Final/src/mcp/schemas.py) (Dòng 16 đến dòng 191), bao gồm các class `SubmitComplaintInput`, `SubmitComplaintOutput`, `CheckComplaintInput`, `LookupPolicyInput`, `ComplaintRecord`.
* **Prompt chính đã dùng:**
  > *Dựa trên yêu cầu bắt buộc R-03 (PDF 02 §2.3) và bài học Tuần 1, hãy viết các Typed Schemas bằng `@dataclass` Python (nghiêm cấm dùng dict thô để vượt qua kiểm tra `grep -n "@dataclass"`) cho các công cụ MCP đề tài T4: nộp khiếu nại `submit_complaint`, tra cứu trạng thái đơn `check_complaint_status`, và tra cứu quy chế `lookup_policy`. Đặc biệt, `LookupPolicyInput` phải có thêm tham số `version: Optional[str] = "latest"` để phục vụ cơ chế Policy Versioning (chọn bản quy chế mới nhất hoặc chỉ định bản cũ 2022/2024 để so sánh mâu thuẫn chính sách Tầng b). Tích hợp classmethod `model_json_schema` dùng `pydantic.TypeAdapter(cls).json_schema()` theo bài học Tuần 6 để trích xuất JSON Schema cho LLM, đồng thời viết hàm kiểm tra dữ liệu đầu vào không được để trống trong `__post_init__`.*

* **Đoạn code do AI hỗ trợ sinh:**
  ```python
  from dataclasses import asdict, dataclass, field
  from typing import Any, Dict, Optional
  from pydantic import TypeAdapter

  def _require_non_empty(name: str, value: Any) -> str:
      if not isinstance(value, str):
          raise TypeError(f"Trường '{name}' phải là kiểu str, nhận: {type(value).__name__}")
      cleaned = value.strip()
      if not cleaned:
          raise ValueError(f"Trường '{name}' không được để trống.")
      return cleaned

  @dataclass
  class SubmitComplaintInput:
      student_id: str
      category: str
      reason: str
      evidence: str = ""

      def __post_init__(self) -> None:
          self.student_id = _require_non_empty("student_id", self.student_id)
          self.category = _require_non_empty("category", self.category)
          self.reason = _require_non_empty("reason", self.reason)

      def to_dict(self) -> Dict[str, Any]:
          return asdict(self)

      @classmethod
      def model_json_schema(cls) -> Dict[str, Any]:
          return TypeAdapter(cls).json_schema()

  @dataclass
  class LookupPolicyInput:
      query: str
      version: Optional[str] = "latest"

      def __post_init__(self) -> None:
          self.query = _require_non_empty("query", self.query)
          if self.version is None:
              self.version = "latest"
          elif not isinstance(self.version, str):
              raise TypeError(f"Trường 'version' phải là kiểu str, nhận: {type(self.version).__name__}")
          else:
              self.version = self.version.strip() or "latest"

      def to_dict(self) -> Dict[str, Any]:
          return asdict(self)

      @classmethod
      def model_json_schema(cls) -> Dict[str, Any]:
          return TypeAdapter(cls).json_schema()
  ```

* **Tinh chỉnh và hoàn thiện của sinh viên:**
  1. Dùng `pydantic.TypeAdapter(cls).json_schema()` xuất schema động chuẩn OpenAPI cho LLM mà vẫn giữ `@dataclass` thuần để vượt qua kiểm tra R-03 (`grep -n "@dataclass"`).
  2. Tự thiết kế tham số `version: Optional[str] = "latest"` trong `LookupPolicyInput` và kiểm tra kiểu nghiêm ngặt trong `__post_init__`: nếu LLM truyền `None` hoặc khoảng trắng, tự động chuẩn hóa về `"latest"` để ưu tiên quy chế mới nhất (2024), giải quyết bài toán Policy Versioning của Tầng b (PDF 01).
  3. Tự viết hàm `_require_non_empty` chặn triệt để tham số rỗng hoặc sai kiểu từ LLM.
  4. Bổ sung classmethod `from_dict` chống lỗi thiếu trường và tách riêng model CSDL `ComplaintRecord` kèm mốc thời gian UTC ISO 8601.


* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).
  **Vị trí áp dụng:** Khởi tạo `MCPServer`, hàm `log_debug`, `load_complaints`, `save_complaints`, và tool `@mcp.tool() submit_complaint` trong [src/mcp/server.py](file:///c:/Users/LENOVO/Desktop/Study/AIPR/AIPR%20Project%20Final/src/mcp/server.py) (Dòng 41 đến dòng 70 và dòng 150 đến dòng 195).
* **Prompt chính đã dùng:**
  > *Xây dựng MCP Server bằng Python qua giao thức stdio (sử dụng MCPServer theo Tuần 7 và R-08). Thiết lập hàm log_debug chuyển hướng toàn bộ thông báo ra sys.stderr để bảo đảm stdout sạch 100% (không phá vỡ gói tin JSON-RPC stdio). Cài đặt tool Ghi Side-Effect `submit_complaint(student_id, category, reason, evidence)`: kiểm tra tham số bằng Typed Schema SubmitComplaintInput, tự động sinh mã khiếu nại nghiệp vụ tăng dần CPL-YYYY-NNNN theo năm hiện tại, và lưu an toàn vào file data/complaints.json bằng UTF-8.*

* **Đoạn code do AI hỗ trợ sinh:**
  ```python
  from mcp.server.mcpserver import MCPServer
  mcp = MCPServer("aipr-complaints-server")

  def log_debug(message: str) -> None:
      print(f"[MCP-Server] {message}", file=sys.stderr)

  @mcp.tool()
  def submit_complaint(student_id: str, category: str, reason: str, evidence: str = "") -> str:
      try:
          inp = SubmitComplaintInput(student_id=student_id, category=category, reason=reason, evidence=evidence)
      except Exception as err:
          return json.dumps({"status": "error", "message": f"Dữ liệu không hợp lệ: {err}"}, ensure_ascii=False)

      records = load_complaints()
      year = datetime.now(timezone.utc).year
      new_id = f"CPL-{year}-{len(records) + 1:04d}"
      now_iso = datetime.now(timezone.utc).isoformat()
      record = ComplaintRecord(complaint_id=new_id, student_id=inp.student_id, category=inp.category, reason=inp.reason, evidence=inp.evidence, status="pending_review", created_at=now_iso, updated_at=now_iso)
      records.append(record.to_dict())
      save_complaints(records)
      return json.dumps(SubmitComplaintOutput(complaint_id=new_id, status="pending_review", created_at=now_iso).to_dict(), ensure_ascii=False)
  ```

* **Tinh chỉnh và hoàn thiện của sinh viên:**
  1. Chuyển hướng 100% log sang `sys.stderr` qua `log_debug()`, bảo vệ kênh `stdout` sạch tuyệt đối cho gói tin JSON-RPC stdio (R-08).
  2. Thiết kế định dạng mã đơn nghiệp vụ `CPL-YYYY-NNNN` tăng dần theo năm UTC, giúp dễ đọc và thuận tiện đối soát.
  3. Tự động khởi tạo thư mục `data/` nếu chưa có và lưu file JSON với `ensure_ascii=False` để giữ nguyên tiếng Việt có dấu (Tầng c - R-07).


* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).
  **Vị trí áp dụng:** Hàm `get_rag_store`, tool `@mcp.tool() lookup_policy`, và tool `@mcp.tool() check_complaint_status` trong [src/mcp/server.py](file:///c:/Users/LENOVO/Desktop/Study/AIPR/AIPR%20Project%20Final/src/mcp/server.py) (Dòng 78 đến dòng 148 và dòng 197 đến dòng 210).
* **Prompt chính đã dùng:**
  > *Viết tool MCP Đọc `lookup_policy(query: str, version: Optional[str] = "latest")` kết nối trực tiếp với module RAG để tra cứu quy chế điểm rèn luyện (Tầng a, b - R-05), hỗ trợ lọc phiên bản (version: 'latest', '2024', '2022', 'all') và tool `check_complaint_status(complaint_id: str)` để đối soát đơn (Tầng c - R-07). Thiết kế hàm singleton nạp trước toàn bộ 71 chunks quy chế từ data/processed/chunks.json (tự động kích hoạt parse_and_chunk_documents() nếu chưa có file) để không nạp lại đĩa ở mỗi request. Tinh gọn mã nguồn server bằng cách ủy quyền tìm kiếm cho RAG pipeline có tích hợp Fallback BM25 Okapi khi embedding gặp lỗi.*

* **Đoạn code do AI hỗ trợ sinh:**
  ```python
  _rag_store = None
  def get_rag_store():
      global _rag_store
      if _rag_store is not None:
          return _rag_store
      store = VectorStore()
      chunks_path = PROJECT_ROOT / "data" / "processed" / "chunks.json"
      if chunks_path.exists():
          with open(chunks_path, "r", encoding="utf-8") as f:
              for item in json.load(f):
                  c = DocumentChunk.from_dict(item)
                  store.chunks[c.chunk_id] = c
      else:
          from src.rag.document_parser import parse_and_chunk_documents
          for c in parse_and_chunk_documents():
              store.chunks[c.chunk_id] = c
      _rag_store = store
      return _rag_store

  @mcp.tool()
  def lookup_policy(query: str, version: Optional[str] = "latest") -> str:
      try:
          inp = LookupPolicyInput(query=query, version=version)
      except Exception as err:
          return json.dumps({"status": "error", "message": f"Dữ liệu không hợp lệ: {err}"}, ensure_ascii=False)

      try:
          store = get_rag_store()
          from src.rag.rag_pipeline import rag_pipeline
          rag_res = rag_pipeline(inp.query, store, top_k=3, search_mode="hybrid", version=inp.version)
          sources = rag_res.get("sources", [])
          output = {
              "status": "success" if sources else "not_found",
              "query": inp.query,
              "version": inp.version,
              "answer": rag_res.get("answer", ""),
              "sources": sources,
          }
          return json.dumps(output, ensure_ascii=False)
      except Exception as err:
          return json.dumps({"status": "error", "message": f"Lỗi tra cứu: {err}"}, ensure_ascii=False)

  @mcp.tool()
  def check_complaint_status(complaint_id: str) -> str:
      search_id = complaint_id.strip().upper()
      for rec in load_complaints():
          if str(rec.get("complaint_id", "")).strip().upper() == search_id:
              return json.dumps(rec, ensure_ascii=False)
      return json.dumps({"status": "not_found", "complaint_id": search_id}, ensure_ascii=False)
  ```

* **Tinh chỉnh và hoàn thiện của sinh viên:**
  1. Tích hợp Policy Versioning vào Tool Contract: Cho phép Agent tự động chọn bản mới nhất (`'latest'` -> 2024) hoặc chỉ định rõ `'2022'`, `'2024'`, `'all'` để giải quyết bài toán so sánh mâu thuẫn điểm áp trần NCKH (10đ ở bản 2022 vs 15đ ở bản 2024) hoặc điều kiện GPA < 2.0 (Tầng b - R-05).
  2. Tinh gọn mã nguồn MCP Server: Ủy quyền việc tìm kiếm và lọc phiên bản xuống `rag_pipeline` (tái dùng hàm `filter_chunks_by_version` và BM25 Okapi Fallback), loại bỏ hơn 40 dòng code trùng lặp, giữ MCP Server chuẩn mực và nhẹ nhàng.
  3. Nạp trước 71 chunks từ cả 3 tài liệu quy chế vào RAM qua Singleton `get_rag_store()`, tự động gọi parser tái sinh dữ liệu nếu đĩa chưa có `chunks.json`.
  4. Chuẩn hóa metadata `sources` trả về kèm `version` và `version_year` làm bằng chứng Grounding phục vụ trích dẫn minh bạch (Tầng a).


* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).
  **Vị trí áp dụng:** Toàn bộ file [src/mcp/client.py](file:///c:/Users/LENOVO/Desktop/Study/AIPR/AIPR%20Project%20Final/src/mcp/client.py) (Dòng 1 đến dòng 123) và [src/mcp/\_\_init\_\_.py](file:///c:/Users/LENOVO/Desktop/Study/AIPR/AIPR%20Project%20Final/src/mcp/__init__.py).
* **Prompt chính đã dùng:**
  > *Viết class MCPClientManager trong Python để kết nối với MCP Server qua subprocess stdio sử dụng StdioServerParameters của mcp SDK chính thức. Cài đặt hàm list_tools() khám phá công cụ động Dynamic Discovery (R-08) và hàm call_tool() thực thi. Đặc biệt, giải quyết triệt để lỗi Module Shadowing hiểm hóc trên Windows khi thư mục chứa mã nguồn là src/mcp làm trùng tên với thư viện mcp cài từ uv/pip, đồng thời xử lý bóc tách khối nội dung TextContent từ CallToolResult.*

* **Đoạn code do AI hỗ trợ sinh:**
  ```python
  import sys
  from pathlib import Path
  _src_dir = Path(__file__).resolve().parent.parent
  sys.path = [p for p in sys.path if Path(p).resolve() != _src_dir and p != "src"]

  from mcp import Client
  from mcp.client.stdio import StdioServerParameters

  class MCPClientManager:
      def __init__(self, server_script: Optional[str] = None, command: str = "uv", args: Optional[List[str]] = None):
          self.server_params = StdioServerParameters(command=command, args=args or ["run", server_script], env=dict(os.environ))
          self.client: Optional[Client] = None

      async def list_tools(self) -> List[Any]:
          if self.client is None: await self.connect()
          res = await self.client.list_tools()
          return res.tools if hasattr(res, "tools") else (res if isinstance(res, list) else [])

      async def call_tool(self, name: str, arguments: Dict[str, Any]) -> ToolCallResult:
          res = await self.client.call_tool(name, arguments)
          parts = [c.text for c in res.content if hasattr(c, "text")]
          return ToolCallResult(tool_name=name, is_error=getattr(res, "is_error", False), content="\n".join(parts))
  ```

* **Tinh chỉnh và hoàn thiện của sinh viên:**
  1. Xử lý triệt để lỗi Module Shadowing trên Windows bằng cách lọc `src` khỏi `sys.path` trước khi import thư viện `mcp`.
  2. Hiện thực hóa Dynamic Discovery qua `client.list_tools()`, không fix cứng danh sách công cụ trong code hay prompt (R-08).
  3. Bóc tách thuộc tính `.text` từ các block `TextContent` và quản lý tiến trình subprocess an toàn qua `__aenter__`/`__aexit__`.


* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).
  **Vị trí áp dụng:** Hàm `parse_reply` trong [src/orchestrator.py](file:///c:/Users/LENOVO/Desktop/Study/AIPR/AIPR%20Project%20Final/src/orchestrator.py) (Dòng 62 đến dòng 112).
* **Prompt chính đã dùng:**
  > *Viết hàm parse_reply(reply: str) trong Python để bóc tách phản hồi đa định dạng từ LLM trong ReAct Orchestrator. Hỗ trợ nhận diện cả 2 định dạng: (1) Khối JSON chuẩn bọc trong ```json {...}``` có trường action ('final_answer' hoặc 'call_tool'); (2) Fallback Regex cho cú pháp text chuẩn Tuần 6 'Action: tool_name(args)' và 'Final Answer: ...'. Bắt toàn bộ ngoại lệ lỗi cú pháp, trả về tuple ('unknown', error_msg) để vòng lặp ReAct thực hiện cơ chế bắt lỗi mềm (R-06) mà không bị crash.*

* **Đoạn code do AI hỗ trợ sinh:**
  ```python
  def parse_reply(reply: str) -> Tuple[str, Any]:
      cleaned = (reply or "").strip()
      if not cleaned: return "unknown", "LLM trả về phản hồi rỗng."

      # Cách 1: Parse JSON bọc trong ```json hoặc { }
      match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
      candidate = match.group(1).strip() if match else cleaned
      first, last = candidate.find("{"), candidate.rfind("}")
      if first != -1 and last > first:
          candidate = candidate[first:last + 1]

      try:
          data = json.loads(candidate)
          if isinstance(data, dict):
              action = data.get("action")
              if action == "final_answer":
                  return "final", str(data.get("final_answer", "")).strip()
              elif action == "call_tool":
                  tool_name = str(data.get("tool_name") or data.get("tool") or "").strip()
                  tool_args = data.get("tool_args") or data.get("args") or {}
                  if tool_name:
                      return "action", (tool_name, tool_args if isinstance(tool_args, dict) else {})
      except Exception:
          pass

      # Cách 2: Fallback Regex chuẩn bài tập W6
      final_match = re.search(r"Final Answer:\s*(.+)", cleaned, flags=re.IGNORECASE | re.DOTALL)
      if final_match: return "final", final_match.group(1).strip()
      action_match = re.search(r"Action:\s*(\w+)\s*\((.*)\)", cleaned, flags=re.IGNORECASE)
      if action_match:
          t_name, arg_str = action_match.group(1).strip(), action_match.group(2).strip()
          try: t_args = json.loads(arg_str) if arg_str.startswith("{") else {"query": arg_str}
          except Exception: t_args = {"query": arg_str} if arg_str else {}
          return "action", (t_name, t_args)

      return "unknown", "Không tìm thấy khối JSON hợp lệ hoặc cấu trúc Action/Final Answer."
  ```

* **Tinh chỉnh và hoàn thiện của sinh viên:**
  1. Thiết kế cơ chế Fallback 2 tầng (JSON-first, Regex-second), giúp hệ thống tương thích linh hoạt với nhiều dòng mô hình LLM khác nhau.
  2. Bổ sung trích xuất chuỗi con giữa `{` đầu tiên và `}` cuối cùng để lọc bỏ các đoạn text giải thích thừa của LLM trước khi parse JSON.
  3. Chuẩn hóa kết quả trả về thành tuple tường minh `('final', text)`, `('action', (name, args))`, hoặc `('unknown', msg)` giúp luồng điều phối xử lý dễ dàng.


* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).
  **Vị trí áp dụng:** Bộ kiểm soát State Machine `pending_verification_cid` và kiểm định Verify R-07 trong hàm `react_agent` thuộc [src/orchestrator.py](file:///c:/Users/LENOVO/Desktop/Study/AIPR/AIPR%20Project%20Final/src/orchestrator.py) (Dòng 219 đến 220, dòng 246 đến 259, và dòng 276 đến 284).
* **Prompt chính đã dùng:**
  > *Trong vòng lặp ReAct Agent đề tài T4, LLM sau khi gọi tool ghi khiếu nại `submit_complaint` thường vội vàng đưa ra Final Answer cho người dùng mà không gọi lại tool đọc `check_complaint_status` để kiểm chứng dữ liệu đã ghi thật (vi phạm nghiêm ngặt tiêu chí Tầng c và R-07 trong PDF 01/02). Hãy gợi ý cơ chế State Machine bằng biến cờ trong vòng lặp: khi tool ghi trả về mã đơn CPL-xxx, ghi nhớ mã này; nếu LLM muốn kết luận Final Answer trong khi chưa verify, lập tức chặn lại và gửi Observation cưỡng chế ép LLM phải gọi tool đọc xác minh.*

* **Đoạn code do AI hỗ trợ sinh:**
  ```python
  pending_verification_cid: Optional[str] = None
  verified = False

  for step_idx in range(1, max_steps + 1):
      # ...
      kind, payload = parse_reply(raw_output)

      if kind == "final":
          # Kiểm định R-07: Nếu vừa ghi đơn mà chưa xác minh lại thì BẮT BUỘC gọi tool đọc
          if pending_verification_cid:
              step.error = "Chưa verify đơn theo R-07"
              steps.append(step)
              messages.append({"role": "assistant", "content": raw_output})
              messages.append({
                  "role": "user",
                  "content": (
                      f"Observation: Error: Theo quy định R-07, bạn vừa tạo đơn {pending_verification_cid}. "
                      "BẮT BUỘC bạn phải gọi tool đọc 'check_complaint_status' với mã này để xác minh trước khi kết luận."
                  ),
              })
              continue

          final_answer = str(payload)
          break

      elif kind == "action":
          tool_name, tool_args = payload
          obs = await run_action(tool_name, tool_args, mcp_client)

          # R-07: Theo dõi trạng thái Verify khi nộp khiếu nại
          if tool_name == "submit_complaint":
              cid_match = re.search(r"CPL-\d{4}-\d{4}", obs)
              if cid_match:
                  pending_verification_cid = cid_match.group(0)
          elif tool_name == "check_complaint_status":
              pending_verification_cid = None
              verified = True
  ```

* **Tinh chỉnh và hoàn thiện của sinh viên:**
  1. Xây dựng regex trích xuất chính xác mã đơn chuẩn `CPL-\d{4}-\d{4}` từ kết quả phản hồi của MCP Server để nạp vào biến trạng thái `pending_verification_cid`.
  2. Bắt lỗi mềm bằng cơ chế can thiệp ngữ cảnh: Chặn đứng ý định trả lời sớm của LLM, đưa phản hồi `Observation: Error: ...` để LLM tự giác quay lại chu trình suy luận gọi `check_complaint_status`, bảo đảm 100% không làm gãy luồng hội thoại.
  3. Cập nhật cờ `verified = True` trả về cho bộ đánh giá `make eval` (test_agent.py) và `SessionLogger`, chứng minh hệ thống đạt tiêu chí "Hành động có kiểm chứng" của Tầng (c).


* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).
  **Vị trí áp dụng:** Class `AgentStep` và hàm `run_action` trong [src/orchestrator.py](file:///c:/Users/LENOVO/Desktop/Study/AIPR/AIPR%20Project%20Final/src/orchestrator.py) (Dòng 28 đến dòng 37 và dòng 127 đến dòng 148).
* **Prompt chính đã dùng:**
  > *Viết dataclass AgentStep để mô hình hóa từng bước suy luận của ReAct Agent (step_number, thought, action, tool_name, tool_args, observation, error, raw_response). Đồng thời viết hàm run_action(name, argument, mcp_client) để bọc lệnh gọi MCP Client: tự động chuẩn hóa đối số đầu vào (cho phép cả chuỗi JSON string hoặc dict) và bắt lỗi mềm trả về chuỗi str thông báo lỗi để không làm sập chương trình khi công cụ ném ngoại lệ (R-06).*

* **Đoạn code do AI hỗ trợ sinh:**
  ```python
  @dataclass
  class AgentStep:
      step_number: int
      thought: str = ""
      action: str = ""
      tool_name: Optional[str] = None
      tool_args: Optional[Dict[str, Any]] = None
      observation: Optional[str] = None
      error: Optional[str] = None
      raw_response: str = ""

  async def run_action(name: str, argument: Union[Dict[str, Any], str], mcp_client: Any) -> str:
      if not mcp_client:
          return f"Error: Chưa kết nối MCP Client để thực thi công cụ '{name}'."
      if isinstance(argument, str):
          try: args_dict = json.loads(argument)
          except Exception: args_dict = {"query": argument} if argument else {}
      elif isinstance(argument, dict): args_dict = argument
      else: args_dict = {}

      try:
          res = await mcp_client.call_tool(name, args_dict)
          return res.content if hasattr(res, "content") else str(res)
      except Exception as err:
          return f"Error khi gọi tool '{name}': {err}"
  ```

* **Tinh chỉnh và hoàn thiện của sinh viên:**
  1. Tự động ép kiểu chuỗi JSON sang dict trong `run_action`, khắc phục tình trạng LLM đôi khi truyền tham số dưới dạng chuỗi string bị escape.
  2. Bắt lỗi mềm mọi ngoại lệ từ MCP Client, luôn bảo đảm trả về kiểu chuỗi `str` cho `observation` để không bao giờ ngắt quãng vòng lặp ReAct.
  3. Định nghĩa dataclass `AgentStep` tinh gọn phục vụ trích xuất dữ liệu cho `SessionLogger` và file báo cáo đồ án.


* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).
  **Vị trí áp dụng:** Hàm `format_tools_description` và hàm `run_sync` trong [src/orchestrator.py](file:///c:/Users/LENOVO/Desktop/Study/AIPR/AIPR%20Project%20Final/src/orchestrator.py) (Dòng 42 đến dòng 56 và dòng 166 đến dòng 178).
* **Prompt chính đã dùng:**
  > *Viết hàm tiện ích format_tools_description(tools) để chuyển đổi danh sách schema công cụ từ MCP Client thành định dạng Markdown chèn vào biến {tools_description} của System Prompt (R-04, R-08). Đồng thời viết hàm run_sync(coro) sử dụng concurrent.futures.ThreadPoolExecutor để chạy an toàn coroutine bất đồng bộ từ hàm đồng bộ mà không bị xung đột RuntimeError: This event loop is already running khi chạy trong pytest hoặc CLI.*

* **Đoạn code do AI hỗ trợ sinh:**
  ```python
  def format_tools_description(tools: List[Any]) -> str:
      if not tools: return "Hiện tại không có công cụ nào khả dụng."
      descriptions = []
      for tool in tools:
          name = getattr(tool, "name", str(tool))
          desc = getattr(tool, "description", "")
          schema = getattr(tool, "input_schema", getattr(tool, "inputSchema", {}))
          descriptions.append(f"- Tool: `{name}`\n  Mô tả: {desc}\n  Tham số (Schema): {json.dumps(schema, ensure_ascii=False)}")
      return "\n\n".join(descriptions)

  def run_sync(coro: Any) -> Any:
      try: loop = asyncio.get_running_loop()
      except RuntimeError: loop = None
      if loop and loop.is_running():
          with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
              return executor.submit(asyncio.run, coro).result()
      return asyncio.run(coro)
  ```

* **Tinh chỉnh và hoàn thiện của sinh viên:**
  1. Tự viết hàm `run_sync` bằng `ThreadPoolExecutor(max_workers=1)` giải quyết triệt để lỗi xung đột event loop lồng nhau khi gọi hàm async từ môi trường sync.
  2. Tự động kiểm tra thuộc tính linh hoạt (`input_schema` hoặc `inputSchema`) từ đối tượng Tool của MCP SDK và tuần tự hóa sang JSON UTF-8 cho System Prompt.
  3. Đảm bảo toàn bộ prompt được nạp tách rời mã nguồn từ file ngoài `prompts/system_react.txt` (đáp ứng nghiêm ngặt R-04).


---

### Thành viên: [Phạm Phước Anh - 24110075] — Member C (System Integrator & Evaluator)

* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).  
  **Vị trí áp dụng:** Class `RobustLLMClient` trong [./AIPR-Final-Student-Policy-Agent/src/llm_client.py](./AIPR-Final-Student-Policy-Agent/src/llm_client.py) (Dòng 58 đến dòng 94) và file unit test [./AIPR-Final-Student-Policy-Agent/tests/test_llm_client.py](./AIPR-Final-Student-Policy-Agent/tests/test_llm_client.py) (Dòng 1 đến dòng 83).
* **Prompt chính đã dùng:**  
  > *Viết class RobustLLMClient bọc Groq API (mô hình qwen/qwen3.8-27b), tích hợp cơ chế tự động thử lại Exponential Backoff time.sleep(2 ** attempt) khi gặp sự cố mạng hoặc lỗi rate limit (R-04, Tuần 2). Trích xuất chính xác token thật (prompt_tokens, completion_tokens, total_tokens) từ response và viết bộ unit test hoàn chỉnh (tests/test_llm_client.py) bằng unittest.mock.MagicMock để kiểm thử tự động: (1) Nạp prompt ngoài; (2) Trích xuất token usage không tốn tiền API thật; (3) Tự động thử lại khi mock API ném lỗi.*

* **Đoạn code do AI hỗ trợ sinh:**  
  ```python
  # --- Trích đoạn triển khai class RobustLLMClient (src/llm_client.py) ---
  class RobustLLMClient:
      def __init__(self, model: str = DEFAULT_MODEL, max_retries: int = 3, timeout: int = 30, client: Optional[Any] = None):
          self.model = os.getenv("MODEL") or model
          self.max_retries = max_retries
          self.timeout = timeout
          self.client = client if client is not None else Groq(api_key=os.getenv("GROQ_API_KEY") or "gsk-dummy")

      def generate(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
          for attempt in range(self.max_retries):
              try:
                  response = self.client.chat.completions.create(model=self.model, messages=messages, timeout=self.timeout)
                  return {
                      "content": response.choices[0].message.content or "",
                      "usage": {
                          "prompt_tokens": response.usage.prompt_tokens,
                          "completion_tokens": response.usage.completion_tokens,
                          "total_tokens": response.usage.total_tokens,
                      },
                  }
              except Exception as e:
                  if attempt == self.max_retries - 1: raise e
                  time.sleep(2 ** attempt)

  # --- Trích đoạn bộ kiểm thử Mocking (tests/test_llm_client.py) ---
  def test_robust_client_generate_success():
      mock_client = MagicMock()
      mock_response = MagicMock()
      mock_choice = MagicMock()
      mock_choice.message.content = "Xin chào, tôi là Trợ lý AI."
      mock_response.choices = [mock_choice]
      mock_response.usage.prompt_tokens = 25
      mock_response.usage.completion_tokens = 10
      mock_response.usage.total_tokens = 35
      mock_client.chat.completions.create.return_value = mock_response

      client = RobustLLMClient(client=mock_client)
      res = client.generate([{"role": "user", "content": "Alo"}])
      assert res["content"] == "Xin chào, tôi là Trợ lý AI."
      assert res["usage"]["prompt_tokens"] == 25
      assert res["usage"]["total_tokens"] == 35

  def test_robust_client_retry_on_error():
      mock_client = MagicMock()
      mock_response = MagicMock()
      mock_response.choices = [MagicMock(message=MagicMock(content="Đã thử lại thành công!"))]
      mock_response.usage.prompt_tokens = 15
      mock_response.usage.completion_tokens = 5
      mock_response.usage.total_tokens = 20

      mock_client.chat.completions.create.side_effect = [
          Exception("Rate limit / Network error"),
          mock_response,
      ]
      client = RobustLLMClient(client=mock_client, max_retries=2)
      res = client.generate([{"role": "user", "content": "Test retry"}])
      assert res["content"] == "Đã thử lại thành công!"
      assert mock_client.chat.completions.create.call_count == 2
  ```

* **Tinh chỉnh và hoàn thiện của sinh viên:**  
  1. Tự thiết kế và cài đặt kết nối Groq API linh hoạt qua biến môi trường `MODEL` và `GROQ_API_KEY`.
  2. Bổ sung cơ chế bóc tách mã lỗi HTTP (`status_code`), in log cảnh báo retry chi tiết thời gian thực và cấu hình `sys.stdout.reconfigure(encoding="utf-8")` tránh lỗi charmap trên Windows.
  3. Làm chủ mã nguồn file test giả lập Mocking, chạy lệnh `uv run pytest tests/test_llm_client.py` xác minh 100% test pass (3/3 test cases).


* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).  
  **Vị trí áp dụng:** Bộ kiểm thử đơn vị [./AIPR-Final-Student-Policy-Agent/tests/test_logger.py](./AIPR-Final-Student-Policy-Agent/tests/test_logger.py) (Dòng 1 đến dòng 79) và hướng dẫn mở rộng lưu vết ReAct trong [./AIPR-Final-Student-Policy-Agent/src/utils/logger.py](./AIPR-Final-Student-Policy-Agent/src/utils/logger.py).
* **Prompt chính đã dùng:**  
  > *Module SessionLogger và bảng giá PRICING đã có sẵn nền tảng từ bài tập thực hành Tuần 2. Hãy hướng dẫn cách mở rộng hàm log_record để lưu thêm chuỗi suy luận steps của ReAct Orchestrator, và sinh toàn bộ mã nguồn file unit test (tests/test_logger.py) bằng pytest và tempfile: kiểm tra khởi tạo file log JSONL, kiểm tra công thức tính chi phí USD estimate_cost theo bảng giá Tuần 2, và kiểm tra tính toàn vẹn của dữ liệu UTF-8 tiếng Việt có dấu.*

* **Đoạn code do AI hỗ trợ sinh (Toàn bộ file unit test tests/test_logger.py):**  
  ```python
  # --- Bộ kiểm thử đơn vị do AI sinh hoàn chỉnh (tests/test_logger.py) ---
  def test_estimate_cost_calculation():
      """Kiểm tra công thức tính chi phí token theo bảng giá của model ở Tuần 2."""
      with tempfile.TemporaryDirectory() as tmpdir:
          logger = SessionLogger(log_dir=tmpdir)
          # Giả sử 1.000.000 input tokens (0.15$) và 1.000.000 output tokens (0.30$)
          cost = logger.estimate_cost(1_000_000, 1_000_000, model="openai/gpt-oss-20b")
          assert round(cost, 2) == 0.45

  def test_log_record_content_and_utf8_encoding():
      """Kiểm tra ghi log đầy đủ các trường và giữ nguyên định dạng tiếng Việt có dấu."""
      with tempfile.TemporaryDirectory() as tmpdir:
          logger = SessionLogger(log_dir=tmpdir, session_file="test_run.jsonl")
          mock_steps = [
              {"step_number": 1, "thought": "Cần tra cứu quy chế", "action": "call_tool", "tool_name": "lookup"},
              {"step_number": 2, "thought": "Đã có thông tin", "action": "final_answer", "observation": "[Done]"},
          ]
          mock_usage = {"calls": 2, "prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

          record = logger.log_record(
              query_id="Q01",
              user_query="Quy chế điểm rèn luyện năm 2024?",
              steps=mock_steps,
              usage=mock_usage,
              final_answer="Điểm tối đa là 100 điểm.",
          )
          assert os.path.exists(logger.log_file)
          with open(logger.log_file, "r", encoding="utf-8") as f:
              lines = [json.loads(line) for line in f if line.strip()]
          assert len(lines) == 1
          logged_data = lines[0]
          assert logged_data["query_id"] == "Q01"
          assert logged_data["user_query"] == "Quy chế điểm rèn luyện năm 2024?"
          assert logged_data["final_answer"] == "Điểm tối đa là 100 điểm."
          assert len(logged_data["steps"]) == 2
          assert logged_data["usage"]["total_tokens"] == 150
          assert logged_data["cost_estimate_usd"] > 0
  ```

* **Tinh chỉnh và hoàn thiện của sinh viên:**  
  1. Kế thừa trực tiếp 100% kiến trúc `SessionLogger` và bảng giá `PRICING` từ bài tập thực hành Tuần 2; tự tay cài đặt hàm `estimate_cost` ở cấp module hỗ trợ linh hoạt cả 2 kiểu thứ tự đối số (tương thích ngược hoàn hảo).
  2. Tự thiết kế việc kết nối và đồng bộ dữ liệu giữa `ReActOrchestrator` và `SessionLogger` để tự động thu thập chuỗi suy luận ReAct và token usage từ API thật.
  3. Tiếp nhận toàn bộ mã nguồn file unit test do AI sinh, rà soát logic kiểm thử, sửa lỗi đường dẫn import và cấu hình môi trường bảo đảm chạy 100% test pass (3/3 test cases trong `tests/test_logger.py`).


* **Công cụ sử dụng:** ChatGPT (tinh chỉnh câu chữ 4 câu hỏi kiểm thử và nội dung bổ sung trong Prompt) & Antigravity AI Assistant (hỗ trợ sinh mã nguồn kịch bản đánh giá `tests/test_agent.py`).  
  **Vị trí áp dụng:** 
  - 4 câu hỏi đánh đố/kiểm chứng ngộ nhận bổ sung (Q11 đến Q14) trong [./AIPR-Final-Student-Policy-Agent/tests/testset.jsonl](./AIPR-Final-Student-Policy-Agent/tests/testset.jsonl).
  - Nội dung quy tắc tư duy phản biện bổ sung ở Mục 2 trong [./AIPR-Final-Student-Policy-Agent/prompts/system_react.txt](./AIPR-Final-Student-Policy-Agent/prompts/system_react.txt).
  - Kịch bản đánh giá tự động đa tầng trong [./AIPR-Final-Student-Policy-Agent/tests/test_agent.py](./AIPR-Final-Student-Policy-Agent/tests/test_agent.py).
* **Quy trình phối hợp giữa Sinh viên và AI:**
  1. **Về phần 4 câu hỏi đánh đố (`tests/testset.jsonl`) và nội dung bổ sung vào Prompt (`prompts/system_react.txt`):**
     - **Sinh viên tự lên ý tưởng và tự viết:** Sinh viên tự nghĩ ra 4 tình huống đánh đố thực tế (sinh viên nhớ sai Điều 10, sinh viên đòi cộng điểm rớt môn, sinh viên ngộ nhận 88đ là chắc chắn loại Tốt dù chưa rõ GPA theo Điều 11, và thắc mắc nâng điểm hiến máu 3đ lên 5đ giữa 2 quy chế). Đồng thời sinh viên tự soạn các quy tắc tư duy phản biện (chống ba phải/nịnh người dùng, bắt buộc kiểm chứng số Điều, áp trần và xét Điều 11) để bổ sung vào System Prompt.
     - **ChatGPT hỗ trợ tinh chỉnh câu chữ:** Sinh viên dùng ChatGPT để trau chuốt lại câu chữ, kiểm tra chính tả và chuẩn hóa hành văn tiếng Việt tự nhiên cho 4 câu hỏi và nội dung bổ sung vào Prompt.
  2. **Về phần Script đánh giá tự động (`tests/test_agent.py`):**
     - **Sinh viên đặt đề bài:** Nêu rõ các yêu cầu về logic chấm điểm 4 tầng (Grounding, Calculation caps, Side-effect Verify R-07, Calibration Rate $\ge 80\%$, và chấm đúng các ca phản biện/đánh đố).
     - **AI hỗ trợ sinh mã nguồn:** AI được nhờ giải quyết các vấn đề kỹ thuật liên quan trong `tests/test_agent.py`: viết regex bóc tách kết quả sau dấu `=`, bóc tách danh sách Điều/Khoản, kiểm tra cặp tool `submit_complaint` và `check_complaint_status`, điều phối bất đồng bộ `async/await` gửi lần lượt câu hỏi vào `ReActOrchestrator`, đo đếm token usage tích lũy từ API và in bảng tổng kết Evaluation Summary Table.
* **Prompt chính đã dùng với AI hỗ trợ code:**  
  > *Viết script đánh giá tự động toàn diện hệ thống (make eval) đọc tập câu hỏi từ tests/testset.jsonl. Thiết kế logic chấm điểm 4 tầng nghiệp vụ: Grounding accuracy (trích dẫn Điều/Khoản và văn bản quy chế), Calculation accuracy (áp trần điểm số theo công thức Min(a+b, Cap), nhận diện thiếu dữ liệu, đính chính câu hỏi đánh đố nhớ sai số Điều, tổng hợp ràng buộc Điều 11), Tool Side-Effect Verify (R-07 kiểm tra đủ cặp tool submit_complaint và check_complaint_status), và Calibration Rate (tỉ lệ từ chối câu hỏi bẫy ngoài quy chế >= 80%). Đồng thời viết hàm run_evaluation_async tích hợp SessionLogger và xuất bảng tổng kết Evaluation Summary Table in ra console.*

* **Đoạn code do AI hỗ trợ sinh (tests/test_agent.py):**  
  ```python
  # --- Logic chấm điểm 4 tầng nghiệp vụ do AI hỗ trợ sinh mã nguồn (tests/test_agent.py) ---
  REFUSAL_KEYWORDS = ["không có", "từ chối", "ngoài phạm vi", "không quy định", "không thể xác định"]

  def evaluate_single_query(test_item: Dict[str, Any], agent_response: Dict[str, Any]) -> Dict[str, Any]:
      final_answer = (agent_response.get("final_answer") or "").strip().lower()
      steps = agent_response.get("steps") or []
      tier = test_item.get("tier", "unknown")
      item_type = test_item.get("type", "")

      passed = False
      # Nhóm 1: Kiểm tra Calibration trên câu hỏi bẫy ngoài quy chế
      if test_item.get("no_answer", False) or tier == "calibration":
          passed = any(kw in final_answer for kw in REFUSAL_KEYWORDS)
      # Nhóm 2: Kiểm tra Tầng a - Tra cứu thông tin có căn cứ (Grounding Accuracy)
      elif tier == "a_lookup":
          dieu_list = [d.strip() for d in str(test_item.get("expected_dieu", "")).split(",") if d.strip()]
          has_dieu = any(f"điều {d}" in final_answer or f"điều {d}" in str(steps).lower() for d in dieu_list)
          has_doc = any(v in final_answer or v in str(steps).lower() for v in ["htrl", "quy chế", "quy định"])
          passed = has_dieu and has_doc
      # Nhóm 3: Kiểm tra Tầng b - Tính toán áp trần, phát hiện xung đột, phản biện đánh đố
      elif tier == "b_transform":
          if item_type == "calculation_caps":
              match = re.search(r"=\s*(\d+)", str(test_item.get("expected_calculation", "")))
              expected_num = match.group(1) if match else ""
              passed = expected_num in final_answer if expected_num else True
          elif item_type == "missing_data_refusal":
              passed = any(kw in final_answer for kw in ["thiếu", "không đủ", "chưa đủ", "cần thêm"])
          elif item_type == "adversarial_fact_check":
              passed = any(kw in final_answer for kw in ["không đúng", "nhớ sai", "điều 10", "tiêu chí", "không có quy định"])
          elif item_type == "multi_doc_synthesis":
              passed = any(kw in final_answer for kw in ["điều 11", "gpa", "2.0", "khá", "kỷ luật"])
          else:
              passed = any(kw in final_answer for kw in ["2024", "mới nhất", "thay đổi", "nâng lên", "không nhầm"])
      # Nhóm 4: Kiểm tra Tầng c - Tác vụ ghi có tác dụng phụ và bắt buộc xác minh (R-07)
      elif tier == "c_action":
          called_tools = [s.get("tool_name") for s in steps if isinstance(s, dict) and s.get("tool_name")]
          passed = ("submit_complaint" in called_tools) and ("check_complaint_status" in called_tools)

      return {"id": test_item.get("id"), "tier": tier, "passed": passed}
  ```

* **Tinh chỉnh và hoàn thiện của sinh viên:**  
  1. Tự thiết kế ý tưởng 4 câu hỏi đánh đố (Q11-Q14) và dùng ChatGPT tinh chỉnh câu chữ, bổ sung vào `tests/testset.jsonl` và `prompts/system_react.txt`, đạt kết quả tuyệt đối **100.0%** trên `make eval`.
  2. Bổ sung danh sách 12 từ khóa từ chối lịch sự trong `REFUSAL_KEYWORDS`, chặn đứng hiện tượng ảo giác (hallucination) trên các câu hỏi bẫy (đạt 4/4 câu calibration).
  3. Trực tiếp rà soát toàn bộ code do AI hỗ trợ trong `tests/test_agent.py`, tự tay viết thêm các hàm unit tests độc lập (`test_evaluate_*`) để kiểm thử tính chính xác của hàm chấm điểm trước khi chạy benchmark.
  4. Tích hợp `SessionLogger` tự động lưu toàn bộ lượt chạy đánh giá thành file log độc lập `logs/run_*.jsonl`, in bảng Rich Table tổng kết chi phí và token rõ ràng.




* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).  
  **Vị trí áp dụng:** Giao diện dòng lệnh tương tác REPL và các hàm hiển thị bảng điều khiển trong [./AIPR-Final-Student-Policy-Agent/src/main.py](./AIPR-Final-Student-Policy-Agent/src/main.py) (Dòng 1 đến dòng 262).
* **Prompt chính đã dùng:**  
  > *Viết giao diện dòng lệnh tương tác CLI REPL (make demo) bằng thư viện Rich cho hệ thống Trợ lý Điểm Rèn luyện T4. Khởi tạo và kết nối RobustLLMClient, MCPClientManager (stdio), ReActOrchestrator và SessionLogger. Hiển thị Panel giới thiệu đẹp mắt (render_banner), bảng câu hỏi mẫu 4 tầng nghiệp vụ (render_help), hiển thị công cụ (render_tools), in tiến trình suy luận ReAct từng bước (Table các bước Think -> Act -> Observe) và in bảng thống kê Usage token/chi phí theo thời gian thực. Xử lý triệt để lỗi môi trường Windows với sys.stdout.reconfigure và KeyboardInterrupt an toàn.*

* **Đoạn code do AI hỗ trợ sinh:**  
  ```python
  # --- Cấu hình tương thích môi trường Windows & sys.path (src/main.py) ---
  if hasattr(sys.stdout, "reconfigure"):
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
      sys.stderr.reconfigure(encoding="utf-8", errors="replace")

  PROJECT_ROOT = Path(__file__).resolve().parent.parent
  src_dir_path = (PROJECT_ROOT / "src").resolve()
  sys.path = [p for p in sys.path if Path(p).resolve() != src_dir_path and p != "src"]

  # --- Giao diện dòng lệnh tương tác CLI REPL với Rich UI ---
  async def run_interactive_cli() -> None:
      render_banner()
      llm_client = RobustLLMClient()
      logger = SessionLogger(log_dir="logs")
      mcp_manager = MCPClientManager()
      await mcp_manager.connect()

      orchestrator = ReActOrchestrator(llm_client=llm_client, mcp_client=mcp_manager, logger=logger, max_steps=10)
      try:
          while True:
              try:
                  user_input = console.input("[bold green]Sinh viên[/bold green] [bold cyan]>[/bold cyan] ").strip()
              except (KeyboardInterrupt, EOFError):
                  break
              if not user_input: continue
              if user_input.lower() in ["exit", "quit", "q"]: break
              if user_input.lower() == "help": render_help(); continue
              if user_input.lower() == "tools": await render_tools(mcp_manager); continue

              res = await orchestrator.arun(user_input, return_details=True)
              steps = res.get("steps") or []
              if steps:
                  step_table = Table(title=f"⚡ TIẾN TRÌNH SUY LUẬN REACT ({len(steps)} BƯỚC)")
                  # In bảng từng bước suy luận (Think -> Act -> Observe)
                  console.print(step_table)

              console.print(Panel(Markdown(res.get("final_answer", "")), title="🤖 TRỢ LÝ T4 TRẢ LỜI"))
              # In panel thống kê token thật và chi phí USD thời gian thực
              console.print(Panel(f"Tokens: {res.get('usage', {})} | Chi phí: ${cost:.6f} USD"))
      finally:
          await mcp_manager.close()
  ```

* **Tinh chỉnh và hoàn thiện của sinh viên:**  
  1. Xử lý triệt để lỗi môi trường Windows với `sys.stdout.reconfigure(encoding="utf-8")` chống lỗi `UnicodeEncodeError (charmap cp1252)` khi hiển thị tiếng Việt và emoji trên Command Prompt / PowerShell.
  2. Bổ sung đoạn mã lọc `src` khỏi `sys.path` để không làm che khuất (shadow) gói thư viện `mcp` SDK chính thức trên Windows.
  3. Bổ sung bảng trợ giúp nghiệp vụ 4 tầng `render_help()`, lệnh xem công cụ `tools`, và cơ chế ngắt `KeyboardInterrupt` an toàn đảm bảo luôn đóng MCP Client subprocess trong khối `finally`.



---

## 3. CAM KẾT LIÊM CHÍNH HỌC THUẬT

1. Toàn bộ nội dung khai báo trên phản ánh trung thực quá trình làm việc trong dự án.
2. Tự đọc hiểu, làm chủ 100% mã nguồn và sẵn sàng giải thích chi tiết trong buổi vấn đáp.
3. Sử dụng AI làm công cụ hỗ trợ gợi ý cú pháp và tối ưu tốc độ, hoàn toàn làm chủ tư duy thuật toán và logic nghiệp vụ.

