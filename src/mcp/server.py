"""MCP Server stdio cho Đề tài T4 (Đồ án AIPR).

Cung cấp đúng 2 công cụ cốt lõi đáp ứng R-07 và R-08 (PDF 02 §2):
1. submit_complaint [GHI - Side Effect]: Ghi nhận đơn khiếu nại mới vào data/complaints.json.
2. check_complaint_status [ĐỌC - Verify]: Tra cứu trạng thái đơn để đối soát xác minh (R-07).

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
# 2 MCP TOOLS CỐT LÕI BẮT BUỘC (R-07 & R-08)
# ==============================================================================

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
