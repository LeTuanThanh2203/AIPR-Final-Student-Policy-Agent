"""MCP Client cho Đề tài T4 (Đồ án AIPR).

Cung cấp kết nối stdio tới MCP Server và khám phá công cụ động (W7/R-08):
- Khám phá danh sách công cụ động qua list_tools() (R-08).
- Thực thi công cụ qua call_tool() và trả về kết quả dạng chuỗi (W7).
- Thiết kế tinh gọn, dễ hiểu, phù hợp sinh viên năm 3.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Tự động gỡ bỏ thư mục 'src' khỏi sys.path để không che khuất thư viện 'mcp' chính thức (R-08)
_src_dir = Path(__file__).resolve().parent.parent
sys.path = [p for p in sys.path if Path(p).resolve() != _src_dir and p != "src"]

from mcp import Client
from mcp.client.stdio import StdioServerParameters

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SERVER_SCRIPT = str(PROJECT_ROOT / "src" / "mcp" / "server.py")


@dataclass
class ToolDefinition:
    """Mô tả công cụ MCP (Dynamic Discovery)."""
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCallResult:
    """Kết quả khi gọi tool MCP."""
    tool_name: str
    is_error: bool
    content: str

    def __str__(self) -> str:
        return self.content


class MCPClientManager:
    """Quản lý kết nối Client tới MCP Server qua giao thức stdio (W7)."""

    def __init__(
        self,
        server_script: Optional[str] = None,
        command: str = "uv",
        args: Optional[List[str]] = None,
    ) -> None:
        self.command = command
        script = server_script or DEFAULT_SERVER_SCRIPT
        self.args = args or ["run", script]

        env = dict(os.environ)
        env["PYTHONPATH"] = str(PROJECT_ROOT)
        self.server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=env,
        )
        self.client: Optional[Client] = None

    async def connect(self) -> None:
        """Khởi động tiến trình con MCP Server và bắt tay stdio."""
        if self.client is None:
            self.client = Client(self.server_params)
            await self.client.__aenter__()

    async def close(self) -> None:
        """Đóng kết nối stdio an toàn."""
        if self.client is not None:
            try:
                await self.client.__aexit__(None, None, None)
            except Exception:
                pass
            finally:
                self.client = None

    async def __aenter__(self) -> MCPClientManager:
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def list_tools(self) -> List[Any]:
        """Khám phá động danh sách công cụ từ MCP Server (R-08)."""
        if self.client is None:
            await self.connect()
        res = await self.client.list_tools()
        return res.tools if hasattr(res, "tools") else (res if isinstance(res, list) else [])

    async def list_available_tools(self) -> List[Any]:
        """Alias tương thích cho list_tools()."""
        return await self.list_tools()

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> ToolCallResult:
        """Gọi công cụ trên MCP Server qua stdio và trích xuất chuỗi quan sát."""
        if self.client is None:
            await self.connect()

        try:
            res = await self.client.call_tool(name, arguments)
            
            # Trích xuất văn bản từ content blocks (chuẩn MCP SDK W7)
            content_text = ""
            if hasattr(res, "content") and res.content:
                parts = [c.text for c in res.content if hasattr(c, "text")]
                content_text = "\n".join(parts) if parts else str(res.content)
            else:
                content_text = str(res)

            is_err = getattr(res, "is_error", False)
            return ToolCallResult(tool_name=name, is_error=is_err, content=content_text)
        except Exception as err:
            return ToolCallResult(tool_name=name, is_error=True, content=f"Error khi gọi tool '{name}': {err}")
