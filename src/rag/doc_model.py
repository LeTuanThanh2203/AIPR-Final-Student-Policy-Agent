"""Data Models cho RAG (Kế thừa từ W1/ex2_3_data_model.py & W3/doc_model.py)."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Document:
    """Đại diện cho một tài liệu quy chế (DOC0001, DOC0002...)."""
    content: str
    doc_id: str = ""
    title: str = ""
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class DocumentChunk:
    """Đoạn trích logic theo Điều/Khoản kèm vector embedding."""
    content: str
    chunk_id: str = ""
    doc_id: str = ""
    chunk_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """Kết quả truy xuất tài liệu từ hệ thống RAG."""
    chunk: DocumentChunk
    score: float
    retrieval_mode: str  # "cosine" hoặc "hybrid"
