"""MCP Server stdio cho Đề tài T4 (Kế thừa từ W7/ex2_1_mcp_server.py).

Tuân thủ quy định:
- R-03: Khai báo type hints đầy đủ tương ứng với Schemas dataclass.
- R-07: Có tool Ghi (submit_complaint) và tool Đọc (check_complaint_status) để VERIFY.
- R-08: Giao tiếp qua stdio, stdout sạch 100% (mọi debug log phải in qua sys.stderr).
"""

from __future__ import annotations
import sys
from typing import List, Optional
from mcp.server.fastmcp import FastMCP
from src.mcp.schemas import (
    SubmitComplaintInput,
    CheckComplaintInput,
    ListComplaintsInput,
    CalculateDRLInput,
)

# Khởi tạo MCP Server (stdout phải sạch 100%, log debug xuất qua sys.stderr - R-08)
mcp = FastMCP("aipr-complaints-server")


@mcp.tool()
def submit_complaint(student_id: str, category: str, reason: str, evidence: str = "") -> str:
    """Tool Ghi: Tiếp nhận đơn khiếu nại và lưu vào data/complaints.json (Tầng c - R-07)."""
    # Gợi ý: Tạo mã CPL-xxx, ghi bản ghi vào file data/complaints.json, trả về chuỗi JSON kết quả
    pass


@mcp.tool()
def check_complaint_status(complaint_id: str) -> str:
    """Tool Đọc: Kiểm tra trạng thái đơn khiếu nại (bước BẮT BUỘC VERIFY sau khi ghi - R-07)."""
    # Gợi ý: Đọc file data/complaints.json theo complaint_id để xác minh dữ liệu đã được ghi thật
    pass


@mcp.tool()
def list_student_complaints(student_id: str) -> str:
    """Tool Đọc: Liệt kê tất cả các đơn khiếu nại của sinh viên (Tra cứu lịch sử)."""
    # Gợi ý: Lọc danh sách khiếu nại trong data/complaints.json theo student_id
    pass


@mcp.tool()
def calculate_drl(student_id: str, semester: str, activities_json: str) -> str:
    """Tool Tính toán: Tính tổng điểm rèn luyện và áp mức trần theo từng tiêu chí (Tầng b - R-05)."""
    # Gợi ý: Parse activities_json, tính tổng điểm theo từng tiêu chí (TC1 max 20, TC2 max 25, ...), trả về điểm tổng kết
    pass


if __name__ == "__main__":
    mcp.run()
