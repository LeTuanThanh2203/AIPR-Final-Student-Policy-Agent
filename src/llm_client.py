"""LLM Client Wrapper (Sử dụng Groq)."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from groq import Groq

load_dotenv()


def load_prompt(filename: str, prompts_dir: str = "prompts") -> str:
    """Nạp nội dung System Prompt từ thư mục prompts/ (R-04: prompt tách khỏi code)."""
    # Gợi ý: Đọc file text trong prompts_dir / filename
    filepath = os.path.join(prompts_dir, filename)
    if not os.path.exists(filepath):
        # Fallback kiểm tra từ thư mục gốc dự án
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filepath = os.path.join(base_dir, prompts_dir, filename)

    with open(filepath, "r", encoding="utf-8") as f:
        return f.read().strip()


class RobustLLMClient:
    """Client giao tiếp Groq an toàn có cơ chế thử lại."""

    def __init__(
        self,
        model: str = "openai/gpt-oss-20b",
        max_retries: int = 3,
        timeout: int = 30,
        client: Optional[Any] = None,
    ):
        self.model = os.getenv("MODEL") or model
        self.max_retries = max_retries
        self.timeout = timeout
        if client is not None:
            self.client = client
        else:
            api_key = os.getenv("GROQ_API_KEY") or "gsk-dummy"
            self.client = Groq(api_key=api_key)

    def generate(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Gọi Groq API với cơ chế thử lại Exponential Backoff (W2 & R-04)."""
        for attempt in range(self.max_retries):
            try:
                # Gửi yêu cầu sinh phản hồi đến Groq API kèm thời gian chờ tối đa
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    timeout=self.timeout,
                )

                # Bóc tách nội dung câu trả lời và số lượng token tiêu thụ thực tế
                return {
                    "content": response.choices[0].message.content or "",
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    },
                }
            except Exception as e:
                # Bắt lỗi đặc biệt của Groq khi model (như openai/gpt-oss-20b) tự động kích hoạt tool_use_failed
                err_body = getattr(e, "body", {})
                if isinstance(err_body, dict):
                    err_info = err_body.get("error", {})
                    if err_info.get("code") == "tool_use_failed" and "failed_generation" in err_info:
                        try:
                            tool_data = json.loads(err_info["failed_generation"])
                            tool_name = str(tool_data.get("name") or "").replace("tool_", "").strip()
                            tool_args = tool_data.get("arguments") or {}
                            react_payload = {
                                "thought": f"Cần gọi công cụ {tool_name} để tra cứu",
                                "action": "call_tool",
                                "tool_name": tool_name,
                                "tool_args": tool_args if isinstance(tool_args, dict) else {"query": str(tool_args)},
                            }
                            return {
                                "content": json.dumps(react_payload, ensure_ascii=False),
                                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                            }
                        except Exception:
                            pass

                # Nếu đã thử đến lần cuối cùng mà vẫn lỗi thì ném exception ra ngoài
                if attempt == self.max_retries - 1:
                    raise e
                # Khi gặp lỗi mạng hoặc quá tải (rate limit), tạm dừng theo hàm số mũ rồi thử lại
                time.sleep(2 ** attempt)
