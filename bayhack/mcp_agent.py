"""Physical MCP beat -- an agent drives the bench over the plr-mcp MCP server.

Instead of calling `plr_mcp.lab.Lab` in-process, this spawns the real `plr-mcp` MCP
server over stdio and runs one experiment by calling its tools -- plr_setup_deck,
plr_transfer, plr_read_plate -- exactly as an MCP agent (e.g. Claude) would. That is
the "Physical MCP" the World Models Hack host champions: an agent turns a goal into
tool calls against a real (sim-first) liquid handler.

    python -m bayhack.mcp_agent

Needs `mcp` + `plr-mcp` installed; guarded so it never touches the pure-sim path.
"""
from __future__ import annotations

import asyncio
import json
import sys


class McpUnavailable(RuntimeError):
    """The mcp SDK or the plr-mcp server isn't available."""


async def _drive(x: float) -> dict:
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as e:
        raise McpUnavailable("mcp SDK not installed: pip install mcp") from e

    params = StdioServerParameters(
        command=sys.executable,
        args=["-c", "from plr_mcp.server import main; main()"],
    )
    calls: list[tuple[str, bool]] = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            n_tools = len((await session.list_tools()).tools)

            async def call(tool: str, args: dict) -> dict:
                res = await session.call_tool(tool, args)
                data = json.loads(res.content[0].text) if res.content else {}
                calls.append((tool, bool(data.get("ok"))))
                return data

            vol = max(1.0, 50.0 * x)                      # build the reaction at ratio x
            await call("plr_setup_deck", {})
            await call("plr_transfer", {"source": "A1", "dest": "A2", "volume": vol})
            read = await call("plr_read_plate", {"mode": "fluorescence"})

    return {
        "tools_exposed": n_tools,
        "calls": calls,
        "all_ok": all(ok for _, ok in calls),
        "reader_mode": read.get("mode"),
        "simulated": read.get("simulated"),
    }


def run_over_mcp(x: float = 0.5) -> dict:
    """Drive one bench experiment through the plr-mcp MCP server over stdio."""
    return asyncio.run(_drive(x))


def main():
    print("=" * 62)
    print("bay-hack -- an agent drives the bench over MCP  (Physical MCP)")
    print("=" * 62)
    try:
        r = run_over_mcp()
    except McpUnavailable as e:
        print(f"  skipped -- {e}")
        return
    print(f"  plr-mcp exposed {r['tools_exposed']} tools over stdio; the agent called:")
    for tool, ok in r["calls"]:
        print(f"    -> {tool:18s} {'ok' if ok else 'FAIL'}")
    print(f"  all calls ok: {r['all_ok']}   (chatterbox backend, no hardware; the sim "
          f"reader returns 0, so signal stays modeled until a real reader)")


if __name__ == "__main__":
    main()
