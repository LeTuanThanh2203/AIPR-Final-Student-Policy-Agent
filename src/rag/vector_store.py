"""Vector Store & Cosine Similarity (Kế thừa từ W3_LAB/lab3_vector_store.py & W4_2)."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np

from src.rag.doc_model import Document, DocumentChunk


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Tính độ tương quan Cosine Similarity: dot(a, b) / (norm(a) * norm(b))."""
    # Gợi ý: Dùng np.dot và np.linalg.norm
    pass


def embed_text(text: str) -> List[float]:
    """Tạo vector embedding cho passage qua API."""
    # Gợi ý: Gọi client.embeddings.create(input=text)
    pass


def embed_query(query: str) -> List[float]:
    """Tạo vector embedding cho query qua API."""
    # Gợi ý: Gọi client.embeddings.create(input=query)
    pass


@dataclass
class DocumentStore:
    """Kho lưu trữ cơ sở cho các văn bản và đoạn trích (W3_LAB)."""
    documents: Dict[str, Document] = field(default_factory=dict)
    chunks: Dict[str, DocumentChunk] = field(default_factory=dict)

    def add(self, document: Document) -> str:
        # Gợi ý: Gán doc_id nếu chưa có, lưu vào self.documents
        pass


@dataclass
class VectorStore(DocumentStore):
    """VectorStore hỗ trợ tìm kiếm ngữ nghĩa theo Cosine Similarity (W3_LAB & W4_2)."""

    def add_chunk(self, chunk: DocumentChunk) -> str:
        # Gợi ý: Tự động embed_text nếu chunk.embedding is None, lưu vào self.chunks
        pass

    def search(
        self, query: str, top_k: int = 3, min_score: float = 0.0
    ) -> List[Tuple[DocumentChunk, float]]:
        # Gợi ý: Tạo embed_query(query) -> Tính cosine_similarity với từng chunk -> Sort -> Top_k
        pass

    def save(self, path: str) -> None:
        # Gợi ý: Lưu self.documents và self.chunks ra file JSON
        pass

    def load(self, path: str) -> None:
        # Gợi ý: Nạp lại self.documents và self.chunks từ file JSON
        pass
