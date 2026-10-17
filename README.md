# AIPR Final Project — Đề tài T4: Trợ lý Điểm Rèn luyện

Hệ thống AI Agent hỗ trợ tra cứu quy chế, tính điểm rèn luyện (áp trần) và quản lý khiếu nại (có verify).
Đồ án tuân thủ nghiêm ngặt 8 yêu cầu kỹ thuật (R-01 đến R-08) từ file yêu cầu `02-Yeu-cau-Thuc-hien.pdf` và các bài học từ Tuần 1 đến Tuần 7.

---

## 1. Khởi chạy nhanh (Cold-Start)

```bash
# 1. Cấu hình API key (sao chép từ file mẫu)
cp .env.example .env

# 2. Cài đặt môi trường và chạy thử bằng 1 lệnh duy nhất (R-01)
make setup && make demo

# 3. Đánh giá tự động trên bộ kiểm thử 16 câu hỏi (Tầng a, b, c & Calibration)
make eval

# 4. Chạy toàn bộ 12 unit tests
make test
```

---

## 2. Phân công Công việc 3 Thành viên (A, B, C)

| Thành viên | Vai trò cốt lõi | File phụ trách chính | Yêu cầu kỹ thuật & Kiến thức tuần liên quan |
| :---: | :--- | :--- | :--- |
| **🟢 Ca Ngọc Tân** | **RAG & Data Engineer** | `src/rag/document_parser.py`<br>`src/rag/vector_store.py`<br>`src/rag/hybrid_search.py`<br>`src/rag/rag_pipeline.py` | **R-05**: Logical chunking theo Điều/Khoản, VectorStore Cosine NumPy (W3), Hybrid BM25 + Cosine (W4), và Calibration threshold để từ chối câu ngoài lề. |
| **🔵 Lê Tuấn Thành** | **Agent & MCP Architect** | `src/mcp/schemas.py`<br>`src/mcp/server.py`<br>`src/mcp/client.py`<br>`src/orchestrator.py` | **R-02, R-03, R-06, R-07, R-08**: Schemas `@dataclass` (W1), 4 MCP Tools (W7 stdio), Vòng lặp ReAct tự viết tay (W6), cơ chế an toàn và BẮT BUỘC VERIFY sau khi ghi. |
| **🟣 Phạm Phước Anh** | **System Integrator & Evaluator** | `src/llm_client.py`<br>`src/utils/logger.py`<br>`src/main.py`<br>`tests/testset.jsonl`<br>`tests/test_agent.py`<br>`tests/test_llm_client.py`<br>`tests/test_logger.py` | **R-01, R-04**: Wrapper gọi LLM API với Exponential Backoff & Timeout (W2), log lỗi HTTP, System Prompts file ngoài, Logger JSONL đo token thật từ API, CLI tương tác Rich, bộ testset & runner `make eval`, bộ 12 unit tests. |

---

## 3. Hệ thống 4 Tools MCP cho Đề tài T4 (`src/mcp/server.py`)

1. **`submit_complaint(student_id, category, reason, evidence)` [GHI - Side Effect]:** Tiếp nhận đơn khiếu nại, sinh mã `CPL-xxx`, ghi vào `data/complaints.json` (Tầng c - R-07).
2. **`check_complaint_status(complaint_id)` [ĐỌC - BẮT BUỘC VERIFY]:** Tra cứu trạng thái đơn khiếu nại để xác minh dữ liệu đã thay đổi thật trong file JSON ngay trong phiên chạy (Tầng c - R-07).
3. **`list_student_complaints(student_id)` [ĐỌC]:** Tra cứu toàn bộ lịch sử khiếu nại của sinh viên.
4. **`calculate_drl(student_id, semester, activities_json)` [TÍNH TOÁN]:** Tính tổng điểm rèn luyện và áp mức trần theo từng tiêu chí quy chế (Tầng b - R-05).

---

## 4. Hybrid Search (W4) & Kỹ năng Calibration (PDF 01)

- **Hybrid Search (`src/rag/hybrid_search.py`):** Tái dùng trực tiếp từ bài học `w4/ex2_1_hybrid_search.py` theo yêu cầu PDF 02 §2.5. Kết hợp tìm kiếm ngữ nghĩa Dense (Vector Cosine Similarity trên NumPy) và tìm kiếm từ khóa Sparse (BM25 Okapi) theo trọng số:
  $$\text{Score}_{hybrid} = 0.3 \times \text{Score}_{BM25} + 0.7 \times \text{Score}_{Cosine}$$
  *(Lưu ý: Không có hàm code nào tên là `calibration` trong RAG).*
- **Calibration (Kỹ năng tại Tầng a — PDF 01 §1):** Là cơ chế **"biết khi nào KHÔNG trả lời" (Say "I don't know")** nhằm chống ảo giác (hallucination):
  - Khi gặp câu hỏi bẫy hoặc ngoài quy chế (`no_answer: true` trong testset như hỏi về rank game, phim Marvel, đổi bằng lái xe), tài liệu truy xuất sẽ không có câu trả lời.
  - System Prompt và logic kiểm soát context yêu cầu Agent từ chối lịch sự: *"Thông tin này không có trong quy chế điểm rèn luyện"*.
  - Bộ kiểm thử `tests/test_agent.py` khi chạy `make eval` sẽ đo lường **Tỉ lệ từ chối đúng (Calibration Rate $\ge 80\%$)** trên 4 câu `no_answer`.

---

## 5. Cấu trúc thư mục dự án

```
.
├── .env.example              # Mẫu biến môi trường (Phạm Phước Anh)
├── Makefile                  # make setup, make demo, make eval, make test (Phạm Phước Anh)
├── pyproject.toml            # Quản lý thư viện và môi trường qua uv
├── ai-usage.md               # Bản khai báo minh bạch việc dùng AI
├── data/
│   ├── raw/                  # Văn bản quy chế gốc (.txt, .pdf)
│   ├── processed/            # chunks.json sau khi phân đoạn theo Điều/Khoản
│   └── complaints.json       # CSDL lưu trữ hồ sơ khiếu nại
├── prompts/                  # Prompt hệ thống tách riêng ngoài mã nguồn (R-04)
│   ├── system_react.txt      # Prompt vòng lặp Agent ReAct
│   └── rag_grounding.txt     # Prompt RAG trích dẫn căn cứ
├── src/
│   ├── main.py               # Giao diện dòng lệnh CLI tương tác Rich (Phạm Phước Anh)
│   ├── orchestrator.py       # Vòng lặp Agent ReAct tự viết (Lê Tuấn Thành - W6)
│   ├── llm_client.py         # Robust LLM Client Retry Backoff/Timeout/HTTP Log (Phạm Phước Anh - W2)
│   ├── rag/                  # Module RAG Tra cứu Quy chế (Ca Ngọc Tân - W3, W4)
│   │   ├── doc_model.py      # Data models Document, DocumentChunk
│   │   ├── document_parser.py# Logical Chunking Điều/Khoản
│   │   ├── vector_store.py   # VectorStore + Cosine Similarity (NumPy)
│   │   ├── hybrid_search.py  # BM25 + Vector Cosine + Calibration Threshold
│   │   └── rag_pipeline.py   # Pipeline RAG hoàn chỉnh
│   ├── mcp/                  # MCP Server & Client (Lê Tuấn Thành - W7)
│   │   ├── schemas.py        # Typed @dataclass (R-03 & W1)
│   │   ├── server.py         # MCP Server stdio (4 tools)
│   │   └── client.py         # MCP Client gọi tool động (Dynamic Discovery)
│   └── utils/
│       ├── config.py         # Hằng số cấu hình & đường dẫn
│       └── logger.py         # JSONL Logger đo token USAGE thật & chi phí USD (Phạm Phước Anh)
└── tests/
    ├── testset.jsonl         # 16 câu hỏi kiểm thử đủ 3 tầng + bẫy Calibration (Phạm Phước Anh)
    ├── test_agent.py         # Script chạy make eval & benchmark tự động (Phạm Phước Anh)
    ├── test_llm_client.py    # Unit test LLM Client Mocking & Retry (Phạm Phước Anh)
    └── test_logger.py        # Unit test Session & Token Usage Logger (Phạm Phước Anh)
```