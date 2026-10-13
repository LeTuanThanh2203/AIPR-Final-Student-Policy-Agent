"""Unit tests for MCP Server Tools & Storage (Đề tài T4 - AIPR Final Project).

Kiểm thử toàn diện 3 MCP Tools theo yêu cầu:
1. Tạo khiếu nại thành công (submit_complaint).
2. Đọc lại record vừa lưu để verify (check_complaint_status - R-07).
3. Tra cứu ID không tồn tại (not_found).
4. Lọc theo student_id (list_student_complaints).
5. Xử lý đầu vào không hợp lệ (chuỗi rỗng, khoảng trắng).
6. Xử lý an toàn file chưa tồn tại và file JSON bị lỗi/hỏng.
7. Lỗi ghi đĩa không bao giờ được báo thành công giả.
8. Đảm bảo 2 lần tạo không bao giờ sinh trùng ID.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Generator

# Bootstrap project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import pytest
except ImportError:
    # Fallback cho chạy bằng python thuần
    class _MockPytest:
        @staticmethod
        def fixture(func):
            return func
    pytest = _MockPytest()  # type: ignore

from src.mcp.server import (
    submit_complaint,
    check_complaint_status,
    list_student_complaints,
    load_complaints,
    save_complaints,
    generate_complaint_id,
    get_data_file_path,
)


@pytest.fixture
def temp_complaints_file(tmp_path: Path, monkeypatch) -> Path:
    """Fixture tạo file tạm thời cô lập, không làm bẩn data/complaints.json thật."""
    test_file = tmp_path / "test_complaints.json"
    test_file.write_text("[]", encoding="utf-8")
    monkeypatch.setenv("AIPR_COMPLAINTS_FILE", str(test_file))
    return test_file


# ==============================================================================
# 1. Test tạo khiếu nại và đọc lại để verify (Tầng c - R-07)
# ==============================================================================

def test_submit_complaint_success(temp_complaints_file):
    res_str = submit_complaint(
        student_id="21120001",
        category="Tiêu chí 3",
        reason="Em tham gia Mùa hè xanh nhưng chưa thấy cộng điểm",
        evidence="https://minhchung.edu.vn/mhx.png",
    )
    res = json.loads(res_str)

    assert "complaint_id" in res
    assert res["complaint_id"].startswith("CPL-")
    assert res["status"] == "pending_review"
    assert "chờ xét duyệt" in res["message"]

    # Kiểm tra dữ liệu thực sự đã được ghi vào file đĩa
    file_records = json.loads(temp_complaints_file.read_text(encoding="utf-8"))
    assert len(file_records) == 1
    assert file_records[0]["complaint_id"] == res["complaint_id"]
    assert file_records[0]["student_id"] == "21120001"
    assert file_records[0]["category"] == "Tiêu chí 3"
    assert file_records[0]["evidence"] == "https://minhchung.edu.vn/mhx.png"


def test_check_complaint_status_after_submit(temp_complaints_file):
    """Kiểm tra luồng VERIFY: submit xong phải đọc lại được đúng record đó."""
    res_submit = json.loads(submit_complaint(
        student_id="21120002",
        category="Tiêu chí 1",
        reason="Điểm rèn luyện học kỳ 1 bị tính thiếu",
    ))
    cid = res_submit["complaint_id"]

    # Đọc lại trạng thái
    res_check = json.loads(check_complaint_status(cid))
    assert res_check["complaint_id"] == cid
    assert res_check["student_id"] == "21120002"
    assert res_check["status"] == "pending_review"
    assert res_check["reason"] == "Điểm rèn luyện học kỳ 1 bị tính thiếu"


# ==============================================================================
# 2. Test ID không tồn tại
# ==============================================================================

def test_check_complaint_status_not_found(temp_complaints_file):
    res_check = json.loads(check_complaint_status("CPL-9999-9999"))
    assert res_check["status"] == "not_found"
    assert res_check["complaint_id"] == "CPL-9999-9999"
    assert "Không tìm thấy" in res_check["message"]


# ==============================================================================
# 3. Test lọc theo student_id
# ==============================================================================

def test_list_student_complaints_filter(temp_complaints_file):
    # Nộp 2 đơn cho SV 21120001
    submit_complaint("21120001", "TC1", "Lý do 1")
    submit_complaint("21120001", "TC3", "Lý do 2")
    # Nộp 1 đơn cho SV khác 21120002
    submit_complaint("21120002", "TC2", "Lý do SV khác")

    # Lọc đơn của 21120001
    list_str = list_student_complaints("21120001")
    student_records = json.loads(list_str)
    assert len(student_records) == 2
    assert all(r["student_id"] == "21120001" for r in student_records)

    # Lọc đơn của sinh viên chưa từng nộp
    empty_list = json.loads(list_student_complaints("21129999"))
    assert empty_list == []


# ==============================================================================
# 4. Test input không hợp lệ
# ==============================================================================

def test_submit_complaint_invalid_input(temp_complaints_file):
    # MSSV rỗng
    res1 = json.loads(submit_complaint("", "TC1", "Lý do"))
    assert res1["status"] == "error"
    assert "student_id" in res1["message"]

    # Tiêu chí rỗng
    res2 = json.loads(submit_complaint("21120001", "   ", "Lý do"))
    assert res2["status"] == "error"
    assert "category" in res2["message"]

    # Lý do rỗng
    res3 = json.loads(submit_complaint("21120001", "TC1", ""))
    assert res3["status"] == "error"
    assert "reason" in res3["message"]

    # Đảm bảo không có record nào bị ghi bậy vào file
    file_records = json.loads(temp_complaints_file.read_text(encoding="utf-8"))
    assert len(file_records) == 0


def test_check_and_list_invalid_input(temp_complaints_file):
    res_check = json.loads(check_complaint_status(""))
    assert res_check["status"] == "error"

    res_list = json.loads(list_student_complaints("   "))
    assert res_list["status"] == "error"


# ==============================================================================
# 5. Test xử lý file chưa tồn tại và file JSON bị lỗi
# ==============================================================================

def test_storage_file_not_exist(tmp_path: Path, monkeypatch):
    """Khi file chưa tồn tại, hệ thống tự động khởi tạo danh sách rỗng và ghi được."""
    non_exist_file = tmp_path / "subdir" / "new_complaints.json"
    monkeypatch.setenv("AIPR_COMPLAINTS_FILE", str(non_exist_file))

    # Đọc khi file chưa có
    assert load_complaints() == []

    # Ghi đơn mới sẽ tự tạo file
    res = json.loads(submit_complaint("21120001", "TC1", "Đơn đầu tiên"))
    assert "complaint_id" in res
    assert non_exist_file.exists()


def test_storage_file_corrupted_json(temp_complaints_file):
    """Khi file bị lỗi cú pháp JSON, hệ thống báo lỗi rõ ràng và không crash."""
    temp_complaints_file.write_text("{ đây không phải json hợp lệ ...", encoding="utf-8")

    res_check = json.loads(check_complaint_status("CPL-2026-0001"))
    assert res_check["status"] == "error"
    assert "Lỗi đọc dữ liệu" in res_check["message"]

    res_submit = json.loads(submit_complaint("21120001", "TC1", "Thử nộp khi DB hỏng"))
    assert res_submit["status"] == "error"


# ==============================================================================
# 6. Test lỗi ghi đĩa tuyệt đối không được báo thành công
# ==============================================================================

def test_save_failure_reports_error(temp_complaints_file, monkeypatch):
    """Khi việc ghi file thất bại (IOError), hệ thống phải trả về status error."""
    import src.mcp.server as srv

    def mock_broken_save(records, file_path=None):
        raise IOError("Mô phỏng đĩa đầy hoặc không có quyền ghi!")

    monkeypatch.setattr(srv, "save_complaints", mock_broken_save)

    res = json.loads(submit_complaint("21120001", "TC1", "Lý do"))
    assert res["status"] == "error"
    assert "Lưu khiếu nại thất bại" in res["message"]


# ==============================================================================
# 7. Test hai lần tạo không bao giờ sinh trùng ID
# ==============================================================================

def test_unique_complaint_id_generation(temp_complaints_file):
    res1 = json.loads(submit_complaint("21120001", "TC1", "Khiếu nại 1"))
    res2 = json.loads(submit_complaint("21120001", "TC2", "Khiếu nại 2"))
    res3 = json.loads(submit_complaint("21120002", "TC3", "Khiếu nại 3"))

    id1 = res1["complaint_id"]
    id2 = res2["complaint_id"]
    id3 = res3["complaint_id"]

    assert id1 != id2
    assert id2 != id3
    assert id1 != id3

    # Kiểm tra tính lũy tiến duy nhất
    records = json.loads(temp_complaints_file.read_text(encoding="utf-8"))
    assert len(records) == 3
    assert {r["complaint_id"] for r in records} == {id1, id2, id3}


# ==============================================================================
# ENTRYPOINT CHO PHÉP CHẠY TRỰC TIẾP QUA PYTHON THUẦN
# ==============================================================================

if __name__ == "__main__":
    import inspect
    import shutil

    print("=== Running unit tests for MCP Server (src/mcp/server.py) ===")
    test_funcs = [
        obj for name, obj in inspect.getmembers(sys.modules[__name__])
        if inspect.isfunction(obj) and name.startswith("test_")
    ]

    passed = 0
    temp_dir = Path(tempfile.mkdtemp(prefix="aipr_test_"))
    try:
        test_file = temp_dir / "complaints.json"
        test_file.write_text("[]", encoding="utf-8")
        os.environ["AIPR_COMPLAINTS_FILE"] = str(test_file)

        class MonkeyPatchHelper:
            def __init__(self):
                self._undo_attrs = []
                self._undo_envs = []

            def setenv(self, key, val):
                old = os.environ.get(key)
                self._undo_envs.append((key, old))
                os.environ[key] = val

            def setattr(self, target, name, val):
                old = getattr(target, name)
                self._undo_attrs.append((target, name, old))
                setattr(target, name, val)

            def undo(self):
                for target, name, old in reversed(self._undo_attrs):
                    setattr(target, name, old)
                self._undo_attrs.clear()
                for key, old in reversed(self._undo_envs):
                    if old is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = old
                self._undo_envs.clear()

        mp = MonkeyPatchHelper()

        for func in test_funcs:
            test_file.write_text("[]", encoding="utf-8")
            os.environ["AIPR_COMPLAINTS_FILE"] = str(test_file)
            sig = inspect.signature(func)
            params = sig.parameters
            kwargs = {}
            if "temp_complaints_file" in params:
                kwargs["temp_complaints_file"] = test_file
            if "tmp_path" in params:
                kwargs["tmp_path"] = temp_dir
            if "monkeypatch" in params:
                kwargs["monkeypatch"] = mp

            try:
                func(**kwargs)
                passed += 1
                print(f"  [PASS] {func.__name__}")
            except Exception as err:
                print(f"  [FAIL] {func.__name__}: {err}")
            finally:
                mp.undo()

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    print(f"\nResult: {passed}/{len(test_funcs)} test cases PASSED!")
