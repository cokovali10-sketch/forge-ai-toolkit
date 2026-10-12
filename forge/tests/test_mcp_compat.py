"""MCP compatibility vs the OFFICIAL SDK client (prompt section 22).

Spawns our server over stdio and drives it with mcp.ClientSession.
Skipped with a clear reason when the SDK is absent.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

mcp = pytest.importorskip("mcp")

ROOT = Path(__file__).resolve().parents[1]
SERVER = [sys.executable, "-m", "forge.cli", "mcp"]


def _run_exchange():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    import anyio

    async def go():
        params = StdioServerParameters(command=SERVER[0], args=SERVER[1:],
                                       cwd=str(ROOT), env=None)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as s:
                init = await s.initialize()
                tools = await s.list_tools()
                names = [t.name for t in tools.tools]
                res = await s.call_tool("forge.ping", {"echo": "sdk"})
                text = res.content[0].text if res.content else ""
                return init, names, text

    return anyio.run(go)


def test_sdk_initialize_list_call():
    init, names, text = _run_exchange()
    assert init is not None
    assert "forge.ping" in names
    assert "sdk" in text


def test_sdk_unknown_tool_errors_cleanly():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    import anyio

    async def go():
        params = StdioServerParameters(command=SERVER[0], args=SERVER[1:],
                                       cwd=str(ROOT))
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as s:
                await s.initialize()
                try:
                    await s.call_tool("nope.missing", {})
                    return "no-error"
                except Exception as e:
                    return f"{type(e).__name__}"

    out = anyio.run(go)
    assert out != "no-error", "unknown tool must raise, not silently pass"
