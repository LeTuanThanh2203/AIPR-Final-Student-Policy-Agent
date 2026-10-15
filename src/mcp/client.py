"""MCP Client Manager cho Đề tài T4 (Đồ án AIPR).

Cung cấp khả năng kết nối MCP Server qua stdio và khám phá công cụ động (W7/R-08):
- Khám phá danh sách tools động (Dynamic Tool Discovery) qua API client.list_tools().
- Gọi tool qua API client.call_tool() và chuẩn hóa kết quả về ToolCallResult.
- Quản lý vòng đời kết nối an toàn (connect, close, async context manager).
- Xử lý các lỗi kết nối, tiến trình dừng đột ngột hoặc tool không tồn tại.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp import Client
from mcp.client.stdio import StdioServerParameters

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SERVER_SCRIPT = str(PROJECT_ROOT / "src" / "mcp" / "server.py")


@dataclass
class ToolDefinition:
    """Mô tả công cụ được khám phá động từ MCP Server (Dynamic Tool Discovery)."""
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCallResult:
    """Kết quả chuẩn hóa khi gọi một công cụ MCP."""
    tool_name: str
    is_error: bool
    content: str
    raw_data: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        return self.content


class MCPClientManager:
    """Quản lý kết nối Client tới MCP Server qua giao thức stdio."""

    def __init__(
        self,
        server_script: Optional[str] = None,
        command: str = "uv",
        args: Optional[List[str]] = None,
    ) -> None:
        self.command = command
        script_path = server_script or DEFAULT_SERVER_SCRIPT
        self.args = args if args is not None else ["run", script_path]

        # Cấu hình tham số tiến trình con stdio
        self.server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=dict(os.environ),
        )

        self._client: Optional[Client] = None
        self._is_connected: bool = False
        self._cached_tools: Dict[str, ToolDefinition] = {}

    @property
    def is_connected(self) -> bool:
        """Kiểm tra trạng thái kết nối hiện tại."""
        return self._is_connected

    async def connect(self) -> None:
        """Khởi động MCP Server qua tiến trình con stdio và thực hiện bắt tay giao thức."""
        if self._is_connected and self._client is not None:
            return

        try:
            self._client = Client(self.server_params)
            await self._client.__aenter__()
            self._is_connected = True
        except FileNotFoundError as err:
            self._is_connected = False
            self._client = None
            raise ConnectionError(
                f"Không tìm thấy lệnh '{self.command}' để khởi chạy MCP Server. "
                f"Hãy đảm bảo uv đã được cài đặt và có trong PATH."
            ) from err
        except Exception as err:
            self._is_connected = False
            self._client = None
            raise ConnectionError(f"Không thể kết nối tới MCP Server: {err}") from err

    async def close(self) -> None:
        """Đóng kết nối an toàn và giải phóng tiến trình con MCP Server."""
        if not self._is_connected or self._client is None:
            self._is_connected = False
            self._client = None
            return

        try:
            await self._client.__aexit__(None, None, None)
        except Exception:
            pass
        finally:
            self._is_connected = False
            self._client = None
            self._cached_tools.clear()

    async def __aenter__(self) -> MCPClientManager:
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def list_available_tools(self) -> List[ToolDefinition]:
        """Khám phá động danh sách công cụ từ MCP Server bằng API list_tools().
        
        Không hardcode bất kỳ schema hay tên tool nào trong Client.
        """
        if not self._is_connected or self._client is None:
            await self.connect()

        try:
            result = await self._client.list_tools()
            tool_items = result.tools if hasattr(result, "tools") else result

            discovered: List[ToolDefinition] = []
            self._cached_tools.clear()

            for t in tool_items:
                schema = t.inputSchema if hasattr(t, "inputSchema") else {}
                tool_def = ToolDefinition(
                    name=t.name,
                    description=t.description or "",
                    input_schema=schema,
                )
                discovered.append(tool_def)
                self._cached_tools[t.name] = tool_def

            return discovered
        except Exception as err:
            raise ConnectionError(f"Mất kết nối hoặc lỗi khi khám phá tools: {err}") from err

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> ToolCallResult:
        """Gọi một công cụ trên MCP Server bằng tên và tham số.
        
        Chuẩn hóa kết quả trả về thành ToolCallResult mà không làm mất thông tin lỗi.
        """
        if not self._is_connected or self._client is None:
            await self.connect()

        # 1. Kiểm tra sự tồn tại của tool nếu đã từng nạp cache tools
        if self._cached_tools and name not in self._cached_tools:
            return ToolCallResult(
                tool_name=name,
                is_error=True,
                content=f"Error: Công cụ '{name}' không tồn tại trên MCP Server. Các công cụ khả dụng: {list(self._cached_tools.keys())}",
                raw_data={"status": "error", "error": f"Unknown tool: {name}"},
            )

        # 2. Gọi tool thông qua SDK
        try:
            res = await self._client.call_tool(name, arguments)

            # Trích xuất nội dung văn bản từ content blocks
            content_text = ""
            if hasattr(res, "content") and res.content:
                parts = [c.text for c in res.content if hasattr(c, "text")]
                content_text = "\n".join(parts) if parts else str(res.content)
            else:
                content_text = str(res)

            # Thử parse JSON data nếu kết quả là JSON string
            parsed_data = None
            try:
                parsed_data = json.loads(content_text)
            except Exception:
                pass

            is_error = getattr(res, "is_error", False)
            return ToolCallResult(
                tool_name=name,
                is_error=is_error,
                content=content_text,
                raw_data=parsed_data,
            )

        except Exception as err:
            return ToolCallResult(
                tool_name=name,
                is_error=True,
                content=f"Error executing tool '{name}': {err}",
                raw_data={"status": "error", "error": str(err)},
            )
