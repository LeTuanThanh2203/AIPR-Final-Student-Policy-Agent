"""Unit tests cho ReAct Agent Orchestrator (Phase 5).

Kiểm thử toàn diện các tình huống theo yêu cầu:
1. LLM trả lời ngay, không cần tool.
2. LLM yêu cầu gọi một tool hợp lệ.
3. Quy tắc R-07: Bắt buộc verify sau khi gọi submit_complaint.
4. Output LLM bị lỗi định dạng (malformed JSON) và tự hồi phục.
5. Thiếu trường bắt buộc trong JSON.
6. Gọi tool không tồn tại.
7. Tool trả lỗi khi thực thi.
8. Vòng lặp dừng đúng giới hạn MAX_STEPS = 10 (chống lặp vô hạn).
9. Tích hợp SessionLogger ghi nhận trace và usage.
10. Parser hoạt động chính xác với nhiều định dạng markdown JSON mà không dùng eval().
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union
import pytest

from src.mcp.client import ToolCallResult, ToolDefinition
from src.orchestrator import (
    MAX_STEPS,
    ReActOrchestrator,
    format_tools_description,
    parse_llm_decision,
    validate_decision,
)


class MockLLMClient:
    """Mock LLM Client tương thích interface RobustLLMClient (Teammate C)."""

    def __init__(self, responses: List[Union[str, Dict[str, Any]]]) -> None:
        self.responses = list(responses)
        self.call_count = 0
        self.received_messages: List[List[Dict[str, str]]] = []

    def generate(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        self.received_messages.append(messages)
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
        else:
            resp = self.responses[-1]

        if isinstance(resp, str):
            return {
                "content": resp,
                "usage": {"prompt_tokens": 50, "completion_tokens": 20},
            }
        return resp


class MockMCPClient:
    """Mock MCP Client cung cấp danh sách công cụ và thực thi công cụ."""

    def __init__(self, tools: Optional[List[ToolDefinition]] = None) -> None:
        self.tools = tools if tools is not None else [
            ToolDefinition(
                name="submit_complaint",
                description="Ghi nhận đơn khiếu nại mới vào hệ thống",
                input_schema={"type": "object", "properties": {"student_id": {"type": "string"}}},
            ),
            ToolDefinition(
                name="check_complaint_status",
                description="Tra cứu trạng thái đơn khiếu nại (bước verify R-07)",
                input_schema={"type": "object", "properties": {"complaint_id": {"type": "string"}}},
            ),
            ToolDefinition(
                name="list_student_complaints",
                description="Liệt kê danh sách khiếu nại của sinh viên",
                input_schema={"type": "object", "properties": {"student_id": {"type": "string"}}},
            ),
            ToolDefinition(
                name="failing_tool",
                description="Công cụ mô phỏng lỗi thực thi",
                input_schema={},
            ),
        ]
        self.called_tools: List[tuple[str, Dict[str, Any]]] = []

    async def list_available_tools(self) -> List[ToolDefinition]:
        return self.tools

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> ToolCallResult:
        self.called_tools.append((name, arguments))

        if name == "submit_complaint":
            return ToolCallResult(
                tool_name=name,
                is_error=False,
                content=json.dumps({
                    "status": "success",
                    "complaint_id": "CPL-2026-0001",
                    "student_id": arguments.get("student_id", "21120001"),
                }),
            )
        elif name == "check_complaint_status":
            return ToolCallResult(
                tool_name=name,
                is_error=False,
                content=json.dumps({
                    "status": "success",
                    "complaint_id": arguments.get("complaint_id", "CPL-2026-0001"),
                    "current_status": "pending_review",
                }),
            )
        elif name == "list_student_complaints":
            return ToolCallResult(
                tool_name=name,
                is_error=False,
                content=json.dumps({
                    "status": "success",
                    "complaints": [
                        {"complaint_id": "CPL-2026-0001", "criteria_id": "TieuChi3"}
                    ],
                }),
            )
        elif name == "failing_tool":
            return ToolCallResult(
                tool_name=name,
                is_error=True,
                content="Error: Database disk full, cannot execute failing_tool",
            )
        else:
            return ToolCallResult(
                tool_name=name,
                is_error=True,
                content=f"Error: Tool '{name}' không tồn tại.",
            )


class MockSessionLogger:
    """Mock Logger để kiểm tra tích hợp SessionLogger."""

    def __init__(self) -> None:
        self.logged_records: List[Dict[str, Any]] = []

    def log_record(
        self, query_id: str, user_query: str, steps: List[Any], usage: Dict[str, Any], final_answer: str
    ) -> None:
        self.logged_records.append({
            "query_id": query_id,
            "user_query": user_query,
            "steps": steps,
            "usage": usage,
            "final_answer": final_answer,
        })


# ==============================================================================
# 1. TEST PARSER & VALIDATION (Không dùng eval)
# ==============================================================================


def test_parse_llm_decision_pure_json() -> None:
    raw = '{"thought": "Hiểu rồi", "action": "final_answer", "final_answer": "Kết quả là 15đ"}'
    res = parse_llm_decision(raw)
    assert res["action"] == "final_answer"
    assert res["final_answer"] == "Kết quả là 15đ"


def test_parse_llm_decision_markdown_fenced() -> None:
    raw = """Dưới đây là quyết định:
```json
{
  "thought": "Cần gọi công cụ tra cứu",
  "action": "call_tool",
  "tool_name": "list_student_complaints",
  "tool_args": {"student_id": "21120001"}
}
```
Hi vọng hữu ích!"""
    res = parse_llm_decision(raw)
    assert res["action"] == "call_tool"
    assert res["tool_name"] == "list_student_complaints"
    assert res["tool_args"]["student_id"] == "21120001"


def test_parse_llm_decision_embedded_braces() -> None:
    raw = 'Tôi xin gửi quyết định: {"thought": "Xong", "action": "final_answer", "final_answer": "OK"} cảm ơn bạn.'
    res = parse_llm_decision(raw)
    assert res["action"] == "final_answer"


def test_parse_llm_decision_invalid_raises_error() -> None:
    with pytest.raises(ValueError, match="Không tìm thấy khối JSON hợp lệ"):
        parse_llm_decision("Xin chào bạn tôi không biết trả lời dạng JSON")


def test_validate_decision_missing_fields() -> None:
    with pytest.raises(ValueError, match="Thiếu trường bắt buộc 'thought'"):
        validate_decision({"action": "final_answer", "final_answer": "ok"})

    with pytest.raises(ValueError, match="Thiếu trường bắt buộc 'action'"):
        validate_decision({"thought": "nghi xong"})

    with pytest.raises(ValueError, match="bắt buộc phải có trường 'final_answer'"):
        validate_decision({"thought": "nghi xong", "action": "final_answer"})

    with pytest.raises(ValueError, match="bắt buộc phải có trường 'tool_name'"):
        validate_decision({"thought": "nghi xong", "action": "call_tool"})


# ==============================================================================
# 2. TEST ORCHESTRATOR REACT LOOP SCENARIOS
# ==============================================================================


@pytest.mark.anyio
async def test_llm_direct_answer_without_tools() -> None:
    """Kịch bản 1: LLM trả lời trực tiếp ngay bước 1, không gọi tool nào."""
    mock_llm = MockLLMClient([
        json.dumps({
            "thought": "Câu hỏi tra cứu đơn giản, không cần gọi MCP tool.",
            "action": "final_answer",
            "final_answer": "Theo Điều 5 Quy chế 2024, Mùa hè xanh cấp trường được cộng 5 điểm.",
        })
    ])
    mock_mcp = MockMCPClient()

    orchestrator = ReActOrchestrator(llm_client=mock_llm, mcp_client=mock_mcp)
    answer = await orchestrator.arun("Mùa hè xanh được mấy điểm?")

    assert "Mùa hè xanh cấp trường được cộng 5 điểm" in answer
    assert mock_llm.call_count == 1
    assert len(mock_mcp.called_tools) == 0
    assert len(orchestrator.last_steps) == 1
    assert orchestrator.last_steps[0].action == "final_answer"


@pytest.mark.anyio
async def test_llm_valid_tool_call_and_then_answer() -> None:
    """Kịch bản 2: LLM gọi một tool hợp lệ, nhận kết quả và đưa ra câu trả lời."""
    mock_llm = MockLLMClient([
        # Bước 1: Yêu cầu gọi tool
        json.dumps({
            "thought": "Cần kiểm tra danh sách khiếu nại của sinh viên 21120001.",
            "action": "call_tool",
            "tool_name": "list_student_complaints",
            "tool_args": {"student_id": "21120001"},
        }),
        # Bước 2: Đọc Observation và trả lời
        json.dumps({
            "thought": "Đã nhận được danh sách từ tool, có 1 đơn mã CPL-2026-0001.",
            "action": "final_answer",
            "final_answer": "Sinh viên 21120001 hiện có 1 đơn khiếu nại mã CPL-2026-0001.",
        }),
    ])
    mock_mcp = MockMCPClient()

    orchestrator = ReActOrchestrator(llm_client=mock_llm, mcp_client=mock_mcp)
    answer = await orchestrator.arun("Tra cứu đơn của sinh viên 21120001")

    assert "CPL-2026-0001" in answer
    assert mock_llm.call_count == 2
    assert len(mock_mcp.called_tools) == 1
    assert mock_mcp.called_tools[0] == ("list_student_complaints", {"student_id": "21120001"})
    assert len(orchestrator.last_steps) == 2


@pytest.mark.anyio
async def test_side_effect_verify_flow_r07() -> None:
    """Kịch bản 3 (Quy tắc R-07): Sau khi submit_complaint, bắt buộc verify bằng check_complaint_status."""
    mock_llm = MockLLMClient([
        # Bước 1: Nộp khiếu nại
        json.dumps({
            "thought": "Người dùng muốn nộp đơn, tôi gọi submit_complaint.",
            "action": "call_tool",
            "tool_name": "submit_complaint",
            "tool_args": {
                "student_id": "21120001",
                "semester": "HK1_2024_2025",
                "criteria_id": "TieuChi3",
                "claimed_points": 5.0,
                "reason": "Sót điểm Mùa hè xanh",
            },
        }),
        # Bước 2: LLM thử vội vã final_answer mà CHƯA verify -> Bị hệ thống chặn theo R-07!
        json.dumps({
            "thought": "Đã nộp xong, tôi báo ngay cho người dùng.",
            "action": "final_answer",
            "final_answer": "Đã nộp đơn thành công!",
        }),
        # Bước 3: LLM nhận lời nhắc R-07, gọi check_complaint_status để verify
        json.dumps({
            "thought": "Cần tuân thủ quy tắc R-07 để verify đơn CPL-2026-0001.",
            "action": "call_tool",
            "tool_name": "check_complaint_status",
            "tool_args": {"complaint_id": "CPL-2026-0001"},
        }),
        # Bước 4: Sau khi verify thành công, LLM đưa ra final_answer hợp lệ
        json.dumps({
            "thought": "Đã xác minh trạng thái đơn CPL-2026-0001 đang ở pending_review.",
            "action": "final_answer",
            "final_answer": "Đơn khiếu nại của bạn đã được ghi nhận và xác minh thành công với mã CPL-2026-0001.",
        }),
    ])
    mock_mcp = MockMCPClient()

    orchestrator = ReActOrchestrator(llm_client=mock_llm, mcp_client=mock_mcp)
    answer = await orchestrator.arun("Tôi muốn nộp đơn khiếu nại")

    assert "xác minh thành công với mã CPL-2026-0001" in answer
    # Kiểm tra cả hai tool Ghi và Đọc đều đã được gọi theo đúng thứ tự
    called_names = [call[0] for call in mock_mcp.called_tools]
    assert called_names == ["submit_complaint", "check_complaint_status"]
    assert mock_llm.call_count == 4


@pytest.mark.anyio
async def test_llm_malformed_json_recovery() -> None:
    """Kịch bản 4: LLM trả về text không phải JSON, hệ thống báo lỗi và LLM tự sửa sai."""
    mock_llm = MockLLMClient([
        # Bước 1: Trả về văn bản hỏng không có JSON
        "Chào bạn, tôi là AI trợ lý. Để tôi suy nghĩ nhé: { json bị lỗi",
        # Bước 2: Nhận thông báo lỗi cú pháp từ orchestrator, tự sửa lại JSON đúng
        json.dumps({
            "thought": "Xin lỗi, tôi đã sửa lại định dạng JSON chuẩn.",
            "action": "final_answer",
            "final_answer": "Điểm rèn luyện của bạn đã được kiểm tra.",
        }),
    ])
    mock_mcp = MockMCPClient()

    orchestrator = ReActOrchestrator(llm_client=mock_llm, mcp_client=mock_mcp)
    answer = await orchestrator.arun("Kiểm tra điểm")

    assert "Điểm rèn luyện của bạn đã được kiểm tra" in answer
    assert mock_llm.call_count == 2
    assert orchestrator.last_steps[0].error is not None


@pytest.mark.anyio
async def test_missing_required_fields_recovery() -> None:
    """Kịch bản 5: LLM trả về JSON thiếu trường bắt buộc 'action'."""
    mock_llm = MockLLMClient([
        # Bước 1: Thiếu trường action
        json.dumps({"thought": "Tôi đang suy nghĩ nhưng quên ghi action"}),
        # Bước 2: Tự sửa lại đầy đủ trường
        json.dumps({
            "thought": "Đã bổ sung đầy đủ trường action.",
            "action": "final_answer",
            "final_answer": "Câu trả lời hoàn chỉnh.",
        }),
    ])
    mock_mcp = MockMCPClient()

    orchestrator = ReActOrchestrator(llm_client=mock_llm, mcp_client=mock_mcp)
    answer = await orchestrator.arun("Hỏi câu hỏi")

    assert "Câu trả lời hoàn chỉnh" in answer
    assert mock_llm.call_count == 2


@pytest.mark.anyio
async def test_tool_not_found_handling() -> None:
    """Kịch bản 6: LLM gọi một tool không tồn tại trên MCP Server."""
    mock_llm = MockLLMClient([
        # Bước 1: Gọi tool không tồn tại
        json.dumps({
            "thought": "Thử gọi tool tra cứu kỳ thi",
            "action": "call_tool",
            "tool_name": "lookup_exam_schedule",
            "tool_args": {"student_id": "21120001"},
        }),
        # Bước 2: Nhận lỗi tool không tồn tại từ MCP, giải thích lại cho người dùng
        json.dumps({
            "thought": "Công cụ không tồn tại, tôi sẽ thông báo cho người dùng.",
            "action": "final_answer",
            "final_answer": "Hệ thống không hỗ trợ tra cứu lịch thi, chỉ hỗ trợ khiếu nại điểm rèn luyện.",
        }),
    ])
    mock_mcp = MockMCPClient()

    orchestrator = ReActOrchestrator(llm_client=mock_llm, mcp_client=mock_mcp)
    answer = await orchestrator.arun("Xem lịch thi giúp tôi")

    assert "không hỗ trợ tra cứu lịch thi" in answer
    assert mock_llm.call_count == 2
    assert "lookup_exam_schedule" not in [c[0] for c in mock_mcp.called_tools]


@pytest.mark.anyio
async def test_tool_execution_failure_handling() -> None:
    """Kịch bản 7: Tool thực thi thất bại (trả về is_error=True)."""
    mock_llm = MockLLMClient([
        # Bước 1: Gọi tool bị lỗi
        json.dumps({
            "thought": "Gọi tool failing_tool để test",
            "action": "call_tool",
            "tool_name": "failing_tool",
            "tool_args": {},
        }),
        # Bước 2: Nhận kết quả lỗi và thông báo lịch sự
        json.dumps({
            "thought": "Tool gặp sự cố cơ sở dữ liệu, thông báo cho người dùng thử lại sau.",
            "action": "final_answer",
            "final_answer": "Hệ thống đang bảo trì cơ sở dữ liệu, vui lòng thử lại sau.",
        }),
    ])
    mock_mcp = MockMCPClient()

    orchestrator = ReActOrchestrator(llm_client=mock_llm, mcp_client=mock_mcp)
    answer = await orchestrator.arun("Thực thi thao tác")

    assert "Hệ thống đang bảo trì" in answer
    assert mock_llm.call_count == 2
    assert len(mock_mcp.called_tools) == 1


@pytest.mark.anyio
async def test_max_steps_limit_stops_infinite_loop() -> None:
    """Kịch bản 8: LLM liên tục gọi tool không dừng, vòng lặp dừng đúng MAX_STEPS = 5."""
    infinite_tool_call = json.dumps({
        "thought": "Tôi muốn gọi tool tiếp tục",
        "action": "call_tool",
        "tool_name": "list_student_complaints",
        "tool_args": {"student_id": "21120001"},
    })
    # Cung cấp 20 câu trả lời lặp lại
    mock_llm = MockLLMClient([infinite_tool_call] * 20)
    mock_mcp = MockMCPClient()

    custom_max_steps = 4
    orchestrator = ReActOrchestrator(
        llm_client=mock_llm, mcp_client=mock_mcp, max_steps=custom_max_steps
    )
    answer = await orchestrator.arun("Lặp vô hạn")

    assert f"Đã đạt giới hạn tối đa {custom_max_steps} bước" in answer
    assert mock_llm.call_count == custom_max_steps
    assert len(orchestrator.last_steps) == custom_max_steps


def test_sync_run_and_logger_integration() -> None:
    """Kịch bản 9: Kiểm tra chạy đồng bộ (run) và tích hợp SessionLogger."""
    mock_llm = MockLLMClient([
        json.dumps({
            "thought": "Trả lời đồng bộ",
            "action": "final_answer",
            "final_answer": "Kết quả chạy đồng bộ thành công.",
        })
    ])
    mock_mcp = MockMCPClient()
    mock_logger = MockSessionLogger()

    orchestrator = ReActOrchestrator(
        llm_client=mock_llm, mcp_client=mock_mcp, logger=mock_logger
    )

    # Chạy hàm sync run()
    answer = orchestrator.run("Câu hỏi đồng bộ", query_id="test_sync_01")

    assert answer == "Kết quả chạy đồng bộ thành công."
    assert len(mock_logger.logged_records) == 1
    logged = mock_logger.logged_records[0]
    assert logged["query_id"] == "test_sync_01"
    assert logged["user_query"] == "Câu hỏi đồng bộ"
    assert logged["usage"]["calls"] == 1
    assert logged["usage"]["prompt_tokens"] == 50
