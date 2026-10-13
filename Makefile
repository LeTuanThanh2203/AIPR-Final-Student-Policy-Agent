# ====================================================================
# AIPR FINAL PROJECT — ĐỀ TÀI T4
# Lệnh khởi chạy: make setup && make demo | make eval
# ====================================================================

.PHONY: setup demo eval clean test

setup:
	@echo "=== 1. Cài đặt môi trường ảo và thư viện phụ thuộc bằng uv ==="
	uv sync
	@python -c "import shutil, os; shutil.copyfile('.env.example', '.env') if not os.path.exists('.env') else None"
	@echo "=== 2. Khởi tạo dữ liệu và cấu trúc chỉ mục RAG ==="
	uv run python src/rag/document_parser.py

demo:
	@echo "=== Khởi chạy giao diện dòng lệnh tương tác Trợ lý T4 ==="
	uv run python src/main.py

eval:
	@echo "=== Chạy đánh giá tự động trên bộ kiểm thử testset.jsonl ==="
	uv run python tests/test_agent.py --testset tests/testset.jsonl

test:
	@echo "=== Chạy kiểm thử đơn vị (pytest) ==="
	uv run pytest

clean:
	@echo "=== Dọn dẹp cache và file tạm ==="
	@python -c "import pathlib, shutil; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]"
