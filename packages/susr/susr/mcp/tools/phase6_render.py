"""susr.mcp.tools.phase6_render — Phase 6 in-process docx renderer.

TL;DR（顧問速讀，≤150 字）：
    MCP tool ``render_docx_simple(client, year)`` 一步出 .docx 到
    ``<workspace>/projects/<slug>/output/Report_<year>.docx``。內部走
    ``prepare_docx_payload`` → python-docx 渲染（搬自 gen_lealea_docx.py）→
    寫 ``timeline_entry`` 到 project page。python-docx 不可用 → ``RenderError``；
    payload 缺章節 / KPI → 放 ``warnings`` 不阻擋。

TOC:
    - Constants（brand color / font / renderer version）
    - RenderError + DocxRenderResult (Pydantic)
    - Style helpers（_set_run_font / _add_heading / _add_para / _add_kv / _fill_cell）
    - Markdown → docx renderer（_add_inline / _render_markdown）
    - Section renderers（cover / company / materiality / chapters / iros / kpis / targets / gri）
    - render_docx_payload_to_path（純渲染，可獨立 unit test）
    - _ensure_project_page_in_brain + _write_render_timeline（brain side-effects）
    - render_docx_simple（MCP tool，端到端）
    - register(server) + __all__

設計選項：

    - **不重做 payload 邏輯**：本模組只接 ``DocxPayload``，不自己讀 brain。
      所以 caller 既可走 ``render_docx_simple`` 的 wired path，也可在外部
      組好 payload 後直接呼叫 ``render_docx_payload_to_path`` 做客製化。
    - **timeline_entry 寫 project page**：renderer 把「docx rendered」當成
      report-level event（呼應 ReportFrontmatter / `contains_chapter` edge）。
      project page slug 慣例為 ``<year>-sustainability-report`` ── 與 ingest
      路徑一致。若該 page 不存在於 brain DB，``append_dual`` 自動 fallback
      MD-only，渲染不被阻擋。
    - **warnings 不阻擋**：缺章節 / 缺 KPI / 缺 target 屬「資料不足」而非
      「渲染失敗」── 顧問仍要能拿到結構性的 .docx 給客戶看大綱（呼應
      Co-pilot 定位：放大顧問，不替代決策）。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from susr.brain.timeline import append_dual
from susr.mcp.tools.phase6 import DocxPayload, prepare_docx_payload
from susr.workspace import find_client_workspace

# ---------------------------------------------------------------------------
# Constants — brand / font / renderer version
# ---------------------------------------------------------------------------

_RENDERER_VERSION = "v0.1"

# python-docx 是 optional dep ── 如果環境沒裝會在 register / call time 報清楚錯。
# 顏色 / 字型常數延後到 _ensure_docx() 後再讀 docx.shared，避免 import time 失敗。
_BRAND_DARK_HEX = (0x1F, 0x5F, 0x4A)
_BRAND_ACCENT_HEX = (0x4A, 0x8F, 0x6E)
_GREY_MUTED_HEX = (0x55, 0x55, 0x55)
_FONT_CN = "微軟正黑體"
_FONT_EN = "Calibri"

# Markdown inline **bold**
_RE_BOLD = re.compile(r"\*\*([^*]+)\*\*")


# ---------------------------------------------------------------------------
# Errors + Pydantic result
# ---------------------------------------------------------------------------


class RenderError(RuntimeError):
    """python-docx 渲染過程失敗 — caller 應停下修檔再試。"""


class DocxRenderResult(BaseModel):
    """``render_docx_simple`` 回傳結構。

    Attributes:
        output_path: 產出的 .docx 絕對路徑。
        size_bytes: 檔案大小（bytes）。
        chapter_count: 渲染章節數（payload.chapters）。
        iro_count: IRO 數（payload.iros）。
        kpi_count: KPI 數（payload.kpis_summary）。
        target_count: target 數（payload.targets_summary）。
        timeline_entry_id: brain timeline_entries.id（或 fallback synthetic id）。
        warnings: 渲染期間累積的非致命警告（"no_chapters" / "no_iros"…）。
    """

    output_path: str
    size_bytes: int
    chapter_count: int
    iro_count: int
    kpi_count: int
    target_count: int
    timeline_entry_id: int
    warnings: list[str] = []


# ---------------------------------------------------------------------------
# python-docx ensure + lazy imports
# ---------------------------------------------------------------------------


def _ensure_docx():
    """Lazy import + raise ``RenderError`` 若 python-docx 未裝。

    回傳 ``(docx_module, shared, enum_text, enum_table, oxml_ns, oxml)`` 給
    renderer 內部使用，避免重複 import boilerplate。
    """
    try:
        import docx
        from docx.enum.table import WD_ALIGN_VERTICAL
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Cm, Pt, RGBColor
    except ImportError as e:  # pragma: no cover — exercised via mock in test 6
        raise RenderError(
            "python-docx is not installed; run `pip install python-docx` "
            f"({e}). 顧問若用 Claude Desktop MCP，docker 環境變數應已預裝。"
        ) from e
    return {
        "docx": docx, "Cm": Cm, "Pt": Pt, "RGBColor": RGBColor,
        "WD_ALIGN_PARAGRAPH": WD_ALIGN_PARAGRAPH,
        "WD_ALIGN_VERTICAL": WD_ALIGN_VERTICAL,
        "OxmlElement": OxmlElement, "qn": qn,
    }


# ---------------------------------------------------------------------------
# Style helpers — every helper takes the resolved docx-modules dict as `D`
# ---------------------------------------------------------------------------


def _set_run_font(D, run, size=11, bold=False, color=None, name_cn=_FONT_CN, name_en=_FONT_EN):
    run.font.name = name_en
    run.font.size = D["Pt"](size)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(D["qn"]("w:rFonts"))
    if rFonts is None:
        rFonts = D["OxmlElement"]("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(D["qn"]("w:eastAsia"), name_cn)
    rFonts.set(D["qn"]("w:ascii"), name_en)
    rFonts.set(D["qn"]("w:hAnsi"), name_en)


def _brand_dark(D):
    return D["RGBColor"](*_BRAND_DARK_HEX)


def _grey_muted(D):
    return D["RGBColor"](*_GREY_MUTED_HEX)


def _add_heading(D, doc, text, level=1):
    style = {1: "Heading 1", 2: "Heading 2", 3: "Heading 3", 4: "Heading 4"}[level]
    p = doc.add_paragraph(style=style)
    run = p.add_run(text)
    size = {1: 22, 2: 18, 3: 14, 4: 12}[level]
    _set_run_font(D, run, size=size, bold=True, color=_brand_dark(D))
    p.paragraph_format.space_before = D["Pt"](12 if level > 1 else 18)
    p.paragraph_format.space_after = D["Pt"](6)
    return p


def _add_para(D, doc, text, size=11, bold=False, italic=False, color=None, align=None, indent=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    _set_run_font(D, run, size=size, bold=bold, color=color)
    run.italic = italic
    if align is not None:
        p.alignment = align
    if indent is not None:
        p.paragraph_format.left_indent = D["Cm"](indent)
    p.paragraph_format.space_after = D["Pt"](4)
    return p


def _add_kv(D, doc, key, value):
    p = doc.add_paragraph()
    r1 = p.add_run(f"{key}：")
    _set_run_font(D, r1, size=11, bold=True, color=_brand_dark(D))
    r2 = p.add_run(str(value))
    _set_run_font(D, r2, size=11)
    p.paragraph_format.space_after = D["Pt"](2)


def _set_cell_shading(D, cell, fill_hex):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = D["OxmlElement"]("w:shd")
    shd.set(D["qn"]("w:fill"), fill_hex)
    shd.set(D["qn"]("w:val"), "clear")
    tc_pr.append(shd)


def _fill_cell(D, cell, text, bold=False, header=False, size=10, align=None):
    cell.vertical_alignment = D["WD_ALIGN_VERTICAL"].CENTER
    for p in cell.paragraphs:
        p._element.getparent().remove(p._element)
    p = cell.add_paragraph()
    run = p.add_run(str(text) if text not in (None, "") else "—")
    color = D["RGBColor"](0xFF, 0xFF, 0xFF) if header else None
    _set_run_font(D, run, size=size, bold=bold or header, color=color)
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = D["Pt"](0)
    if header:
        _set_cell_shading(D, cell, "1F5F4A")


# ---------------------------------------------------------------------------
# Markdown → docx
# ---------------------------------------------------------------------------


def _add_inline(D, p, text):
    """Handle ``**bold**`` inline; ignore other markdown decoration."""
    last = 0
    for m in _RE_BOLD.finditer(text):
        if m.start() > last:
            r = p.add_run(text[last:m.start()])
            _set_run_font(D, r, size=11)
        rb = p.add_run(m.group(1))
        _set_run_font(D, rb, size=11, bold=True)
        last = m.end()
    if last < len(text):
        r = p.add_run(text[last:])
        _set_run_font(D, r, size=11)


def _render_markdown(D, doc, md_text, base_heading_level=2):
    """Convert chapter markdown into docx paragraphs / lists / tables.

    Supports: ``# H1`` / ``## H2`` / ``### H3`` / blockquote / unordered list /
    numbered list / table / horizontal rule (``---``).  Inline ``**bold``.
    """
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^-{3,}$", stripped):
            p = doc.add_paragraph()
            pPr = p._element.get_or_add_pPr()
            pbdr = D["OxmlElement"]("w:pBdr")
            bottom = D["OxmlElement"]("w:bottom")
            bottom.set(D["qn"]("w:val"), "single")
            bottom.set(D["qn"]("w:sz"), "6")
            bottom.set(D["qn"]("w:color"), "888888")
            pbdr.append(bottom)
            pPr.append(pbdr)
            p.paragraph_format.space_after = D["Pt"](4)
            i += 1
            continue

        # Headings — relative to chapter base level
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level_raw = len(m.group(1))
            level = min(4, base_heading_level + level_raw - 1)
            _add_heading(D, doc, m.group(2), level=level)
            i += 1
            continue

        # Blockquote
        if stripped.startswith(">"):
            quote_text = stripped[1:].strip()
            p = doc.add_paragraph()
            _add_inline(D, p, quote_text)
            for run in p.runs:
                run.italic = True
                run.font.color.rgb = _grey_muted(D)
            p.paragraph_format.left_indent = D["Cm"](0.5)
            p.paragraph_format.space_after = D["Pt"](4)
            i += 1
            continue

        # Table
        if stripped.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|$", lines[i + 1].strip()):
            header_cells = [c.strip() for c in stripped.strip("|").split("|")]
            row_lines = []
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                row = [c.strip() for c in lines[j].strip().strip("|").split("|")]
                row_lines.append(row)
                j += 1
            t = doc.add_table(rows=1 + len(row_lines), cols=len(header_cells))
            t.style = "Light Grid Accent 1"
            for k, h in enumerate(header_cells):
                _fill_cell(D, t.rows[0].cells[k], h, header=True, size=10)
            for r_idx, row in enumerate(row_lines):
                for k, c in enumerate(row[:len(header_cells)]):
                    _fill_cell(D, t.rows[1 + r_idx].cells[k], c, size=10)
            doc.add_paragraph().paragraph_format.space_after = D["Pt"](2)
            i = j
            continue

        # Numbered list
        m = re.match(r"^\d+\.\s+(.*)$", stripped)
        if m:
            p = doc.add_paragraph(style="List Number")
            _add_inline(D, p, m.group(1))
            i += 1
            continue

        # Bullet
        m = re.match(r"^[-*]\s+(.*)$", stripped)
        if m:
            p = doc.add_paragraph(style="List Bullet")
            _add_inline(D, p, m.group(1))
            i += 1
            continue

        # Plain paragraph
        p = doc.add_paragraph()
        _add_inline(D, p, stripped)
        p.paragraph_format.space_after = D["Pt"](4)
        i += 1


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _render_cover(D, doc, payload: DocxPayload, year_hint: Optional[int] = None):
    for _ in range(6):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = D["WD_ALIGN_PARAGRAPH"].CENTER
    r = p.add_run(payload.client.legal_name)
    _set_run_font(D, r, size=32, bold=True, color=_brand_dark(D))

    p = doc.add_paragraph()
    p.alignment = D["WD_ALIGN_PARAGRAPH"].CENTER
    year_text = str(year_hint) if year_hint else payload.reporting_period
    r = p.add_run(f"{year_text} 永續報告書")
    _set_run_font(D, r, size=28, bold=True, color=_brand_dark(D))

    p = doc.add_paragraph()
    p.alignment = D["WD_ALIGN_PARAGRAPH"].CENTER
    r = p.add_run("Sustainability Report")
    _set_run_font(D, r, size=14, color=_grey_muted(D))

    for _ in range(2):
        doc.add_paragraph()

    for label, val in (
        ("報告期間", payload.reporting_period),
        ("適用框架", " / ".join(payload.frameworks)),
        ("股票代號", payload.client.stock_code or "—"),
    ):
        p = doc.add_paragraph()
        p.alignment = D["WD_ALIGN_PARAGRAPH"].CENTER
        r = p.add_run(f"{label}：{val}")
        _set_run_font(D, r, size=12)

    for _ in range(8):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = D["WD_ALIGN_PARAGRAPH"].CENTER
    r = p.add_run("— 由 susr ESG Co-pilot 自動組裝 —")
    _set_run_font(D, r, size=10, color=_grey_muted(D))
    r.italic = True
    p = doc.add_paragraph()
    p.alignment = D["WD_ALIGN_PARAGRAPH"].CENTER
    r = p.add_run("Powered by m4ore · github.com/M4ORE/m4ore-skill-susr")
    _set_run_font(D, r, size=9, color=_grey_muted(D))

    doc.add_page_break()


def _render_company_profile(D, doc, payload: DocxPayload):
    _add_heading(D, doc, "第一章　公司概況", level=1)
    _add_kv(D, doc, "公司全名", payload.client.legal_name)
    _add_kv(D, doc, "產業別", payload.client.industry or "—")
    _add_kv(D, doc, "股票代號", payload.client.stock_code or "—")
    _add_kv(D, doc, "報告期間", payload.reporting_period)
    _add_kv(D, doc, "適用框架", " / ".join(payload.frameworks))
    _add_para(D, doc, "本報告書由 susr ESG Co-pilot 自動組裝，內容基於 brain 內各 entity"
              " 與 chapter compiled_truth；專業判斷與最終決策仍由顧問及客戶承擔。",
              italic=True, color=_grey_muted(D), size=10)
    doc.add_page_break()


def _render_materiality(D, doc, payload: DocxPayload):
    _add_heading(D, doc, "第二章　重大性議題評估", level=1)
    _add_para(D, doc,
              "本章節依雙重重大性（Double Materiality）原則，從影響重大性與財務重大性兩個維度評估議題。")
    matrix = payload.materiality_matrix
    if matrix.core_topics:
        _add_heading(D, doc, f"2.1 核心議題（{len(matrix.core_topics)} 項）", level=2)
        t = doc.add_table(rows=1 + len(matrix.core_topics), cols=1)
        t.style = "Light Grid Accent 1"
        _fill_cell(D, t.rows[0].cells[0], "議題代碼", header=True, size=10)
        for i, slug in enumerate(matrix.core_topics):
            _fill_cell(D, t.rows[1 + i].cells[0], slug.split("/")[-1], size=10)
    extras = [s for s in matrix.material_topics if s not in matrix.core_topics]
    if extras:
        _add_heading(D, doc, f"2.2 重大議題（追加揭露 {len(extras)} 項）", level=2)
        t = doc.add_table(rows=1 + len(extras), cols=1)
        t.style = "Light Grid Accent 1"
        _fill_cell(D, t.rows[0].cells[0], "議題代碼", header=True, size=10)
        for i, slug in enumerate(extras):
            _fill_cell(D, t.rows[1 + i].cells[0], slug.split("/")[-1], size=10)
    if matrix.tier_overrides:
        _add_heading(D, doc, "2.3 議題評分覆寫紀錄", level=2)
        _add_para(D, doc,
                  f"本年度顧問依專業判斷對 {len(matrix.tier_overrides)} 個議題進行 tier 等級覆寫。所有覆寫均留有 audit trail（見 brain timeline_entries 表）。")
    doc.add_page_break()


def _render_chapters(D, doc, payload: DocxPayload):
    """Render every chapter in payload.chapters (already sorted by order, slug)."""
    for idx, ch in enumerate(payload.chapters, start=3):  # 章節編號從第三章起
        title = ch.title or ch.slug
        _add_heading(D, doc, f"第{_zh_num(idx)}章　{title}", level=1)
        if ch.framework_refs:
            _add_para(D, doc, f"適用框架：{' / '.join(ch.framework_refs)}",
                      italic=True, color=_grey_muted(D), size=10)
        if ch.content_md:
            _render_markdown(D, doc, ch.content_md, base_heading_level=2)
        else:
            _add_para(D, doc, "（章節內容尚未補齊 — 請先跑 Phase 5 章節撰寫工具）",
                      italic=True, color=_grey_muted(D))
        doc.add_page_break()


_ZH_NUM_TABLE = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]


def _zh_num(n: int) -> str:
    """Tiny int→中文數字（用在「第 N 章」標題）。"""
    if 0 <= n <= 10:
        return _ZH_NUM_TABLE[n]
    if 11 <= n <= 19:
        return "十" + _ZH_NUM_TABLE[n - 10]
    if 20 <= n <= 99:
        return _ZH_NUM_TABLE[n // 10] + "十" + (_ZH_NUM_TABLE[n % 10] if n % 10 else "")
    return str(n)


def _time_horizon_label(code):
    return {"S": "短期（<1y）", "M": "中期（1-5y）", "L": "長期（5-10y）"}.get(code, code or "—")


def _render_iro_appendix(D, doc, payload: DocxPayload):
    if not payload.iros:
        return
    _add_heading(D, doc, "附錄 A　IRO 風險與機會清單", level=1)
    _add_para(D, doc, f"本附錄列出本報告期間經 brain 整理之 {len(payload.iros)} 項 IRO。", size=10)
    iros_by_type: dict[str, list] = {"Impact": [], "Risk": [], "Opportunity": []}
    for iro in payload.iros:
        iros_by_type.setdefault(iro.iro_type, []).append(iro)
    for itype, label in [("Impact", "影響"), ("Risk", "風險"), ("Opportunity", "機會")]:
        rows = iros_by_type.get(itype, [])
        if not rows:
            continue
        _add_heading(D, doc, f"A.{['Impact','Risk','Opportunity'].index(itype) + 1} {label}（{itype}） — {len(rows)} 項", level=2)
        t = doc.add_table(rows=1 + len(rows), cols=5)
        t.style = "Light Grid Accent 1"
        for k, h in enumerate(("議題", "IRO 名稱", "類別", "時間軸", "財務量級")):
            _fill_cell(D, t.rows[0].cells[k], h, header=True, size=9)
        for i, iro in enumerate(rows):
            _fill_cell(D, t.rows[1 + i].cells[0], iro.topic_slug, size=9)
            _fill_cell(D, t.rows[1 + i].cells[1], iro.name or "—", size=9)
            _fill_cell(D, t.rows[1 + i].cells[2], iro.category or "—", size=9)
            _fill_cell(D, t.rows[1 + i].cells[3], _time_horizon_label(iro.time_horizon), size=9)
            _fill_cell(D, t.rows[1 + i].cells[4],
                       f"{iro.financial_magnitude:.1f}" if iro.financial_magnitude is not None else "—",
                       size=9)
    doc.add_page_break()


def _render_kpi_appendix(D, doc, payload: DocxPayload):
    if not payload.kpis_summary:
        return
    _add_heading(D, doc, "附錄 B　KPI 績效摘要", level=1)
    _add_para(D, doc, f"本附錄列出 {len(payload.kpis_summary)} 項本年度追蹤的 KPI。", size=10)
    t = doc.add_table(rows=1 + len(payload.kpis_summary), cols=6)
    t.style = "Light Grid Accent 1"
    for k, h in enumerate(("KPI 名稱", "單位", "對應議題", "最新值", "年度", "YoY")):
        _fill_cell(D, t.rows[0].cells[k], h, header=True, size=9)
    for i, kpi in enumerate(payload.kpis_summary):
        _fill_cell(D, t.rows[1 + i].cells[0], kpi.name, size=9)
        _fill_cell(D, t.rows[1 + i].cells[1], kpi.unit or "—", size=9)
        _fill_cell(D, t.rows[1 + i].cells[2], kpi.topic_slug or "—", size=9)
        _fill_cell(D, t.rows[1 + i].cells[3],
                   kpi.latest_value if kpi.latest_value is not None else "—", size=9)
        _fill_cell(D, t.rows[1 + i].cells[4], kpi.latest_year or "—", size=9)
        _fill_cell(D, t.rows[1 + i].cells[5],
                   f"{kpi.yoy_change_pct:+.1f}%" if kpi.yoy_change_pct is not None else "—",
                   size=9)
    doc.add_page_break()


def _render_target_appendix(D, doc, payload: DocxPayload):
    if not payload.targets_summary:
        return
    _add_heading(D, doc, "附錄 C　目標進度追蹤", level=1)
    _add_para(D, doc, f"本附錄列出 {len(payload.targets_summary)} 項本年度設定的永續目標。", size=10)
    t = doc.add_table(rows=1 + len(payload.targets_summary), cols=6)
    t.style = "Light Grid Accent 1"
    for k, h in enumerate(("目標", "對應 KPI", "基準年", "基準值", "目標年", "目標值")):
        _fill_cell(D, t.rows[0].cells[k], h, header=True, size=9)
    for i, tgt in enumerate(payload.targets_summary):
        _fill_cell(D, t.rows[1 + i].cells[0], tgt.slug.split("/")[-1], size=9)
        _fill_cell(D, t.rows[1 + i].cells[1], tgt.kpi_slug or "—", size=9)
        _fill_cell(D, t.rows[1 + i].cells[2], tgt.baseline_year or "—", size=9)
        _fill_cell(D, t.rows[1 + i].cells[3],
                   tgt.baseline_value if tgt.baseline_value is not None else "—", size=9)
        _fill_cell(D, t.rows[1 + i].cells[4], tgt.target_year or "—", size=9)
        _fill_cell(D, t.rows[1 + i].cells[5],
                   tgt.target_value if tgt.target_value is not None else "—", size=9)
    doc.add_page_break()


def _render_gri_appendix(D, doc, payload: DocxPayload):
    _add_heading(D, doc, "附錄 D　GRI Content Index", level=1)
    if payload.gri_content_index_ref:
        _add_para(D, doc, f"本年度 GRI Content Index 完整版見：{payload.gri_content_index_ref}")
    else:
        _add_para(D, doc, "本附錄為 GRI Content Index 之佔位章節，請先跑 Phase 7 generate_gri_content_index。",
                  italic=True, color=_grey_muted(D))


# ---------------------------------------------------------------------------
# Pure renderer — takes payload + path, no brain side-effects
# ---------------------------------------------------------------------------


def render_docx_payload_to_path(
    payload: DocxPayload, out_path: Path, *, year_hint: Optional[int] = None,
) -> list[str]:
    """純渲染：把 ``DocxPayload`` 寫到 ``out_path``，回傳 warnings list。

    Args:
        payload: 由 ``prepare_docx_payload`` 或測試 stub 構造的 payload。
        out_path: 目標 .docx 絕對路徑（父目錄會自動建立）。
        year_hint: 封面年度顯示提示；不給時用 payload.reporting_period。

    Returns:
        ``warnings``：list of string tokens 如 ``"no_chapters"`` / ``"no_iros"`` /
        ``"no_kpis"`` / ``"no_targets"``，給 caller 累進 ``DocxRenderResult``。

    Raises:
        RenderError: python-docx 不可用、或渲染期間任何 docx exception。
    """
    D = _ensure_docx()
    warnings: list[str] = []
    if not payload.chapters:
        warnings.append("no_chapters")
    if not payload.iros:
        warnings.append("no_iros")
    if not payload.kpis_summary:
        warnings.append("no_kpis")
    if not payload.targets_summary:
        warnings.append("no_targets")

    try:
        doc = D["docx"].Document()
        section = doc.sections[0]
        section.page_height = D["Cm"](29.7)
        section.page_width = D["Cm"](21.0)
        section.top_margin = D["Cm"](2.5)
        section.bottom_margin = D["Cm"](2.5)
        section.left_margin = D["Cm"](2.5)
        section.right_margin = D["Cm"](2.5)

        # Default Normal style — Calibri + 微軟正黑體
        style = doc.styles["Normal"]
        style.font.name = _FONT_EN
        style.font.size = D["Pt"](11)
        rPr = style.element.get_or_add_rPr()
        rFonts = rPr.find(D["qn"]("w:rFonts"))
        if rFonts is None:
            rFonts = D["OxmlElement"]("w:rFonts")
            rPr.append(rFonts)
        rFonts.set(D["qn"]("w:eastAsia"), _FONT_CN)

        _render_cover(D, doc, payload, year_hint=year_hint)
        _render_company_profile(D, doc, payload)
        _render_materiality(D, doc, payload)
        _render_chapters(D, doc, payload)
        _render_iro_appendix(D, doc, payload)
        _render_kpi_appendix(D, doc, payload)
        _render_target_appendix(D, doc, payload)
        _render_gri_appendix(D, doc, payload)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(out_path))
    except RenderError:
        raise
    except Exception as e:
        raise RenderError(f"python-docx render failed: {e}") from e
    return warnings


# ---------------------------------------------------------------------------
# MCP tool — render_docx_simple
# ---------------------------------------------------------------------------


def _ensure_project_page_in_brain(
    engine, client_path: Path, project_slug: str, *, client_slug: str, year: int,
) -> Optional[str]:
    """Best-effort：確保 brain 有 ``reports/<project_slug>`` page 給 timeline 掛載。

    流程：

        1. 已在 brain DB → 直接回 canonical slug。
        2. 否則先試 ``ingest_markdown_file(_project.md)`` —— 若 frontmatter
           完整且 schema-valid 會抓到顧問真實 metadata。
        3. 失敗（schema 不過 / 檔案不存在）→ fallback 寫一個 minimal report
           page。timeline 仍能落地 brain DB，不會降級為 MD-only。
    """
    if engine is None:
        return None

    canonical_slug = f"reports/{project_slug}"

    # 1. 已存在 brain DB？(同時 try unqualified 以兼容舊資料)
    for candidate in (canonical_slug, project_slug):
        try:
            page = engine.get_page(candidate)
        except Exception:  # pragma: no cover — defensive
            page = None
        if page is not None:
            return canonical_slug

    # 2. 試 ingest 顧問寫的 _project.md
    project_md = client_path / "projects" / project_slug / "_project.md"
    if project_md.exists():
        try:
            from susr.brain.ingest import ingest_markdown_file

            ingest_markdown_file(engine.conn, project_md, entity_type="report")
            engine.conn.commit()
            return canonical_slug
        except Exception:  # schema mismatch（version: 0.1 是 float 等）
            pass

    # 3. Fallback：寫 minimal report page 讓 timeline 能 attach
    try:
        engine.put_page(
            slug=canonical_slug, entity_type="report",
            title=f"{client_slug} {year} Sustainability Report",
            compiled_truth="# (auto-created by render_docx_simple)\n",
            file_path=str(project_md) if project_md.exists() else f"projects/{project_slug}/_project.md",
            frontmatter={
                "slug": project_slug,
                "client_slug": client_slug,
                "year": int(year),
                "version": "0.1",
                "language": "zh-TW",
                "framework_bundle": ["GRI Standards 2021"],
                "status": "draft",
            },
        )
        engine.conn.commit()
        return canonical_slug
    except Exception:  # pragma: no cover — defensive
        return None


def _write_render_timeline(
    client_path: Path, year: int, project_slug: str,
    *, payload: DocxPayload, out_path: Path, size_bytes: int,
    client_slug: str, actor: str = "consultant",
) -> int:
    """Append a ``render_docx_simple`` timeline entry to the project page.

    Tries brain DB first; if the project page is not ingested, also tries
    to ingest ``_project.md`` so the entry lands in brain ``timeline_entries``
    instead of silently falling back to MD-only.
    """
    project_md = client_path / "projects" / project_slug / "_project.md"
    existing_body = ""
    if project_md.exists():
        try:
            existing_body = project_md.read_text(encoding="utf-8")
        except OSError:
            existing_body = ""

    tl_payload: dict[str, Any] = {
        "action": "render_docx_simple",
        "output_path": str(out_path),
        "size_bytes": size_bytes,
        "chapter_count": len(payload.chapters),
        "iro_count": len(payload.iros),
        "kpi_count": len(payload.kpis_summary),
        "target_count": len(payload.targets_summary),
        "renderer_version": _RENDERER_VERSION,
    }

    # Try brain DB; fallback graceful when project page absent.
    engine = None
    new_body = existing_body
    try:
        from susr.brain.engine import BrainEngine

        db_path = client_path / ".susr" / "db.sqlite"
        if db_path.exists():
            try:
                engine = BrainEngine.open(str(db_path), load_sqlite_vec=False)
            except Exception:  # pragma: no cover — defensive
                engine = None

        project_brain_slug = _ensure_project_page_in_brain(
            engine, client_path, project_slug,
            client_slug=client_slug, year=year,
        )

        tl_id, new_body = append_dual(
            engine,
            page_slug=project_brain_slug,  # None → append_dual MD-only fallback
            action="ingest",  # 受 ActionType CHECK 限制；細節塞 payload['action']
            payload=tl_payload,
            actor=actor,
            body=existing_body,
            source_ref=str(out_path),
        )
    finally:
        if engine is not None:
            try:
                engine.close()
            except Exception:  # pragma: no cover
                pass

    # Best-effort write back to _project.md so 顧問 git diff 看得到 timeline 行。
    if project_md.exists() and new_body and new_body != existing_body:
        try:
            project_md.write_text(new_body, encoding="utf-8")
        except OSError:  # pragma: no cover — defensive
            pass

    return int(tl_id)


def render_docx_simple(
    client_slug: str, year: int, project_slug: Optional[str] = None,
    *, actor: str = "consultant",
) -> DocxRenderResult:
    """一步到位渲染報告書 docx（不必再 invoke document-skills sub-skill）。

    流程：

        1. 呼叫 ``prepare_docx_payload(client_slug, year, project_slug)`` 拿 payload。
        2. 用 python-docx 渲染到 ``<workspace>/projects/<project_slug>/output/Report_<year>.docx``。
        3. 寫 ``timeline_entry`` 到該 project page（``brain.timeline.append_dual``）。
        4. 回 ``DocxRenderResult`` — 含 output_path / size_bytes / *counts /
           timeline_entry_id / warnings。

    Args:
        client_slug: per-client workspace 目錄名（如 ``lealea-5364``）。
        year: 報告年度。
        project_slug: 預設 ``<year>-sustainability-report``。
        actor: 寫入 timeline 的 actor 欄位。

    Returns:
        ``DocxRenderResult``。

    Raises:
        FileNotFoundError: client workspace 不存在。
        RenderError: python-docx 未裝、或渲染期間遇到 docx exception。
    """
    client_path = find_client_workspace(client_slug)  # raises FileNotFoundError
    payload = prepare_docx_payload(client_slug, year, project_slug=project_slug)
    resolved_project = payload.annex.get("project_slug") or f"{year}-sustainability-report"

    out_path = (
        client_path / "projects" / resolved_project / "output" / f"Report_{year}.docx"
    )

    warnings = render_docx_payload_to_path(payload, out_path, year_hint=year)

    size_bytes = out_path.stat().st_size
    tl_id = _write_render_timeline(
        client_path, year, resolved_project,
        payload=payload, out_path=out_path, size_bytes=size_bytes,
        client_slug=client_slug, actor=actor,
    )

    return DocxRenderResult(
        output_path=str(out_path),
        size_bytes=size_bytes,
        chapter_count=len(payload.chapters),
        iro_count=len(payload.iros),
        kpi_count=len(payload.kpis_summary),
        target_count=len(payload.targets_summary),
        timeline_entry_id=tl_id,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Server registration
# ---------------------------------------------------------------------------


def register(server) -> None:  # noqa: ANN001
    """Bind ``render_docx_simple`` to a FastMCP server instance."""
    server.tool()(render_docx_simple)


__all__ = [
    "RenderError",
    "DocxRenderResult",
    "render_docx_payload_to_path",
    "render_docx_simple",
    "register",
]
