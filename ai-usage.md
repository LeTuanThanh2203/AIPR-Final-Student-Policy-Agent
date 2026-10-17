# BẢNG KHAI BÁO SỬ DỤNG AI (AI USAGE DECLARATION)

## 1. BẢNG TỔNG QUAN
| STT | Thành viên | MSSV | Công cụ AI | Phạm vi áp dụng |
| :---: | :--- | :---: | :--- | :--- |
| 1 | [Tên SV 1] | [MSSV 1] | ChatGPT-4o | Regex tách Điều/Khoản trong RAG |
| 2 | [Tên SV 2] | [MSSV 2] | GitHub Copilot | Gợi ý schema @dataclass |
| 3 | [Tên SV 3] | [MSSV 3] | Claude 3.5 Sonnet | Cấu trúc Retry backoff LLM |

---

## 2. CHI TIẾT KHAI BÁO (SAMPLE MẪU)

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




### Thành viên: [Họ và tên SV - MSSV] — Member A (RAG & Data Engineer)
* **Công cụ sử dụng:** Antigravity AI Assistant / ChatGPT-4o
* **Vị trí áp dụng:** File `src/rag/rag_pipeline.py` (Toàn bộ pipeline RAG, hàm `build_rag_prompt`, `search_chunks`, `rag_pipeline`, và hàm `main`)
* **Prompt đã dùng:**
  > *"Dựa trên bài tập RAG pipeline v1 (dùng Groq, VectorStore, Grounding Prompt, Evidence Trail) và cấu trúc đề tài T4 Điểm rèn luyện HCMUTE, hãy xây dựng file `src/rag/rag_pipeline.py` hoàn chỉnh: hỗ trợ cả Groq lẫn OpenAI qua .env, tìm kiếm lai Hybrid/Cosine, định dạng prompt trích dẫn Điều/Khoản, sinh Evidence Trail có score và hàm main() kiểm thử độc lập."*
* **Đoạn code AI gợi ý ban đầu:**
  ```python
  def rag_pipeline(query, store, top_k=3, search_mode="hybrid"):
      results = search_chunks(query, store, top_k=top_k, search_mode=search_mode)
      if not results:
          return {"answer": REFUSAL_MESSAGE, "sources": [], "messages": []}
      chunks = [chunk for chunk, _ in results]
      messages = build_rag_prompt(query, chunks)
      response = client.chat.completions.create(model=selected_model, messages=messages, temperature=0.0)
      sources = [{"source": c.metadata.get("source"), "dieu": c.metadata.get("dieu"), "score": score} for c, score in results]
      return {"answer": response.choices[0].message.content, "sources": sources, "messages": messages}
  ```
* **Chỉnh sửa của sinh viên:**
  1. Bản địa hóa system prompt sang tiếng Việt chuẩn quy chế ĐRL HCMUTE và cơ chế Calibration từ chối câu hỏi ngoài lề.
  2. Bổ sung hỗ trợ kép linh hoạt cho cả Groq (`GROQ_API_KEY`) và OpenAI (`OPENAI_API_KEY`) với cơ chế fallback an toàn khi thiếu key.
  3. Mở rộng truy xuất đa chế độ (`search_mode="hybrid"` hoặc `"cosine"`).
  4. Bổ sung hàm `main()` nạp dữ liệu chunks thực tế và chạy kiểm thử 3 câu hỏi với định dạng Evidence Trail trực quan.
* **Mức độ hiểu code:** 100% — Nắm vững luồng RAG, cách tính điểm tương đồng, định dạng prompt và sẵn sàng phản biện khi vấn đáp.

---

<!-- Copy cấu trúc trên cho Thành viên 2 và Thành viên 3 -->
