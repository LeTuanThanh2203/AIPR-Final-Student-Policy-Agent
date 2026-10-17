"""Bộ kiểm thử đơn vị cho module Session Logger (src/utils/logger.py).

Mục đích:
- Kiểm tra việc tự động khởi tạo thư mục và file log JSONL theo mốc thời gian.
- Kiểm tra tính toán chi phí token (cost estimation) kế thừa từ Tuần 2.
- Kiểm tra việc ghi log đầy đủ các trường (query_id, user_query, steps, usage, final_answer).
- Đảm bảo dữ liệu tiếng Việt có dấu được lưu đúng chuẩn UTF-8, không bị lỗi font khi phân tích sau này.
"""

import os
import json
import tempfile
import pytest
from src.utils.logger import SessionLogger, PRICING


def test_session_logger_init_and_file_creation():
    """Kiểm tra SessionLogger tự động tạo thư mục và sinh đường dẫn file log hợp lệ."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = SessionLogger(log_dir=tmpdir)
        # Đường dẫn file log phải nằm trong thư mục tạm vừa tạo và có đuôi .jsonl
        assert os.path.exists(tmpdir)
        assert logger.log_file.endswith(".jsonl")
        assert tmpdir in logger.log_file


def test_estimate_cost_calculation():
    """Kiểm tra công thức tính chi phí token theo bảng giá của model ở Tuần 2."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = SessionLogger(log_dir=tmpdir)
        # Giả sử 1.000.000 input tokens (0.15$) và 1.000.000 output tokens (0.30$)
        cost = logger.estimate_cost(1_000_000, 1_000_000, model="openai/gpt-oss-20b")
        assert round(cost, 2) == 0.45


def test_log_record_content_and_utf8_encoding():
    """Kiểm tra ghi log đầy đủ các trường và giữ nguyên định dạng tiếng Việt có dấu."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_name = "test_run.jsonl"
        logger = SessionLogger(log_dir=tmpdir, session_file=session_name)

        mock_steps = [
            {"step_number": 1, "thought": "Cần tra cứu quy chế", "action": "call_tool", "tool_name": "lookup"},
            {"step_number": 2, "thought": "Đã có thông tin", "action": "final_answer", "observation": "[Done]"},
        ]
        mock_usage = {
            "calls": 2,
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }

        # Thực hiện ghi 1 bản ghi vào logger
        record = logger.log_record(
            query_id="Q01",
            user_query="Quy chế điểm rèn luyện năm 2024?",
            steps=mock_steps,
            usage=mock_usage,
            final_answer="Điểm tối đa là 100 điểm.",
        )

        # File log phải được tạo ra trên đĩa
        assert os.path.exists(logger.log_file)

        # Đọc lại nội dung file và kiểm tra từng trường dữ liệu
        with open(logger.log_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        assert len(lines) == 1
        logged_data = lines[0]

        # Xác nhận các trường khớp với dữ liệu truyền vào
        assert logged_data["query_id"] == "Q01"
        assert logged_data["user_query"] == "Quy chế điểm rèn luyện năm 2024?"
        assert logged_data["final_answer"] == "Điểm tối đa là 100 điểm."
        assert len(logged_data["steps"]) == 2
        assert logged_data["usage"]["total_tokens"] == 150
        assert logged_data["cost_estimate_usd"] > 0
