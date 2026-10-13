"""Hybrid Search (Tái dùng trực tiếp từ W4_2/ex2_1_hybrid_search.py theo yêu cầu R-05)."""

from __future__ import annotations
from typing import List, Tuple
from rank_bm25 import BM25Okapi

from src.rag.doc_model import DocumentChunk


def normalise_scores(scores: List[float]) -> List[float]:
    """Chuẩn hóa điểm số về khoảng [0, 1] (W4_2)."""
    # Gợi ý: (score - min_s) / (max_s - min_s)
    pass


def build_bm25_index(chunks: List[DocumentChunk]) -> BM25Okapi:
    """Xây dựng chỉ mục BM25 từ danh sách chunks (W4_2)."""
    # Gợi ý: Tokenize content bằng split() và khởi tạo BM25Okapi
    pass


def hybrid_search(
    query: str,
    chunks: List[DocumentChunk],
    bm25_index: BM25Okapi,
    embeddings: List[List[float]],
    top_k: int = 3,
    w_bm25: float = 0.3,
    w_vector: float = 0.7,
) -> List[Tuple[DocumentChunk, float]]:
    """Tìm kiếm lai kết hợp BM25 và Vector Cosine (W4_2)."""
    # Gợi ý:
    # 1. bm25_scores = bm25_index.get_scores(query.split())
    # 2. cosine_scores = [cosine_similarity(query_emb, emb) for emb in embeddings]
    # 3. normalise_scores cho cả 2 mảng điểm
    # 4. hybrid_score = w_bm25 * bm25_norm + w_vector * cosine_norm -> sắp xếp giảm dần -> lấy top_k
    pass
