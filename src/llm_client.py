"""LLM Client Wrapper (Sử dụng Groq)."""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from groq import Groq

# Đảm bảo hiển thị UTF-8 an toàn trên console Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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


DEFAULT_MODEL = "qwen/qwen3.8-27b"


class RobustLLMClient:
    """Client giao tiếp Groq an toàn có cơ chế thử lại."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
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
                # Trích xuất mã trạng thái HTTP nếu có (từ Groq API Error hoặc HTTP error)
                status_code = getattr(e, "status_code", None)
                err_detail = f"Mã HTTP {status_code} - {e}" if status_code else str(e)
                print(
                    f"[LLMClient] Cảnh báo lỗi API (Lần thử {attempt + 1}/{self.max_retries}): {err_detail}. "
                    f"Đang tạm dừng {2 ** attempt}s trước khi thử lại..."
                )

                # Nếu đã thử đến lần cuối cùng mà vẫn lỗi thì ném exception ra ngoài
                if attempt == self.max_retries - 1:
                    print(f"[LLMClient] Đã thử lại tối đa {self.max_retries} lần nhưng vẫn thất bại.")
                    raise e

                # Khi gặp lỗi mạng hoặc quá tải (rate limit), tạm dừng theo hàm số mũ rồi thử lại
                time.sleep(2 ** attempt)
