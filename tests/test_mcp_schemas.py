"""Unit tests for MCP Typed Schemas (Đề tài T4 - AIPR Final Project).

Kiểm thử toàn diện:
- Tạo đối tượng hợp lệ cho cả 7 schema.
- Giá trị mặc định (status="pending_review", created_at, message).
- Kiểm tra tính hợp lệ và bắt lỗi (ValueError, TypeError) khi dữ liệu rỗng, sai kiểu hoặc số âm.
- Khả năng chuyển đổi hai chiều to_dict() và from_dict().
- Tính tương thích của ActivityInput và alias ActivityItem.
"""

import os
import sys

# Đảm bảo đường dẫn import src hoạt động dù chạy từ bất kỳ thư mục nào
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    import pytest
except ImportError:
    import re
    from contextlib import contextmanager

    # Fallback giả lập pytest.raises nếu người dùng chạy bằng Python thường chưa cài pytest
    class _PytestFallback:
        @staticmethod
        @contextmanager
        def raises(expected_exc, match=None):
            try:
                yield
            except expected_exc as err:
                if match and not re.search(match, str(err)):
                    raise AssertionError(f"Lỗi '{err}' không khớp mẫu regex '{match}'")
            except Exception as err:
                raise AssertionError(f"Kỳ vọng {expected_exc.__name__}, nhận {type(err).__name__}: {err}")
            else:
                raise AssertionError(f"Kỳ vọng ngoại lệ {expected_exc.__name__} nhưng không có lỗi xảy ra.")

    pytest = _PytestFallback()

from src.mcp.schemas import (
    ActivityInput,
    ActivityItem,
    SubmitComplaintInput,
    SubmitComplaintOutput,
    CheckComplaintInput,
    ListComplaintsInput,
    CalculateDRLInput,
    ComplaintRecord,
)


# ==============================================================================
# 1. Tests cho ActivityInput / ActivityItem
# ==============================================================================

def test_activity_input_valid():
    act = ActivityInput(category="Tiêu chí 3", name="Tham gia Mùa hè xanh", points=15.0)
    assert act.category == "Tiêu chí 3"
    assert act.name == "Tham gia Mùa hè xanh"
    assert act.points == 15.0
    assert act.raw_points == 15.0  # Alias backward compatibility

    # Test serialization
    data = act.to_dict()
    assert data == {"category": "Tiêu chí 3", "name": "Tham gia Mùa hè xanh", "points": 15.0}

    # Test deserialization
    reconstructed = ActivityInput.from_dict(data)
    assert reconstructed == act


def test_activity_input_from_dict_with_raw_points():
    """Kiểm tra from_dict hỗ trợ key 'raw_points' của code cũ."""
    data = {"category": "Tiêu chí 1", "name": "Học tập tốt", "raw_points": 20.0}
    act = ActivityInput.from_dict(data)
    assert act.category == "Tiêu chí 1"
    assert act.name == "Học tập tốt"
    assert act.points == 20.0


def test_activity_item_alias():
    """Kiểm tra ActivityItem là alias của ActivityInput."""
    assert ActivityItem is ActivityInput
    act = ActivityItem(category="TC2", name="Văn nghệ", points=5.0)
    assert isinstance(act, ActivityInput)


def test_activity_input_invalid_empty_fields():
    with pytest.raises(ValueError, match="category"):
        ActivityInput(category="", name="Tham gia hiến máu", points=5.0)

    with pytest.raises(ValueError, match="category"):
        ActivityInput(category="   ", name="Tham gia hiến máu", points=5.0)

    with pytest.raises(ValueError, match="name"):
        ActivityInput(category="Tiêu chí 4", name="", points=5.0)


def test_activity_input_negative_points():
    with pytest.raises(ValueError, match="không được âm"):
        ActivityInput(category="Tiêu chí 1", name="Vi phạm", points=-2.0)


def test_activity_input_invalid_types():
    with pytest.raises(TypeError, match="str"):
        ActivityInput(category=123, name="Hội thảo", points=5.0)  # type: ignore

    with pytest.raises(TypeError, match="points"):
        ActivityInput(category="TC1", name="Hội thảo", points="5đ")  # type: ignore


# ==============================================================================
# 2. Tests cho SubmitComplaintInput
# ==============================================================================

def test_submit_complaint_input_valid():
    inp = SubmitComplaintInput(
        student_id="21120001",
        category="Tiêu chí 3",
        reason="Em bị sót 5 điểm hoạt động Mùa hè xanh",
        evidence="https://chungnhan.edu.vn/mhx-2024.jpg",
    )
    assert inp.student_id == "21120001"
    assert inp.category == "Tiêu chí 3"
    assert inp.reason == "Em bị sót 5 điểm hoạt động Mùa hè xanh"
    assert inp.evidence == "https://chungnhan.edu.vn/mhx-2024.jpg"

    # Test dictionary roundtrip
    d = inp.to_dict()
    assert d["student_id"] == "21120001"
    restored = SubmitComplaintInput.from_dict(d)
    assert restored == inp


def test_submit_complaint_input_default_evidence():
    inp = SubmitComplaintInput(
        student_id="21120002",
        category="Tiêu chí 1",
        reason="Điểm thi học kỳ chưa cập nhật",
    )
    assert inp.evidence == ""


def test_submit_complaint_input_invalid_empty():
    with pytest.raises(ValueError, match="student_id"):
        SubmitComplaintInput(student_id="", category="TC1", reason="Lý do")

    with pytest.raises(ValueError, match="category"):
        SubmitComplaintInput(student_id="21120001", category="  ", reason="Lý do")

    with pytest.raises(ValueError, match="reason"):
        SubmitComplaintInput(student_id="21120001", category="TC1", reason="")


def test_submit_complaint_input_invalid_type():
    with pytest.raises(TypeError, match="student_id"):
        SubmitComplaintInput(student_id=21120001, category="TC1", reason="Lý do")  # type: ignore


# ==============================================================================
# 3. Tests cho SubmitComplaintOutput
# ==============================================================================

def test_submit_complaint_output_valid():
    out = SubmitComplaintOutput(complaint_id="CPL-2026-001")
    assert out.complaint_id == "CPL-2026-001"
    assert out.status == "pending_review"  # Thống nhất mặc định ban đầu
    assert "chờ xét duyệt" in out.message
    assert out.created_at != ""

    d = out.to_dict()
    assert d["complaint_id"] == "CPL-2026-001"
    assert d["status"] == "pending_review"

    restored = SubmitComplaintOutput.from_dict(d)
    assert restored.complaint_id == out.complaint_id
    assert restored.status == out.status


def test_submit_complaint_output_invalid():
    with pytest.raises(ValueError, match="complaint_id"):
        SubmitComplaintOutput(complaint_id="")


# ==============================================================================
# 4. Tests cho CheckComplaintInput
# ==============================================================================

def test_check_complaint_input_valid():
    inp = CheckComplaintInput(complaint_id="CPL-2026-001")
    assert inp.complaint_id == "CPL-2026-001"
    assert inp.to_dict() == {"complaint_id": "CPL-2026-001"}

    restored = CheckComplaintInput.from_dict({"complaint_id": "CPL-2026-001"})
    assert restored.complaint_id == "CPL-2026-001"


def test_check_complaint_input_invalid():
    with pytest.raises(ValueError, match="complaint_id"):
        CheckComplaintInput(complaint_id="   ")

    with pytest.raises(TypeError, match="complaint_id"):
        CheckComplaintInput(complaint_id=12345)  # type: ignore


# ==============================================================================
# 5. Tests cho ListComplaintsInput
# ==============================================================================

def test_list_complaints_input_valid():
    inp = ListComplaintsInput(student_id="21120001")
    assert inp.student_id == "21120001"
    assert inp.to_dict() == {"student_id": "21120001"}

    restored = ListComplaintsInput.from_dict({"student_id": "21120001"})
    assert restored.student_id == "21120001"


def test_list_complaints_input_invalid():
    with pytest.raises(ValueError, match="student_id"):
        ListComplaintsInput(student_id="")


# ==============================================================================
# 6. Tests cho CalculateDRLInput
# ==============================================================================

def test_calculate_drl_input_valid_with_objects():
    act1 = ActivityInput(category="Tiêu chí 1", name="Điểm học tập", points=18.0)
    act2 = ActivityInput(category="Tiêu chí 3", name="Mùa hè xanh", points=15.0)

    inp = CalculateDRLInput(
        student_id="21120001",
        semester="HK1-2024-2025",
        activities=[act1, act2],
    )
    assert inp.student_id == "21120001"
    assert inp.semester == "HK1-2024-2025"
    assert len(inp.activities) == 2
    assert inp.activities[0].points == 18.0

    d = inp.to_dict()
    assert d["student_id"] == "21120001"
    assert len(d["activities"]) == 2

    restored = CalculateDRLInput.from_dict(d)
    assert len(restored.activities) == 2
    assert restored.activities[1].name == "Mùa hè xanh"


def test_calculate_drl_input_auto_convert_dicts():
    """Kiểm tra CalculateDRLInput tự động chuyển đổi dict sang ActivityInput."""
    raw_data = {
        "student_id": "21120002",
        "semester": "HK2-2024-2025",
        "activities": [
            {"category": "Tiêu chí 2", "name": "Tham gia CLB", "points": 10.0},
            {"category": "Tiêu chí 3", "name": "Hiến máu", "points": 5.0},
        ],
    }
    inp = CalculateDRLInput.from_dict(raw_data)
    assert len(inp.activities) == 2
    assert isinstance(inp.activities[0], ActivityInput)
    assert inp.activities[0].category == "Tiêu chí 2"
    assert inp.activities[1].points == 5.0


def test_calculate_drl_input_invalid():
    with pytest.raises(ValueError, match="student_id"):
        CalculateDRLInput(student_id="", semester="HK1-2024-2025")

    with pytest.raises(ValueError, match="semester"):
        CalculateDRLInput(student_id="21120001", semester="")

    with pytest.raises(TypeError, match="activities"):
        CalculateDRLInput(student_id="21120001", semester="HK1", activities="invalid")  # type: ignore


# ==============================================================================
# 7. Tests cho ComplaintRecord
# ==============================================================================

def test_complaint_record_valid():
    rec = ComplaintRecord(
        complaint_id="CPL-2026-001",
        student_id="21120001",
        category="Tiêu chí 3",
        reason="Thiếu điểm hoạt động",
    )
    assert rec.complaint_id == "CPL-2026-001"
    assert rec.status == "pending_review"  # Mặc định ban đầu
    assert rec.evidence == ""
    assert rec.created_at != ""
    assert rec.updated_at != ""

    d = rec.to_dict()
    assert d["complaint_id"] == "CPL-2026-001"
    assert d["status"] == "pending_review"

    restored = ComplaintRecord.from_dict(d)
    assert restored.complaint_id == rec.complaint_id
    assert restored.status == "pending_review"


def test_complaint_record_invalid():
    with pytest.raises(ValueError, match="complaint_id"):
        ComplaintRecord(
            complaint_id="",
            student_id="21120001",
            category="TC1",
            reason="Lý do",
        )


if __name__ == "__main__":
    import inspect
    current_module = sys.modules[__name__]
    test_functions = [
        obj for name, obj in inspect.getmembers(current_module)
        if inspect.isfunction(obj) and name.startswith("test_")
    ]
    print(f"=== Running {len(test_functions)} test cases for MCP Schemas ===")
    passed = 0
    for func in test_functions:
        try:
            func()
            passed += 1
            print(f"  [PASS] {func.__name__}")
        except Exception as err:
            print(f"  [FAIL] {func.__name__}: {err}")
    print(f"\nResult: {passed}/{len(test_functions)} test cases PASSED!")
