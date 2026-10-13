"""LLM Client Wrapper (Kế thừa từ W2/api_helpers.py)."""

from __future__ import annotations
from typing import Any, Dict, List, Optional


def load_prompt(filename: str, prompts_dir: str = "prompts") -> str:
    """Nạp nội dung System Prompt từ thư mục prompts/ (R-04: prompt tách khỏi code)."""
    # Gợi ý: Đọc file text trong prompts_dir / filename
    pass


class RobustLLMClient:
    """Client giao tiếp LLM an toàn có cơ chế thử lại."""

    def __init__(self, model: str = "gpt-4o-mini", max_retries: int = 3, timeout: int = 30):
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout

    def generate(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        # Gợi ý (R-04):
        # 1. Gọi client.chat.completions.create với timeout=self.timeout.
        # 2. Vòng lặp try/except với time.sleep(2 ** attempt) khi gặp lỗi mạng/rate limit.
        # 3. Trả về dict chứa "content" và "usage" (prompt_tokens, completion_tokens).
        pass
