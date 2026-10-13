"""Typed Schemas và Data Models cho MCP Tools (Đề tài T4 - AIPR Final Project).

Căn cứ yêu cầu R-03 (PDF 02 §2.3) và bài học W1 (ex2_3_data_model.py):
- Định nghĩa schemas bằng @dataclass có type hints đầy đủ.
- Tự thực hiện validation (kiểm tra kiểu, chuỗi rỗng, giá trị âm) trong __post_init__().
- Cung cấp hàm chuyển đổi hai chiều to_dict() và from_dict() phục vụ giao tiếp stdio của MCP.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _validate_non_empty_str(field_name: str, value: Any) -> str:
    """Kiểm tra và chuẩn hóa chuỗi bắt buộc không được rỗng."""
    if not isinstance(value, str):
        raise TypeError(f"Trường '{field_name}' phải là kiểu str, nhận được: {type(value).__name__}")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"Trường '{field_name}' không được để trống hoặc chỉ chứa khoảng trắng.")
    return cleaned


@dataclass
class ActivityInput:
    """Thông tin một hoạt động tham gia để tính điểm rèn luyện."""
    category: str
    name: str
    points: float = 0.0

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Kiểm tra tính hợp lệ của hoạt động rèn luyện."""
        self.category = _validate_non_empty_str("category", self.category)
        self.name = _validate_non_empty_str("name", self.name)

        if not isinstance(self.points, (int, float)):
            raise TypeError(f"Trường 'points' phải là số (int hoặc float), nhận được: {type(self.points).__name__}")
        if self.points < 0:
            raise ValueError(f"Điểm hoạt động 'points' không được âm (nhận: {self.points}).")

    @property
    def raw_points(self) -> float:
        """Alias tương thích ngược cho thuộc tính raw_points."""
        return float(self.points)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "name": self.name,
            "points": float(self.points),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ActivityInput:
        if not isinstance(data, dict):
            raise TypeError(f"Dữ liệu đầu vào phải là dict, nhận được: {type(data).__name__}")
        # Hỗ trợ nhận cả 'points' hoặc 'raw_points'
        pts = data.get("points", data.get("raw_points", 0.0))
        return cls(
            category=data.get("category", ""),
            name=data.get("name", ""),
            points=float(pts),
        )


# Alias tương thích ngược
ActivityItem = ActivityInput


@dataclass
class SubmitComplaintInput:
    """Tham số khi nộp đơn khiếu nại điểm rèn luyện (Tool Ghi - R-07)."""
    student_id: str
    category: str
    reason: str
    evidence: str = ""

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Kiểm tra các trường bắt buộc của đơn khiếu nại."""
        self.student_id = _validate_non_empty_str("student_id", self.student_id)
        self.category = _validate_non_empty_str("category", self.category)
        self.reason = _validate_non_empty_str("reason", self.reason)

        if self.evidence is None:
            self.evidence = ""
        elif not isinstance(self.evidence, str):
            raise TypeError(f"Trường 'evidence' phải là kiểu str, nhận được: {type(self.evidence).__name__}")
        else:
            self.evidence = self.evidence.strip()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "category": self.category,
            "reason": self.reason,
            "evidence": self.evidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SubmitComplaintInput:
        if not isinstance(data, dict):
            raise TypeError(f"Dữ liệu đầu vào phải là dict, nhận được: {type(data).__name__}")
        return cls(
            student_id=data.get("student_id", ""),
            category=data.get("category", ""),
            reason=data.get("reason", ""),
            evidence=data.get("evidence", ""),
        )


@dataclass
class SubmitComplaintOutput:
    """Kết quả trả về sau khi tạo đơn khiếu nại."""
    complaint_id: str
    status: str = "pending_review"
    message: str = "Khiếu nại đã được ghi nhận và đang chờ xét duyệt."
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        self.complaint_id = _validate_non_empty_str("complaint_id", self.complaint_id)
        self.status = _validate_non_empty_str("status", self.status)
        if not isinstance(self.message, str):
            raise TypeError(f"Trường 'message' phải là kiểu str, nhận được: {type(self.message).__name__}")
        if not isinstance(self.created_at, str):
            raise TypeError(f"Trường 'created_at' phải là kiểu str, nhận được: {type(self.created_at).__name__}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "complaint_id": self.complaint_id,
            "status": self.status,
            "message": self.message,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SubmitComplaintOutput:
        if not isinstance(data, dict):
            raise TypeError(f"Dữ liệu đầu vào phải là dict, nhận được: {type(data).__name__}")
        return cls(
            complaint_id=data.get("complaint_id", ""),
            status=data.get("status", "pending_review"),
            message=data.get("message", "Khiếu nại đã được ghi nhận và đang chờ xét duyệt."),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class CheckComplaintInput:
    """Tham số khi tra cứu trạng thái đơn khiếu nại (Tool Đọc để VERIFY - R-07)."""
    complaint_id: str

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        self.complaint_id = _validate_non_empty_str("complaint_id", self.complaint_id)

    def to_dict(self) -> Dict[str, Any]:
        return {"complaint_id": self.complaint_id}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CheckComplaintInput:
        if not isinstance(data, dict):
            raise TypeError(f"Dữ liệu đầu vào phải là dict, nhận được: {type(data).__name__}")
        return cls(complaint_id=data.get("complaint_id", ""))


@dataclass
class ListComplaintsInput:
    """Tham số khi tra cứu toàn bộ đơn khiếu nại của sinh viên (Tool Đọc)."""
    student_id: str

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        self.student_id = _validate_non_empty_str("student_id", self.student_id)

    def to_dict(self) -> Dict[str, Any]:
        return {"student_id": self.student_id}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ListComplaintsInput:
        if not isinstance(data, dict):
            raise TypeError(f"Dữ liệu đầu vào phải là dict, nhận được: {type(data).__name__}")
        return cls(student_id=data.get("student_id", ""))


@dataclass
class CalculateDRLInput:
    """Tham số khi tính điểm rèn luyện (Tầng b - Tính toán)."""
    student_id: str
    semester: str
    activities: List[ActivityInput] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        self.student_id = _validate_non_empty_str("student_id", self.student_id)
        self.semester = _validate_non_empty_str("semester", self.semester)

        if not isinstance(self.activities, list):
            raise TypeError(f"Trường 'activities' phải là List[ActivityInput], nhận được: {type(self.activities).__name__}")

        validated_activities: List[ActivityInput] = []
        for idx, item in enumerate(self.activities):
            if isinstance(item, ActivityInput):
                item.validate()
                validated_activities.append(item)
            elif isinstance(item, dict):
                validated_activities.append(ActivityInput.from_dict(item))
            else:
                raise TypeError(
                    f"Hoạt động thứ {idx} phải là ActivityInput hoặc dict, nhận được: {type(item).__name__}"
                )
        self.activities = validated_activities

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "semester": self.semester,
            "activities": [act.to_dict() for act in self.activities],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CalculateDRLInput:
        if not isinstance(data, dict):
            raise TypeError(f"Dữ liệu đầu vào phải là dict, nhận được: {type(data).__name__}")
        raw_activities = data.get("activities", [])
        return cls(
            student_id=data.get("student_id", ""),
            semester=data.get("semester", ""),
            activities=raw_activities,
        )


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
        self.validate()

    def validate(self) -> None:
        self.complaint_id = _validate_non_empty_str("complaint_id", self.complaint_id)
        self.student_id = _validate_non_empty_str("student_id", self.student_id)
        self.category = _validate_non_empty_str("category", self.category)
        self.reason = _validate_non_empty_str("reason", self.reason)

        if self.evidence is None:
            self.evidence = ""
        elif not isinstance(self.evidence, str):
            raise TypeError(f"Trường 'evidence' phải là kiểu str, nhận được: {type(self.evidence).__name__}")
        else:
            self.evidence = self.evidence.strip()

        self.status = _validate_non_empty_str("status", self.status)
        if not isinstance(self.created_at, str):
            raise TypeError(f"Trường 'created_at' phải là kiểu str, nhận được: {type(self.created_at).__name__}")
        if not isinstance(self.updated_at, str):
            raise TypeError(f"Trường 'updated_at' phải là kiểu str, nhận được: {type(self.updated_at).__name__}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "complaint_id": self.complaint_id,
            "student_id": self.student_id,
            "category": self.category,
            "reason": self.reason,
            "evidence": self.evidence,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ComplaintRecord:
        if not isinstance(data, dict):
            raise TypeError(f"Dữ liệu đầu vào phải là dict, nhận được: {type(data).__name__}")
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
