"""System Configuration & Constants."""

from pathlib import Path

# Thư mục gốc & đường dẫn
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
COMPLAINTS_DB_PATH = DATA_DIR / "complaints.json"
CHUNKS_FILE_PATH = DATA_DIR / "processed" / "chunks.json"
LOGS_DIR = BASE_DIR / "logs"

# Hằng số mặc định
DEFAULT_MODEL = "gpt-4o-mini"
MAX_AGENT_STEPS = 10
CALIBRATION_THRESHOLD = 0.25
