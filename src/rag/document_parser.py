"""Document Parser & Logical Chunking (Kế thừa từ W3/recursive_chunking.py)."""

from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List
from src.rag.doc_model import DocumentChunk


def extract_text_from_file(file_path: Path) -> str:
    """Đọc văn bản từ file .txt, .pdf (pypdf), .docx (python-docx)."""
    # Gợi ý: Đọc file theo phần mở rộng đuôi file
    pass


def parse_and_chunk_documents(
    raw_dir: str = "data/raw", output_path: str = "data/processed/chunks.json"
) -> List[DocumentChunk]:
    """Phân đoạn văn bản quy chế theo từng Điều và Khoản (Logical Chunking - R-05)."""
    # Gợi ý:
    # 1. Duyệt các file trong raw_dir.
    # 2. Dùng regex r"(?=Điều\s+\d+)" và r"(?=Khoản\s+\d+)" để tách logic.
    # 3. Gán metadata: doc_id, dieu, khoan, source -> Lưu vào output_path (JSON).
    pass


if __name__ == "__main__":
    parse_and_chunk_documents()
