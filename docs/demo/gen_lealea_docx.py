"""End-to-end docx generator for lealea-5364 fixture.

Pipeline:
  1. Create temp workspace, init brain DB
  2. Ingest examples/lealea-5364/{entities,projects/2025-sr/chapters}
  3. Call prepare_docx_payload(lealea-5364, 2025) → DocxPayload
  4. Render via python-docx to a real .docx
  5. Drop payload JSON + final .docx into projects/2025-sustainability-report/output/

This script replaces the manual step of invoking document-skills:docx in
Claude Code — useful for demo / end-to-end validation of brain → docx pipeline.

For production, consultants should still go through Claude Desktop + docx skill
(richer typography, better TOC handling).
"""
from __future__ import annotations
import os, sys, tempfile, pathlib, shutil, re
from typing import Optional

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "packages" / "susr"))

import numpy as np
from docx import Document
from docx.shared import Pt, RGBColor, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# Brand consistent with consultant intro pptx
BRAND_DARK = RGBColor(0x1F, 0x5F, 0x4A)
BRAND_ACCENT = RGBColor(0x4A, 0x8F, 0x6E)
GREY_MUTED = RGBColor(0x55, 0x55, 0x55)
FONT_CN = "微軟正黑體"
FONT_EN = "Calibri"

LEALEA = REPO / "examples" / "lealea-5364"
OUT_DIR = LEALEA / "projects" / "2025-sustainability-report" / "output"


# ---------------------------------------------------------------------------
# Pipeline step 1-3: ingest + prepare_docx_payload
# ---------------------------------------------------------------------------

class MockEmb:
    name = "mock-sha256"
    dimension = 1024
    def embed_query(self, text):
        import hashlib
        h = hashlib.sha256(text.encode("utf-8")).digest()
        arr = np.frombuffer((h * 128)[:1024 * 4], dtype=np.uint8).astype(np.float32) / 255.0
        return arr.reshape(-1)[:1024]
    def embed_documents(self, texts):
        return np.stack([self.embed_query(t) for t in texts])


def build_payload():
    """Ingest lealea-5364 into a temp workspace + return prepared docx payload."""
    from susr.brain.engine import BrainEngine
    from susr.brain.ingest import ingest_directory
    from susr.workspace import create_client_workspace
    from susr.mcp.tools.phase6 import prepare_docx_payload

    tmp_root = pathlib.Path(tempfile.mkdtemp(prefix="susr_docxgen_"))
    os.environ["SUSR_WORKSPACE_ROOT"] = str(tmp_root)

    ws = create_client_workspace(
        root=tmp_root, name="lealea-5364",
        legal_name="力麗觀光開發股份有限公司",
        industry="hospitality",
        standards=["GRI 2021", "ISSB", "TWSE-FSC"],
        boundary="合併",
        reporting_period="2025-01-01..2025-12-31",
    )
    ws_path = pathlib.Path(ws["workspace_path"])
    for sub in ("entities", "projects"):
        src, dst = LEALEA / sub, ws_path / sub
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

    db = ws_path / ".susr" / "db.sqlite"
    engine = BrainEngine.open(str(db), load_sqlite_vec=False)
    try:
        ent = ingest_directory(engine.conn, ws_path / "entities", strict=False)
        ch = ingest_directory(
            engine.conn,
            ws_path / "projects" / "2025-sustainability-report" / "chapters",
            strict=False,
        )
    finally:
        engine.close()

    payload = prepare_docx_payload(client_slug="lealea-5364", year=2025)
    return payload, len(ent) + len(ch)


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

def set_run_font(run, size=11, bold=False, color=None, name_cn=FONT_CN, name_en=FONT_EN):
    run.font.name = name_en
    run.font.size = Pt(size)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), name_cn)
    rFonts.set(qn("w:ascii"), name_en)
    rFonts.set(qn("w:hAnsi"), name_en)


def add_heading(doc, text, level=1):
    style = {1: "Heading 1", 2: "Heading 2", 3: "Heading 3", 4: "Heading 4"}[level]
    p = doc.add_paragraph(style=style)
    run = p.add_run(text)
    size = {1: 22, 2: 18, 3: 14, 4: 12}[level]
    set_run_font(run, size=size, bold=True, color=BRAND_DARK)
    p.paragraph_format.space_before = Pt(12 if level > 1 else 18)
    p.paragraph_format.space_after = Pt(6)
    return p


def add_para(doc, text, size=11, bold=False, italic=False, color=None,
             align=None, indent=None, style=None):
    p = doc.add_paragraph(style=style) if style else doc.add_paragraph()
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold, color=color)
    run.italic = italic
    if align is not None:
        p.alignment = align
    if indent is not None:
        p.paragraph_format.left_indent = Cm(indent)
    p.paragraph_format.space_after = Pt(4)
    return p


def add_kv(doc, key, value):
    p = doc.add_paragraph()
    r1 = p.add_run(f"{key}：")
    set_run_font(r1, size=11, bold=True, color=BRAND_DARK)
    r2 = p.add_run(str(value))
    set_run_font(r2, size=11)
    p.paragraph_format.space_after = Pt(2)


def set_cell_shading(cell, fill_hex):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill_hex)
    shd.set(qn("w:val"), "clear")
    tc_pr.append(shd)


def fill_cell(cell, text, bold=False, header=False, size=10, align=None):
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    for p in cell.paragraphs:
        p._element.getparent().remove(p._element)
    p = cell.add_paragraph()
    run = p.add_run(str(text) if text not in (None, "") else "—")
    color = RGBColor(0xFF, 0xFF, 0xFF) if header else None
    set_run_font(run, size=size, bold=bold or header, color=color)
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(0)
    if header:
        set_cell_shading(cell, "1F5F4A")


# ---------------------------------------------------------------------------
# Markdown → docx (minimal, focused on chapter content)
# ---------------------------------------------------------------------------

_RE_BOLD = re.compile(r"\*\*([^*]+)\*\*")


def _add_inline(p, text):
    """Handle **bold** inline; ignore other markdown decoration."""
    last = 0
    for m in _RE_BOLD.finditer(text):
        if m.start() > last:
            r = p.add_run(text[last:m.start()])
            set_run_font(r, size=11)
        rb = p.add_run(m.group(1))
        set_run_font(rb, size=11, bold=True)
        last = m.end()
    if last < len(text):
        r = p.add_run(text[last:])
        set_run_font(r, size=11)


def render_markdown(doc, md_text, base_heading_level=2):
    """Convert chapter markdown into docx paragraphs / lists / tables.

    Supports: # H1 / ## H2 / ### H3 / blockquote / unordered list / numbered list /
    table (| col | col |) / horizontal rule (---).  Inline **bold**.
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
            pbdr = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "6")
            bottom.set(qn("w:color"), "888888")
            pbdr.append(bottom)
            pPr.append(pbdr)
            p.paragraph_format.space_after = Pt(4)
            i += 1
            continue

        # Headings — relative to chapter base level
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level_raw = len(m.group(1))
            level = min(4, base_heading_level + level_raw - 1)
            add_heading(doc, m.group(2), level=level)
            i += 1
            continue

        # Blockquote
        if stripped.startswith(">"):
            quote_text = stripped[1:].strip()
            p = doc.add_paragraph()
            _add_inline(p, quote_text)
            for run in p.runs:
                run.italic = True
                run.font.color.rgb = GREY_MUTED
            p.paragraph_format.left_indent = Cm(0.5)
            p.paragraph_format.space_after = Pt(4)
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
                fill_cell(t.rows[0].cells[k], h, header=True, size=10)
            for r_idx, row in enumerate(row_lines):
                for k, c in enumerate(row[:len(header_cells)]):
                    fill_cell(t.rows[1 + r_idx].cells[k], c, size=10)
            doc.add_paragraph().paragraph_format.space_after = Pt(2)
            i = j
            continue

        # Numbered list
        m = re.match(r"^\d+\.\s+(.*)$", stripped)
        if m:
            p = doc.add_paragraph(style="List Number")
            _add_inline(p, m.group(1))
            i += 1
            continue

        # Bullet
        m = re.match(r"^[-*]\s+(.*)$", stripped)
        if m:
            p = doc.add_paragraph(style="List Bullet")
            _add_inline(p, m.group(1))
            i += 1
            continue

        # Plain paragraph
        p = doc.add_paragraph()
        _add_inline(p, stripped)
        p.paragraph_format.space_after = Pt(4)
        i += 1


# ---------------------------------------------------------------------------
# Document sections
# ---------------------------------------------------------------------------

def render_cover(doc, payload):
    # 留白上方
    for _ in range(6):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(payload.client.legal_name)
    set_run_font(r, size=32, bold=True, color=BRAND_DARK)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("2025 永續報告書")
    set_run_font(r, size=28, bold=True, color=BRAND_DARK)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Sustainability Report")
    set_run_font(r, size=14, color=GREY_MUTED)

    for _ in range(2):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"報告期間：{payload.reporting_period}")
    set_run_font(r, size=12)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"適用框架：{' / '.join(payload.frameworks)}")
    set_run_font(r, size=12)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("股票代號：5364")
    set_run_font(r, size=12)

    for _ in range(8):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("— 由 susr ESG Co-pilot 自動組裝 —")
    set_run_font(r, size=10, color=GREY_MUTED)
    r.italic = True

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Powered by m4ore · github.com/M4ORE/m4ore-skill-susr")
    set_run_font(r, size=9, color=GREY_MUTED)

    doc.add_page_break()


def render_toc_placeholder(doc):
    add_heading(doc, "目次", level=1)
    add_para(doc, "請在 Microsoft Word 內按 [參考資料 → 更新目錄] 或選取本段後按 F9 自動產生章節頁碼。",
             italic=True, color=GREY_MUTED)
    items = [
        "第一章　公司概況",
        "第二章　重大性議題評估",
        "第三章　氣候變遷（TCFD）",
        "第四章　食品安全",
        "第五章　客戶隱私",
        "第六章　在地共融與文化保存",
        "附錄 A　IRO 風險與機會清單",
        "附錄 B　KPI 績效摘要",
        "附錄 C　目標進度追蹤",
        "附錄 D　GRI Content Index",
    ]
    for it in items:
        p = doc.add_paragraph()
        r = p.add_run(it)
        set_run_font(r, size=11)
        p.paragraph_format.space_after = Pt(2)
    doc.add_page_break()


def render_company_profile(doc, payload):
    add_heading(doc, "第一章　公司概況", level=1)
    add_kv(doc, "公司全名", payload.client.legal_name)
    add_kv(doc, "產業別", "觀光休憩（hospitality）")
    add_kv(doc, "股票代號", "5364（上市）")
    add_kv(doc, "報告期間", payload.reporting_period)
    add_kv(doc, "報告邊界", "合併報表範圍（含力麗觀光及其子公司）")
    add_kv(doc, "適用框架", " / ".join(payload.frameworks))
    add_kv(doc, "確信等級", "未進行第三方確信（v0.1 demo 試做）")
    add_kv(doc, "聯絡窗口", "永續發展委員會（範例填空）")
    add_para(doc, "本報告書由 susr ESG Co-pilot 自動組裝，內容基於 lealea-5364 fixture 範例資料、SP1-004 試做案例與 R1-R10 brain 演進。本報告書非力麗觀光開發股份有限公司之正式對外文件，僅作為 susr 端到端能力展示。",
             italic=True, color=GREY_MUTED, size=10)
    doc.add_page_break()


def render_materiality(doc, payload):
    add_heading(doc, "第二章　重大性議題評估", level=1)
    add_para(doc, "本章節依雙重重大性（Double Materiality）原則，從影響重大性（Impact Materiality）與財務重大性（Financial Materiality）兩個維度評估議題。經 susr brain 之 score_topic_dual_axis 工具計算與顧問實際業務判斷整合後，得出本年度核心議題與重大議題清單。")

    add_heading(doc, "2.1 核心議題（9 項）", level=2)
    add_para(doc, "核心議題為雙軸評分皆 ≥ 4 之議題，或經顧問依產業特性與利害關係人重視程度判定為策略關鍵：")

    t = doc.add_table(rows=1 + len(payload.materiality_matrix.core_topics), cols=2)
    t.style = "Light Grid Accent 1"
    fill_cell(t.rows[0].cells[0], "議題代碼", header=True, size=10)
    fill_cell(t.rows[0].cells[1], "議題類別", header=True, size=10)
    for i, slug in enumerate(payload.materiality_matrix.core_topics):
        topic_id = slug.split("/")[-1] if "/" in slug else slug
        category = _topic_category(topic_id)
        fill_cell(t.rows[1 + i].cells[0], topic_id, size=10)
        fill_cell(t.rows[1 + i].cells[1], category, size=10)

    add_heading(doc, "2.2 重大議題（追加揭露 5 項）", level=2)
    add_para(doc, "核心議題之外、雙軸評分達重大門檻者（共 14 項）：")
    extras = [s for s in payload.materiality_matrix.material_topics
              if s not in payload.materiality_matrix.core_topics]
    if extras:
        t = doc.add_table(rows=1 + len(extras), cols=2)
        t.style = "Light Grid Accent 1"
        fill_cell(t.rows[0].cells[0], "議題代碼", header=True, size=10)
        fill_cell(t.rows[0].cells[1], "議題類別", header=True, size=10)
        for i, slug in enumerate(extras):
            topic_id = slug.split("/")[-1] if "/" in slug else slug
            fill_cell(t.rows[1 + i].cells[0], topic_id, size=10)
            fill_cell(t.rows[1 + i].cells[1], _topic_category(topic_id), size=10)

    add_heading(doc, "2.3 議題評分覆寫紀錄", level=2)
    if payload.materiality_matrix.tier_overrides:
        add_para(doc, f"本年度顧問依專業判斷對 {len(payload.materiality_matrix.tier_overrides)} 個議題進行 tier 等級覆寫。所有覆寫均留有 audit trail（見 brain timeline_entries 表）。")
    else:
        add_para(doc, "本年度未進行 tier 等級覆寫，所有議題分級皆由雙軸評分自動推導。",
                 italic=True, color=GREY_MUTED)

    add_heading(doc, "2.4 利害關係人議合摘要", level=2)
    stake = [
        ("投資人", "法說會、年報、月報", "氣候風險、財務影響、治理結構"),
        ("員工", "員工大會、滿意度問卷", "薪酬福利、職涯發展、職安"),
        ("客戶", "客戶滿意度、意見回饋", "食品安全、服務品質、隱私保護"),
        ("當地社區", "社區議合會議、文化保存協作", "在地就業、原住民權益、環境保護"),
        ("供應商", "供應商評鑑、供應鏈問卷", "供應鏈永續、勞動條件"),
        ("監管機關", "金管會公開資訊觀測站、永續報告書", "合規揭露、ISSB 準備度"),
        ("非政府組織", "公益合作、議題對話", "原住民權益、環境議題"),
    ]
    t = doc.add_table(rows=1 + len(stake), cols=3)
    t.style = "Light Grid Accent 1"
    for k, h in enumerate(("利害關係人", "溝通管道", "關注議題")):
        fill_cell(t.rows[0].cells[k], h, header=True, size=10)
    for i, row in enumerate(stake):
        for k, v in enumerate(row):
            fill_cell(t.rows[1 + i].cells[k], v, size=10)

    doc.add_page_break()


_TOPIC_CAT = {
    "E1-climate": "環境（氣候變遷）",
    "E2-energy": "環境（能源）",
    "E3-water": "環境（水資源）",
    "E4-waste": "環境（廢棄物）",
    "E5-biodiversity": "環境（生物多樣性）",
    "S1-labor-conditions": "社會（員工）",
    "S2-occupational-health": "社會（職業安全）",
    "S3-training": "社會（訓練）",
    "S4-diversity": "社會（多元共融）",
    "S5-human-rights": "社會（人權）",
    "S6-supply-chain-labor": "社會（供應鏈）",
    "S7-customer-health": "社會（顧客健康）",
    "S8-customer-privacy": "社會（顧客隱私）",
    "S9-community-engagement": "社會（社區）",
    "S10-local-economic-impact": "社會（在地經濟）",
    "S11-food-safety": "社會（食品安全）",
    "S12-indigenous-culture": "社會（原住民文化）",
    "S13-accessibility": "社會（無障礙）",
    "G1-board-governance": "治理（董事會）",
    "G2-ethics": "治理（道德）",
    "G3-risk-management": "治理（風險管理）",
    "G4-data-security": "治理（資安）",
    "G5-anti-corruption": "治理（反貪腐）",
    "G6-tax-transparency": "治理（稅務透明）",
    "food-safety": "社會（食品安全）",
    "customer-privacy": "社會（顧客隱私）",
    "local-indigenous": "社會（在地與原住民）",
}


def _topic_category(slug):
    return _TOPIC_CAT.get(slug, "未分類")


def render_chapters(doc, payload):
    """Render 5 chapters from chapters[]; skip _skeleton placeholder."""
    chapter_num_map = {
        "tcfd-2025": ("第三章", "氣候變遷（TCFD）"),
        "food-safety-2025": ("第四章", "食品安全"),
        "customer-privacy-2025": ("第五章", "客戶隱私"),
        "local-indigenous-2025": ("第六章", "在地共融與文化保存"),
    }
    order = ["tcfd-2025", "food-safety-2025", "customer-privacy-2025", "local-indigenous-2025"]
    by_slug = {c.slug.split("/")[-1]: c for c in payload.chapters}

    for key in order:
        ch = by_slug.get(key)
        if not ch:
            continue
        num, title = chapter_num_map[key]
        add_heading(doc, f"{num}　{title}", level=1)
        if ch.framework_refs:
            add_para(doc, f"適用框架：{' / '.join(ch.framework_refs)}",
                     italic=True, color=GREY_MUTED, size=10)
        render_markdown(doc, ch.content_md, base_heading_level=2)
        doc.add_page_break()


def render_iro_appendix(doc, payload):
    add_heading(doc, "附錄 A　IRO 風險與機會清單", level=1)
    add_para(doc, f"本附錄列出本報告期間經 brain 整理之 {len(payload.iros)} 項 IRO（Impact / Risk / Opportunity）。所有 IRO 與重大性議題建立 typed edge，並對應至具體因應行動（見各章節）。",
             size=10)

    iros_by_type = {"Impact": [], "Risk": [], "Opportunity": []}
    for iro in payload.iros:
        iros_by_type.setdefault(iro.iro_type, []).append(iro)

    for itype, label in [("Impact", "影響"), ("Risk", "風險"), ("Opportunity", "機會")]:
        rows = iros_by_type.get(itype, [])
        if not rows:
            continue
        add_heading(doc, f"A.{['Impact','Risk','Opportunity'].index(itype) + 1} {label}（{itype}） — {len(rows)} 項", level=2)
        t = doc.add_table(rows=1 + len(rows), cols=5)
        t.style = "Light Grid Accent 1"
        for k, h in enumerate(("議題", "IRO 名稱", "類別", "時間軸", "財務量級")):
            fill_cell(t.rows[0].cells[k], h, header=True, size=9)
        for i, iro in enumerate(rows):
            fill_cell(t.rows[1 + i].cells[0], iro.topic_slug, size=9)
            fill_cell(t.rows[1 + i].cells[1], iro.name or "—", size=9)
            fill_cell(t.rows[1 + i].cells[2], iro.category or "—", size=9)
            fill_cell(t.rows[1 + i].cells[3], _time_horizon_label(iro.time_horizon), size=9)
            fill_cell(t.rows[1 + i].cells[4], f"{iro.financial_magnitude:.1f}" if iro.financial_magnitude is not None else "—", size=9)
    doc.add_page_break()


def _time_horizon_label(code):
    return {"S": "短期（<1y）", "M": "中期（1-5y）", "L": "長期（5-10y）"}.get(code, code or "—")


def render_kpi_appendix(doc, payload):
    add_heading(doc, "附錄 B　KPI 績效摘要", level=1)
    add_para(doc, f"本附錄列出 {len(payload.kpis_summary)} 項本年度追蹤的 KPI，依議題與框架對應。實際數值欄位若為「—」表示本 fixture demo 中該 KPI 尚未填入年度實績（顧問實作時應補 Phase 4 數據包）。",
             size=10)
    t = doc.add_table(rows=1 + len(payload.kpis_summary), cols=6)
    t.style = "Light Grid Accent 1"
    for k, h in enumerate(("KPI 名稱", "單位", "對應議題", "最新值", "年度", "YoY")):
        fill_cell(t.rows[0].cells[k], h, header=True, size=9)
    for i, kpi in enumerate(payload.kpis_summary):
        fill_cell(t.rows[1 + i].cells[0], kpi.name, size=9)
        fill_cell(t.rows[1 + i].cells[1], kpi.unit or "—", size=9)
        fill_cell(t.rows[1 + i].cells[2], kpi.topic_slug or "—", size=9)
        fill_cell(t.rows[1 + i].cells[3], kpi.latest_value if kpi.latest_value is not None else "—", size=9)
        fill_cell(t.rows[1 + i].cells[4], kpi.latest_year or "—", size=9)
        fill_cell(t.rows[1 + i].cells[5], f"{kpi.yoy_change_pct:+.1f}%" if kpi.yoy_change_pct is not None else "—", size=9)

    add_heading(doc, "B.1 KPI 框架對應", level=2)
    t = doc.add_table(rows=1 + len(payload.kpis_summary), cols=2)
    t.style = "Light Grid Accent 1"
    fill_cell(t.rows[0].cells[0], "KPI", header=True, size=9)
    fill_cell(t.rows[0].cells[1], "框架對應", header=True, size=9)
    for i, kpi in enumerate(payload.kpis_summary):
        fill_cell(t.rows[1 + i].cells[0], kpi.name, size=9)
        fill_cell(t.rows[1 + i].cells[1], " / ".join(kpi.framework_refs) if kpi.framework_refs else "—", size=9)
    doc.add_page_break()


def render_target_appendix(doc, payload):
    add_heading(doc, "附錄 C　目標進度追蹤", level=1)
    add_para(doc, f"本附錄列出 {len(payload.targets_summary)} 項本年度設定的永續目標。所有目標依「基準年 → 目標年 → 量化值」三要件揭露，並指明驗證路徑。",
             size=10)
    t = doc.add_table(rows=1 + len(payload.targets_summary), cols=6)
    t.style = "Light Grid Accent 1"
    for k, h in enumerate(("目標", "對應 KPI", "基準年", "基準值", "目標年", "目標值")):
        fill_cell(t.rows[0].cells[k], h, header=True, size=9)
    for i, tgt in enumerate(payload.targets_summary):
        fill_cell(t.rows[1 + i].cells[0], tgt.slug.split("/")[-1], size=9)
        fill_cell(t.rows[1 + i].cells[1], tgt.kpi_slug or "—", size=9)
        fill_cell(t.rows[1 + i].cells[2], tgt.baseline_year or "—", size=9)
        fill_cell(t.rows[1 + i].cells[3], tgt.baseline_value if tgt.baseline_value is not None else "—", size=9)
        fill_cell(t.rows[1 + i].cells[4], tgt.target_year or "—", size=9)
        fill_cell(t.rows[1 + i].cells[5], tgt.target_value if tgt.target_value is not None else "—", size=9)

    add_heading(doc, "C.1 驗證路徑", level=2)
    for tgt in payload.targets_summary:
        if not tgt.verification_path:
            continue
        p = doc.add_paragraph(style="List Bullet")
        r1 = p.add_run(f"{tgt.slug.split('/')[-1]}：")
        set_run_font(r1, size=10, bold=True, color=BRAND_DARK)
        r2 = p.add_run(tgt.verification_path)
        set_run_font(r2, size=10)
    doc.add_page_break()


def render_gri_appendix(doc, payload):
    add_heading(doc, "附錄 D　GRI Content Index", level=1)
    if payload.gri_content_index_ref:
        add_para(doc, f"本年度 GRI Content Index 完整版見：{payload.gri_content_index_ref}")
    else:
        add_para(doc, "本附錄為 GRI Content Index 之佔位章節。susr Phase 7 工具 `generate_gri_content_index` 可由 brain 端對端產出，本 fixture demo 中尚未跑該 tool。",
                 italic=True, color=GREY_MUTED)
    add_para(doc, "標準 GRI Content Index 結構：",
             bold=True, color=BRAND_DARK, size=11)
    items = [
        "GRI 1: Foundation 2021 — 報告原則聲明",
        "GRI 2: General Disclosures 2021 — 組織描述、報告慣例、治理、利害關係人",
        "GRI 3: Material Topics 2021 — 重大主題清單與管理方針",
        "GRI 305: Emissions 2016 — 範疇 1/2/3 排放（待 Phase 4 數據包）",
        "GRI 303: Water and Effluents 2018 — 取水 / 用水 / 排水",
        "GRI 401-403: Employment / Labor / Health & Safety",
        "GRI 411: Rights of Indigenous Peoples — 在地原住民議題",
        "GRI 413: Local Communities — 在地共融",
        "GRI 416-418: Customer Health, Safety, Privacy",
    ]
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        _add_inline(p, it)


# ---------------------------------------------------------------------------
# Footer (page number)
# ---------------------------------------------------------------------------

def add_page_number_footer(doc):
    section = doc.sections[0]
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    run = p.add_run("第 ")
    set_run_font(run, size=9, color=GREY_MUTED)

    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.text = " PAGE "
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run = p.add_run()
    run._element.append(fld_begin)
    run._element.append(instr)
    run._element.append(fld_end)
    set_run_font(run, size=9, color=GREY_MUTED)

    run = p.add_run(" 頁")
    set_run_font(run, size=9, color=GREY_MUTED)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Step 1-3: ingest lealea fixture + prepare_docx_payload ...")
    payload, ingested = build_payload()
    print(f"  Ingested {ingested} pages.")
    print(f"  Chapters={len(payload.chapters)} / IROs={len(payload.iros)} / KPIs={len(payload.kpis_summary)} / Targets={len(payload.targets_summary)}")
    print(f"  Core topics={len(payload.materiality_matrix.core_topics)}, Material topics={len(payload.materiality_matrix.material_topics)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload_json = OUT_DIR / "docx-payload.json"
    payload_json.write_text(payload.model_dump_json(indent=2), encoding="utf-8")
    print(f"  Payload JSON: {payload_json}")

    print("Step 4: render .docx ...")
    doc = Document()
    section = doc.sections[0]
    section.page_height = Cm(29.7)
    section.page_width = Cm(21.0)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

    # Default style
    style = doc.styles["Normal"]
    style.font.name = FONT_EN
    style.font.size = Pt(11)
    rPr = style.element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), FONT_CN)

    render_cover(doc, payload)
    render_toc_placeholder(doc)
    render_company_profile(doc, payload)
    render_materiality(doc, payload)
    render_chapters(doc, payload)
    render_iro_appendix(doc, payload)
    render_kpi_appendix(doc, payload)
    render_target_appendix(doc, payload)
    render_gri_appendix(doc, payload)
    add_page_number_footer(doc)

    out_path = OUT_DIR / "Lealea_Sustainability_Report_2025.docx"
    doc.save(out_path)
    size_kb = out_path.stat().st_size / 1024
    print(f"\n[DONE] Generated: {out_path}")
    print(f"   Size: {size_kb:.1f} KB")
    return out_path


if __name__ == "__main__":
    main()
