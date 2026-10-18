"""Vector Store & Cosine Similarity (Kế thừa từ W3_LAB/lab3_vector_store.py & W4_2)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from dotenv import load_dotenv

try:
    from jina_embeddings import jina_embeddings
except ImportError:
    jina_embeddings = None

from src.rag.doc_model import Document, DocumentChunk

load_dotenv()

JINA_MODEL = "jina-embeddings-v3"

def _embed(text: str, model: str = JINA_MODEL) -> List[float]:
    """Tạo vector embedding cho văn bản bằng Jina AI."""

    cleaned = text.replace("\n", " ").strip()

    if not cleaned:
        raise ValueError("Văn bản đầu vào không được để trống.")

    api_key = os.getenv("JINA_API_KEY")

    if not api_key:
        raise ValueError(
            "Không tìm thấy JINA_API_KEY. "
            "Vui lòng kiểm tra file .env."
        )

    if jina_embeddings is None:
        raise ImportError(
            "Chưa cài đặt thư viện jina_embeddings. "
            "Vui lòng kiểm tra môi trường hoặc sử dụng tìm kiếm BM25."
        )

    response = jina_embeddings(
        input=cleaned,
        model=model,
        api_key=api_key,
    )

    return response.data[0].embedding

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Tính độ tương quan Cosine Similarity: dot(a, b) / (norm(a) * norm(b))."""
    if not a or not b:
        return 0.0

    if len(a) != len(b):
        raise ValueError(
            "Hai vector embedding phải có cùng số chiều."
        )

    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)

    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    sim = float(np.dot(va, vb) / (norm_a * norm_b))

    return max(0.0, min(1.0, sim))


def embed_text(text: str, model: str = JINA_MODEL) -> List[float]:
    """Tạo vector embedding cho passage qua API."""
    
    return _embed(text, model)



def embed_query(query: str, model: str = JINA_MODEL) -> List[float]:
    """Tạo vector embedding cho query qua API."""

    return _embed(query, model)


@dataclass
class DocumentStore:
    """Kho lưu trữ cơ sở cho các văn bản và đoạn trích (W3_LAB)."""
    documents: Dict[str, Document] = field(default_factory=dict)
    chunks: Dict[str, DocumentChunk] = field(default_factory=dict)

    def add(self, document: Document) -> str:
        """Gán doc_id nếu chưa có, lưu vào self.documents."""
        if not document.doc_id:
            document.doc_id = f"DOC{len(self.documents) + 1:04d}"
        self.documents[document.doc_id] = document
        return document.doc_id


@dataclass
class VectorStore(DocumentStore):
    """VectorStore hỗ trợ tìm kiếm ngữ nghĩa theo Cosine Similarity (W3_LAB & W4_2)."""
    def add_chunk(self, chunk: DocumentChunk) -> str:
        """Tự động embed_text nếu chunk.embedding is None, lưu vào self.chunks."""
        if not chunk.chunk_id:
            chunk.chunk_id = f"{chunk.doc_id}_C{chunk.chunk_index:03d}" if chunk.doc_id else f"CHUNK_{len(self.chunks) + 1:04d}"
        if chunk.embedding is None:
            chunk.embedding = embed_text(chunk.content)
        self.chunks[chunk.chunk_id] = chunk
        return chunk.chunk_id
    def search(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.0,
        candidates: Optional[List[DocumentChunk]] = None,
    ) -> List[Tuple[DocumentChunk, float]]:
        """Tìm kiếm tương đồng Cosine Similarity giữa câu query và các đoạn trích."""
        chunk_pool = candidates if candidates is not None else list(self.chunks.values())
        if not chunk_pool:
            return []
        query_emb = embed_query(query)
        scored_chunks: List[Tuple[DocumentChunk, float]] = []
        for chunk in chunk_pool:
            if chunk.embedding is None:
                continue
            sim = cosine_similarity(query_emb, chunk.embedding)
            if sim >= min_score:
                scored_chunks.append((chunk, sim))
        # Sắp xếp giảm dần theo điểm số
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]
    def save(self, path: str) -> None:
        """Lưu toàn bộ documents và chunks ra file JSON."""
        target_path = Path(path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "documents": {doc_id: doc.to_dict() for doc_id, doc in self.documents.items()},
            "chunks": {chk_id: chk.to_dict() for chk_id, chk in self.chunks.items()},
        }
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    def load(self, path: str) -> None:
        """Nạp lại documents và chunks từ file JSON."""
        target_path = Path(path)
        if not target_path.exists():
            return
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.documents = {
            doc_id: Document.from_dict(doc_data)
            for doc_id, doc_data in data.get("documents", {}).items()
        }
        self.chunks = {
            chk_id: DocumentChunk.from_dict(chk_data)
            for chk_id, chk_data in data.get("chunks", {}).items()
        }
