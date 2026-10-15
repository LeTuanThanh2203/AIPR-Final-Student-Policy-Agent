"""MCP Server stdio cho Đề tài T4 (Đồ án AIPR).

Cung cấp đúng 2 tool tối thiểu đáp ứng R-07 và R-08 (PDF 02 §2):
1. submit_complaint [GHI - Side Effect]: Ghi nhận đơn khiếu nại mới vào data/complaints.json.
2. check_complaint_status [ĐỌC - Verify]: Tra cứu trạng thái đơn để đối soát xác minh (R-07).

Quy chuẩn kỹ thuật:
- Chạy qua giao thức stdio (MCPServer).
- stdout sạch 100%, toàn bộ log debug chuyển hướng sang sys.stderr (R-08).
- Ghi dữ liệu an toàn (atomic write) vào file JSON.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Đảm bảo import được module từ project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Tương thích cả mcp 2.x (MCPServer) và mcp 1.x (FastMCP)
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP  # type: ignore

from src.mcp.schemas import (
    CheckComplaintInput,
    ComplaintRecord,
    SubmitComplaintInput,
    SubmitComplaintOutput,
)

mcp = FastMCP("aipr-complaints-server")
DEFAULT_DATA_FILE = PROJECT_ROOT / "data" / "complaints.json"


def _log(msg: str) -> None:
    """Ghi log qua sys.stderr để bảo đảm stdout sạch 100% cho kênh stdio (R-08)."""
    print(f"[MCP-Server] {msg}", file=sys.stderr)


def get_data_file_path() -> Path:
    """Lấy đường dẫn file dữ liệu complaints.json (hỗ trợ biến môi trường để test)."""
    custom_path = os.environ.get("AIPR_COMPLAINTS_FILE")
    return Path(custom_path) if custom_path else DEFAULT_DATA_FILE


def load_complaints(file_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Đọc dữ liệu từ file JSON."""
    path = file_path or get_data_file_path()
    if not path.exists():
        return []
    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        data = json.loads(content)
        return data if isinstance(data, list) else []
    except Exception as err:
        _log(f"Lỗi khi đọc file {path}: {err}")
        raise IOError(f"Lỗi đọc dữ liệu: {err}") from err


def save_complaints(records: List[Dict[str, Any]], file_path: Optional[Path] = None) -> None:
    """Ghi danh sách khiếu nại an toàn bằng atomic write."""
    path = file_path or get_data_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    try:
        content = json.dumps(records, ensure_ascii=False, indent=2)
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(path)
    except Exception as err:
        _log(f"Lỗi khi ghi file {path}: {err}")
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        raise IOError(f"Lưu khiếu nại thất bại: {err}") from err


def generate_complaint_id(records: List[Dict[str, Any]]) -> str:
    """Sinh mã khiếu nại duy nhất định dạng CPL-YYYY-NNNN."""
    year = datetime.now(timezone.utc).year
    prefix = f"CPL-{year}-"
    max_num = 0
    for r in records:
        cid = str(r.get("complaint_id", "")).strip()
        if cid.startswith(prefix):
            suffix = cid[len(prefix):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
    return f"CPL-{year}-{max_num + 1:04d}"


# ==============================================================================
# ĐÚNG 2 MCP TOOLS TỐI THIỂU BẮT BUỘC (R-07 & R-08)
# ==============================================================================

@mcp.tool()
def submit_complaint(student_id: str, category: str, reason: str, evidence: str = "") -> str:
    """Tool Ghi: Tiếp nhận đơn khiếu nại điểm rèn luyện và lưu vào data/complaints.json (Tầng c - R-07)."""
    try:
        inp = SubmitComplaintInput(
            student_id=student_id,
            category=category,
            reason=reason,
            evidence=evidence or "",
        )
    except (ValueError, TypeError) as val_err:
        return json.dumps({"status": "error", "message": str(val_err)}, ensure_ascii=False)

    try:
        records = load_complaints()
    except Exception as read_err:
        return json.dumps({"status": "error", "message": f"Lỗi đọc dữ liệu: {read_err}"}, ensure_ascii=False)

    new_id = generate_complaint_id(records)
    now_iso = datetime.now(timezone.utc).isoformat()

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

    try:
        save_complaints(records)
    except Exception as save_err:
        return json.dumps({"status": "error", "message": f"Lưu khiếu nại thất bại: {save_err}"}, ensure_ascii=False)

    _log(f"Đã ghi nhận thành công khiếu nại {new_id} cho sinh viên {inp.student_id}")

    output = SubmitComplaintOutput(
        complaint_id=new_id,
        status=record.status,
        message="Khiếu nại đã được ghi nhận và đang chờ xét duyệt.",
        created_at=now_iso,
    )
    return json.dumps(output.to_dict(), ensure_ascii=False)


@mcp.tool()
def check_complaint_status(complaint_id: str) -> str:
    """Tool Đọc: Kiểm tra trạng thái đơn khiếu nại từ đĩa (BẮT BUỘC VERIFY sau khi ghi - R-07)."""
    try:
        inp = CheckComplaintInput(complaint_id=complaint_id)
    except (ValueError, TypeError) as val_err:
        return json.dumps({"status": "error", "message": str(val_err)}, ensure_ascii=False)

    search_id = inp.complaint_id.strip().upper()
    try:
        records = load_complaints()
    except Exception as read_err:
        return json.dumps({"status": "error", "message": f"Lỗi đọc dữ liệu: {read_err}"}, ensure_ascii=False)

    for rec in records:
        if str(rec.get("complaint_id", "")).strip().upper() == search_id:
            _log(f"Tìm thấy khiếu nại: {search_id}")
            return json.dumps(rec, ensure_ascii=False)

    _log(f"Không tìm thấy khiếu nại: {search_id}")
    return json.dumps({
        "status": "not_found",
        "complaint_id": search_id,
        "message": f"Không tìm thấy khiếu nại có mã '{search_id}'.",
    }, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
