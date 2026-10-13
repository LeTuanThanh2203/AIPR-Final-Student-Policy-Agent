"""ReAct Agent Orchestrator cho Đề tài T4 (Đồ án AIPR).

Triển khai vòng lặp suy luận ReAct (Think -> Act -> Observe) theo R-02, R-06, R-07:
- Khám phá công cụ động từ MCP Client (Dynamic Tool Discovery).
- Gửi câu hỏi và mô tả công cụ cho LLM Client (RobustLLMClient của Teammate C).
- Phân tích quyết định của LLM (call_tool hoặc final_answer) an toàn qua JSON (không dùng eval).
- Thực thi công cụ qua MCP Client và đưa kết quả thật về cho LLM.
- Thực thi quy tắc xác minh R-07: Sau khi submit_complaint, bắt buộc verify bằng check_complaint_status.
- Giới hạn tối đa MAX_STEPS = 10 để chống vòng lặp vô hạn.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union, runtime_checkable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROMPT_PATH = PROJECT_ROOT / "prompts" / "system_react.txt"
MAX_STEPS = 10


@runtime_checkable
class LLMClientProtocol(Protocol):
    """Interface tiêu chuẩn cho LLM Client (tương thích với RobustLLMClient của Teammate C)."""

    def generate(self, messages: List[Dict[str, str]]) -> Any:
        ...


@dataclass
class AgentStep:
    """Lưu trữ thông tin một bước suy luận trong vòng lặp ReAct."""

    step_number: int
    thought: str = ""
    action: str = ""
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    error: Optional[str] = None
    raw_response: str = ""


def load_system_prompt(prompt_path: Optional[Union[str, Path]] = None) -> str:
    """Nạp nội dung System Prompt từ thư mục prompts/ (R-04: tách prompt khỏi code)."""
    target = Path(prompt_path) if prompt_path else DEFAULT_PROMPT_PATH
    if target.exists():
        return target.read_text(encoding="utf-8")

    # Fallback dự phòng nếu file chưa tồn tại
    return (
        "Bạn là Trợ lý AI chuyên trách về Điểm Rèn luyện và Tiếp nhận Khiếu nại.\n"
        "Danh sách công cụ khả dụng:\n{tools_description}\n"
        "Ở mỗi bước, trả về JSON với 'thought' và 'action' ('call_tool' hoặc 'final_answer')."
    )


def format_tools_description(tools: List[Any]) -> str:
    """Định dạng danh sách công cụ từ MCP Client thành mô tả dễ hiểu cho LLM."""
    if not tools:
        return "Hiện tại không có công cụ MCP nào khả dụng."

    descriptions: List[str] = []
    for tool in tools:
        name = getattr(tool, "name", str(tool))
        desc = getattr(tool, "description", "")
        schema = getattr(tool, "input_schema", getattr(tool, "inputSchema", {}))
        schema_json = json.dumps(schema, ensure_ascii=False) if schema else "{}"
        descriptions.append(
            f"- Tool: `{name}`\n"
            f"  Mô tả: {desc}\n"
            f"  Tham số đầu vào (Input Schema): {schema_json}"
        )

    return "\n\n".join(descriptions)


def parse_llm_decision(raw_text: str) -> Dict[str, Any]:
    """Phân tích chuỗi phản hồi từ LLM thành JSON Object mà TUYỆT ĐỐI KHÔNG dùng eval().

    Hỗ trợ:
    1. Chuỗi JSON hợp lệ trực tiếp.
    2. JSON bọc trong Markdown block (```json ... ``` hoặc ``` ... ```).
    3. Tìm kiếm khối JSON bao bởi cặp ngoặc nhọn `{...}` đầu tiên và cuối cùng.
    """
    cleaned = raw_text.strip()
    if not cleaned:
        raise ValueError("LLM trả về phản hồi rỗng.")

    # 1. Bóc tách nếu LLM bọc trong code block Markdown
    if "```" in cleaned:
        code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if code_block_match:
            candidate = code_block_match.group(1).strip()
            try:
                data = json.loads(candidate)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass

    # 2. Thử parse trực tiếp toàn bộ chuỗi
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # 3. Tìm khối JSON đầu tiên bắt đầu bằng '{' và kết thúc bằng '}'
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidate = cleaned[first_brace : last_brace + 1]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError as err:
            raise ValueError(f"Khối JSON trích xuất không hợp lệ: {err}") from err

    raise ValueError("Không tìm thấy khối JSON hợp lệ trong phản hồi của LLM.")


def validate_decision(decision: Dict[str, Any]) -> None:
    """Kiểm tra tính hợp lệ và các trường bắt buộc của quyết định ReAct."""
    if not isinstance(decision, dict):
        raise ValueError("Quyết định của LLM phải là một JSON Object (dictionary).")

    if "thought" not in decision or not str(decision["thought"]).strip():
        raise ValueError("Thiếu trường bắt buộc 'thought' (suy nghĩ) trong quyết định ReAct.")

    if "action" not in decision:
        raise ValueError("Thiếu trường bắt buộc 'action' trong quyết định ReAct.")

    action = decision["action"]
    if action == "final_answer":
        if "final_answer" not in decision:
            raise ValueError("Khi action='final_answer', bắt buộc phải có trường 'final_answer'.")
    elif action == "call_tool":
        tool_name = decision.get("tool_name") or decision.get("tool")
        if not tool_name or not isinstance(tool_name, str):
            raise ValueError("Khi action='call_tool', bắt buộc phải có trường 'tool_name' dạng chuỗi.")
        args = decision.get("tool_args", decision.get("args", {}))
        if not isinstance(args, dict):
            raise ValueError("Trường 'tool_args' phải là một dictionary (JSON Object).")
    else:
        raise ValueError(
            f"Giá trị action không hợp lệ: '{action}'. Chỉ chấp nhận 'call_tool' hoặc 'final_answer'."
        )


def _call_llm_unified(llm: Any, messages: List[Dict[str, str]]) -> Tuple[str, Dict[str, Any]]:
    """Gọi LLM client thống nhất, tương thích RobustLLMClient (Teammate C), callable hoặc mock."""
    if llm is None:
        raise ValueError("LLM client chưa được cấu hình cho ReActOrchestrator.")

    usage: Dict[str, Any] = {}

    # 1. Nếu client có method generate(messages) (RobustLLMClient)
    if hasattr(llm, "generate") and callable(llm.generate):
        resp = llm.generate(messages)
    elif callable(llm):
        resp = llm(messages)
    elif hasattr(llm, "chat") and callable(llm.chat):
        resp = llm.chat(messages)
    else:
        raise TypeError(f"LLM client không hỗ trợ phương thức generate hoặc callable: {type(llm)}")

    # Trích xuất content và usage
    if isinstance(resp, dict):
        content = resp.get("content", "")
        usage = resp.get("usage", {})
    elif isinstance(resp, str):
        content = resp
    elif hasattr(resp, "content"):
        content = str(resp.content)
        if hasattr(resp, "usage"):
            usage = getattr(resp, "usage", {})
    else:
        content = str(resp)

    return content, usage


async def _safe_execute_async(func_or_coro: Any, *args: Any, **kwargs: Any) -> Any:
    """Hỗ trợ gọi hàm bất đồng bộ hoặc đồng bộ an toàn."""
    if inspect.iscoroutinefunction(func_or_coro):
        return await func_or_coro(*args, **kwargs)
    result = func_or_coro(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


def _run_in_thread(coro: Any) -> Any:
    """Chạy coroutine trong môi trường đồng bộ an toàn kể cả khi đang có event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


class ReActOrchestrator:
    """Bộ điều phối Agent theo mô hình ReAct (Think -> Act -> Observe)."""

    def __init__(
        self,
        llm_client: Any = None,
        mcp_client: Any = None,
        logger: Any = None,
        max_steps: int = MAX_STEPS,
        prompt_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.llm = llm_client
        self.mcp = mcp_client
        self.logger = logger
        self.max_steps = max_steps
        self.prompt_path = prompt_path

        # Lịch sử và thông số của lần chạy gần nhất
        self.last_steps: List[AgentStep] = []
        self.last_usage: Dict[str, Any] = {}

    async def _discover_tools(self) -> Tuple[List[Any], Dict[str, Any]]:
        """Lấy danh sách công cụ thật từ MCP Client (Dynamic Discovery)."""
        if self.mcp is None:
            return [], {}

        try:
            if hasattr(self.mcp, "list_available_tools"):
                tools = await _safe_execute_async(self.mcp.list_available_tools)
            elif hasattr(self.mcp, "list_tools"):
                tools = await _safe_execute_async(self.mcp.list_tools)
            else:
                tools = []

            # Chuẩn hóa danh sách
            tool_list = tools.tools if hasattr(tools, "tools") else (tools if isinstance(tools, list) else [])
            tool_map = {getattr(t, "name", str(t)): t for t in tool_list}
            return tool_list, tool_map
        except Exception as err:
            return [], {}

    async def _execute_mcp_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Tuple[str, bool, Any]:
        """Gọi công cụ MCP thật và trả về (observation_text, is_error, raw_result)."""
        if self.mcp is None:
            return (
                f"Error: Chưa cấu hình MCP Client, không thể thực thi tool '{tool_name}'.",
                True,
                None,
            )

        try:
            if not hasattr(self.mcp, "call_tool"):
                return f"Error: MCP Client không hỗ trợ method call_tool.", True, None

            res = await _safe_execute_async(self.mcp.call_tool, tool_name, tool_args)

            # Phân giải kết quả trả về từ ToolCallResult hoặc object khác
            if hasattr(res, "content"):
                content = str(res.content)
                is_error = getattr(res, "is_error", False)
                return content, is_error, res
            elif isinstance(res, dict):
                content = json.dumps(res, ensure_ascii=False)
                is_error = res.get("status") == "error" or "error" in res
                return content, is_error, res
            else:
                return str(res), False, res

        except Exception as err:
            return f"Error khi thực thi tool '{tool_name}': {err}", True, None

    async def arun_detailed(
        self, user_query: str, query_id: str = "interactive"
    ) -> Dict[str, Any]:
        """Vòng lặp ReAct bất đồng bộ đầy đủ (trả về kết quả, trace các bước và token usage)."""
        self.last_steps = []
        self.last_usage = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}

        # 1. Khám phá danh sách tools động từ MCP Server
        tool_list, tool_map = await self._discover_tools()
        tools_desc = format_tools_description(tool_list)

        # 2. Chuẩn bị System Prompt và hội thoại ban đầu
        system_template = load_system_prompt(self.prompt_path)
        if "{tools_description}" in system_template:
            system_prompt = system_template.replace("{tools_description}", tools_desc)
        else:
            system_prompt = f"{system_template}\n\nDanh sách công cụ khả dụng:\n{tools_desc}"

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ]

        # Biến trạng thái để kiểm soát quy tắc xác minh R-07
        last_submitted_complaint_id: Optional[str] = None
        verified_complaint_id: Optional[str] = None
        final_answer: str = ""

        # 3. Vòng lặp ReAct tối đa MAX_STEPS bước
        for step_idx in range(1, self.max_steps + 1):
            step_record = AgentStep(step_number=step_idx)

            # Gọi LLM sinh phản hồi
            try:
                raw_output, usage = _call_llm_unified(self.llm, messages)
                step_record.raw_response = raw_output
                self.last_usage["calls"] += 1
                if isinstance(usage, dict):
                    self.last_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
                    self.last_usage["completion_tokens"] += usage.get("completion_tokens", 0)
            except Exception as err:
                step_record.error = f"Lỗi gọi LLM: {err}"
                self.last_steps.append(step_record)
                final_answer = f"Lỗi hệ thống khi giao tiếp với LLM: {err}"
                break

            # Phân tích cú pháp JSON quyết định
            try:
                decision = parse_llm_decision(raw_output)
                validate_decision(decision)
            except ValueError as val_err:
                step_record.error = str(val_err)
                self.last_steps.append(step_record)

                # Cung cấp phản hồi lỗi để LLM tự sửa sai ở bước kế tiếp
                messages.append({"role": "assistant", "content": raw_output})
                messages.append({
                    "role": "user",
                    "content": (
                        f"Lỗi cú pháp hoặc thiếu trường: {val_err}. "
                        "Vui lòng chỉ trả về DUY NHẤT một khối JSON hợp lệ theo đúng cấu trúc: "
                        "{\"thought\": \"...\", \"action\": \"call_tool\" | \"final_answer\", ...}."
                    ),
                })
                continue

            # Ghi nhận thought và action
            thought = decision.get("thought", "")
            action = decision.get("action", "")
            step_record.thought = thought
            step_record.action = action

            # Trường hợp A: Final Answer
            if action == "final_answer":
                # Kiểm tra quy tắc R-07: Nếu vừa nộp đơn nhưng chưa verify thì chặn lại
                if last_submitted_complaint_id and verified_complaint_id != last_submitted_complaint_id:
                    feedback = (
                        f"Quy tắc R-07 bắt buộc: Bạn vừa tạo khiếu nại (Mã: {last_submitted_complaint_id}) "
                        "nhưng chưa gọi tool đọc 'check_complaint_status' để xác minh dữ liệu đã được lưu thành công. "
                        "Vui lòng gọi 'check_complaint_status' trước khi đưa ra câu trả lời cuối cùng."
                    )
                    step_record.observation = f"[Bị từ chối theo R-07]: {feedback}"
                    self.last_steps.append(step_record)

                    messages.append({"role": "assistant", "content": raw_output})
                    messages.append({"role": "user", "content": feedback})
                    continue

                final_answer = decision.get("final_answer", "")
                self.last_steps.append(step_record)
                break

            # Trường hợp B: Tool Call
            elif action == "call_tool":
                tool_name = decision.get("tool_name") or decision.get("tool", "")
                tool_args = decision.get("tool_args", decision.get("args", {}))
                step_record.tool_name = tool_name
                step_record.tool_args = tool_args

                # Kiểm tra tool có trong danh sách khả dụng không
                if tool_map and tool_name not in tool_map:
                    obs = (
                        f"Error: Công cụ '{tool_name}' không tồn tại trên MCP Server. "
                        f"Các công cụ khả dụng: {list(tool_map.keys())}"
                    )
                    step_record.observation = obs
                    self.last_steps.append(step_record)

                    messages.append({"role": "assistant", "content": raw_output})
                    messages.append({
                        "role": "user",
                        "content": f"Observation từ hệ thống:\n{obs}",
                    })
                    continue

                # Thực thi tool thật trên MCP Client
                obs, is_error, raw_res = await self._execute_mcp_tool(tool_name, tool_args)
                step_record.observation = obs
                self.last_steps.append(step_record)

                # Theo dõi trạng thái nộp và xác minh cho quy tắc R-07
                if not is_error and tool_name == "submit_complaint":
                    # Tìm complaint_id trong kết quả trả về
                    id_match = re.search(r"CPL-\d{4}-\d{4}", obs)
                    if id_match:
                        last_submitted_complaint_id = id_match.group(0)

                elif not is_error and tool_name == "check_complaint_status":
                    arg_id = tool_args.get("complaint_id")
                    if arg_id:
                        verified_complaint_id = arg_id

                # Đưa kết quả thực thi tool thật về cho LLM làm ngữ cảnh bước tiếp theo
                messages.append({"role": "assistant", "content": raw_output})
                messages.append({
                    "role": "user",
                    "content": f"Observation từ công cụ '{tool_name}':\n{obs}",
                })

        # Nếu hết số bước tối đa mà chưa có final_answer
        if not final_answer:
            final_answer = (
                f"Đã đạt giới hạn tối đa {self.max_steps} bước xử lý mà chưa có câu trả lời cuối cùng. "
                "Vui lòng cung cấp thêm thông tin chi tiết để hỗ trợ tốt hơn."
            )

        # 4. Ghi log nếu có SessionLogger
        if self.logger and hasattr(self.logger, "log_record"):
            try:
                self.logger.log_record(
                    query_id=query_id,
                    user_query=user_query,
                    steps=[s.__dict__ for s in self.last_steps],
                    usage=self.last_usage,
                    final_answer=final_answer,
                )
            except Exception:
                pass

        return {
            "query_id": query_id,
            "user_query": user_query,
            "final_answer": final_answer,
            "steps": [s.__dict__ for s in self.last_steps],
            "usage": self.last_usage,
        }

    async def arun(self, user_query: str, query_id: str = "interactive") -> str:
        """Chạy vòng lặp ReAct bất đồng bộ và trả về câu trả lời cuối cùng."""
        result = await self.arun_detailed(user_query, query_id)
        return result["final_answer"]

    def run_detailed(self, user_query: str, query_id: str = "interactive") -> Dict[str, Any]:
        """Chạy vòng lặp ReAct đồng bộ đầy đủ (Thread-safe wrapper)."""
        return _run_in_thread(self.arun_detailed(user_query, query_id))

    def run(self, user_query: str, query_id: str = "interactive") -> str:
        """Chạy vòng lặp ReAct đồng bộ (Entrypoint chính cho CLI / Evaluation)."""
        result = self.run_detailed(user_query, query_id)
        return result["final_answer"]
