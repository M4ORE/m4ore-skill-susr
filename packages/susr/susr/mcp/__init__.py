"""susr.mcp — Model Context Protocol server.

Exposes the brain to Claude Desktop / Cursor / Windsurf via the official
`mcp` Python SDK (FastMCP, stdio transport).

Sub-modules:
    __main__ — `susr-mcp` console-script entry point
    server   — FastMCP instance + tool registration
    tools/   — tool implementations grouped by domain
        phase3    — 4 Phase-3 (materiality assessment) tools
        workspace — 4 workspace ops (create / health / kb / promote)

R1: signatures only.  R2: implement against docs/research/step1-spec.md §6.
"""

from __future__ import annotations

__all__ = ["server"]
