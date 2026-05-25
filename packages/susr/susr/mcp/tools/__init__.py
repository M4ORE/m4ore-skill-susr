"""susr.mcp.tools — MCP tool implementations grouped by domain.

Each sub-module decorates functions with @mcp.tool() from
susr.mcp.server.  Importing the module is what registers the tools.

Sub-modules:
    phase3    — Phase 3 materiality assessment (the MVP first cut)
    workspace — workspace lifecycle + KB ops

R1: signatures.  R2: implement.
"""

from __future__ import annotations

__all__ = ["phase3", "workspace"]
