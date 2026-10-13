"""MCP Subsystem Package.

Cung cấp các thành phần cho giao thức Model Context Protocol (stdio):
- schemas: Các Typed Schema @dataclass (SubmitComplaintInput, CheckComplaintInput, ...)
- server: MCP Server chạy qua stdio, đảm bảo stdout sạch 100%
- client: MCP Client khám phá công cụ động (Dynamic Tool Discovery)
"""

from src.mcp.schemas import (
    SubmitComplaintInput,
    SubmitComplaintOutput,
    CheckComplaintInput,
    ComplaintRecord,
)

__all__ = [
    "SubmitComplaintInput",
    "SubmitComplaintOutput",
    "CheckComplaintInput",
    "ComplaintRecord",
]
