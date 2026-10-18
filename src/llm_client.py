"""LLM Client Wrapper (Sử dụng Groq)."""

from __future__ import annotations

import os
import re
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
                err_str = str(e)

                # Bóc tách riêng phần thông điệp 'message' ngắn gọn, tránh in toàn bộ body response rộng
                err_message = None
                if hasattr(e, "body") and isinstance(e.body, dict):
                    err_obj = e.body.get("error")
                    if isinstance(err_obj, dict):
                        err_message = err_obj.get("message")
                    elif isinstance(err_obj, str):
                        err_message = err_obj

                if not err_message:
                    match_msg = re.search(r"['\"]message['\"]:\s*['\"]([^'\"]+)['\"]", err_str)
                    err_message = match_msg.group(1) if match_msg else err_str

                err_detail = f"Mã HTTP {status_code} - {err_message}" if status_code else err_message

                # Nếu gặp rate limit (429), bóc tách thời gian chờ cụ thể do Groq yêu cầu (10-20s)
                wait_time = float(2 ** attempt)
                if "429" in err_str or "rate limit" in err_str.lower() or status_code == 429:
                    match = re.search(r"try again in (\d+(?:\.\d+)?)s", err_str, re.IGNORECASE)
                    if match:
                        wait_time = max(float(match.group(1)) + 1.0, 10.0)
                    else:
                        wait_time = max(wait_time, 10.0)

                print(
                    f"[LLMClient] Cảnh báo lỗi API (Lần thử {attempt + 1}/{self.max_retries}): {err_detail}. "
                    f"Đang tạm dừng {wait_time:.1f}s trước khi thử lại..."
                )

                # Nếu đã thử đến lần cuối cùng mà vẫn lỗi thì ném exception ra ngoài
                if attempt == self.max_retries - 1:
                    print(f"[LLMClient] Đã thử lại tối đa {self.max_retries} lần nhưng vẫn thất bại.")
                    raise e

                # Tạm dừng trước khi thử lại
                time.sleep(wait_time)
