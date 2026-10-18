"""ReAct Agent Orchestrator cho Đề tài T4 (Đồ án AIPR).

Cấu trúc tinh gọn, dễ hiểu, phù hợp sinh viên năm 3 và chuẩn W6 - W7:
- R-02: Vòng lặp Agent ReAct tự viết tay (Think -> Act -> Observe).
- R-06: Giới hạn MAX_STEPS = 10, bắt lỗi mềm (không crash khi JSON sai cú pháp).
- R-07: Bắt buộc Verify (kiểm tra lại) ngay sau khi gọi tool ghi khiếu nại.
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


# ---------------------------------------------------------------------------
# 1. Cấu trúc lưu vết từng bước suy luận (Dùng cho Log và Báo cáo)
# ---------------------------------------------------------------------------
@dataclass
class AgentStep:
    step_number: int
    thought: str = ""
    action: str = ""
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    error: Optional[str] = None
    raw_response: str = ""


# ---------------------------------------------------------------------------
# 2. Khám phá công cụ động & Định dạng mô tả Tools cho Prompt (W7 & R-08)
# ---------------------------------------------------------------------------
def format_tools_description(tools: List[Any]) -> str:
    """Chuyển danh sách công cụ từ MCP Client thành đoạn văn bản mô tả cho LLM."""
    if not tools:
        return "Hiện tại không có công cụ nào khả dụng."
    descriptions: List[str] = []
    for tool in tools:
        name = getattr(tool, "name", str(tool))
        desc = getattr(tool, "description", "")
        schema = getattr(tool, "input_schema", getattr(tool, "inputSchema", {}))
        descriptions.append(
            f"- Tool: `{name}`\n"
            f"  Mô tả: {desc}\n"
            f"  Tham số (Schema): {json.dumps(schema, ensure_ascii=False)}"
        )
    return "\n\n".join(descriptions)


# ---------------------------------------------------------------------------
# 3. Phân tích phản hồi từ LLM (Chuẩn W6 ex2_1 + R-06 an toàn không crash)
# ---------------------------------------------------------------------------
def parse_reply(reply: str) -> Tuple[str, Any]:
    """Phân tích câu trả lời của LLM.
    
    Trả về Tuple:
    - ('final', "câu trả lời cho sinh viên")
    - ('action', ("tên_tool", {"tham_số": "giá_trị"}))
    - ('unknown', "thông báo lỗi cú pháp")
    """
    cleaned = (reply or "").strip()
    if not cleaned:
        return "unknown", "LLM trả về phản hồi rỗng."

    # Cách 1: Parse JSON (Định dạng chuẩn của đề tài - bọc trong ```json hoặc { })
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    candidate = match.group(1).strip() if match else cleaned
    first = candidate.find("{")
    last = candidate.rfind("}")
    if first != -1 and last > first:
        candidate = candidate[first:last + 1]

    try:
        data = json.loads(candidate)
        if isinstance(data, dict):
            action = data.get("action")
            if action == "final_answer":
                return "final", str(data.get("final_answer", "")).strip()
            elif action == "call_tool":
                tool_name = str(data.get("tool_name") or data.get("tool") or "").strip()
                tool_args = data.get("tool_args") or data.get("args") or {}
                if tool_name:
                    return "action", (tool_name, tool_args if isinstance(tool_args, dict) else {})
    except Exception:
        pass

    # Cách 2: Fallback Regex chuẩn bài tập W6 (ex2_1_react_0_unfinished.py)
    final_match = re.search(r"Final Answer:\s*(.+)", cleaned, flags=re.IGNORECASE | re.DOTALL)
    if final_match:
        return "final", final_match.group(1).strip()

    action_match = re.search(r"Action:\s*(\w+)\s*\((.*)\)", cleaned, flags=re.IGNORECASE)
    if action_match:
        tool_name = action_match.group(1).strip()
        arg_str = action_match.group(2).strip()
        try:
            tool_args = json.loads(arg_str) if arg_str.startswith("{") else {"query": arg_str}
        except Exception:
            tool_args = {"query": arg_str} if arg_str else {}
        return "action", (tool_name, tool_args)

    return "unknown", "Không tìm thấy khối JSON hợp lệ hoặc cấu trúc Action/Final Answer."


def parse_llm_decision(raw_text: str) -> Dict[str, Any]:
    """Alias tương thích ngược."""
    kind, payload = parse_reply(raw_text)
    if kind == "final":
        return {"thought": "Xong", "action": "final_answer", "final_answer": payload}
    elif kind == "action":
        return {"thought": "Gọi tool", "action": "call_tool", "tool_name": payload[0], "tool_args": payload[1]}
    raise ValueError(f"Không thể phân tích phản hồi: {payload}")


# ---------------------------------------------------------------------------
# 4. Thực thi công cụ qua MCP Client (Chuẩn W6 run_action & W7 MCP)
# ---------------------------------------------------------------------------
async def run_action(name: str, argument: Union[Dict[str, Any], str], mcp_client: Any) -> str:
    """Gọi tool trên MCP Server (luôn trả về chuỗi str, bắt lỗi mềm không crash - R-06)."""
    if not mcp_client:
        return f"Error: Chưa kết nối MCP Client để thực thi công cụ '{name}'."

    # Chuẩn hóa đối số thành dictionary
    if isinstance(argument, str):
        try:
            args_dict = json.loads(argument)
        except Exception:
            args_dict = {"query": argument} if argument else {}
    elif isinstance(argument, dict):
        args_dict = argument
    else:
        args_dict = {}

    try:
        res = await mcp_client.call_tool(name, args_dict)
        return res.content if hasattr(res, "content") else str(res)
    except Exception as err:
        return f"Error khi gọi tool '{name}': {err}"


def call_llm(llm: Any, messages: List[Dict[str, str]]) -> Tuple[str, Dict[str, Any]]:
    """Hàm phụ trợ gọi LLM tương thích cả hàm callable hoặc RobustLLMClient (Member C)."""
    if hasattr(llm, "generate") and callable(llm.generate):
        resp = llm.generate(messages)
    elif callable(llm):
        resp = llm(messages)
    else:
        raise TypeError(f"LLM không hợp lệ: {type(llm)}")

    if isinstance(resp, tuple) and len(resp) == 2:
        return str(resp[0]), resp[1] if isinstance(resp[1], dict) else {}
    if isinstance(resp, dict):
        return resp.get("content", ""), resp.get("usage", {})
    return str(resp), {}


def run_sync(coro: Any) -> Any:
    """Chạy hàm async trong môi trường sync an toàn."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# 5. VÒNG LẶP REACT AGENT DUY NHẤT (Chuẩn W6 + Tầng c Verify R-07)
# ---------------------------------------------------------------------------
async def react_agent(
    client: Any,
    mcp_client: Any,
    question: str,
    max_steps: int = MAX_STEPS,
    prompt_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Vòng lặp ReAct Agent duy nhất trong toàn bộ hệ thống (Think -> Act -> Observe).
    
    Tuân thủ đúng yêu cầu đồ án:
    - R-02: Vòng lặp tự code bằng tay for step in range(max_steps).
    - R-06: Giới hạn max_steps, bắt lỗi mềm đưa lại ngữ cảnh cho LLM sửa sai.
    - R-07: Bắt buộc Verify qua check_complaint_status sau khi ghi đơn khiếu nại.
    - R-08: Tự động khám phá công cụ động từ MCP Client.
    """
    p_path = Path(prompt_path) if prompt_path else DEFAULT_PROMPT_PATH

    # Bước 1: Khám phá tools động từ MCP Server (R-08)
    tool_list = []
    if mcp_client:
        try:
            tool_list = await mcp_client.list_tools()
        except Exception:
            tool_list = []

    tools_desc = format_tools_description(tool_list)
    template = p_path.read_text(encoding="utf-8") if p_path.exists() else "Bạn là Trợ lý AI. Tools:\n{tools_description}"
    system_prompt = template.replace("{tools_description}", tools_desc)

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    steps: List[AgentStep] = []
    usage = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}
    pending_verification_cid: Optional[str] = None
    verified = False
    final_answer = ""

    # Bước 2: Vòng lặp suy luận ReAct (Tối đa MAX_STEPS)
    for step_idx in range(1, max_steps + 1):
        step = AgentStep(step_number=step_idx)

        # 2.1 Gọi LLM
        try:
            raw_output, u = call_llm(client, messages)
            step.raw_response = raw_output
            usage["calls"] += 1
            if isinstance(u, dict):
                usage["prompt_tokens"] += u.get("prompt_tokens", 0)
                usage["completion_tokens"] += u.get("completion_tokens", 0)
        except Exception as err:
            step.error = f"Lỗi gọi LLM: {err}"
            steps.append(step)
            final_answer = f"Lỗi hệ thống khi gọi LLM: {err}"
            break

        # 2.2 Phân tích câu trả lời (Parse Reply)
        kind, payload = parse_reply(raw_output)

        # Trường hợp A: LLM trả lời kết quả cuối cùng (Final Answer)
        if kind == "final":
            # Kiểm định R-07: Nếu vừa ghi đơn mà chưa xác minh lại thì BẮT BUỘC gọi tool đọc
            if pending_verification_cid:
                step.error = "Chưa verify đơn theo R-07"
                steps.append(step)
                messages.append({"role": "assistant", "content": raw_output})
                messages.append({
                    "role": "user",
                    "content": (
                        f"Observation: Error: Theo quy định R-07, bạn vừa tạo đơn {pending_verification_cid}. "
                        "BẮT BUỘC bạn phải gọi tool đọc 'check_complaint_status' với mã này để xác minh trước khi kết luận."
                    ),
                })
                continue

            final_answer = str(payload)
            step.action = "final_answer"
            step.observation = "[Done]"
            steps.append(step)
            break

        # Trường hợp B: LLM muốn gọi công cụ (Action: call_tool)
        elif kind == "action":
            tool_name, tool_args = payload
            step.action = "call_tool"
            step.tool_name = tool_name
            step.tool_args = tool_args

            # Thực thi tool qua hàm run_action (W6)
            obs = await run_action(tool_name, tool_args, mcp_client)

            # R-07: Theo dõi trạng thái Verify khi nộp khiếu nại
            if tool_name == "submit_complaint":
                cid_match = re.search(r"CPL-\d{4}-\d{4}", obs)
                if cid_match:
                    pending_verification_cid = cid_match.group(0)
            elif tool_name == "check_complaint_status":
                pending_verification_cid = None
                verified = True

            step.observation = obs
            steps.append(step)
            messages.append({"role": "assistant", "content": raw_output})
            messages.append({"role": "user", "content": f"Observation: {obs}"})

        # Trường hợp C: Định dạng JSON hoặc cú pháp bị sai -> Bắt lỗi mềm (R-06)
        else:
            step.error = str(payload)
            steps.append(step)
            messages.append({"role": "assistant", "content": raw_output})
            messages.append({"role": "user", "content": f"Observation: Error: {payload}. Vui lòng sửa lại định dạng chuẩn."})

    if not final_answer:
        final_answer = f"Đã đạt giới hạn tối đa {max_steps} bước mà chưa có câu trả lời cuối cùng."

    return {
        "final_answer": final_answer,
        "steps": [s.__dict__ for s in steps],
        "usage": usage,
        "verified": verified,
    }


# ---------------------------------------------------------------------------
# 6. Class ReActOrchestrator Đơn giản (Entrypoint chuẩn cho CLI & Evaluation)
# ---------------------------------------------------------------------------
class ReActOrchestrator:
    """Bộ điều phối ReAct tinh gọn: Chỉ có đúng 1 hàm run() đồng bộ và arun() bất đồng bộ."""

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

    async def arun(self, user_query: str, return_details: bool = False) -> Union[str, Dict[str, Any]]:
        """Chạy bất đồng bộ. Mặc định trả về chuỗi câu trả lời; trả về dict nếu return_details=True."""
        res = await react_agent(self.llm, self.mcp, user_query, self.max_steps, self.prompt_path)
        
        # Ghi log nếu có logger
        if self.logger and hasattr(self.logger, "log_record"):
            try:
                self.logger.log_record(
                    user_query=user_query,
                    final_answer=res["final_answer"],
                    steps=res["steps"],
                    usage=res["usage"],
                )
            except Exception:
                pass

        return res if return_details else res["final_answer"]

    def run(self, user_query: str, return_details: bool = False) -> Union[str, Dict[str, Any]]:
        """Chạy đồng bộ 1 lệnh duy nhất (Dễ dùng cho CLI và Demo)."""
        return run_sync(self.arun(user_query, return_details=return_details))

    # Alias tương thích ngược cho file test nếu có gọi
    async def arun_detailed(self, user_query: str, query_id: str = "interactive") -> Dict[str, Any]:
        return await self.arun(user_query, return_details=True)

    def run_detailed(self, user_query: str, query_id: str = "interactive") -> Dict[str, Any]:
        return self.run(user_query, return_details=True)
