"""Document Parser & Logical Chunking (Kế thừa từ W3/recursive_chunking.py)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import List



PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.doc_model import DocumentChunk


# CẤU HÌNH CÁC FILE VĂN BẢN
SOURCE_FILES = [
    "data/raw/HTRL_2022.txt",
    "data/raw/HTRL_2024.txt",
    "data/raw/HTRL.txt",
]

OUTPUT_PATH = "data/processed/chunks.json"

VERSION_BY_FILE = {
    "HTRL_2022.txt": "2022",
    "HTRL_2024.txt": "2024",
    "HTRL.txt": "main",
}


# CẤU HÌNH 5 TIÊU CHÍ CỦA PHỤ LỤC 1
CRITERIA = [
    (
        "I",
        "5",
        "Tiêu chí I: Ý thức và kết quả học tập",
    ),
    (
        "II",
        "6",
        "Tiêu chí II: Chấp hành nội quy, quy chế",
    ),
    (
        "III",
        "7",
        "Tiêu chí III: Hoạt động chính trị - xã hội, văn hóa, thể thao",
    ),
    (
        "IV",
        "8",
        "Tiêu chí IV: Phẩm chất công dân trong quan hệ cộng đồng",
    ),
    (
        "V",
        "9",
        "Tiêu chí V: Tham gia công tác lớp, đoàn thể",
    ),
]


# HÀM XỬ LÝ ĐƯỜNG DẪN VÀ PHIÊN BẢN
def resolve_path(path: str) -> Path:
    """Chuyển đường dẫn tương đối thành đường dẫn từ gốc project."""
    result = Path(path)

    if not result.is_absolute():
        result = PROJECT_ROOT / result

    return result


def extract_version(filename: str) -> str:
    """Lấy nhãn phiên bản từ tên file."""
    return VERSION_BY_FILE.get(filename, "main")


def make_doc_id(source_path: Path, version: str) -> str:
    """Tạo ID riêng cho từng tài liệu và phiên bản."""
    return f"DOC_{source_path.stem}_v{version}"


def make_version_year(version: str) -> int | None:
    """Chuyển phiên bản dạng năm thành số nguyên."""
    return int(version) if version.isdigit() else None


# TÁCH PHẦN THÂN QUY CHẾ THEO TỪNG ĐIỀU
def extract_articles(
    text: str,
    doc_id: str,
    version: str,
    source_name: str,
    start_index: int = 0,
) -> List[DocumentChunk]:
    """Tách phần thân quy chế thành các chunk theo từng Điều."""

    chunks: List[DocumentChunk] = []

    # Nhận dạng các dạng:
    # Điều 1. Phạm vi điều chỉnh
    # Điều 2: Mục đích
    # Điều 3 Đối tượng áp dụng
    article_pattern = (
        r"(?m)^[ \t]*Điều[ \t]+(\d+)"
        r"[ \t]*[.:]?[ \t]*([^\r\n]*)"
    )

    matches = list(
        re.finditer(article_pattern, text, re.IGNORECASE)
    )

    # Xác định vị trí bắt đầu Phụ lục 1.
    appendix_match = re.search(
        r"(?im)^[ \t]*Phụ\s+lục\s+1\b",
        text,
    )

    appendix_pos = (
        appendix_match.start()
        if appendix_match
        else len(text)
    )

    # Chỉ lấy các Điều nằm trước Phụ lục 1.
    matches = [
        match
        for match in matches
        if match.start() < appendix_pos
    ]

    for i, match in enumerate(matches):
        article_number = match.group(1)
        article_title = match.group(2).strip()

        start_pos = match.start()

        if i + 1 < len(matches):
            end_pos = matches[i + 1].start()
        else:
            end_pos = appendix_pos

        content = text[start_pos:end_pos].strip()

        if not content:
            continue

        chunk_index = start_index + len(chunks) + 1

        chunk = DocumentChunk(
            chunk_id=f"{doc_id}_D{article_number.zfill(2)}",
            doc_id=doc_id,
            chunk_index=chunk_index,
            version=version,
            version_year=make_version_year(version),
            content=content,
            metadata={
                "doc_id": doc_id,
                "version": version,
                "version_year": make_version_year(version),
                "dieu": article_number,
                "title": article_title or f"Điều {article_number}",
                "source": source_name,
                "type": "dieu_khoan",
            },
        )

        chunks.append(chunk)

    return chunks


# TÁCH PHỤ LỤC 1 THÀNH 5 TIÊU CHÍ
def extract_appendix_criteria(
    text: str,
    doc_id: str,
    version: str,
    source_name: str,
    start_index: int = 0,
) -> List[DocumentChunk]:
    """Tách Phụ lục 1 thành các chunk theo 5 tiêu chí."""

    chunks: List[DocumentChunk] = []

    appendix_match = re.search(
        r"(?im)^[ \t]*Phụ\s+lục\s+1\b",
        text,
    )

    if not appendix_match:
        return chunks

    appendix_text = text[appendix_match.start():]

    # Nhận diện tiêu đề TIÊU CHÍ I, II, III, IV, V.
    criteria_matches = list(
        re.finditer(
            r"(?im)^[ \t]*TIÊU\s+CHÍ\s+"
            r"(IV|III|II|I|V)\b",
            appendix_text,
        )
    )

    for i, match in enumerate(criteria_matches):
        roman = match.group(1).upper()

        criterion = next(
            (
                item
                for item in CRITERIA
                if item[0] == roman
            ),
            None,
        )

        if criterion is None:
            continue

        _, mapped_article, criterion_title = criterion

        start_pos = match.start()

        if i + 1 < len(criteria_matches):
            end_pos = criteria_matches[i + 1].start()
        else:
            end_pos = len(appendix_text)

        content = appendix_text[start_pos:end_pos].strip()

        if not content:
            continue

        chunk_index = start_index + len(chunks) + 1

        chunk = DocumentChunk(
            chunk_id=f"{doc_id}_PL1_TC{roman}",
            doc_id=doc_id,
            chunk_index=chunk_index,
            version=version,
            version_year=make_version_year(version),
            content=(
                f"[Phiên bản {version} - "
                f"Phụ lục 1 - {criterion_title}]\n"
                f"{content}"
            ),
            metadata={
                "doc_id": doc_id,
                "version": version,
                "version_year": make_version_year(version),
                "dieu": mapped_article,
                "tieu_chi": roman,
                "title": criterion_title,
                "source": source_name,
                "type": "phu_luc_tieu_chi",
            },
        )

        chunks.append(chunk)

    return chunks


# ĐỌC NHIỀU FILE VÀ SINH LOGICAL CHUNKS
def parse_and_chunk_documents(
    source_files: List[str] | None = None,
    output_path: str = OUTPUT_PATH,
) -> List[DocumentChunk]:
    """
    Đọc nhiều phiên bản quy chế, tách theo từng Điều và
    Tiêu chí, gắn metadata phiên bản và lưu chung vào JSON.
    """

    if source_files is None:
        source_files = SOURCE_FILES

    all_chunks: List[DocumentChunk] = []
    version_stats = []

    for source_file in source_files:
        source_path = resolve_path(source_file)

        if not source_path.is_file():
            raise FileNotFoundError(
                f"Không tìm thấy file dữ liệu: {source_path}"
            )

        text = source_path.read_text(encoding="utf-8-sig")

        if not text.strip():
            print(
                f"[DocumentParser] Bỏ qua file rỗng: "
                f"{source_path.name}"
            )
            continue

        version = extract_version(source_path.name)
        doc_id = make_doc_id(source_path, version)

        # Tách phần thân quy chế.
        article_chunks = extract_articles(
            text=text,
            doc_id=doc_id,
            version=version,
            source_name=source_path.name,
            start_index=len(all_chunks),
        )

        all_chunks.extend(article_chunks)

        # Tách Phụ lục 1.
        criterion_chunks = extract_appendix_criteria(
            text=text,
            doc_id=doc_id,
            version=version,
            source_name=source_path.name,
            start_index=len(all_chunks),
        )

        all_chunks.extend(criterion_chunks)

        total_file_chunks = (
            len(article_chunks) + len(criterion_chunks)
        )

        version_stats.append({
            "file": source_path.name,
            "version": version,
            "doc_id": doc_id,
            "article_chunks": len(article_chunks),
            "criterion_chunks": len(criterion_chunks),
            "total_chunks": total_file_chunks,
        })

        print(f"\n[DocumentParser] File: {source_path.name}")
        print(f"  Phiên bản: {version}")
        print(f"  Document ID: {doc_id}")
        print(f"  Số Điều: {len(article_chunks)}")
        print(f"  Số Tiêu chí: {len(criterion_chunks)}")
        print(f"  Tổng chunks: {total_file_chunks}")

    # LƯU TOÀN BỘ CHUNKS VÀO JSON
    out_file = resolve_path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with out_file.open("w", encoding="utf-8") as f:
        json.dump(
            [chunk.to_dict() for chunk in all_chunks],
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("\n========== TỔNG KẾT ==========")
    print(f"Số file đã xử lý: {len(version_stats)}")
    print(f"Tổng logical chunks: {len(all_chunks)}")

    for stat in version_stats:
        print(
            f"- {stat['file']} | "
            f"version={stat['version']} | "
            f"chunks={stat['total_chunks']}"
        )

    print(f"\nĐã lưu dữ liệu vào: {out_file}")

    return all_chunks



if __name__ == "__main__":
    parse_and_chunk_documents()
