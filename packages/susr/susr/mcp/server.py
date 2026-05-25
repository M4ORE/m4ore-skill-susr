"""susr.mcp.server — FastMCP server instance + tool wiring.

Holds the single FastMCP() singleton that every `@mcp.tool()` decorator
in susr.mcp.tools.* binds to.  Importing this module is what side-effect
registers the tools.

Lifecycle:
    `susr-mcp` (from __main__) calls `serve()` which runs mcp.run(stdio).

Per spec §6.1, the canonical pattern is:

    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("susr")
    @mcp.tool()
    def my_tool(...): ...
    mcp.run(transport="stdio")

To keep `import susr.mcp.server` cheap on dev machines that don't have
the `mcp` SDK installed (Step 1 R2 stage), the FastMCP construction is
lazy.  `create_server()` is the single entry point — it imports `mcp`,
builds the singleton, registers all tools, and returns it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mcp.server.fastmcp import FastMCP

# Module-level singleton, populated by create_server().  Tool modules read
# this when they register their @mcp.tool() decorators.
_SERVER: Optional["FastMCP"] = None


def get_server() -> "FastMCP":
    """Return (lazily) the singleton FastMCP instance with all tools registered."""
    global _SERVER
    if _SERVER is None:
        _SERVER = create_server()
    return _SERVER


def create_server() -> "FastMCP":
    """Construct a fresh FastMCP("susr") and register every tool module.

    Returns the FastMCP instance ready to `.run(transport=...)`.  Idempotent
    against the module singleton: calling twice replaces _SERVER so tests
    can build clean instances.
    """
    global _SERVER

    # Import here so `import susr.mcp.server` itself does not require `mcp`.
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("susr")
    _SERVER = server  # publish before tool modules import to break cycles

    # Importing these modules executes the @server.register(...) calls at
    # module top-level, which is how each tool ends up bound to `server`.
    from susr.mcp.tools import action as _action
    from susr.mcp.tools import iro as _iro
    from susr.mcp.tools import phase3 as _phase3
    from susr.mcp.tools import phase7 as _phase7
    from susr.mcp.tools import workspace as _workspace

    _phase3.register(server)
    _iro.register(server)
    _action.register(server)
    _phase7.register(server)
    _workspace.register(server)

    return server


def serve(transport: str = "stdio") -> None:
    """Start the MCP server.  Blocks until the stdio peer closes.

    `transport='stdio'` is the form Claude Desktop expects (spec §6.1).
    """
    server = get_server()
    server.run(transport=transport)
