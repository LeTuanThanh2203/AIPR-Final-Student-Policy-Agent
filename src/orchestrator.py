"""ReAct Agent Orchestrator (Kế thừa từ W6/ex1_2_ag_loop.py)."""

from __future__ import annotations
from typing import Any, Dict, List, Optional

MAX_STEPS = 10


class ReActOrchestrator:
    """Bộ điều phối Agent theo mô hình ReAct (Think -> Act -> Observe)."""

    def __init__(self, llm_client: Any = None, mcp_client: Any = None, logger: Any = None):
        self.llm = llm_client
        self.mcp = mcp_client
        self.logger = logger
        self.max_steps = MAX_STEPS

    def run(self, user_query: str, query_id: str = "interactive") -> str:
        # Gợi ý (R-02, R-06, R-07):
        # 1. Chạy vòng lặp for step in range(self.max_steps).
        # 2. Gọi LLM để sinh Thought và Action (Tool Call).
        # 3. Try/except khi gọi tool: nếu lỗi trả chuỗi "Error: ..." cho LLM sửa (không crash).
        # 4. Khi gọi tool Ghi (submit_complaint), bắt buộc gọi tool Đọc (check_complaint_status) để VERIFY.
        pass
