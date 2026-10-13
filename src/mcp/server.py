"""MCP Server stdio cho Đề tài T4 (Đồ án AIPR).

Cung cấp 3 tool quản lý khiếu nại điểm rèn luyện lưu trữ thật trên đĩa (R-07, R-08):
1. submit_complaint: Ghi nhận đơn khiếu nại mới vào data/complaints.json
2. check_complaint_status: Tra cứu trạng thái đơn (bước BẮT BUỘC VERIFY theo R-07)
3. list_student_complaints: Liệt kê danh sách khiếu nại của sinh viên

Đặc tả kỹ thuật:
- Giao tiếp stdio 100% sạch: mọi log debug xuất qua sys.stderr.
- Đường dẫn file dữ liệu complaints.json ổn định theo project root.
- Ghi dữ liệu an toàn (atomic write) tránh mất mát hoặc hư hỏng file.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Tương thích cả mcp 2.x (MCPServer) và mcp 1.x (FastMCP)
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP  # type: ignore

from src.mcp.schemas import (
    SubmitComplaintInput,
    SubmitComplaintOutput,
    CheckComplaintInput,
    ListComplaintsInput,
    ComplaintRecord,
)

# Khởi tạo MCP Server
mcp = FastMCP("aipr-complaints-server")

# Đường dẫn mặc định tới file complaints.json
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATA_FILE = PROJECT_ROOT / "data" / "complaints.json"


def get_data_file_path() -> Path:
    """Lấy đường dẫn file dữ liệu complaints.json (cho phép override qua biến môi trường để test)."""
    custom_path = os.environ.get("AIPR_COMPLAINTS_FILE")
    if custom_path:
        return Path(custom_path)
    return DEFAULT_DATA_FILE


def _log(msg: str) -> None:
    """Ghi log qua sys.stderr để giữ stdout sạch 100% cho kênh stdio (R-08)."""
    print(f"[MCP-Server] {msg}", file=sys.stderr)


# ==============================================================================
# HÀM XỬ LÝ LƯU TRỮ (STORAGE HELPERS)
# ==============================================================================

def load_complaints(file_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Đọc danh sách khiếu nại từ file JSON trên đĩa.
    
    Xử lý an toàn các trường hợp: file chưa tồn tại, file rỗng, hoặc lỗi cú pháp JSON.
    """
    target_path = file_path or get_data_file_path()
    if not target_path.exists():
        _log(f"File chưa tồn tại, trả về danh sách rỗng: {target_path}")
        return []

    try:
        content = target_path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        data = json.loads(content)
        if not isinstance(data, list):
            _log(f"Dữ liệu trong {target_path} không phải là list. Khởi tạo rỗng.")
            return []
        return data
    except json.JSONDecodeError as err:
        _log(f"Lỗi phân tích JSON tại {target_path}: {err}")
        raise RuntimeError(f"File dữ liệu bị hỏng hoặc sai cú pháp JSON: {err}") from err
    except Exception as err:
        _log(f"Lỗi khi đọc file {target_path}: {err}")
        raise IOError(f"Không thể đọc file dữ liệu khiếu nại: {err}") from err


def save_complaints(records: List[Dict[str, Any]], file_path: Optional[Path] = None) -> None:
    """Ghi danh sách khiếu nại xuống đĩa bằng cơ chế atomic write (ghi file tạm rồi đổi tên).
    
    Giúp tránh tình trạng file bị corrupt nếu mất điện hoặc crash giữa chừng.
    """
    target_path = file_path or get_data_file_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = target_path.with_suffix(".tmp")
    try:
        content = json.dumps(records, ensure_ascii=False, indent=2)
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(target_path)
    except Exception as err:
        _log(f"Lỗi ghi dữ liệu tại {target_path}: {err}")
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        raise IOError(f"Ghi file dữ liệu thất bại: {err}") from err


def generate_complaint_id(existing_records: List[Dict[str, Any]]) -> str:
    """Sinh mã khiếu nại duy nhất định dạng CPL-YYYY-NNNN, đảm bảo không bao giờ trùng lặp."""
    year = datetime.now(timezone.utc).year
    prefix = f"CPL-{year}-"
    existing_ids = {str(r.get("complaint_id", "")).strip() for r in existing_records}

    max_num = 0
    for cid in existing_ids:
        if cid.startswith(prefix):
            suffix = cid[len(prefix):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))

    candidate_num = max_num + 1
    new_id = f"CPL-{year}-{candidate_num:04d}"
    while new_id in existing_ids:
        candidate_num += 1
        new_id = f"CPL-{year}-{candidate_num:04d}"

    return new_id


# ==============================================================================
# ĐĂNG KÝ CÁC MCP TOOLS
# ==============================================================================

@mcp.tool()
def submit_complaint(student_id: str, category: str, reason: str, evidence: str = "") -> str:
    """Tool Ghi: Tiếp nhận đơn khiếu nại điểm rèn luyện và lưu vào complaints.json (Tầng c - R-07)."""
    # 1. Validate dữ liệu đầu vào qua Schema
    try:
        inp = SubmitComplaintInput(
            student_id=student_id,
            category=category,
            reason=reason,
            evidence=evidence,
        )
    except (ValueError, TypeError) as val_err:
        _log(f"Dữ liệu nộp khiếu nại không hợp lệ: {val_err}")
        return json.dumps({
            "status": "error",
            "message": f"Dữ liệu không hợp lệ: {val_err}"
        }, ensure_ascii=False)

    # 2. Đọc dữ liệu hiện có
    try:
        records = load_complaints()
    except Exception as read_err:
        return json.dumps({
            "status": "error",
            "message": f"Không thể đọc cơ sở dữ liệu hiện có: {read_err}"
        }, ensure_ascii=False)

    # 3. Tạo ID duy nhất và bản ghi ComplaintRecord
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

    # 4. Ghi dữ liệu thật xuống đĩa (không trả success giả nếu ghi thất bại)
    records.append(record.to_dict())
    try:
        save_complaints(records)
    except Exception as save_err:
        _log(f"Lưu khiếu nại thất bại: {save_err}")
        return json.dumps({
            "status": "error",
            "message": f"Lưu khiếu nại thất bại: {save_err}"
        }, ensure_ascii=False)

    _log(f"Đã ghi nhận thành công khiếu nại: {new_id} cho sinh viên {inp.student_id}")

    # 5. Trả về kết quả xác nhận lấy từ record đã lưu
    output = SubmitComplaintOutput(
        complaint_id=record.complaint_id,
        status=record.status,
        message="Khiếu nại đã được ghi nhận và đang chờ xét duyệt.",
        created_at=record.created_at,
    )
    return json.dumps(output.to_dict(), ensure_ascii=False)


@mcp.tool()
def check_complaint_status(complaint_id: str) -> str:
    """Tool Đọc: Kiểm tra trạng thái đơn khiếu nại từ đĩa (BẮT BUỘC VERIFY sau khi ghi - R-07)."""
    # 1. Validate mã khiếu nại
    try:
        inp = CheckComplaintInput(complaint_id=complaint_id)
    except (ValueError, TypeError) as val_err:
        _log(f"Mã tra cứu không hợp lệ: {val_err}")
        return json.dumps({
            "status": "error",
            "message": f"Mã tra cứu không hợp lệ: {val_err}"
        }, ensure_ascii=False)

    # 2. Đọc dữ liệu từ đĩa
    try:
        records = load_complaints()
    except Exception as read_err:
        return json.dumps({
            "status": "error",
            "message": f"Lỗi đọc dữ liệu: {read_err}"
        }, ensure_ascii=False)

    # 3. Tìm bản ghi khớp với complaint_id
    search_id = inp.complaint_id.strip().upper()
    for rec in records:
        if str(rec.get("complaint_id", "")).strip().upper() == search_id:
            _log(f"Đã tìm thấy khiếu nại: {search_id}")
            return json.dumps(rec, ensure_ascii=False)

    # 4. Trả về thông báo không tìm thấy
    _log(f"Không tìm thấy khiếu nại với mã: {inp.complaint_id}")
    return json.dumps({
        "status": "not_found",
        "complaint_id": inp.complaint_id,
        "message": f"Không tìm thấy khiếu nại có mã '{inp.complaint_id}'."
    }, ensure_ascii=False)


@mcp.tool()
def list_student_complaints(student_id: str) -> str:
    """Tool Đọc: Liệt kê tất cả các đơn khiếu nại của một sinh viên (Tra cứu lịch sử)."""
    # 1. Validate mã số sinh viên
    try:
        inp = ListComplaintsInput(student_id=student_id)
    except (ValueError, TypeError) as val_err:
        _log(f"MSSV không hợp lệ: {val_err}")
        return json.dumps({
            "status": "error",
            "message": f"Mã số sinh viên không hợp lệ: {val_err}"
        }, ensure_ascii=False)

    # 2. Đọc dữ liệu từ đĩa
    try:
        records = load_complaints()
    except Exception as read_err:
        return json.dumps({
            "status": "error",
            "message": f"Lỗi đọc dữ liệu: {read_err}"
        }, ensure_ascii=False)

    # 3. Lọc danh sách theo student_id
    clean_id = inp.student_id.strip()
    student_records = [rec for rec in records if str(rec.get("student_id", "")).strip() == clean_id]

    _log(f"Tìm thấy {len(student_records)} khiếu nại của sinh viên: {clean_id}")
    return json.dumps(student_records, ensure_ascii=False)


# ==============================================================================
# GHI CHÚ GIAO TIẾP TÍCH HỢP (INTERFACE GỢI Ý)
# ==============================================================================
# Interface dự kiến tích hợp cho Tool calculate_drl (Tầng b - R-05):
# Sẽ đăng ký @mcp.tool() sau khi Member A hoàn thiện module tính điểm và áp trần.
# Prototype:
# def calculate_drl(student_id: str, semester: str, activities_json: str) -> str:
#     ...


if __name__ == "__main__":
    mcp.run()
