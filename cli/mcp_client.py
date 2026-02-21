"""MCP client using the official SDK's StreamableHTTP transport."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

DEFAULT_SERVER_URL = "http://127.0.0.1:8000"
TIMEOUT = 30.0


class MCPClientError(Exception):
    """Error communicating with the MCP server."""


class MCPClient:
    def __init__(self, server_url: str = DEFAULT_SERVER_URL) -> None:
        self.server_url = server_url.rstrip("/")
        self._mcp_url = f"{self.server_url}/mcp"

    def health(self) -> dict[str, Any]:
        """Health check via plain HTTP (not MCP protocol)."""
        try:
            with httpx.Client(timeout=TIMEOUT) as client:
                resp = client.get(f"{self.server_url}/health")
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as e:
            raise MCPClientError(f"Health check failed: {e}") from e

    def list_tools(self) -> list[dict[str, Any]]:
        """List available MCP tools."""
        return asyncio.run(self._list_tools_async())

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call an MCP tool by name."""
        return asyncio.run(self._call_tool_async(name, arguments))

    async def _list_tools_async(self) -> list[dict[str, Any]]:
        try:
            async with streamablehttp_client(self._mcp_url) as (r, w, _):
                async with ClientSession(r, w) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return [
                        {
                            "name": t.name,
                            "description": t.description or "",
                            "inputSchema": t.inputSchema,
                        }
                        for t in result.tools
                    ]
        except Exception as e:
            raise MCPClientError(f"List tools failed: {e}") from e

    async def _call_tool_async(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            async with streamablehttp_client(self._mcp_url) as (r, w, _):
                async with ClientSession(r, w) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments)
                    # Extract text content from MCP response
                    contents = []
                    for item in result.content:
                        if item.type == "text":
                            # Try to parse as JSON, fall back to raw text
                            try:
                                contents.append(json.loads(item.text))
                            except json.JSONDecodeError:
                                contents.append({"text": item.text})
                        else:
                            contents.append({"type": item.type})
                    if len(contents) == 1:
                        return contents[0]
                    return {"results": contents}
        except MCPClientError:
            raise
        except Exception as e:
            raise MCPClientError(f"Tool call failed: {e}") from e

    def close(self) -> None:
        pass
