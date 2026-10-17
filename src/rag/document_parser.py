"""Document Parser & Logical Chunking (Kế thừa từ W3/recursive_chunking.py)."""

from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List
import sys
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent.parent))
from src.rag.doc_model import DocumentChunk


def parse_and_chunk_documents(
    source_file: str = "data/raw/HTRL.txt",
    output_path: str = "data/processed/chunks.json",
) -> List[DocumentChunk]:
    """
    Đọc văn bản từ HTRL.txt, phân đoạn quy chế theo từng Điều
    và Phụ lục 1 theo 5 Tiêu chí, sau đó lưu vào file JSON.
    """

    # 1. Xác định đường dẫn file nguồn
    source_path = Path(source_file)

    # 2. Kiểm tra file nguồn tồn tại
    if not source_path.is_file():
        raise FileNotFoundError(
            f"Không tìm thấy file dữ liệu: {source_path.resolve()}"
        )

    # 3. Đọc trực tiếp nội dung file TXT
    text = source_path.read_text(encoding="utf-8")

    if not text.strip():
        raise ValueError(f"File {source_path} không có nội dung.")

    all_chunks: List[DocumentChunk] = []
    chunk_counter = 0

    # ID định danh tài liệu nguồn
    doc_id = "DOC0002_quy_che_hcmute"

    # =========================================================
    # 4. TÁCH PHẦN THÂN QUY ĐỊNH THEO TỪNG ĐIỀU
    # =========================================================

    # Tìm các tiêu đề Điều, ví dụ:
    # Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng
    # Điều 2: Mục đích
    dieu_matches = list(
        re.finditer(
            r"(Điều\s+(\d+)[\.: \t]+([^\n]*))",
            text,
        )
    )

    for i, match in enumerate(dieu_matches):
        dieu_num = match.group(2)
        dieu_title = match.group(1).strip()
        start_pos = match.start()

        # Xác định vị trí kết thúc của Điều hiện tại
        if i + 1 < len(dieu_matches):
            end_pos = dieu_matches[i + 1].start()
        else:
            # Nếu là Điều cuối cùng, kết thúc trước Phụ lục 1
            appendix_pos = text.find("Phụ lục 1", start_pos)

            if appendix_pos != -1:
                end_pos = appendix_pos
            else:
                end_pos = len(text)

        dieu_content = text[start_pos:end_pos].strip()

        # Bỏ qua nội dung rỗng
        if not dieu_content:
            continue

        chunk_counter += 1

        chunk = DocumentChunk(
            chunk_id=f"{doc_id}_D{dieu_num.zfill(2)}",
            doc_id=doc_id,
            chunk_index=chunk_counter,
            content=dieu_content,
            metadata={
                "doc_id": doc_id,
                "dieu": dieu_num,
                "title": dieu_title,
                "source": source_path.name,
                "type": "dieu_khoan",
            },
        )

        all_chunks.append(chunk)

    # =========================================================
    # 5. TÁCH PHỤ LỤC 1 THÀNH 5 TIÊU CHÍ
    # =========================================================

    appendix_pos = text.find("Phụ lục 1")

    if appendix_pos != -1:
        appendix_text = text[appendix_pos:]

        # Mỗi tiêu chí được tách thành một logical chunk riêng
        criteria_patterns = [
            (
                "I",
                "5",
                "Tiêu chí I: Ý thức và kết quả học tập",
                r"TIÊU CHÍ I[\s\S]*?(?=TIÊU CHÍ II|$)",
            ),
            (
                "II",
                "6",
                "Tiêu chí II: Chấp hành nội quy, quy chế",
                r"TIÊU CHÍ II[\s\S]*?(?=TIÊU CHÍ III|$)",
            ),
            (
                "III",
                "7",
                "Tiêu chí III: Hoạt động chính trị - xã hội, văn hóa, thể thao",
                r"TIÊU CHÍ III[\s\S]*?(?=TIÊU CHÍ IV|$)",
            ),
            (
                "IV",
                "8",
                "Tiêu chí IV: Phẩm chất công dân trong quan hệ cộng đồng",
                r"TIÊU CHÍ IV[\s\S]*?(?=TIÊU CHÍ V|$)",
            ),
            (
                "V",
                "9",
                "Tiêu chí V: Tham gia công tác lớp, đoàn thể",
                r"TIÊU CHÍ V[\s\S]*?$",
            ),
        ]

        for tc_roman, map_dieu, tc_name, pattern in criteria_patterns:
            match = re.search(pattern, appendix_text)

            if not match:
                continue

            tc_content = match.group(0).strip()

            chunk_counter += 1

            tc_chunk = DocumentChunk(
                chunk_id=f"{doc_id}_PL1_TC{tc_roman}",
                doc_id=doc_id,
                chunk_index=chunk_counter,
                content=f"[Phụ lục 1 - {tc_name}]\n{tc_content}",
                metadata={
                    "doc_id": doc_id,
                    "dieu": map_dieu,
                    "tieu_chi": tc_roman,
                    "title": tc_name,
                    "source": source_path.name,
                    "type": "phu_luc_tieu_chi",
                },
            )

            all_chunks.append(tc_chunk)

    # =========================================================
    # 6. LƯU TOÀN BỘ CHUNKS VÀO FILE JSON
    # =========================================================

    out_file = Path(output_path)

    # Tạo thư mục đầu ra nếu chưa tồn tại
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with out_file.open("w", encoding="utf-8") as f:
        json.dump(
            [chunk.to_dict() for chunk in all_chunks],
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"[DocumentParser] Đã đọc file: {source_path.name}"
    )
    print(
        f"[DocumentParser] Số Điều tìm thấy: {len(dieu_matches)}"
    )
    print(
        f"[DocumentParser] Tổng logical chunks: {len(all_chunks)}"
    )
    print(
        f"[DocumentParser] Đã lưu dữ liệu vào: {out_file}"
    )

    return all_chunks


if __name__ == "__main__":
    parse_and_chunk_documents()
