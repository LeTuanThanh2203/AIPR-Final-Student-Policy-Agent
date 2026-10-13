# BẢNG KHAI BÁO SỬ DỤNG AI (AI USAGE DECLARATION)

## 1. BẢNG TỔNG QUAN
| STT | Thành viên | MSSV | Công cụ AI | Phạm vi áp dụng |
| :---: | :--- | :---: | :--- | :--- |
| 1 | [Tên SV 1] | [MSSV 1] | ChatGPT-4o | Regex tách Điều/Khoản trong RAG |
| 2 | [Tên SV 2] | [MSSV 2] | GitHub Copilot | Gợi ý schema @dataclass |
| 3 | [Tên SV 3] | [MSSV 3] | Claude 3.5 Sonnet | Cấu trúc Retry backoff LLM |

---

## 2. CHI TIẾT KHAI BÁO (SAMPLE MẪU)

### Thành viên: [Họ và tên SV - MSSV]
* **Công cụ sử dụng:** ChatGPT-4o
* **Vị trí áp dụng:** File `src/rag/document_parser.py` (Hàm `parse_and_chunk_documents`)
* **Prompt đã dùng:** *"Viết regex Python tách văn bản theo các đoạn bắt đầu bằng 'Điều [số]' và 'Khoản [số]'."*
* **Đoạn code AI gợi ý ban đầu:**
  ```python
  pattern = r"(Điều\s+\d+[\.:\s]+.*?)(?=Điều\s+\d+|$)"
  chunks = re.findall(pattern, text, re.DOTALL)
  ```
* **Chỉnh sửa của sinh viên:** Thêm logic bóc tách từng Khoản con bên trong Điều và gán metadata (`doc_id`, `dieu`, `khoan`).
* **Mức độ hiểu code:** 100% — Hiểu rõ từng group regex và sẵn sàng giải thích khi GV vấn đáp.

---

<!-- Copy cấu trúc trên cho Thành viên 2 và Thành viên 3 -->
