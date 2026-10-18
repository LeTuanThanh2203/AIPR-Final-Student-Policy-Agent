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

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi đối tượng Document thành Dictionary."""
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "source": self.source,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Document:
        """Tái tạo Document từ Dictionary."""
        created_at_val = data.get("created_at")
        if isinstance(created_at_val, str):
            try:
                created_at = datetime.fromisoformat(created_at_val)
            except ValueError:
                created_at = datetime.now()
        else:
            created_at = created_at_val or datetime.now()
        return cls(
            content=data.get("content", ""),
            doc_id=data.get("doc_id", ""),
            title=data.get("title", ""),
            source=data.get("source", ""),
            metadata=data.get("metadata", {}),
            created_at=created_at,
        )

@dataclass
class DocumentChunk:
    """Đoạn trích logic theo Điều/Khoản kèm vector embedding."""
    content: str
    chunk_id: str = ""
    doc_id: str = ""
    chunk_index: int = 0
    version: str = ""
    version_year: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi DocumentChunk thành Dictionary để lưu JSON."""
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "chunk_index": self.chunk_index,
            "version": self.version,
            "version_year": self.version_year,
            "content": self.content,
            "metadata": self.metadata,
            "embedding": self.embedding,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DocumentChunk:
        """Khôi phục DocumentChunk từ Dictionary."""
        metadata = data.get("metadata", {})
        version = data.get("version") or metadata.get("version", "")
        version_year = (
            data.get("version_year")
            if data.get("version_year") is not None
            else metadata.get("version_year")
        )
        return cls(
            content=data.get("content", ""),
            chunk_id=data.get("chunk_id", ""),
            doc_id=data.get("doc_id", ""),
            chunk_index=data.get("chunk_index", 0),
            version=version,
            version_year=version_year,
            metadata=metadata,
            embedding=data.get("embedding"),
        )


@dataclass
class SearchResult:
    """Kết quả truy xuất tài liệu từ hệ thống RAG."""
    chunk: DocumentChunk
    score: float
    retrieval_mode: str  # "cosine" hoặc "hybrid"
