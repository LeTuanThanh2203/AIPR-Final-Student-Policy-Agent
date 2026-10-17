"""Session Logger (Ghi trace JSONL và USAGE token thật - R-01)."""

from __future__ import annotations
from typing import Any, Dict, List


class SessionLogger:
    """Ghi log JSONL cho các phiên chạy thật (PDF 02 §1: logs/run_TIMESTAMP.jsonl)."""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir

    def log_record(
        self, query_id: str, user_query: str, steps: List[Any], usage: Dict[str, Any], final_answer: str
    ) -> None:
        # Gợi ý: Ghi nhận timestamp, query_id, steps, usage thật (calls, prompt_tokens, completion_tokens), final_answer
        pass
