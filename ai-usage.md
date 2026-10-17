# BẢNG KHAI BÁO SỬ DỤNG AI (AI USAGE DECLARATION)
**Dự án:** Hệ thống Trợ lý Điểm Rèn luyện & Quản lý Khiếu nại (Đề tài T4 - AIPR Final Project)  
**Nhóm:** 3 Sinh viên

---

## 1. BẢNG TỔNG QUAN THEO THÀNH VIÊN

| STT | Thành viên | Vai trò phụ trách | Công cụ AI | Phạm vi áp dụng chính |
| :---: | :--- | :--- | :--- | :--- |
| 1 | **Ca Ngọc Tân** | **RAG và Data Engineer** | **Antigravity** | **AI hỗ trợ sinh mã nguồn xử lý và phân đoạn văn bản, triển khai Hybrid Search và tích hợp cơ chế Calibration trong RAG Pipeline** |
| 2 | **Lê Tuấn Thành** | **Agent & MCP Architect** | **Antigravity AI Assistant (Gemini 3.8 Flash High)** | **Typed Schemas (@dataclass), MCP Server stdio (stdout sạch 100%), Dynamic Tool Discovery (mcp SDK), Fallback BM25 Okapi, bộ parse Action đa định dạng và ThreadPool async bridge (src/mcp/, src/orchestrator.py). *Vòng lặp ReAct tự viết tay 100%.* |
| 3 | **Phạm Phước Anh** | **System Integrator & Evaluator** | **Antigravity AI Assistant (Gemini 3.8 Flash High)** | **Cơ chế Exponential Backoff trong LLM Client, Session Logger JSONL, bộ đánh giá tự động đa tầng (make eval), và giao diện CLI Rich (src/main.py)** |


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

> ⚠️ **Cam kết tuân thủ Yêu cầu R-02 (PDF 02 §2.2):**  
> Toàn bộ logic **Vòng lặp Agent ReAct (`react_agent` và `ReActOrchestrator`)** gồm chu trình suy luận *Think -> Act -> Observe*, cơ chế bóc tách Action đa định dạng (`parse_reply`), khống chế `MAX_STEPS = 10` (R-06), bắt lỗi mềm tự sửa sai, và **bộ kiểm soát bắt buộc đối soát Verify Tầng c (`pending_verification_cid` - R-07)** là do **sinh viên tự tay lập trình 100% bằng Python thuần** (CẤM dùng LangChain/CrewAI, không sử dụng AI sinh vòng lặp này). Sinh viên hoàn toàn làm chủ từng dòng lệnh và sẵn sàng vấn đáp, sửa code trực tiếp tại chỗ theo yêu cầu của Giảng viên.  
> Dưới đây là bảng khai báo minh bạch 7 hạng mục kỹ thuật chuyên sâu thuộc gói Model Context Protocol (`src/mcp/`) và các module hỗ trợ suy luận (`src/orchestrator.py`) có tham khảo trợ lý AI để sinh mã nền tảng:

* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).
  **Vị trí áp dụng:** Toàn bộ file [src/mcp/schemas.py](file:///c:/Users/LENOVO/Desktop/Study/AIPR/AIPR%20Project%20Final/src/mcp/schemas.py) (Dòng 16 đến dòng 181), bao gồm các class `SubmitComplaintInput`, `SubmitComplaintOutput`, `CheckComplaintInput`, `LookupPolicyInput`, `ComplaintRecord`.
* **Prompt chính đã dùng:**
  > *Dựa trên yêu cầu bắt buộc R-03 (PDF 02 §2.3) và bài học Tuần 1, hãy viết các Typed Schemas bằng `@dataclass` Python (nghiêm cấm dùng dict thô để vượt qua kiểm tra `grep -n "@dataclass"`) cho các công cụ MCP đề tài T4: nộp khiếu nại `submit_complaint`, tra cứu trạng thái đơn `check_complaint_status`, và tra cứu quy chế `lookup_policy`. Tích hợp classmethod `model_json_schema` dùng `pydantic.TypeAdapter(cls).json_schema()` theo bài học Tuần 6 để trích xuất JSON Schema cho LLM, đồng thời viết hàm kiểm tra dữ liệu đầu vào không được để trống trong `__post_init__`.*

* **Đoạn code do AI hỗ trợ sinh:**
  ```python
  from dataclasses import asdict, dataclass, field
  from typing import Any, Dict
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

      @classmethod
      def from_dict(cls, data: Dict[str, Any]) -> SubmitComplaintInput:
          return cls(
              student_id=data.get("student_id", ""),
              category=data.get("category", ""),
              reason=data.get("reason", ""),
              evidence=data.get("evidence", ""),
          )
  ```

* **Tinh chỉnh và hoàn thiện của sinh viên:**
  1. Dùng `pydantic.TypeAdapter(cls).json_schema()` xuất schema động chuẩn OpenAPI cho LLM mà vẫn giữ `@dataclass` thuần để vượt qua kiểm tra R-03 (`grep -n "@dataclass"`).
  2. Tự viết hàm `_require_non_empty` trong `__post_init__` để chặn triệt để tham số rỗng hoặc sai kiểu từ LLM.
  3. Bổ sung classmethod `from_dict` chống lỗi thiếu trường và tách riêng model CSDL `ComplaintRecord` kèm mốc thời gian UTC ISO 8601.


* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).
  **Vị trí áp dụng:** Khởi tạo `MCPServer`, hàm `log_debug`, `load_complaints`, `save_complaints`, và tool `@mcp.tool() submit_complaint` trong [src/mcp/server.py](file:///c:/Users/LENOVO/Desktop/Study/AIPR/AIPR%20Project%20Final/src/mcp/server.py) (Dòng 41 đến dòng 70 và dòng 197 đến dòng 241).
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
  **Vị trí áp dụng:** Hàm `get_rag_store`, tool `@mcp.tool() lookup_policy`, và tool `@mcp.tool() check_complaint_status` trong [src/mcp/server.py](file:///c:/Users/LENOVO/Desktop/Study/AIPR/AIPR%20Project%20Final/src/mcp/server.py) (Dòng 78 đến dòng 195 và dòng 243 đến dòng 265).
* **Prompt chính đã dùng:**
  > *Viết tool MCP Đọc `lookup_policy(query: str)` kết nối trực tiếp với module RAG để tra cứu quy chế điểm rèn luyện (Tầng a, b - R-05), và tool `check_complaint_status(complaint_id: str)` để đối soát đơn (Tầng c - R-07). Thiết kế hàm singleton nạp trước kho dữ liệu VectorStore từ data/processed/chunks.json để không bị nạp lại đĩa ở mỗi request. Quan trọng: nếu module RAG Dense/Hybrid gặp lỗi embedding hoặc quá tải mô hình, hãy lập trình cơ chế tự động Fallback tức thời sang thuật toán BM25 Okapi tính điểm từ khóa để đảm bảo tool luôn trả về kết quả trích dẫn Điều/Khoản hợp lệ.*

* **Đoạn code do AI hỗ trợ sinh:**
  ```python
  _rag_store = None
  def get_rag_store():
      global _rag_store
      if _rag_store is not None: return _rag_store
      store = VectorStore()
      with open(PROJECT_ROOT / "data" / "processed" / "chunks.json", "r", encoding="utf-8") as f:
          for item in json.load(f):
              c = DocumentChunk.from_dict(item)
              store.chunks[c.chunk_id] = c
      _rag_store = store
      return _rag_store

  @mcp.tool()
  def lookup_policy(query: str) -> str:
      store = get_rag_store()
      try:
          rag_res = rag_pipeline(query, store, top_k=3, search_mode="hybrid")
      except Exception:
          # Fallback BM25 Okapi khi Hybrid gặp sự cố
          bm25_idx = build_bm25_index(list(store.chunks.values()))
          scores = bm25_idx.get_scores(query.lower().split())
          scored = [(chunks[i], float(scores[i])) for i in range(len(chunks))]
          scored.sort(key=lambda x: x[1], reverse=True)
          rag_res = {"sources": [{"source": c.metadata.get("source"), "dieu": c.metadata.get("dieu"), "content": c.content} for c, s in scored[:3]]}
      return json.dumps(rag_res, ensure_ascii=False)

  @mcp.tool()
  def check_complaint_status(complaint_id: str) -> str:
      search_id = complaint_id.strip().upper()
      for rec in load_complaints():
          if str(rec.get("complaint_id", "")).strip().upper() == search_id:
              return json.dumps(rec, ensure_ascii=False)
      return json.dumps({"status": "not_found", "complaint_id": search_id}, ensure_ascii=False)
  ```

* **Tinh chỉnh và hoàn thiện của sinh viên:**
  1. Cài đặt singleton `get_rag_store()` nạp RAM 24 chunks quy chế từ đầu, loại bỏ độ trễ đọc đĩa lặp lại.
  2. Lập trình cơ chế tự động Fallback sang BM25 Okapi khi module Hybrid search embedding gặp lỗi, bảo đảm tool không bao giờ crash.
  3. Chuẩn hóa metadata `sources` (Điều, Khoản, nội dung, điểm số) phục vụ trích dẫn căn cứ Grounding (Tầng a).


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

### Thành viên: [Phạm Phước Anh] — Member C (System Integrator & Evaluator)

* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).
  **Vị trí áp dụng:** Hàm `generate` của class `RobustLLMClient` trong [src/llm_client.py](file:///c:/Users/LENOVO/Desktop/Study/AIPR/AIPR%20Project%20Final/src/llm_client.py) (Dòng 58 đến dòng 94) và file unit test [tests/test_llm_client.py](file:///c:/Users/LENOVO/Desktop/Study/AIPR/AIPR%20Project%20Final/tests/test_llm_client.py).
* **Prompt chính đã dùng:**
  > *Viết class RobustLLMClient bọc Groq API (mô hình qwen/qwen3.8-27b), tích hợp cơ chế tự động thử lại Exponential Backoff time.sleep(2 ** attempt) khi gặp sự cố mạng hoặc lỗi rate limit (R-04, Tuần 2). Trích xuất chính xác token thật (prompt_tokens, completion_tokens, total_tokens) từ response và viết unit test bằng unittest.mock.MagicMock để kiểm thử tự động mà không tốn chi phí gọi API thật.*

* **Đoạn code do AI hỗ trợ sinh:**
  ```python
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
  ```

* **Tinh chỉnh và hoàn thiện của sinh viên:**
  1. Tự thiết kế và cài đặt kết nối Groq API linh hoạt qua biến môi trường `MODEL` và `GROQ_API_KEY`.
  2. Bổ sung cơ chế bóc tách mã lỗi HTTP (`status_code`), in log cảnh báo retry chi tiết thời gian thực và cấu hình `sys.stdout.reconfigure(encoding="utf-8")` tránh lỗi charmap trên Windows.
  3. Làm chủ mã nguồn file test giả lập Mocking, chạy lệnh `pytest tests/test_llm_client.py` xác minh 100% test pass.


* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).
  **Vị trí áp dụng:** Khởi tạo class `SessionLogger`, hàm `log_record`, và hàm `estimate_cost` trong [src/utils/logger.py](file:///c:/Users/LENOVO/Desktop/Study/AIPR/AIPR%20Project%20Final/src/utils/logger.py) (Dòng 29 đến dòng 105) cùng [tests/test_logger.py](file:///c:/Users/LENOVO/Desktop/Study/AIPR/AIPR%20Project%20Final/tests/test_logger.py).
* **Prompt chính đã dùng:**
  > *Viết class SessionLogger để ghi trace từng phiên chạy của Agent thành file JSON Lines tại logs/run_TIMESTAMP.jsonl theo yêu cầu R-01 (PDF 02 §1). Lưu đầy đủ timestamp, user_query, steps suy luận, usage token thật và chi phí USD quy đổi theo bảng giá models. Viết hàm estimate_cost linh hoạt hỗ trợ tính toán chi phí token.*

* **Đoạn code do AI hỗ trợ sinh:**
  ```python
  class SessionLogger:
      def __init__(self, log_dir: str = "logs", session_file: Optional[str] = None):
          self.log_dir = log_dir
          os.makedirs(self.log_dir, exist_ok=True)
          timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
          self.log_file = os.path.join(self.log_dir, session_file or f"run_{timestamp}.jsonl")

      def log_record(self, query_id: str = "interactive", user_query: str = "", steps: Optional[List[Any]] = None, usage: Optional[Dict[str, Any]] = None, final_answer: str = "", **kwargs: Any) -> Dict[str, Any]:
          safe_usage = usage or {"prompt_tokens": 0, "completion_tokens": 0}
          cost = estimate_cost(model=os.getenv("MODEL", DEFAULT_MODEL), prompt_tokens=safe_usage.get("prompt_tokens", 0), completion_tokens=safe_usage.get("completion_tokens", 0))
          record = {"timestamp": datetime.now().isoformat(), "query_id": query_id, "user_query": user_query, "steps": steps or [], "usage": safe_usage, "cost_usd": cost, "final_answer": final_answer}
          with open(self.log_file, "a", encoding="utf-8") as f:
              f.write(json.dumps(record, ensure_ascii=False) + "\n")
          return record
  ```

* **Tinh chỉnh và hoàn thiện của sinh viên:**
  1. Tự kế thừa bảng giá `PRICING` quy đổi token từ bài học Tuần 2 và thiết kế hàm `estimate_cost` ở cấp module hỗ trợ linh hoạt cả 2 kiểu thứ tự đối số.
  2. Bổ sung trường `steps` để lưu vết đầy đủ chuỗi suy luận ReAct và đồng bộ các tham số của hàm `log_record` khớp hoàn toàn với `ReActOrchestrator`.
  3. Đảm bảo dữ liệu ghi vào file JSONL dùng `ensure_ascii=False` để giữ nguyên tiếng Việt có dấu và giải quyết triệt để lỗi import khi chạy test.


* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).
  **Vị trí áp dụng:** Bộ kiểm thử đánh giá tự động đa tầng trong [tests/test_agent.py](file:///c:/Users/LENOVO/Desktop/Study/AIPR/AIPR%20Project%20Final/tests/test_agent.py) (Dòng 53 đến dòng 377).
* **Prompt chính đã dùng:**
  > *Viết script đánh giá tự động toàn diện hệ thống (make eval) đọc tập 16 câu hỏi từ tests/testset.jsonl. Thiết kế logic chấm điểm 4 tầng nghiệp vụ: Grounding accuracy (trích dẫn Điều/Khoản), Calculation accuracy (áp trần điểm số), Tool Side-Effect Verify (R-07 kiểm tra đủ cặp tool submit và check status), và Calibration Rate (tỉ lệ từ chối câu hỏi bẫy >= 80%). Xuất bảng tổng kết Evaluation Summary Table in ra console.*

* **Đoạn code do AI hỗ trợ sinh:**
  ```python
  def evaluate_single_query(query_data: Dict[str, Any], agent_result: Dict[str, Any]) -> Dict[str, Any]:
      category = query_data.get("category", "")
      final_ans = agent_result.get("final_answer", "")
      steps = agent_result.get("steps", [])
      tools_called = [s.get("tool_name") for s in steps if s.get("action") == "call_tool"]
      
      passed = False
      if category == "grounding":
          passed = any(re.search(pat, final_ans, re.IGNORECASE) for pat in query_data.get("expected_sources", []))
      elif category == "side_effect":
          passed = ("submit_complaint" in tools_called) and ("check_complaint_status" in tools_called)
      elif category == "calibration":
          passed = any(kw in final_ans.lower() for kw in REFUSAL_KEYWORDS)
      return {"query_id": query_data.get("id"), "passed": passed, "tools_called": tools_called}
  ```

* **Tinh chỉnh và hoàn thiện của sinh viên:**
  1. Tự thiết kế và cài đặt logic chấm điểm đa tầng trong `evaluate_single_query` bám sát yêu cầu nghiệp vụ PDF 02 §1.4.
  2. Tích hợp `ReActOrchestrator`, `RobustLLMClient` và `SessionLogger` vào hàm `run_evaluation_async` để đọc bộ câu hỏi, đo đếm token thực tế và chi phí API.
  3. Cấu hình cờ CLI `--max-queries` và `--model`, xử lý hiển thị bảng kết quả đánh giá (Evaluation Summary Table) trực quan.


* **Công cụ sử dụng:** Antigravity AI Assistant (Gemini 3.8 Flash High).
  **Vị trí áp dụng:** Giao diện dòng lệnh tương tác REPL và các hàm hiển thị bảng điều khiển trong [src/main.py](file:///c:/Users/LENOVO/Desktop/Study/AIPR/AIPR%20Project%20Final/src/main.py) (Dòng 52 đến dòng 262).
* **Prompt chính đã dùng:**
  > *Viết giao diện dòng lệnh tương tác CLI REPL (make demo) bằng thư viện Rich cho hệ thống Trợ lý Điểm Rèn luyện T4. Khởi tạo và kết nối RobustLLMClient, MCPClientManager (stdio), ReActOrchestrator và SessionLogger. Hiển thị Panel giới thiệu đẹp mắt, hỗ trợ các lệnh điều khiển ('help', 'tools', 'exit'/'q'), in tiến trình suy luận ReAct từng bước (Think -> Act -> Observe) và in bảng thống kê Usage token/chi phí theo thời gian thực.*

* **Đoạn code do AI hỗ trợ sinh:**
  ```python
  async def run_interactive_cli() -> None:
      render_banner()
      async with MCPClientManager() as mcp_client:
          orchestrator = ReActOrchestrator(llm_client=llm, mcp_client=mcp_client, logger=logger)
          while True:
              try:
                  query = console.input("[bold yellow]Sinh viên[/bold yellow]: ").strip()
                  if not query: continue
                  if query.lower() in ("exit", "quit", "q"): break
                  if query.lower() == "help": render_help(); continue
                  res = await orchestrator.arun(query, return_details=True)
                  for step in res.get("steps", []): render_step(step)
                  render_final_answer(res.get("final_answer", ""))
                  render_stats(res.get("usage", {}), res.get("steps", []))
              except KeyboardInterrupt:
                  break
  ```

* **Tinh chỉnh và hoàn thiện của sinh viên:**
  1. Xử lý triệt để lỗi môi trường Windows với `sys.stdout.reconfigure(encoding="utf-8")` chống lỗi `UnicodeEncodeError (charmap cp1252)`.
  2. Bổ sung đoạn mã lọc `src` khỏi `sys.path` để không làm che khuất gói thư viện `mcp` SDK chính thức trên Windows.
  3. Bổ sung các lệnh tương tác `tools` và bảng hướng dẫn mẫu `render_help()` theo 4 tầng nghiệp vụ phục vụ việc chấm demo trực tiếp.



---

## 3. CAM KẾT LIÊM CHÍNH HỌC THUẬT

1. Toàn bộ nội dung khai báo trên phản ánh trung thực quá trình làm việc trong dự án.
2. Tự đọc hiểu, làm chủ 100% mã nguồn và sẵn sàng giải thích chi tiết trong buổi vấn đáp.
3. Sử dụng AI làm công cụ hỗ trợ gợi ý cú pháp và tối ưu tốc độ, hoàn toàn làm chủ tư duy thuật toán và logic nghiệp vụ.

