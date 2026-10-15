"""ReAct Agent Orchestrator cho Đề tài T4 (Đồ án AIPR).

Tuân thủ nghiêm ngặt các yêu cầu kỹ thuật bắt buộc:
- R-02: Vòng lặp Agent ReAct (Think -> Act -> Observe) tự code bằng tay (for step in range(MAX_STEPS)).
- R-06: Giới hạn MAX_STEPS = 10, bắt lỗi mềm (không crash khi JSON sai cú pháp hoặc tool lỗi).
- R-07: Cơ chế bắt buộc xác minh (Verify) sau khi gọi tool Ghi (submit_complaint).
- R-08: Khám phá công cụ động từ MCP Client (Dynamic Tool Discovery).
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROMPT_PATH = PROJECT_ROOT / "prompts" / "system_react.txt"
MAX_STEPS = 10


@dataclass
class AgentStep:
    """Ghi nhận vết một bước suy luận trong vòng lặp ReAct."""
    step_number: int
    thought: str = ""
    action: str = ""
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    error: Optional[str] = None
    raw_response: str = ""


@dataclass
class VerificationResult:
    """Kết quả đối soát xác minh dữ liệu trên đĩa (R-07)."""
    attempted: bool = False
    verified: bool = False
    complaint_id: Optional[str] = None
    student_id: Optional[str] = None
    status: Optional[str] = None
    reason: str = ""


def format_tools_description(tools: List[Any]) -> str:
    """Định dạng danh sách công cụ từ MCP Client thành mô tả cho LLM (R-08)."""
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
    """Phân tích phản hồi từ LLM thành JSON an toàn, tuyệt đối không dùng eval() (R-06)."""
    cleaned = raw_text.strip()
    if not cleaned:
        raise ValueError("LLM trả về phản hồi rỗng.")

    # 1. Trích xuất nếu LLM bọc trong khối code Markdown ```json ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    candidate = match.group(1).strip() if match else cleaned

    # 2. Tìm khối JSON đầu tiên bắt đầu bằng '{' và kết thúc bằng '}'
    first = candidate.find("{")
    last = candidate.rfind("}")
    if first != -1 and last > first:
        try:
            data = json.loads(candidate[first:last + 1])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    try:
        data = json.loads(candidate)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    raise ValueError("Không tìm thấy khối JSON hợp lệ trong phản hồi của LLM.")


def validate_decision(decision: Dict[str, Any]) -> None:
    """Kiểm tra tính hợp lệ của khối quyết định ReAct (R-06)."""
    if not isinstance(decision, dict):
        raise ValueError("Quyết định phải là một JSON Object (dict).")

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
    else:
        raise ValueError(f"Giá trị action không hợp lệ: '{action}'. Chỉ chấp nhận 'call_tool' hoặc 'final_answer'.")


def _call_llm(llm: Any, messages: List[Dict[str, str]]) -> Tuple[str, Dict[str, Any]]:
    """Gọi LLM thống nhất, tương thích RobustLLMClient (Member C) hoặc hàm callable."""
    if hasattr(llm, "generate") and callable(llm.generate):
        resp = llm.generate(messages)
    elif callable(llm):
        resp = llm(messages)
    else:
        raise TypeError(f"LLM client không hỗ trợ phương thức generate hoặc callable: {type(llm)}")

    if isinstance(resp, dict):
        return resp.get("content", ""), resp.get("usage", {})
    return str(resp), {}


def _run_sync(coro: Any) -> Any:
    """Chạy coroutine an toàn kể cả khi đang có event loop (Thread-safe)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


class ReActOrchestrator:
    """Bộ điều phối Agent theo mô hình ReAct tự viết tay (R-02)."""

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
        self.prompt_path = Path(prompt_path) if prompt_path else DEFAULT_PROMPT_PATH

        self.last_steps: List[AgentStep] = []
        self.last_usage: Dict[str, Any] = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}
        self.last_verification: Optional[VerificationResult] = None

    async def _discover_tools(self) -> Tuple[List[Any], Dict[str, Any]]:
        """Lấy danh sách công cụ thật từ MCP Client (Dynamic Discovery - R-08)."""
        if not self.mcp:
            return [], {}
        try:
            tools = await self.mcp.list_available_tools()
            tool_list = tools.tools if hasattr(tools, "tools") else (tools if isinstance(tools, list) else [])
            tool_map = {getattr(t, "name", str(t)): t for t in tool_list}
            return tool_list, tool_map
        except Exception:
            return [], {}

    async def arun_detailed(self, user_query: str, query_id: str = "interactive") -> Dict[str, Any]:
        """Vòng lặp ReAct bất đồng bộ đầy đủ (trả về kết quả, trace các bước và token usage)."""
        self.last_steps = []
        self.last_usage = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}
        self.last_verification = None

        # 1. Khám phá công cụ động và nạp System Prompt
        tool_list, tool_map = await self._discover_tools()
        tools_desc = format_tools_description(tool_list)
        system_template = self.prompt_path.read_text(encoding="utf-8") if self.prompt_path.exists() else "Bạn là Trợ lý AI. Tools:\n{tools_description}"
        system_prompt = system_template.replace("{tools_description}", tools_desc)

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ]
        final_answer = ""
        pending_verification_cid: Optional[str] = None
        pending_student_id: Optional[str] = None

        # 2. Vòng lặp ReAct tối đa MAX_STEPS bước (R-02 & R-06)
        for step_idx in range(1, self.max_steps + 1):
            step = AgentStep(step_number=step_idx)

            # Gọi LLM
            try:
                raw_output, usage = _call_llm(self.llm, messages)
                step.raw_response = raw_output
                self.last_usage["calls"] += 1
                if isinstance(usage, dict):
                    self.last_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
                    self.last_usage["completion_tokens"] += usage.get("completion_tokens", 0)
            except Exception as err:
                step.error = f"Lỗi gọi LLM: {err}"
                self.last_steps.append(step)
                final_answer = f"Lỗi hệ thống khi giao tiếp với LLM: {err}"
                break

            # Parse & validate JSON an toàn (R-06)
            try:
                decision = parse_llm_decision(raw_output)
                validate_decision(decision)
            except Exception as err:
                step.error = f"Lỗi: {err}"
                self.last_steps.append(step)
                messages.append({"role": "assistant", "content": raw_output})
                messages.append({"role": "user", "content": f"Observation: Error: {err}. Vui lòng sửa lại định dạng JSON chuẩn."})
                continue

            step.thought = decision.get("thought", "")
            action = decision.get("action", "")
            step.action = action

            # Trường hợp A: Final Answer
            if action == "final_answer":
                # ÉP BUỘC BƯỚC VERIFY (R-07): Nếu vừa ghi đơn mà chưa gọi tool đọc check_complaint_status
                if pending_verification_cid:
                    step.error = "Chưa verify đơn theo R-07"
                    self.last_steps.append(step)
                    messages.append({"role": "assistant", "content": raw_output})
                    messages.append({
                        "role": "user",
                        "content": (
                            f"Observation: Error: Theo quy định R-07, bạn vừa ghi nhận đơn {pending_verification_cid}. "
                            "BẮT BUỘC bạn phải gọi tool đọc 'check_complaint_status' với mã này để xác minh trước khi kết luận."
                        ),
                    })
                    continue

                final_answer = decision.get("final_answer", "")
                step.observation = "[Final Answer Accepted]"
                self.last_steps.append(step)
                break

            # Trường hợp B: Call Tool
            elif action == "call_tool":
                tool_name = str(decision.get("tool_name") or decision.get("tool", "")).strip()
                tool_args = decision.get("tool_args", decision.get("args", {}))
                step.tool_name = tool_name
                step.tool_args = tool_args

                # Kiểm tra tool có khả dụng không
                if tool_map and tool_name not in tool_map:
                    obs = f"Error: Tool '{tool_name}' không tồn tại trên MCP Server. Các tool khả dụng: {list(tool_map.keys())}"
                    step.observation = obs
                    self.last_steps.append(step)
                    messages.append({"role": "assistant", "content": raw_output})
                    messages.append({"role": "user", "content": f"Observation: {obs}"})
                    continue

                # Thực thi tool qua MCP Client
                try:
                    res = await self.mcp.call_tool(tool_name, tool_args)
                    obs = res.content if hasattr(res, "content") else str(res)
                except Exception as err:
                    obs = f"Error khi thực thi tool '{tool_name}': {err}"

                # Theo dõi trạng thái Verify (R-07)
                if tool_name == "submit_complaint":
                    cid_match = re.search(r"CPL-\d{4}-\d{4}", obs)
                    if cid_match:
                        pending_verification_cid = cid_match.group(0)
                        pending_student_id = str(tool_args.get("student_id", ""))
                elif tool_name == "check_complaint_status":
                    cid_match = re.search(r"CPL-\d{4}-\d{4}", obs)
                    verified = bool(cid_match and "not_found" not in obs and "error" not in obs.lower())
                    cid = cid_match.group(0) if cid_match else pending_verification_cid
                    self.last_verification = VerificationResult(
                        attempted=True,
                        verified=verified,
                        complaint_id=cid,
                        student_id=pending_student_id,
                        status="pending_review",
                        reason="Đã đối soát xác minh dữ liệu qua check_complaint_status.",
                    )
                    pending_verification_cid = None  # Đã verify xong!

                step.observation = obs
                self.last_steps.append(step)

                # Cập nhật ngữ cảnh cho bước suy luận tiếp theo
                messages.append({"role": "assistant", "content": raw_output})
                messages.append({"role": "user", "content": f"Observation: {obs}"})

        if not final_answer:
            final_answer = f"Đã đạt giới hạn tối đa {self.max_steps} bước mà chưa có câu trả lời cuối cùng."

        # Ghi log nếu có SessionLogger (Member C)
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
            "verification": self.last_verification.__dict__ if self.last_verification else None,
        }

    async def arun(self, user_query: str, query_id: str = "interactive") -> str:
        """Chạy vòng lặp ReAct bất đồng bộ và trả về câu trả lời cuối cùng."""
        res = await self.arun_detailed(user_query, query_id)
        return res["final_answer"]

    def run_detailed(self, user_query: str, query_id: str = "interactive") -> Dict[str, Any]:
        """Chạy vòng lặp ReAct đồng bộ đầy đủ (Thread-safe wrapper)."""
        return _run_sync(self.arun_detailed(user_query, query_id))

    def run(self, user_query: str, query_id: str = "interactive") -> str:
        """Chạy vòng lặp ReAct đồng bộ (Entrypoint chính cho CLI / Evaluation)."""
        return _run_sync(self.arun(user_query, query_id))
