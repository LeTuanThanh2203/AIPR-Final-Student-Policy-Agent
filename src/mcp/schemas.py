"""Typed Schemas cho MCP Tools (Đề tài T4 - AIPR Final Project).

Căn cứ yêu cầu R-03 (PDF 02 §2.3) và bài học W1:
- Khai báo schema bằng @dataclass có type hints đầy đủ (grep -n "@dataclass").
- Tự động chuyển đổi dictionary qua asdict() chuẩn Python.
- Tinh gọn tối đa: Chỉ định nghĩa đúng các schema cho 2 tools cốt lõi (submit & check).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


def _require_non_empty(name: str, value: Any) -> str:
    """Kiểm tra và trả về chuỗi đã strip, báo lỗi nếu rỗng hoặc sai kiểu."""
    if not isinstance(value, str):
        raise TypeError(f"Trường '{name}' phải là kiểu str, nhận: {type(value).__name__}")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"Trường '{name}' không được để trống.")
    return cleaned


@dataclass
class SubmitComplaintInput:
    """Tham số đầu vào khi nộp đơn khiếu nại (Tool Ghi - R-07)."""
    student_id: str
    category: str
    reason: str
    evidence: str = ""

    def __post_init__(self) -> None:
        self.student_id = _require_non_empty("student_id", self.student_id)
        self.category = _require_non_empty("category", self.category)
        self.reason = _require_non_empty("reason", self.reason)
        if self.evidence is None:
            self.evidence = ""
        elif not isinstance(self.evidence, str):
            raise TypeError("Trường 'evidence' phải là str.")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def model_json_schema(cls) -> Dict[str, Any]:
        """Tương thích cú pháp Pydantic (W6 ex0_2_pydantic_schema.py)."""
        from pydantic import TypeAdapter
        return TypeAdapter(cls).json_schema()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SubmitComplaintInput:
        return cls(
            student_id=data.get("student_id", ""),
            category=data.get("category", ""),
            reason=data.get("reason", ""),
            evidence=data.get("evidence", ""),
        )


@dataclass
class SubmitComplaintOutput:
    """Kết quả trả về sau khi tạo đơn khiếu nại thành công."""
    complaint_id: str
    status: str = "pending_review"
    message: str = "Khiếu nại đã được ghi nhận và đang chờ xét duyệt."
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        self.complaint_id = _require_non_empty("complaint_id", self.complaint_id)
        self.status = _require_non_empty("status", self.status)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def model_json_schema(cls) -> Dict[str, Any]:
        """Tương thích cú pháp Pydantic (W6 ex0_2_pydantic_schema.py)."""
        from pydantic import TypeAdapter
        return TypeAdapter(cls).json_schema()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SubmitComplaintOutput:
        return cls(
            complaint_id=data.get("complaint_id", ""),
            status=data.get("status", "pending_review"),
            message=data.get("message", "Khiếu nại đã được ghi nhận và đang chờ xét duyệt."),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class CheckComplaintInput:
    """Tham số khi tra cứu trạng thái đơn để Verify (Tool Đọc - R-07)."""
    complaint_id: str

    def __post_init__(self) -> None:
        self.complaint_id = _require_non_empty("complaint_id", self.complaint_id)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def model_json_schema(cls) -> Dict[str, Any]:
        """Tương thích cú pháp Pydantic (W6 ex0_2_pydantic_schema.py)."""
        from pydantic import TypeAdapter
        return TypeAdapter(cls).json_schema()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CheckComplaintInput:
        return cls(complaint_id=data.get("complaint_id", ""))


@dataclass
class LookupPolicyInput:
    """Tham số khi tra cứu quy chế điểm rèn luyện (Tool Đọc - R-05 & Tầng a)."""
    query: str

    def __post_init__(self) -> None:
        self.query = _require_non_empty("query", self.query)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def model_json_schema(cls) -> Dict[str, Any]:
        """Tương thích cú pháp Pydantic (W6 ex0_2_pydantic_schema.py)."""
        from pydantic import TypeAdapter
        return TypeAdapter(cls).json_schema()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LookupPolicyInput:
        return cls(query=data.get("query", ""))


@dataclass
class ComplaintRecord:
    """Bản ghi khiếu nại lưu trữ trong CSDL file data/complaints.json."""
    complaint_id: str
    student_id: str
    category: str
    reason: str
    evidence: str = ""
    status: str = "pending_review"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        self.complaint_id = _require_non_empty("complaint_id", self.complaint_id)
        self.student_id = _require_non_empty("student_id", self.student_id)
        self.category = _require_non_empty("category", self.category)
        self.reason = _require_non_empty("reason", self.reason)
        if self.evidence is None:
            self.evidence = ""
        elif not isinstance(self.evidence, str):
            raise TypeError("Trường 'evidence' phải là str.")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def model_json_schema(cls) -> Dict[str, Any]:
        """Tương thích cú pháp Pydantic (W6 ex0_2_pydantic_schema.py)."""
        from pydantic import TypeAdapter
        return TypeAdapter(cls).json_schema()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ComplaintRecord:
        now_str = datetime.now(timezone.utc).isoformat()
        return cls(
            complaint_id=data.get("complaint_id", ""),
            student_id=data.get("student_id", ""),
            category=data.get("category", ""),
            reason=data.get("reason", ""),
            evidence=data.get("evidence", ""),
            status=data.get("status", "pending_review"),
            created_at=data.get("created_at", now_str),
            updated_at=data.get("updated_at", now_str),
        )
