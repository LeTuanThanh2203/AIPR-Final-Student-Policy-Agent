"""RAG Module (Xây dựng trực tiếp từ các bài tập W3_LAB và W4_2).

Các module cốt lõi:
- doc_model: Document, DocumentChunk, SearchResult (W1, W3, W4_2)
- vector_store: DocumentStore, VectorStore, cosine_similarity, embed_text, embed_query (W3_LAB, W4_2)
- hybrid_search: build_bm25_index, normalise_scores, hybrid_search (W4_2/ex2_1_hybrid_search.py)
- rag_pipeline: build_rag_prompt, search_chunks, rag_pipeline (W4_2/ex2_2_rag_pipeline_v2.py)
- document_parser: parse_and_chunk_documents (W3/recursive_chunking.py)
"""

from src.rag.doc_model import Document, DocumentChunk, SearchResult
from src.rag.vector_store import (
    DocumentStore,
    VectorStore,
    cosine_similarity,
    embed_text,
    embed_query,
)
from src.rag.hybrid_search import (
    build_bm25_index,
    normalise_scores,
    hybrid_search,
)
from src.rag.rag_pipeline import (
    build_rag_prompt,
    search_chunks,
    rag_pipeline,
)
from src.rag.document_parser import parse_and_chunk_documents

__all__ = [
    "Document",
    "DocumentChunk",
    "SearchResult",
    "DocumentStore",
    "VectorStore",
    "cosine_similarity",
    "embed_text",
    "embed_query",
    "build_bm25_index",
    "normalise_scores",
    "hybrid_search",
    "build_rag_prompt",
    "search_chunks",
    "rag_pipeline",
    "parse_and_chunk_documents",
]
