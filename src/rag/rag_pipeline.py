"""RAG Pipeline (Kế thừa từ W4_2/ex2_2_rag_pipeline_v2.py)."""

from __future__ import annotations
from typing import List, Tuple, Optional
from src.rag.doc_model import DocumentChunk
from src.rag.vector_store import VectorStore


def build_rag_prompt(question: str, chunks: List[DocumentChunk]) -> List[dict]:
    """Tạo messages cho LLM kèm trích dẫn nguồn [doc_id, Điều x] (W4_2)."""
    # Gợi ý: Format context_text từ chunks, ghép vào prompt template (tách file ngoài R-04)
    pass


def search_chunks(
    query: str, store: VectorStore, top_k: int = 3, search_mode: str = "hybrid"
) -> List[Tuple[DocumentChunk, float]]:
    """Truy xuất chunks theo chế độ 'cosine' hoặc 'hybrid' (W4_2)."""
    # Gợi ý:
    # Nếu "cosine": gọi store.search()
    # Nếu "hybrid": gọi build_bm25_index() và hybrid_search()
    pass


def rag_pipeline(
    query: str,
    store: VectorStore,
    top_k: int = 3,
    search_mode: str = "hybrid",
) -> Tuple[str, List[Tuple[DocumentChunk, float]]]:
    """Quy trình RAG tiêu chuẩn: search_chunks -> build_rag_prompt -> gọi LLM -> trả lời (W4_2)."""
    # Gợi ý: Gọi search_chunks, nếu rỗng thì trả về câu từ chối; ngược lại gọi LLM sinh câu trả lời
    pass
