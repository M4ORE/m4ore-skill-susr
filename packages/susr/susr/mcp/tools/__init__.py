"""susr.mcp.tools — MCP tool implementations grouped by domain.

Each sub-module decorates functions with @mcp.tool() from
susr.mcp.server.  Importing the module is what registers the tools.

Sub-modules:
    phase3        — Phase 3 materiality assessment (the MVP first cut)
    iro           — Phase 3 IRO linkage（補 walkthrough §5 暴露的 I1 缺口）
    action        — Phase 5 Action linkage（R4 拆 I1 後關閉 I1b 的工具）
    phase7        — Phase 7 Gap Analysis & Assurance Readiness（4 tools）
    phase6        — Phase 6 document-skills payload preparation（4 tools）
    phase6_render — Phase 6 in-process docx renderer（render_docx_simple）
    kpi           — Phase 4/6 KPI ranking helper（R6+ list_top_kpis）
    workspace     — workspace lifecycle + KB ops

R1: signatures.  R2: implement.  R3: 加 iro 補 IRO 建立。
R4: 加 action 為 Phase 5 link_iro_to_action 鋪路。
R5: 加 phase7 (compliance + GRI + assurance + full gap analysis aggregator)。
Phase 6: 加 phase6（document-skills payload prep — 4 tools，不渲染檔）。
R6+ (Agent C): 加 kpi.list_top_kpis（priority-based ranking）。
"""

from __future__ import annotations

__all__ = ["phase3", "iro", "action", "phase7", "phase6", "phase6_render", "kpi", "workspace"]
