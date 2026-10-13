"""MCP Client (Kế thừa từ W7/ex2_1_mcp_client.py)."""

from __future__ import annotations
from typing import Any, Dict, List
from mcp import Client, StdioServerParameters


class MCPClientManager:
    """Quản lý kết nối MCP qua stdio và gọi tool động."""

    def __init__(self, server_script: str = "src/mcp/server.py"):
        self.server_params = StdioServerParameters(command="uv", args=["run", server_script])

    async def list_available_tools(self) -> List[Any]:
        # Gợi ý: async with Client(self.server_params) as client: tools = (await client.list_tools()).tools
        pass

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        # Gợi ý: async with Client(self.server_params) as client: result = await client.call_tool(name, arguments)
        pass
