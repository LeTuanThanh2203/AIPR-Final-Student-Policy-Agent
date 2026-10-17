"""MCP Subsystem Package (Đề tài T4 - AIPR Final Project).

Cung cấp các thành phần cho giao thức Model Context Protocol (stdio):
- schemas: Các Typed Schema @dataclass cho 2 tool (SubmitComplaintInput, CheckComplaintInput, ...)
- server: MCP Server chạy qua stdio, đảm bảo stdout sạch 100% (R-08)
- client: MCP Client khám phá công cụ động (Dynamic Tool Discovery)
"""

import sys
from pathlib import Path

# Tự động gỡ bỏ thư mục 'src' khỏi sys.path để không che khuất thư viện 'mcp' chính thức
_src_dir = Path(__file__).resolve().parent.parent
sys.path = [p for p in sys.path if Path(p).resolve() != _src_dir and p != "src"]

from src.mcp.schemas import (
    CheckComplaintInput,
    ComplaintRecord,
    LookupPolicyInput,
    SubmitComplaintInput,
    SubmitComplaintOutput,
)
from src.mcp.client import (
    MCPClientManager,
    ToolCallResult,
    ToolDefinition,
)

__all__ = [
    "LookupPolicyInput",
    "SubmitComplaintInput",
    "SubmitComplaintOutput",
    "CheckComplaintInput",
    "ComplaintRecord",
    "MCPClientManager",
    "ToolDefinition",
    "ToolCallResult",
]
