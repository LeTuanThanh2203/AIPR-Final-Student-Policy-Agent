"""Hybrid Search (Tái dùng trực tiếp từ W4_2/ex2_1_hybrid_search.py theo yêu cầu R-05)."""

from __future__ import annotations
from typing import List, Tuple
from rank_bm25 import BM25Okapi

from src.rag.doc_model import DocumentChunk
from src.rag.vector_store import cosine_similarity, embed_query


def normalise_scores(scores: List[float]) -> List[float]:
    """Chuẩn hóa điểm số về khoảng [0, 1] (W4_2)."""
    if not scores:
        return []
    min_s = float(min(scores))
    max_s = float(max(scores))
    if max_s == min_s:
        return [1.0 if max_s > 0 else 0.0 for _ in scores]
    return [(s - min_s) / (max_s - min_s) for s in scores]


def build_bm25_index(chunks: List[DocumentChunk]) -> BM25Okapi:
    """Xây dựng chỉ mục BM25 từ danh sách chunks (W4_2)."""
    tokenized_corpus = [chunk.content.lower().split() for chunk in chunks]
    return BM25Okapi(tokenized_corpus)

def hybrid_search(
    query: str,
    chunks: List[DocumentChunk],
    bm25_index: BM25Okapi,
    embeddings: List[List[float]],
    top_k: int = 3,
    w_bm25: float = 0.3,
    w_vector: float = 0.7,
) -> List[Tuple[DocumentChunk, float]]:
    """Tìm kiếm lai kết hợp BM25 (Sparse) và Vector Cosine (Dense) theo trọng số chuẩn:
    Score = 0.3 * BM25_norm + 0.7 * Cosine_norm
    """
    if not chunks:
        return []
    # 1. Tính điểm Sparse BM25
    query_tokens = query.lower().split()
    bm25_raw_scores = list(bm25_index.get_scores(query_tokens))
    # 2. Tính điểm Dense Cosine Similarity
    query_emb = embed_query(query)
    cosine_raw_scores = [
        cosine_similarity(query_emb, emb) if emb is not None else 0.0
        for emb in embeddings
    ]
    # 3. Chuẩn hóa thang điểm [0, 1]
    bm25_norm = normalise_scores(bm25_raw_scores)
    cosine_norm = normalise_scores(cosine_raw_scores)
    # 4. Ghép điểm số lai theo trọng số
    combined_scores: List[Tuple[DocumentChunk, float]] = []
    for i in range(len(chunks)):
        hybrid_score = (w_bm25 * bm25_norm[i]) + (w_vector * cosine_norm[i])
        combined_scores.append((chunks[i], float(hybrid_score)))
    # Sắp xếp giảm dần và lấy top_k
    combined_scores.sort(key=lambda x: x[1], reverse=True)
    return combined_scores[:top_k]
