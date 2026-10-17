"""Bộ kiểm thử đơn vị cho module LLM Client (src/llm_client.py).

Mục đích:
- Kiểm tra tính đúng đắn của việc nạp System Prompt từ thư mục ngoài.
- Dùng kỹ thuật Giả lập (Mock) để kiểm tra việc gọi API và bóc tách token usage mà không tốn chi phí gọi thật.
- Kiểm tra cơ chế tự động thử lại (Exponential Backoff) khi gặp sự cố mạng hoặc nghẽn API.
"""

import pytest
from unittest.mock import MagicMock
from src.llm_client import load_prompt, RobustLLMClient


def test_load_prompt_success():
    """Kiểm tra nạp file prompt có sẵn từ thư mục prompts/."""
    # Đọc thử file prompt grounding của RAG và xác nhận nội dung không bị rỗng
    content = load_prompt("rag_grounding.txt")
    assert len(content) > 0


def test_load_prompt_not_found():
    """Kiểm tra khả năng bắt lỗi khi file prompt không tồn tại."""
    # Hệ thống phải báo lỗi FileNotFoundError để tránh chạy nhầm prompt rỗng
    with pytest.raises(FileNotFoundError):
        load_prompt("non_existent_prompt.txt")


def test_robust_client_generate_success():
    """Kiểm tra gọi API thành công và trích xuất đúng số lượng token thật từ đối tượng phản hồi."""
    # Tạo đối tượng phản hồi giả lập (Mock Response) có đầy đủ choices và usage
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Xin chào, tôi là Trợ lý AI."
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 25
    mock_response.usage.completion_tokens = 10
    mock_response.usage.total_tokens = 35

    # Thiết lập client giả trả về mock_response ngay lần đầu gọi
    mock_client.chat.completions.create.return_value = mock_response

    # Truyền mock_client vào RobustLLMClient để kiểm tra hàm generate
    client = RobustLLMClient(client=mock_client)
    res = client.generate([{"role": "user", "content": "Alo"}])

    # Xác nhận nội dung và số lượng token được bóc tách chính xác
    assert res["content"] == "Xin chào, tôi là Trợ lý AI."
    assert res["usage"]["prompt_tokens"] == 25
    assert res["usage"]["completion_tokens"] == 10
    assert res["usage"]["total_tokens"] == 35
    # Xác nhận API chỉ cần gọi 1 lần khi thành công
    assert mock_client.chat.completions.create.call_count == 1


def test_robust_client_retry_on_error():
    """Kiểm tra cơ chế Exponential Backoff thử lại khi gặp lỗi tạm thời (lỗi mạng hoặc rate limit)."""
    mock_client = MagicMock()

    # Dữ liệu phản hồi giả lập cho lần gọi thành công sau khi thử lại
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Đã thử lại thành công!"
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 15
    mock_response.usage.completion_tokens = 5
    mock_response.usage.total_tokens = 20

    # Giả lập: Lần gọi thứ 1 ném exception (mô phỏng mất mạng/rate limit), lần gọi thứ 2 mới thành công
    mock_client.chat.completions.create.side_effect = [
        Exception("Rate limit / Network error"),
        mock_response,
    ]

    # Cấu hình tối đa 2 lần thử lại
    client = RobustLLMClient(client=mock_client, max_retries=2)
    res = client.generate([{"role": "user", "content": "Test retry"}])

    # Xác nhận hàm generate đã tự động thử lại lần thứ 2 và lấy được kết quả thành công
    assert res["content"] == "Đã thử lại thành công!"
    # Xác nhận API đã được gọi đúng 2 lần (1 lần thất bại + 1 lần thành công)
    assert mock_client.chat.completions.create.call_count == 2
