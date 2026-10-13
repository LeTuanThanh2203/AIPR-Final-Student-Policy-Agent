"""Typed Schemas cho MCP Tools (Đề tài T4).

Căn cứ yêu cầu R-03 (PDF 02 §2.3) & bài học W1 (ex2_3_data_model.py):
- Khai báo schema bằng @dataclass có type hints, không dùng dict thô.
- Phục vụ kiểm tra: `grep -n "@dataclass"` của Giảng viên.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SubmitComplaintInput:
    """Tham số khi nộp đơn khiếu nại điểm rèn luyện (Tool Ghi)."""
    student_id: str
    category: str
    reason: str
    evidence: str = ""


@dataclass
class SubmitComplaintOutput:
    """Kết quả trả về sau khi tạo đơn khiếu nại."""
    complaint_id: str
    status: str
    message: str


@dataclass
class CheckComplaintInput:
    """Tham số khi tra cứu trạng thái đơn khiếu nại (Tool Đọc để VERIFY)."""
    complaint_id: str


@dataclass
class ListComplaintsInput:
    """Tham số khi xem toàn bộ lịch sử khiếu nại của sinh viên (Tool Đọc)."""
    student_id: str


@dataclass
class ActivityItem:
    """Một hoạt động rèn luyện sinh viên tham gia để tính điểm."""
    category: str      # Ví dụ: "Tieu_chi_1", "Tieu_chi_3"
    name: str          # Ví dụ: "Tham gia Mùa hè xanh"
    raw_points: float  # Điểm thô của hoạt động


@dataclass
class CalculateDRLInput:
    """Tham số khi tính điểm rèn luyện và áp mức trần (Tầng b - Tính toán)."""
    student_id: str
    semester: str
    activities: List[ActivityItem] = field(default_factory=list)


@dataclass
class ComplaintRecord:
    """Bản ghi lưu trữ trong CSDL file data/complaints.json."""
    complaint_id: str
    student_id: str
    category: str
    reason: str
    evidence: str
    status: str
    created_at: str
