"""MCP Server stdio cho Đề tài T4 (Đồ án AIPR).

Cung cấp các công cụ cốt lõi đáp ứng R-05, R-07 và R-08 (PDF 02 §2):
1. lookup_policy [ĐỌC - RAG Tra cứu]: Tra cứu quy chế điểm rèn luyện và trích dẫn căn cứ (Tầng a, b - R-05).
2. submit_complaint [GHI - Side Effect]: Ghi nhận đơn khiếu nại mới vào data/complaints.json (Tầng c - R-07).
3. check_complaint_status [ĐỌC - Verify]: Tra cứu trạng thái đơn để đối soát xác minh (Tầng c - R-07).

Quy chuẩn kỹ thuật:
- Giao thức stdio qua MCPServer (W7).
- stdout sạch 100%, mọi log debug đều chuyển hướng sang sys.stderr (R-08).
- Dùng Typed Schemas @dataclass theo yêu cầu R-03 (grep -n "@dataclass").
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Tương thích MCPServer (chuẩn W7 ex2_1_mcp_server.py)
try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer  # type: ignore

from src.mcp.schemas import (
    CheckComplaintInput,
    ComplaintRecord,
    LookupPolicyInput,
    SubmitComplaintInput,
    SubmitComplaintOutput,
)

DATA_FILE = PROJECT_ROOT / "data" / "complaints.json"

mcp = MCPServer("aipr-complaints-server")


def log_debug(message: str) -> None:
    """Ghi log qua sys.stderr để bảo đảm stdout sạch 100% cho kênh stdio (R-08)."""
    print(f"[MCP-Server] {message}", file=sys.stderr)


def load_complaints() -> List[Dict[str, Any]]:
    """Đọc dữ liệu từ file JSON data/complaints.json."""
    if not DATA_FILE.exists():
        return []
    try:
        content = DATA_FILE.read_text(encoding="utf-8").strip()
        if not content:
            return []
        data = json.loads(content)
        return data if isinstance(data, list) else []
    except Exception as err:
        log_debug(f"Lỗi đọc file {DATA_FILE}: {err}")
        return []


def save_complaints(records: List[Dict[str, Any]]) -> None:
    """Lưu danh sách khiếu nại an toàn vào file JSON."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")


# ==============================================================================
# QUẢN LÝ KHO DỮ LIỆU RAG DÙNG CHUNG (TÂN - MEMBER A)
# ==============================================================================
_rag_store: Any = None


def get_rag_store() -> Any:
    """Khởi tạo và nạp VectorStore tĩnh dùng chung cho các lượt tra cứu RAG."""
    global _rag_store
    if _rag_store is not None:
        return _rag_store

    from src.rag.vector_store import VectorStore
    from src.rag.doc_model import DocumentChunk

    store = VectorStore()
    chunks_path = PROJECT_ROOT / "data" / "processed" / "chunks.json"
    if chunks_path.exists():
        try:
            with open(chunks_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                c = DocumentChunk.from_dict(item)
                store.chunks[c.chunk_id] = c
            log_debug(f"Đã nạp thành công {len(store.chunks)} chunks quy chế từ {chunks_path}")
        except Exception as err:
            log_debug(f"Lỗi khi đọc file chunks {chunks_path}: {err}")
    else:
        # Nếu chưa có chunks.json, kiểm tra nếu có file text nguồn HTRL.txt để parse
        htrl_path = PROJECT_ROOT / "HTRL.txt"
        if htrl_path.exists():
            try:
                from src.rag.document_parser import parse_and_chunk_documents
                parsed_chunks = parse_and_chunk_documents(str(htrl_path), str(chunks_path))
                for c in parsed_chunks:
                    store.chunks[c.chunk_id] = c
                log_debug(f"Đã tự động parse {len(parsed_chunks)} chunks từ {htrl_path}")
            except Exception as err:
                log_debug(f"Không thể tự động parse từ {htrl_path}: {err}")
        else:
            log_debug(f"Chưa tìm thấy file dữ liệu chunks tại {chunks_path}")

    _rag_store = store
    return _rag_store


# ==============================================================================
# HỆ THỐNG MCP TOOLS (R-05, R-07 & R-08)
# ==============================================================================

@mcp.tool()
def lookup_policy(query: str) -> str:
    """Tool Đọc: Tra cứu quy định, điều khoản, tiêu chí và mức điểm rèn luyện theo quy chế (Tầng a & Tầng b - R-05)."""
    try:
        inp = LookupPolicyInput(query=query)
    except Exception as err:
        return json.dumps({"status": "error", "message": f"Dữ liệu không hợp lệ: {err}"}, ensure_ascii=False)

    try:
        store = get_rag_store()
        from src.rag.rag_pipeline import rag_pipeline

        try:
            # Gọi RAG pipeline chuẩn của Tân (Hybrid BM25 + Cosine)
            rag_res = rag_pipeline(inp.query, store, top_k=3, search_mode="hybrid")
        except Exception as search_err:
            log_debug(f"Hybrid search gặp lỗi ({search_err}), chuyển sang dự phòng BM25...")
            from src.rag.hybrid_search import build_bm25_index
            chunks_list = list(store.chunks.values())
            if chunks_list:
                bm25_idx = build_bm25_index(chunks_list)
                query_tokens = inp.query.lower().split()
                scores = bm25_idx.get_scores(query_tokens)
                scored = [(chunks_list[i], float(scores[i])) for i in range(len(chunks_list))]
                scored.sort(key=lambda x: x[1], reverse=True)
                top_chunks = scored[:3]
                rag_res = {
                    "answer": f"Đã tìm thấy {len(top_chunks)} đoạn quy chế phù hợp qua BM25.",
                    "sources": [
                        {
                            "source": c.metadata.get("source", c.doc_id or "unknown"),
                            "dieu": c.metadata.get("dieu", "unknown"),
                            "title": c.metadata.get("title", "unknown"),
                            "content": c.content,
                            "score": score,
                        }
                        for c, score in top_chunks
                    ],
                }
            else:
                rag_res = {
                    "answer": "Thông tin này không có trong quy chế điểm rèn luyện được cung cấp.",
                    "sources": [],
                }

        sources = [
            {
                "source": s.get("source", ""),
                "dieu": s.get("dieu", ""),
                "title": s.get("title", ""),
                "content": s.get("content", ""),
                "score": s.get("score", 0.0),
            }
            for s in rag_res.get("sources", [])
        ]

        output = {
            "status": "success" if sources else "not_found",
            "query": inp.query,
            "answer": rag_res.get("answer", ""),
            "sources": sources,
        }
        log_debug(f"lookup_policy thành công cho query='{inp.query}' - tìm thấy {len(sources)} căn cứ")
        return json.dumps(output, ensure_ascii=False)
    except Exception as err:
        log_debug(f"Lỗi khi thực thi lookup_policy cho query='{query}': {err}")
        return json.dumps({
            "status": "error",
            "query": query,
            "message": f"Lỗi khi tra cứu quy chế: {err}",
            "answer": "Không thể tra cứu quy chế do lỗi hệ thống RAG.",
            "sources": [],
        }, ensure_ascii=False)


@mcp.tool()
def submit_complaint(student_id: str, category: str, reason: str, evidence: str = "") -> str:
    """Tool Ghi: Tiếp nhận đơn khiếu nại điểm rèn luyện và lưu vào data/complaints.json (Tầng c - R-07)."""
    try:
        # 1. Kiểm tra tham số qua Typed Schema @dataclass (R-03)
        inp = SubmitComplaintInput(
            student_id=student_id,
            category=category,
            reason=reason,
            evidence=evidence or "",
        )
    except Exception as err:
        return json.dumps({"status": "error", "message": f"Dữ liệu không hợp lệ: {err}"}, ensure_ascii=False)

    records = load_complaints()

    # 2. Sinh mã đơn định dạng CPL-YYYY-NNNN dễ hiểu cho SV năm 3
    year = datetime.now(timezone.utc).year
    new_id = f"CPL-{year}-{len(records) + 1:04d}"
    now_iso = datetime.now(timezone.utc).isoformat()

    # 3. Tạo bản ghi và lưu trữ
    record = ComplaintRecord(
        complaint_id=new_id,
        student_id=inp.student_id,
        category=inp.category,
        reason=inp.reason,
        evidence=inp.evidence,
        status="pending_review",
        created_at=now_iso,
        updated_at=now_iso,
    )
    records.append(record.to_dict())
    save_complaints(records)

    log_debug(f"Đã lưu thành công đơn {new_id} cho sinh viên {inp.student_id}")

    output = SubmitComplaintOutput(
        complaint_id=new_id,
        status="pending_review",
        message="Khiếu nại đã được ghi nhận thành công và đang chờ xét duyệt.",
        created_at=now_iso,
    )
    return json.dumps(output.to_dict(), ensure_ascii=False)


@mcp.tool()
def check_complaint_status(complaint_id: str) -> str:
    """Tool Đọc: Kiểm tra trạng thái đơn khiếu nại từ đĩa để Verify đối soát (Tầng c - R-07)."""
    try:
        inp = CheckComplaintInput(complaint_id=complaint_id)
    except Exception as err:
        return json.dumps({"status": "error", "message": f"Mã khiếu nại không hợp lệ: {err}"}, ensure_ascii=False)

    search_id = inp.complaint_id.strip().upper()
    records = load_complaints()

    for rec in records:
        if str(rec.get("complaint_id", "")).strip().upper() == search_id:
            log_debug(f"Tìm thấy đơn: {search_id}")
            return json.dumps(rec, ensure_ascii=False)

    log_debug(f"Không tìm thấy đơn: {search_id}")
    return json.dumps({
        "status": "not_found",
        "complaint_id": search_id,
        "message": f"Không tìm thấy đơn khiếu nại có mã '{search_id}'.",
    }, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
