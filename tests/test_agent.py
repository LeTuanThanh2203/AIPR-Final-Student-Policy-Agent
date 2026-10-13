"""Automated Evaluation Runner (make eval) — Phụ trách chính: Member C.

Thực hiện:
- Đọc testset từ tests/testset.jsonl (>= 12 câu, gồm >= 4 câu no_answer - PDF 02 §1.4).
- Gửi từng câu hỏi vào Orchestrator.
- Đánh giá:
  + Grounding accuracy (trích dẫn đúng doc_id, điều, khoản).
  + Calculation accuracy (tính đúng và áp mức trần).
  + Tool Side-Effect & Verify (đã gọi tool Ghi và tool Đọc để xác minh - R-07).
  + Calibration Rate: Tỉ lệ từ chối đúng trên các câu no_answer (mục tiêu >= 80% - R-05).
  + Đo đếm và tổng hợp Token Usage thật từ API (R-01).
- Xuất bảng kết quả đánh giá (Evaluation Summary Table).
"""

from __future__ import annotations
import argparse
from typing import Dict, List, Any


def evaluate_single_query(test_item: Dict[str, Any], agent_response: Dict[str, Any]) -> Dict[str, Any]:
    """Đánh giá kết quả của 1 câu hỏi kiểm thử."""
    # Gợi ý: So sánh agent_response với test_item['no_answer'], expected_doc, expected_calculation
    pass


def run_evaluation(testset_path: str = "tests/testset.jsonl") -> Dict[str, Any]:
    """Chạy toàn bộ bài đánh giá trên tập testset và in báo cáo."""
    # Gợi ý:
    # 1. Đọc từng dòng json trong testset_path
    # 2. Khởi tạo Orchestrator và SessionLogger
    # 3. Chạy từng câu hỏi, thu thập metric (grounding, calculation, calibration, tool_verify, tokens)
    # 4. In bảng tổng kết ra màn hình terminal
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate AIPR Assistant T4")
    parser.add_argument("--testset", default="tests/testset.jsonl", help="Path to testset JSONL")
    args = parser.parse_args()
    run_evaluation(args.testset)
