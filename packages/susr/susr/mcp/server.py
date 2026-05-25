"""susr.mcp.server — FastMCP server instance + tool wiring.

Holds the single FastMCP() singleton that every `@mcp.tool()` decorator
in susr.mcp.tools.* binds to.  Importing this module is what side-effect
registers the tools (imports below are intentional).

Lifecycle:
    `susr-mcp` (from __main__) calls `serve()` which runs mcp.run(stdio).

R1: stub.  R2: implement.
See docs/research/step1-spec.md §6.1.
"""

from __future__ import annotations


def get_server():
    """Return (lazily) the singleton FastMCP instance with all tools registered.

    R2 will construct `FastMCP("susr")` here and import the tool modules
    so their @mcp.tool() decorators take effect.
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §6.1")


def serve(transport: str = "stdio") -> None:
    """Start the MCP server.  Blocks until the stdio peer closes."""
    raise NotImplementedError("Step 1 R2 — mcp.run(transport='stdio')")
