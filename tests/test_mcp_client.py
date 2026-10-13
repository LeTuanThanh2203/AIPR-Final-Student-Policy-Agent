"""Unit tests for MCP Client Manager (Đề tài T4 - AIPR Final Project).

Kiểm thử tích hợp thực tế với MCP Server qua kênh stdio:
1. Khám phá công cụ động (Dynamic Tool Discovery) trả về 3 tools thật.
2. Gọi thành công một tool (submit_complaint và check_complaint_status).
3. Gọi tool không tồn tại (xử lý lỗi chuẩn hóa).
4. Xử lý lỗi khi lệnh khởi chạy server không hợp lệ (ConnectionError).
5. Quản lý vòng đời kết nối và dọn dẹp tài nguyên (cleanup).
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Generator

# Bootstrap project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import pytest
except ImportError:
    class _MockPytest:
        @staticmethod
        def fixture(func):
            return func
        @staticmethod
        def mark():
            class _Mark:
                @staticmethod
                def anyio(f):
                    return f
            return _Mark()
    pytest = _MockPytest()  # type: ignore

from src.mcp.client import MCPClientManager, ToolDefinition, ToolCallResult


@pytest.fixture
def temp_complaints_file(tmp_path: Path, monkeypatch) -> Path:
    """Fixture tạo file tạm thời cô lập cho server."""
    test_file = tmp_path / "test_client_complaints.json"
    test_file.write_text("[]", encoding="utf-8")
    monkeypatch.setenv("AIPR_COMPLAINTS_FILE", str(test_file))
    return test_file


# ==============================================================================
# 1. Test Khám phá công cụ động (Dynamic Tool Discovery)
# ==============================================================================

@pytest.mark.anyio
async def test_client_tool_discovery(temp_complaints_file):
    """Client kết nối server thật và khám phá động danh sách công cụ."""
    async with MCPClientManager() as client:
        assert client.is_connected is True

        tools = await client.list_available_tools()
        assert len(tools) == 3
        tool_names = [t.name for t in tools]

        assert "submit_complaint" in tool_names
        assert "check_complaint_status" in tool_names
        assert "list_student_complaints" in tool_names

        # Đảm bảo mỗi tool có description và input_schema
        for tool in tools:
            assert isinstance(tool, ToolDefinition)
            assert tool.name != ""
            assert tool.description != ""
            assert isinstance(tool.input_schema, dict)


# ==============================================================================
# 2. Test Gọi thành công tool thật qua MCP Server
# ==============================================================================

@pytest.mark.anyio
async def test_client_call_tool_success(temp_complaints_file):
    """Client gọi tool Ghi (submit) và tool Đọc (check) thành công."""
    async with MCPClientManager() as client:
        # Gọi tool submit_complaint
        submit_args = {
            "student_id": "21120001",
            "category": "Tiêu chí 3",
            "reason": "Thiếu điểm Mùa hè xanh",
            "evidence": "https://minhchung.edu.vn/mhx.jpg",
        }
        res_submit = await client.call_tool("submit_complaint", submit_args)

        assert isinstance(res_submit, ToolCallResult)
        assert res_submit.is_error is False
        assert res_submit.tool_name == "submit_complaint"
        assert res_submit.raw_data is not None

        cid = res_submit.raw_data["complaint_id"]
        assert cid.startswith("CPL-")
        assert res_submit.raw_data["status"] == "pending_review"

        # Gọi tool check_complaint_status để VERIFY
        check_args = {"complaint_id": cid}
        res_check = await client.call_tool("check_complaint_status", check_args)

        assert res_check.is_error is False
        assert res_check.tool_name == "check_complaint_status"
        assert res_check.raw_data is not None
        assert res_check.raw_data["complaint_id"] == cid
        assert res_check.raw_data["student_id"] == "21120001"


# ==============================================================================
# 3. Test Gọi tool không tồn tại
# ==============================================================================

@pytest.mark.anyio
async def test_client_call_tool_not_found(temp_complaints_file):
    """Khi gọi tool không có trên server, kết quả trả về chuẩn hóa is_error=True."""
    async with MCPClientManager() as client:
        # Load danh sách tool trước
        await client.list_available_tools()

        res = await client.call_tool("non_existent_tool_xyz", {"foo": "bar"})
        assert res.is_error is True
        assert res.tool_name == "non_existent_tool_xyz"
        assert "không tồn tại" in res.content or "Unknown tool" in res.content


# ==============================================================================
# 4. Test Lỗi khi khởi chạy server thất bại
# ==============================================================================

@pytest.mark.anyio
async def test_client_connection_error_on_invalid_command():
    """Khi command không tồn tại, client ném ConnectionError rõ ràng."""
    bad_client = MCPClientManager(command="non_existent_command_12345")
    try:
        await bad_client.connect()
        assert False, "Kỳ vọng ConnectionError nhưng không xảy ra"
    except ConnectionError as err:
        assert "Không tìm thấy lệnh" in str(err)
    finally:
        await bad_client.close()


# ==============================================================================
# 5. Test Vòng đời kết nối và dọn dẹp tài nguyên (Lifecycle Cleanup)
# ==============================================================================

@pytest.mark.anyio
async def test_client_lifecycle_and_cleanup(temp_complaints_file):
    """Kiểm tra quản lý vòng đời connect, close và context manager."""
    client = MCPClientManager()
    assert client.is_connected is False

    await client.connect()
    assert client.is_connected is True

    # Gọi thử 1 tool khi đang mở kết nối
    res = await client.call_tool("list_student_complaints", {"student_id": "21129999"})
    assert res.is_error is False

    await client.close()
    assert client.is_connected is False

    # Đóng lần thứ 2 không gây lỗi
    await client.close()
    assert client.is_connected is False


@pytest.mark.anyio
async def test_client_call_list_student_complaints(temp_complaints_file):
    """Client gọi tool list_student_complaints để tra cứu danh sách khiếu nại của SV."""
    async with MCPClientManager() as client:
        # Nộp 2 đơn cho SV 21120001 và 1 đơn cho SV 21120002
        await client.call_tool("submit_complaint", {
            "student_id": "21120001",
            "category": "TC1",
            "reason": "Đơn 1 của SV 1",
        })
        await client.call_tool("submit_complaint", {
            "student_id": "21120001",
            "category": "TC3",
            "reason": "Đơn 2 của SV 1",
        })
        await client.call_tool("submit_complaint", {
            "student_id": "21120002",
            "category": "TC2",
            "reason": "Đơn của SV 2",
        })

        # Gọi tool list_student_complaints
        res = await client.call_tool("list_student_complaints", {"student_id": "21120001"})
        assert res.is_error is False
        assert isinstance(res.raw_data, list)
        assert len(res.raw_data) == 2
        assert all(r["student_id"] == "21120001" for r in res.raw_data)

        # Gọi cho sinh viên không có đơn
        res_empty = await client.call_tool("list_student_complaints", {"student_id": "21129999"})
        assert res_empty.is_error is False
        assert res_empty.raw_data == []


@pytest.mark.anyio
async def test_client_call_tool_validation_error(temp_complaints_file):
    """Client nhận phản hồi lỗi từ tool một cách an toàn mà không bị crash."""
    async with MCPClientManager() as client:
        # Gửi MSSV rỗng
        res = await client.call_tool("submit_complaint", {
            "student_id": "",
            "category": "TC1",
            "reason": "Lý do",
        })
        assert res.is_error is False  # Server xử lý lỗi mềm và trả JSON status: error
        assert res.raw_data is not None
        assert res.raw_data["status"] == "error"
        assert "student_id" in res.raw_data["message"]


@pytest.mark.anyio
async def test_client_auto_connect_on_demand(temp_complaints_file):
    """Client tự động kết nối nếu người dùng gọi call_tool mà chưa gọi connect()."""
    client = MCPClientManager()
    assert client.is_connected is False

    try:
        # Gọi tool trực tiếp không qua await client.connect()
        res = await client.call_tool("check_complaint_status", {"complaint_id": "CPL-9999-9999"})
        assert client.is_connected is True
        assert res.raw_data["status"] == "not_found"
    finally:
        await client.close()


@pytest.mark.anyio
async def test_tool_call_result_str_and_properties():
    """Kiểm tra tính năng ép kiểu str và thuộc tính của ToolCallResult."""
    result = ToolCallResult(
        tool_name="test_tool",
        is_error=False,
        content='{"status": "ok"}',
        raw_data={"status": "ok"},
    )
    assert str(result) == '{"status": "ok"}'
    assert result.is_error is False
    assert result.raw_data == {"status": "ok"}


# ==============================================================================
# ENTRYPOINT CHO PHÉP CHẠY TRỰC TIẾP QUA PYTHON THUẦN
# ==============================================================================

if __name__ == "__main__":
    import shutil
    import tempfile

    print("=== Running integration tests for MCP Client (src/mcp/client.py) ===")
    temp_dir = Path(tempfile.mkdtemp(prefix="aipr_client_test_"))
    try:
        test_file = temp_dir / "complaints.json"
        test_file.write_text("[]", encoding="utf-8")
        os.environ["AIPR_COMPLAINTS_FILE"] = str(test_file)

        async def run_all():
            tests = [
                ("test_client_tool_discovery", test_client_tool_discovery(test_file)),
                ("test_client_call_tool_success", test_client_call_tool_success(test_file)),
                ("test_client_call_tool_not_found", test_client_call_tool_not_found(test_file)),
                ("test_client_connection_error_on_invalid_command", test_client_connection_error_on_invalid_command()),
                ("test_client_lifecycle_and_cleanup", test_client_lifecycle_and_cleanup(test_file)),
            ]
            passed = 0
            for name, coro in tests:
                try:
                    await coro
                    passed += 1
                    print(f"  [PASS] {name}")
                except Exception as err:
                    print(f"  [FAIL] {name}: {err}")
            print(f"\nResult: {passed}/{len(tests)} test cases PASSED!")

        asyncio.run(run_all())

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
