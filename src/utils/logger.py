"""Session Logger (Ghi trace JSONL và USAGE token thật - R-01, kế thừa W2/api_helpers.py)."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# Bảng giá quy đổi token sang chi phí (kế thừa trực tiếp từ W2/api_helpers.py)
PRICING: Dict[str, Dict[str, float]] = {
    "openai/gpt-oss-20b": {
        "input": 0.15,   # Giá mỗi 1.000.000 input tokens (USD)
        "output": 0.30,  # Giá mỗi 1.000.000 output tokens (USD)
    },
    "llama-3.3-70b-versatile": {
        "input": 0.59,
        "output": 0.79,
    },
}


class SessionLogger:
    """Ghi log JSONL cho các phiên chạy thật (PDF 02 §1: logs/run_TIMESTAMP.jsonl)."""

    def __init__(self, log_dir: str = "logs", session_file: Optional[str] = None):
        self.log_dir = log_dir
        # Đảm bảo thư mục lưu log luôn tồn tại
        os.makedirs(self.log_dir, exist_ok=True)

        # Tự động đặt tên file log theo mốc thời gian phiên chạy nếu chưa chỉ định
        if session_file:
            self.log_file = os.path.join(self.log_dir, session_file) if not os.path.isabs(session_file) else session_file
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = os.path.join(self.log_dir, f"run_{timestamp}.jsonl")

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int, model: str = "openai/gpt-oss-20b") -> float:
        """Tính toán chi phí dựa trên token tiêu thụ (kế thừa W2/api_helpers.py)."""
        pricing = PRICING.get(model, PRICING["openai/gpt-oss-20b"])
        input_price = (prompt_tokens / 1_000_000) * pricing["input"]
        output_price = (completion_tokens / 1_000_000) * pricing["output"]
        return input_price + output_price

    def log_record(
        self,
        query_id: str = "interactive",
        user_query: str = "",
        steps: Optional[List[Any]] = None,
        usage: Optional[Dict[str, Any]] = None,
        final_answer: str = "",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Ghi nhận một bản ghi truy vấn hoàn chỉnh vào file log JSONL."""
        safe_steps = steps or []
        safe_usage = usage or {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        prompt_tokens = safe_usage.get("prompt_tokens", 0)
        completion_tokens = safe_usage.get("completion_tokens", 0)
        model_name = os.getenv("MODEL", "openai/gpt-oss-20b")
        cost = self.estimate_cost(prompt_tokens, completion_tokens, model=model_name)

        # Cấu trúc bản ghi JSON Lines chuẩn yêu cầu đồ án
        record = {
            "timestamp": datetime.now().isoformat(),
            "query_id": query_id,
            "user_query": user_query,
            "steps": safe_steps,
            "usage": safe_usage,
            "cost_estimate_usd": round(cost, 8),
            "final_answer": final_answer,
        }

        # Ghi nối tiếp vào file log với mã hóa utf-8 để giữ nguyên tiếng Việt
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return record
