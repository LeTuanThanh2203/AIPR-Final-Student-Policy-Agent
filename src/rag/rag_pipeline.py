"""RAG Pipeline Module (Kế thừa từ W4_2 & tham khảo Exercise 1.3 - RAG v1).

Hỗ trợ:
- Tải biến môi trường (.env) cho Groq API hoặc OpenAI API.
- Định dạng Prompt trích dẫn nguồn có kiểm soát (Grounding).
- Tìm kiếm Chunks qua VectorStore (Cosine hoặc Hybrid BM25 + Cosine).
- Calibration Check: Tự động từ chối nếu không đủ thông tin hoặc ngoài quy chế.
- Hàm main() chạy độc lập kiểm thử quy trình và xuất Evidence Trail trực quan.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dotenv import load_dotenv

load_dotenv()

from src.rag.doc_model import Document, DocumentChunk
from src.rag.vector_store import VectorStore
from src.rag.hybrid_search import build_bm25_index, hybrid_search

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH LLM CLIENT (Hỗ trợ cả Groq và OpenAI linh hoạt)
# -----------------------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

_client = None
_client_type = None

if GROQ_API_KEY:
    try:
        from groq import Groq
        _client = Groq(api_key=GROQ_API_KEY)
        _client_type = "groq"
    except ImportError:
        pass

if _client is None and OPENAI_API_KEY:
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_API_KEY)
        _client_type = "openai"
    except ImportError:
        pass


def get_llm_client():
    """Lấy LLM client (Groq hoặc OpenAI) đã được khởi tạo."""
    return _client, _client_type


# -----------------------------------------------------------------------------
# 2. HỆ THỐNG PROMPT & MẪU TRÍCH DẪN NGUỒN
# -----------------------------------------------------------------------------
REFUSAL_MESSAGE = "Thông tin này không có trong quy chế điểm rèn luyện được cung cấp."

RAG_SYSTEM_PROMPT = """Bạn là trợ lý chính sách sinh viên chuyên nghiệp và chính xác.

Yêu cầu nghiêm ngặt:
1. Chỉ trả lời dựa vào ngữ cảnh (Context) được cung cấp dưới đây.
2. Không sử dụng kiến thức bên ngoài, không suy diễn hoặc tự bịa đặt thông tin.
3. Luôn trích dẫn rõ căn cứ [Nguồn, Điều, Khoản hoặc Tiêu chí] cho mỗi thông tin được trả lời.
4. Nếu ngữ cảnh không có hoặc không đủ thông tin để trả lời câu hỏi, hãy trả lời chính xác:
"{refusal_message}"

Context:
{context}

Question:
{question}
"""


# -----------------------------------------------------------------------------
# 3. CÁC HÀM XỬ LÝ DỮ LIỆU & BUILD PROMPT
# -----------------------------------------------------------------------------
def load_document(path: Union[str, Path], title: str = "") -> Document:
    """Đọc và nạp một tài liệu văn bản vào đối tượng Document."""
    file_path = Path(path)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    doc_title = title or file_path.stem
    return Document(
        content=content,
        title=doc_title,
        source=str(file_path),
        metadata={
            "source": str(file_path),
            "title": doc_title,
            "type": "policy",
            "section": "Full document",
        },
    )


def build_rag_prompt(question: str, chunks: List[DocumentChunk]) -> List[Dict[str, str]]:
    """Tạo messages cho LLM kèm trích dẫn số thứ tự, nguồn, phiên bản và điều khoản."""
    context_text = "\n\n".join(
        f"[{i + 1}] (Source: {c.metadata.get('source', c.doc_id or 'unknown')}, "
        f"Phiên bản: {c.version or c.metadata.get('version', 'unknown')}, "
        f"Điều/Tiêu chí: {c.metadata.get('dieu', c.metadata.get('tieu_chi', c.metadata.get('section', 'unknown')))}, "
        f"Tiêu đề: {c.metadata.get('title', 'unknown')})\n"
        f"{c.content}"
        for i, c in enumerate(chunks)
    )

    system_content = RAG_SYSTEM_PROMPT.format(
        refusal_message=REFUSAL_MESSAGE,
        context=context_text if context_text else "Không có ngữ cảnh phù hợp.",
        question=question,
    )

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": question},
    ]


# -----------------------------------------------------------------------------
# 4. TRUY XUẤT CHUNKS & RAG PIPELINE
# -----------------------------------------------------------------------------
def filter_chunks_by_version(
    chunks: List[DocumentChunk],
    version: Optional[str] = "latest",
) -> List[DocumentChunk]:
    """Lọc danh sách DocumentChunk theo phiên bản quy chế.
    
    - 'latest' (mặc định): Tự động chọn phiên bản quy chế mới nhất (năm cao nhất, ví dụ: 2024).
    - 'all' hoặc '*': Không lọc, lấy toàn bộ các phiên bản.
    - '<tên_phiên_bản>': Lọc theo phiên bản tương ứng ('2024', '2022', 'main'...).
    """
    if not chunks:
        return []

    if not version or version.strip().lower() in ("all", "*"):
        return chunks

    target = version.strip().lower()

    if target == "latest":
        # Xác định năm quy chế mới nhất
        valid_years: List[int] = []
        for c in chunks:
            if c.version_year is not None:
                valid_years.append(c.version_year)
            elif c.version and c.version.isdigit():
                valid_years.append(int(c.version))
            elif c.metadata and c.metadata.get("version_year") is not None:
                try:
                    valid_years.append(int(c.metadata["version_year"]))
                except (ValueError, TypeError):
                    pass
            elif c.metadata and str(c.metadata.get("version", "")).isdigit():
                try:
                    valid_years.append(int(c.metadata["version"]))
                except (ValueError, TypeError):
                    pass

        if valid_years:
            latest_year = max(valid_years)
            filtered = [
                c for c in chunks
                if (c.version_year == latest_year)
                or (c.version == str(latest_year))
                or (c.metadata.get("version_year") == latest_year)
                or (str(c.metadata.get("version", "")) == str(latest_year))
            ]
            if filtered:
                return filtered
        return chunks

    # Lọc theo phiên bản cụ thể
    filtered = [
        c for c in chunks
        if (c.version.lower() == target)
        or (str(c.version_year or "").lower() == target)
        or (c.metadata.get("version", "").lower() == target)
        or (str(c.metadata.get("version_year", "")).lower() == target)
        or (f"_v{target}" in c.doc_id.lower())
    ]
    return filtered if filtered else chunks


def search_chunks(
    query: str,
    store: VectorStore,
    top_k: int = 3,
    search_mode: str = "hybrid",
    version: Optional[str] = "latest",
) -> List[Tuple[DocumentChunk, float]]:
    """Truy xuất các chunks tương đồng theo chế độ 'cosine' hoặc 'hybrid' (BM25 + Cosine).
    
    Hỗ trợ lọc theo phiên bản tài liệu (mặc định 'latest').
    """
    if not store.chunks:
        return []

    # Lọc chunks theo phiên bản trước khi tìm kiếm
    candidate_chunks = filter_chunks_by_version(list(store.chunks.values()), version=version)
    if not candidate_chunks:
        candidate_chunks = list(store.chunks.values())

    if search_mode == "cosine":
        return store.search(query, top_k=top_k, candidates=candidate_chunks)

    # Chế độ Hybrid: BM25 + Vector Cosine (Tự động fallback BM25 nếu lỗi embedding)
    try:
        bm25_idx = build_bm25_index(candidate_chunks)
        embeddings = [c.embedding if c.embedding is not None else [] for c in candidate_chunks]
        return hybrid_search(
            query=query,
            chunks=candidate_chunks,
            bm25_index=bm25_idx,
            embeddings=embeddings,
            top_k=top_k,
        )
    except Exception:
        bm25_idx = build_bm25_index(candidate_chunks)
        query_tokens = query.lower().split()
        scores = bm25_idx.get_scores(query_tokens)
        scored = [(candidate_chunks[i], float(scores[i])) for i in range(len(candidate_chunks))]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


def rag_pipeline(
    query: str,
    store: VectorStore,
    top_k: int = 3,
    search_mode: str = "hybrid",
    model: Optional[str] = None,
    version: Optional[str] = "latest",
) -> Dict[str, Any]:
    """Quy trình RAG tiêu chuẩn hoàn chỉnh:
    1. Tìm kiếm chunks qua VectorStore có lọc theo version (mặc định 'latest').
    2. Áp dụng Calibration Check (từ chối câu bẫy/ngoài phạm vi nếu không có kết quả).
    3. Định dạng Messages kèm Evidence Context.
    4. Gọi LLM sinh câu trả lời có trích dẫn.
    5. Đóng gói kết quả dạng Dict gồm answer, sources (Evidence Trail) và messages.
    """
    # 1. Truy xuất dữ liệu
    results = search_chunks(query, store, top_k=top_k, search_mode=search_mode, version=version)

    # 2. Calibration Check: Nếu rỗng hoặc không có kết quả
    if not results:
        return {
            "answer": REFUSAL_MESSAGE,
            "sources": [],
            "messages": [],
            "results": [],
            "version": version,
        }

    chunks = [chunk for chunk, _ in results]
    messages = build_rag_prompt(query, chunks)

    # 3. Gọi LLM
    client, client_type = get_llm_client()
    answer_text = ""

    if client is not None:
        try:
            if client_type == "groq":
                selected_model = model or "llama-3.3-70b-versatile"
                response = client.chat.completions.create(
                    model=selected_model,
                    messages=messages,
                    temperature=0.0,
                )
                answer_text = response.choices[0].message.content
            elif client_type == "openai":
                selected_model = model or "gpt-4o-mini"
                response = client.chat.completions.create(
                    model=selected_model,
                    messages=messages,
                    temperature=0.0,
                )
                answer_text = response.choices[0].message.content
        except Exception as e:
            answer_text = f"Lỗi khi gọi API LLM ({client_type}): {str(e)}"
    else:
        # Khi chưa có API Key, phản hồi thông báo thân thiện
        answer_text = (
            f"[Mô phỏng RAG - Chưa phát hiện GROQ_API_KEY hoặc OPENAI_API_KEY trong .env]\n"
            f"Đã tìm thấy {len(chunks)} đoạn quy chế (phiên bản: {version}) liên quan để trả lời cho câu hỏi: '{query}'."
        )

    # 4. Định dạng danh sách nguồn minh chứng (Evidence Trail)
    sources = []
    for chunk, score in results:
        metadata = chunk.metadata or {}
        sources.append({
            "source": metadata.get("source", chunk.doc_id or "unknown"),
            "title": metadata.get("title", "unknown"),
            "dieu": metadata.get("dieu", "unknown"),
            "section": metadata.get("section", metadata.get("title", "unknown")),
            "type": metadata.get("type", "policy"),
            "version": chunk.version or metadata.get("version", ""),
            "version_year": chunk.version_year or metadata.get("version_year"),
            "score": score,
            "content": chunk.content,
        })

    return {
        "answer": answer_text,
        "sources": sources,
        "messages": messages,
        "results": results,
        "version": version,
    }


# -----------------------------------------------------------------------------
# 5. HÀM MAIN TEST ĐỘC LẬP (Evidence Trail Runner)
# -----------------------------------------------------------------------------
def main():
    print("=" * 65)
    print("AIPR Final Project - RAG Pipeline (Quy chế Điểm rèn luyện HCMUTE)")
    print("=" * 65)

    store = VectorStore()

    # Kiểm tra nạp dữ liệu chunks đã xử lý nếu có
    chunks_path = Path("data/processed/chunks.json")
    if chunks_path.exists():
        import json
        with open(chunks_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            c = DocumentChunk.from_dict(item)
            store.chunks[c.chunk_id] = c
        print(f"Đã nạp {len(store.chunks)} chunks từ {chunks_path}")
    else:
        print(f"Chưa tìm thấy {chunks_path}. Hãy chạy `python src/rag/document_parser.py` trước.")

    print(f"Số lượng chunks trong VectorStore: {len(store.chunks)}")

    # Bộ câu hỏi kiểm thử tiêu biểu
    questions = [
        (
            "Q1 [Tra cứu]",
            "Sinh viên tham gia chiến dịch tình nguyện Mùa hè xanh cấp trường được cộng bao nhiêu điểm và vào tiêu chí nào?",
        ),
        (
            "Q2 [Vi phạm]",
            "Sinh viên bị cấm thi một môn thì bị trừ bao nhiêu điểm rèn luyện theo quy chế?",
        ),
        (
            "Q3 [Calibration - Bẫy ngoài lề]",
            "Nếu tôi xem phim Marvel tại rạp vào cuối tuần thì trường có cộng điểm rèn luyện không?",
        ),
    ]

    for q_id, question in questions:
        print("\n" + "=" * 65)
        print(f"{q_id}")
        print("=" * 65)
        print(f"Câu hỏi: {question}")

        result = rag_pipeline(question, store, top_k=3, search_mode="hybrid")

        print("\nCâu trả lời (Answer):")
        print(result["answer"])

        print("\nBằng chứng truy xuất (Evidence Trail):")
        for i, src in enumerate(result["sources"], start=1):
            try:
                score_str = f"{float(src['score']):.4f}"
            except Exception:
                score_str = str(src["score"])

            print(
                f"[{i}] source={src['source']} | "
                f"điều={src['dieu']} | "
                f"score={score_str} | "
                f"tiêu đề={src['title']}"
            )

    print("\n" + "=" * 65)
    print("HOÀN THÀNH KIỂM THỬ RAG PIPELINE")
    print("=" * 65)


if __name__ == "__main__":
    main()
