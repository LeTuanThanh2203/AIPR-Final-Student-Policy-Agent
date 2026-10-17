"""Automated Evaluation Runner (make eval) — Phụ trách chính: Member C.

Thực hiện:
- Đọc testset từ tests/testset.jsonl (16 câu, gồm 4 câu no_answer theo PDF 02 §1.4).
- Gửi từng câu hỏi vào ReActOrchestrator.
- Đánh giá tự động:
  + Grounding accuracy (trích dẫn đúng căn cứ điều, khoản quy chế).
  + Calculation accuracy (tính đúng và áp mức trần quy định).
  + Tool Side-Effect & Verify (gọi tool nộp đơn và bắt buộc đối soát lại qua check_complaint_status - R-07).
  + Calibration Rate (tỉ lệ từ chối đúng trên các câu hỏi bẫy ngoài quy chế, mục tiêu >= 80% - R-05).
  + Đo đếm và tổng hợp Token Usage thật từ API (R-01).
- Xuất bảng kết quả đánh giá (Evaluation Summary Table).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Cấu hình chuẩn UTF-8 cho stdout và stderr trên Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Thêm thư mục gốc vào PYTHONPATH và loại bỏ src để tránh che khuất gói mcp
PROJECT_ROOT = Path(__file__).resolve().parent.parent
src_dir = str(PROJECT_ROOT / "src")
while src_dir in sys.path:
    sys.path.remove(src_dir)

proj_root_str = str(PROJECT_ROOT)
if proj_root_str in sys.path:
    sys.path.remove(proj_root_str)
sys.path.insert(0, proj_root_str)


from src.llm_client import RobustLLMClient
from src.mcp.client import MCPClientManager
from src.orchestrator import ReActOrchestrator
from src.utils.logger import SessionLogger, estimate_cost


# Từ khóa từ chối lịch sự khi gặp câu hỏi bẫy hoặc ngoài quy chế (Calibration)
REFUSAL_KEYWORDS = [
    "không có",
    "không tìm thấy",
    "từ chối",
    "không thuộc",
    "không nằm trong",
    "ngoài phạm vi",
    "không quy định",
    "không được quy đổi",
    "chưa có quy định",
    "không được công nhận",
    "không đủ dữ liệu",
    "không thể xác định",
]


def evaluate_single_query(test_item: Dict[str, Any], agent_response: Dict[str, Any]) -> Dict[str, Any]:
    """Đánh giá chi tiết kết quả của một câu hỏi kiểm thử đối chiếu với đáp án chuẩn."""
    final_answer = (agent_response.get("final_answer") or "").strip().lower()
    steps = agent_response.get("steps") or []
    verified = agent_response.get("verified", False)
    tier = test_item.get("tier", "unknown")
    item_type = test_item.get("type", "")

    passed = False
    details = ""

    # Nhóm 1: Kiểm tra Calibration trên các câu hỏi bẫy ngoài quy chế (no_answer: true)
    if test_item.get("no_answer", False) or tier == "calibration":
        # Agent phải biết nói "không biết" hoặc từ chối lịch sự, không được bịa đặt
        is_refused = any(kw in final_answer for kw in REFUSAL_KEYWORDS)
        passed = is_refused
        details = "Từ chối đúng câu bẫy" if passed else "Lỗi: Agent bị ảo giác, không từ chối câu bẫy"

    # Nhóm 2: Kiểm tra Tầng a - Tra cứu thông tin có căn cứ (Grounding Accuracy)
    elif tier == "a_lookup":
        expected_dieu = str(test_item.get("expected_dieu", "")).strip()
        expected_doc = str(test_item.get("expected_doc", "")).strip().lower()

        # Kiểm tra trích dẫn số Điều hoặc tên văn bản trong câu trả lời hoặc trong chuỗi suy luận
        has_dieu = f"điều {expected_dieu}" in final_answer or f"điều {expected_dieu}" in str(steps).lower() if expected_dieu else True
        has_doc = expected_doc in final_answer or expected_doc in str(steps).lower() if expected_doc else True

        passed = has_dieu and has_doc
        details = f"Khớp trích dẫn Điều {expected_dieu}" if passed else f"Lỗi: Thiếu trích dẫn Điều {expected_dieu}"

    # Nhóm 3: Kiểm tra Tầng b - Tính toán áp mức trần hoặc xử lý xung đột quy chế
    elif tier == "b_transform":
        if item_type == "calculation_caps":
            # Kiểm tra số điểm cuối cùng sau khi áp trần có xuất hiện trong câu trả lời không
            expected_calc = str(test_item.get("expected_calculation", ""))
            # Trích xuất số điểm kết quả ở vế sau dấu = (ví dụ: Min(3*5 + 10, 15) = 15 -> 15)
            match = re.search(r"=\s*(\d+)", expected_calc)
            expected_num = match.group(1) if match else ""
            passed = expected_num in final_answer if expected_num else True
            details = f"Tính đúng kết quả {expected_num}đ (có áp trần)" if passed else f"Lỗi: Không tìm thấy kết quả {expected_num}đ"
        elif item_type == "missing_data_refusal":
            # Nhận diện thiếu dữ liệu và từ chối kết luận vội vàng
            passed = any(kw in final_answer for kw in ["thiếu", "không đủ", "chưa đủ", "cần thêm"])
            details = "Nhận diện đúng việc thiếu dữ liệu" if passed else "Lỗi: Đưa ra kết luận khi thiếu dữ liệu"
        else:
            # So sánh xung đột giữa các phiên bản quy chế
            passed = "2024" in final_answer or "mới nhất" in final_answer or "thay đổi" in final_answer
            details = "Xử lý đúng xung đột phiên bản quy chế" if passed else "Lỗi: Chưa chỉ ra xung đột quy chế"

    # Nhóm 4: Kiểm tra Tầng c - Tác vụ ghi có tác dụng phụ và bắt buộc xác minh (R-07)
    elif tier == "c_action":
        called_tools = [s.get("tool_name") for s in steps if isinstance(s, dict) and s.get("tool_name")]
        has_submit = "submit_complaint" in called_tools
        has_check = "check_complaint_status" in called_tools or verified
        passed = has_submit and has_check
        details = "Gọi tool ghi và xác minh lại thành công (R-07)" if passed else "Lỗi: Chưa gọi đủ tool ghi và đọc để verify theo R-07"

    return {
        "id": test_item.get("id"),
        "tier": tier,
        "type": item_type,
        "passed": passed,
        "details": details,
    }


async def run_evaluation_async(testset_path: str = "tests/testset.jsonl") -> Dict[str, Any]:
    """Chạy trọn vẹn quy trình đánh giá tự động và in báo cáo tổng hợp."""
    path = Path(testset_path)
    if not path.is_file():
        # Tìm từ thư mục gốc dự án
        path = PROJECT_ROOT / testset_path
        if not path.is_file():
            raise FileNotFoundError(f"Không tìm thấy file kiểm thử: {testset_path}")

    # Đọc danh sách câu hỏi kiểm thử từ file JSON Lines
    test_items: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                test_items.append(json.loads(line_str))

    print("=" * 80)
    print(f"BẮT ĐẦU ĐÁNH GIÁ TỰ ĐỘNG TRỢ LÝ ĐIỂM RÈN LUYỆN T4 ({len(test_items)} CÂU HỎI)")
    print("=" * 80)

    # Khởi tạo các thành phần hệ thống của Member C
    llm_client = RobustLLMClient()
    logger = SessionLogger(log_dir="logs")
    mcp_manager = MCPClientManager()

    # Thử kết nối MCP Server để sẵn sàng thực thi công cụ
    try:
        await mcp_manager.connect()
    except Exception as err:
        print(f"[Cảnh báo] Chưa thể khởi động MCP Server qua stdio: {err}")

    orchestrator = ReActOrchestrator(
        llm_client=llm_client,
        mcp_client=mcp_manager,
        logger=logger,
        max_steps=10,
    )

    results: List[Dict[str, Any]] = []
    total_prompt_tokens = 0
    total_completion_tokens = 0
    start_time = time.time()

    for idx, item in enumerate(test_items, start=1):
        q_id = item.get("id", f"Q{idx:02d}")
        question = item.get("question", "")
        tier = item.get("tier", "")
        print(f"\n[{idx}/{len(test_items)}] Đang xử lý {q_id} ({tier}): {question[:65]}...")

        try:
            # Gửi câu hỏi vào ReAct Agent
            agent_resp = await orchestrator.arun(question, return_details=True)
            if not isinstance(agent_resp, dict):
                agent_resp = {"final_answer": str(agent_resp), "steps": [], "usage": {}}
        except Exception as exc:
            agent_resp = {"final_answer": f"Lỗi thực thi: {exc}", "steps": [], "usage": {}}

        # Đo đếm token usage thật tích lũy
        u = agent_resp.get("usage") or {}
        p_tokens = u.get("prompt_tokens", 0)
        c_tokens = u.get("completion_tokens", 0)
        total_prompt_tokens += p_tokens
        total_completion_tokens += c_tokens

        # Chấm điểm câu trả lời
        eval_res = evaluate_single_query(item, agent_resp)
        results.append(eval_res)

        status_text = "ĐẠT" if eval_res["passed"] else "CHƯA ĐẠT"
        print(f" -> Kết quả: {status_text} | {eval_res['details']}")

    # Đóng kết nối MCP an toàn sau khi hoàn thành
    await mcp_manager.close()

    elapsed_time = time.time() - start_time
    total_tokens = total_prompt_tokens + total_completion_tokens
    model_name = getattr(llm_client, "model", "qwen/qwen3.8-27b")
    cost_usd = estimate_cost(model_name, total_prompt_tokens, total_completion_tokens)

    # Thống kê kết quả theo từng tầng nghiệp vụ
    def calc_rate(tier_name: str) -> tuple[int, int, float]:
        tier_items = [r for r in results if r.get("tier") == tier_name]
        if not tier_items:
            return 0, 0, 0.0
        passed_cnt = sum(1 for r in tier_items if r.get("passed"))
        return passed_cnt, len(tier_items), (passed_cnt / len(tier_items)) * 100.0

    a_pass, a_tot, a_rate = calc_rate("a_lookup")
    b_pass, b_tot, b_rate = calc_rate("b_transform")
    c_pass, c_tot, c_rate = calc_rate("c_action")
    cal_pass, cal_tot, cal_rate = calc_rate("calibration")
    total_passed = sum(1 for r in results if r.get("passed"))
    overall_rate = (total_passed / len(results)) * 100.0 if results else 0.0

    # In Bảng tổng kết kết quả đánh giá (Evaluation Summary Table)
    print("\n" + "=" * 80)
    print("                    BẢNG TỔNG KẾT ĐÁNH GIÁ HỆ THỐNG AGENT T4")
    print("=" * 80)
    print(f"{'Hạng mục kiểm thử':<42} | {'Đạt / Tổng số':<15} | {'Tỉ lệ (%)':<10}")
    print("-" * 80)
    print(f"{'Tầng a: Tra cứu RAG trích dẫn căn cứ':<42} | {f'{a_pass}/{a_tot}':<15} | {f'{a_rate:.1f}%':<10}")
    print(f"{'Tầng b: Tính toán & Áp trần quy chế':<42} | {f'{b_pass}/{b_tot}':<15} | {f'{b_rate:.1f}%':<10}")
    print(f"{'Tầng c: Nộp khiếu nại & Verify (R-07)':<42} | {f'{c_pass}/{c_tot}':<15} | {f'{c_rate:.1f}%':<10}")
    print(f"{'Calibration Rate: Từ chối câu hỏi bẫy':<42} | {f'{cal_pass}/{cal_tot}':<15} | {f'{cal_rate:.1f}%':<10}")
    print("-" * 80)
    print(f"{'TỔNG KẾT TOÀN BỘ BỘ KIỂM THỬ':<42} | {f'{total_passed}/{len(results)}':<15} | {f'{overall_rate:.1f}%':<10}")
    print("-" * 80)
    print(f"Tổng token tiêu thụ : {total_tokens:,} tokens (Input: {total_prompt_tokens:,} | Output: {total_completion_tokens:,})")
    print(f"Ước tính chi phí API : ${cost_usd:.6f} USD (Model: {model_name})")
    print(f"Tổng thời gian chạy : {elapsed_time:.2f} giây ({elapsed_time/len(test_items):.2f}s/câu)")
    print("=" * 80)

    return {
        "results": results,
        "metrics": {
            "a_lookup_rate": a_rate,
            "b_transform_rate": b_rate,
            "c_action_rate": c_rate,
            "calibration_rate": cal_rate,
            "overall_rate": overall_rate,
            "total_tokens": total_tokens,
            "estimated_cost_usd": cost_usd,
        },
    }


def run_evaluation(testset_path: str = "tests/testset.jsonl") -> Dict[str, Any]:
    """Hàm bao bọc đồng bộ để gọi từ dòng lệnh hoặc Makefile."""
    return asyncio.run(run_evaluation_async(testset_path))


# ===========================================================================
# CÁC HÀM KIỂM THỬ ĐƠN VỊ (UNIT TESTS) CHO LOGIC ĐÁNH GIÁ (MEMBER C)
# ===========================================================================

def test_evaluate_calibration_refusal_pass():
    """Kiểm thử trường hợp Agent từ chối đúng câu bẫy không có trong quy chế."""
    test_item = {
        "id": "Q_CALIB_01",
        "tier": "calibration",
        "no_answer": True,
        "question": "Quy đổi chứng chỉ lái xe sang điểm rèn luyện?",
    }
    agent_response = {
        "final_answer": "Quy chế không quy định việc quy đổi giấy phép lái xe sang điểm rèn luyện.",
        "steps": [],
    }
    result = evaluate_single_query(test_item, agent_response)
    assert result["passed"] is True
    assert "Từ chối đúng" in result["details"]


def test_evaluate_calibration_hallucination_fail():
    """Kiểm thử trường hợp Agent bị ảo giác, không từ chối câu bẫy."""
    test_item = {
        "id": "Q_CALIB_02",
        "tier": "calibration",
        "no_answer": True,
        "question": "Điểm rèn luyện cho hoạt động câu cá?",
    }
    agent_response = {
        "final_answer": "Bạn được cộng 5 điểm cho hoạt động câu cá theo quy định.",
        "steps": [],
    }
    result = evaluate_single_query(test_item, agent_response)
    assert result["passed"] is False
    assert "ảo giác" in result["details"]


def test_evaluate_lookup_with_citation_pass():
    """Kiểm thử trích dẫn đầy đủ số Điều và tên văn bản quy chế."""
    test_item = {
        "id": "Q_A_01",
        "tier": "a_lookup",
        "expected_dieu": "8",
        "expected_doc": "42/2024",
    }
    agent_response = {
        "final_answer": "Căn cứ theo Điều 8 của quy chế 42/2024, sinh viên vi phạm bị trừ điểm.",
        "steps": [],
    }
    result = evaluate_single_query(test_item, agent_response)
    assert result["passed"] is True


def test_evaluate_calculation_with_cap_pass():
    """Kiểm thử tính toán đúng mức trần quy chế."""
    test_item = {
        "id": "Q_B_01",
        "tier": "b_transform",
        "type": "calculation_caps",
        "expected_calculation": "Min(3*5 + 10, 15) = 15",
    }
    agent_response = {
        "final_answer": "Tổng điểm tích lũy của bạn sau khi áp mức trần tối đa là 15 điểm.",
        "steps": [],
    }
    result = evaluate_single_query(test_item, agent_response)
    assert result["passed"] is True


def test_evaluate_action_with_verification_pass():
    """Kiểm thử tầng c tuân thủ đúng R-07 (gọi submit và check lại)."""
    test_item = {
        "id": "Q_C_01",
        "tier": "c_action",
    }
    agent_response = {
        "final_answer": "Đơn khiếu nại CPL-2024-0012 đã được ghi nhận và xác thực thành công.",
        "steps": [
            {"tool_name": "submit_complaint"},
            {"tool_name": "check_complaint_status"},
        ],
        "verified": True,
    }
    result = evaluate_single_query(test_item, agent_response)
    assert result["passed"] is True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate AIPR Assistant T4")
    parser.add_argument("--testset", default="tests/testset.jsonl", help="Path to testset JSONL")
    args = parser.parse_args()
    run_evaluation(args.testset)


