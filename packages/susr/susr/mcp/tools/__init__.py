"""susr.mcp.tools — MCP tool implementations grouped by domain.

Each sub-module decorates functions with @mcp.tool() from
susr.mcp.server.  Importing the module is what registers the tools.

Sub-modules:
    phase3    — Phase 3 materiality assessment (the MVP first cut)
    iro       — Phase 3 IRO linkage（補 walkthrough §5 暴露的 I1 缺口）
    workspace — workspace lifecycle + KB ops

R1: signatures.  R2: implement.  R3: 加 iro 補 IRO 建立。
"""

from __future__ import annotations

__all__ = ["phase3", "iro", "workspace"]
