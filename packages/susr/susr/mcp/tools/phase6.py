"""susr.mcp.tools.phase6 — Phase 6 document-skills payload preparation tools.

TL;DR（顧問速讀）：
    susr **不渲染** docx / pdf / pptx — 那是 anthropics/skills/{docx,pdf,pptx}
    sub-skill 的工作。Phase 6 susr 端只做「payload prep」：從 brain（client
    workspace 的 SQLite DB + filesystem markdown）撈出 chapters / topics /
    matrix / IRO / KPI / target，組成各 sub-skill **預期的 input schema**，
    回 dict payload + 給 caller 的 invocation instruction。

    Caller（Claude / agent）拿到 payload 後，再自行 invoke document-skills
    sub-skill 完成實際渲染。這把 susr 的 scope 維持在「資料準備 + 結構化」，
    把渲染環境依賴（pandoc / docx-js / pptxgenjs / LibreOffice / Pillow / qpdf）
    全部留給 sub-skill 自己處理。

模組 4 個 tool：

    1. ``prepare_docx_payload``           — 報告書 docx 主檔組裝 payload
    2. ``prepare_pdf_payload``            — 最終 PDF（含 iXBRL preview）payload
    3. ``prepare_pptx_investor_deck``     — 投資人版 10-15 頁 deck payload
    4. ``prepare_pptx_board_deck``        — 董事會版 5-8 頁 deck payload

TOC:
    - Helpers: brain lookup（chapters / iros / kpis / targets）
    - Helpers: matrix svg embed + project file resolve
    - Pydantic models: DocxPayload / PdfPayload / PptxInvestorPayload / PptxBoardPayload
    - Tool 1: prepare_docx_payload
    - Tool 2: prepare_pdf_payload
    - Tool 3: prepare_pptx_investor_deck
    - Tool 4: prepare_pptx_board_deck
    - register(server) + __all__

設計選項：

    - **不寫渲染**：susr Phase 6 v0.1 不 invoke document-skills；只 prep dict
      payload。實際 docx/pdf/pptx 渲染由 Claude / agent 拿 payload 後再做。
      理由：susr 不想揹 docx-js/pandoc/pptxgenjs/LibreOffice 環境依賴；那條
      路在 sub-skill 自己的 SKILL.md。
    - **payload schema 對齊** ``references/phase6-{docx,pdf,pptx}-prompts.md``
      內描述的 input 期待（已在 Step 3 搬到 ``shared_kb/data/prompts/``）。
      schema 欄位皆 nullable / list-or-empty，brain 沒資料時不 raise，回部分
      payload 讓顧問可以先看結構。
    - **chapter content_md 從哪來**：brain 內 chapter page 的 ``compiled_truth``
      （body）即為內容。若 brain 沒 chapter，content_md 為空字串、order 為
      0；caller 可依此判斷是否要先跑 Phase 5 寫章節。
    - **KPI top selection**：投資人 deck ``highlights.key_kpis`` 取 top 5 — 排序
      依（has values_by_year DESC, alphabetical slug ASC），保證 deterministic
      且優先含有實際資料的 KPI。
    - **materiality matrix SVG embed**：直接讀 ``projects/<project_slug>/
      materiality-<year>.svg``（generate_materiality_matrix 寫的）。檔案不存在
      → empty string；caller 知道要先跑 Phase 3 tool 3。
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from susr.workspace import find_client_workspace

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# 預設報告書框架（金管會永續報告書 baseline — 與 SKILL.md §「台灣上市櫃預設情境」對齊）
_DEFAULT_FRAMEWORKS: tuple[str, ...] = (
    "GRI Standards 2021",
    "ISSB IFRS S1/S2",
    "金管會上市上櫃公司編製與申報永續報告書作業辦法",
)

# 投資人 / 董事會 deck 頁數上限（references/phase6-pptx-prompts.md §2）
_INVESTOR_SLIDES_MAX = 15
_BOARD_SLIDES_MAX = 8

# Top-K KPI 與 target 在 deck highlights 採用的數量（防 payload 爆量）
_DECK_TOP_KPIS = 5
_DECK_TOP_TARGETS = 5

# Frontmatter regex — 與 phase3 一致
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


# ---------------------------------------------------------------------------
# Pydantic result models
# ---------------------------------------------------------------------------


class ChapterPayload(BaseModel):
    """單一章節在 docx / pdf payload 內的 minimal schema。"""

    title: str
    slug: str
    content_md: str
    order: int
    framework_refs: list[str] = []
    owner: Optional[str] = None


class IroPayload(BaseModel):
    """單一 IRO entity 在 payload 內的 schema。"""

    iro_slug: str
    topic_slug: str
    iro_type: Literal["Impact", "Risk", "Opportunity"]
    category: Optional[str] = None
    time_horizon: Optional[str] = None
    financial_magnitude: Optional[float] = None
    name: str = ""


class KpiPayload(BaseModel):
    """KPI summary item — 給 docx 章節 reference + deck highlights。"""

    slug: str
    name: str
    unit: str = ""
    topic_slug: Optional[str] = None
    boundary: Optional[str] = None
    formula: Optional[str] = None
    framework_refs: list[str] = []
    latest_value: Optional[float] = None
    latest_year: Optional[int] = None
    yoy_change_pct: Optional[float] = None


class TargetPayload(BaseModel):
    """Target summary item — 給 docx 章節 + deck highlights。"""

    slug: str
    kpi_slug: Optional[str] = None
    baseline_year: Optional[int] = None
    baseline_value: Optional[float] = None
    target_value: Optional[float] = None
    target_year: Optional[int] = None
    verification_path: Optional[str] = None
    is_quantitative: bool = True


class MaterialityMatrixPayload(BaseModel):
    """重大性矩陣在 payload 內的 embed schema。"""

    embedded_svg: str = ""
    core_topics: list[str] = []
    material_topics: list[str] = []
    tier_overrides: list[dict[str, Any]] = []  # R3-C output（slug + warning）


class ClientProfilePayload(BaseModel):
    """從 _client.md 抽出的 minimal client profile。"""

    slug: str
    legal_name: str
    industry: str = ""
    stock_code: Optional[str] = None


class DocxPayload(BaseModel):
    """``prepare_docx_payload`` 回傳結構 — 對齊 references/phase6-docx-prompts.md §2 + §4.1。

    Caller 拿到後應呼叫 ``document-skills:docx`` skill，把本 payload 內容組進
    Report_<year>.docx。``invocation_hint`` 給 Claude 一段 prompt 雛形。
    """

    document_type: Literal["sustainability_report"] = "sustainability_report"
    client: ClientProfilePayload
    reporting_period: str
    frameworks: list[str]
    chapters: list[ChapterPayload]
    materiality_matrix: MaterialityMatrixPayload
    iros: list[IroPayload]
    kpis_summary: list[KpiPayload]
    targets_summary: list[TargetPayload]
    gri_content_index_ref: Optional[str] = None
    annex: dict[str, Any] = {}
    invocation_hint: str = ""


class PdfPayload(BaseModel):
    """``prepare_pdf_payload`` 回傳結構 — 對齊 references/phase6-pdf-prompts.md §3 + §4.1。

    PDF 預設來源是 docx → PDF（LibreOffice headless），所以本 payload 結構大量
    複用 DocxPayload，但加 print_layout / language / cover_design_hints /
    ixbrl_concepts_preview（Q16 預留）四欄。
    """

    document_type: Literal["sustainability_report_pdf"] = "sustainability_report_pdf"
    client: ClientProfilePayload
    reporting_period: str
    frameworks: list[str]
    chapters: list[ChapterPayload]
    materiality_matrix: MaterialityMatrixPayload
    iros: list[IroPayload]
    kpis_summary: list[KpiPayload]
    targets_summary: list[TargetPayload]
    gri_content_index_ref: Optional[str] = None
    annex: dict[str, Any] = {}
    print_layout: Literal["A4", "Letter"] = "A4"
    language: str = "zh-TW"
    cover_design_hints: dict[str, Any] = Field(default_factory=dict)
    ixbrl_concepts_preview: list[dict[str, str]] = []
    invocation_hint: str = ""


class InvestorHighlights(BaseModel):
    """投資人 deck 重點摘要 — 績效 + 目標 + 風險導向。"""

    key_kpis: list[KpiPayload] = []
    core_topics: list[str] = []
    key_targets: list[TargetPayload] = []
    performance_chart_hints: list[str] = []


class PptxInvestorPayload(BaseModel):
    """``prepare_pptx_investor_deck`` 回傳結構 — 對齊 phase6-pptx-prompts.md §2 + §3 + §5.1。"""

    deck_type: Literal["investor"] = "investor"
    client: ClientProfilePayload
    reporting_period: str
    target_audience: str = "ESG investors / analysts"
    slides_max: int = _INVESTOR_SLIDES_MAX
    highlights: InvestorHighlights
    embed_matrix_svg: str = ""
    tone: str = "投資人關注 — 強調績效 + 風險揭露 + 目標達成度"
    invocation_hint: str = ""


class BoardHighlights(BaseModel):
    """董事會 deck 重點摘要 — 治理 + 風險 + 決策請求導向。"""

    governance_summary: str = ""
    material_risks: list[IroPayload] = []
    material_opportunities: list[IroPayload] = []
    key_decisions_needed: list[str] = []
    regulatory_compliance_status: str = ""


class PptxBoardPayload(BaseModel):
    """``prepare_pptx_board_deck`` 回傳結構 — 對齊 phase6-pptx-prompts.md §2 + §3 + §5.2。"""

    deck_type: Literal["board"] = "board"
    client: ClientProfilePayload
    reporting_period: str
    target_audience: str = "Board members"
    slides_max: int = _BOARD_SLIDES_MAX
    highlights: BoardHighlights
    tone: str = "董事會關注 — 治理 + 風險 + 決策需要"
    invocation_hint: str = ""


# ---------------------------------------------------------------------------
# Helpers — brain lookups（純讀）
# ---------------------------------------------------------------------------


def _read_md_frontmatter(path: Path) -> dict[str, Any]:
    """讀 markdown 並 parse YAML frontmatter；無 frontmatter 或檔案不存在 → {}."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    try:
        import yaml  # type: ignore

        return yaml.safe_load(m.group(1)) or {}
    except Exception:
        return {}


def _resolve_project_slug(client_path: Path, year: int, project_slug: Optional[str]) -> str:
    """project_slug 預設為 ``<year>-sustainability-report`` — 與 lealea fixture 對齊。

    若 caller 給定 project_slug，直接使用；否則嘗試 ``<year>-sustainability-report``
    再 fallback ``<year>-sr``（phase7 慣例）。
    """
    if project_slug:
        return project_slug
    long_form = f"{year}-sustainability-report"
    if (client_path / "projects" / long_form).exists():
        return long_form
    short_form = f"{year}-sr"
    if (client_path / "projects" / short_form).exists():
        return short_form
    return long_form  # 仍回長式，讓 caller 看到「應該存在的路徑」


def _load_client_profile(client_path: Path, client_slug: str) -> ClientProfilePayload:
    """從 ``_client.md`` 抽 legal_name / industry / stock_code。"""
    fm = _read_md_frontmatter(client_path / "_client.md")
    return ClientProfilePayload(
        slug=client_slug,
        legal_name=str(fm.get("legal_name") or client_slug),
        industry=str(fm.get("industry_gri_sector") or fm.get("industry") or ""),
        stock_code=(str(fm["stock_code"]) if fm.get("stock_code") else None),
    )


def _load_reporting_period(client_path: Path, year: int) -> str:
    """從 ``projects/<project>/_project.md`` 抽 reporting_period；找不到 fallback ``YYYY``."""
    fm = _read_md_frontmatter(client_path / "_client.md")
    period = fm.get("reporting_period")
    if isinstance(period, str) and period and period != "annual":
        # _client.md 若有具體區間就用，否則回 year string
        return period
    return str(year)


def _load_frameworks(client_path: Path) -> list[str]:
    """從 ``_client.md`` 抽 applicable_standards；空時回 ``_DEFAULT_FRAMEWORKS``。"""
    fm = _read_md_frontmatter(client_path / "_client.md")
    standards = fm.get("applicable_standards")
    if isinstance(standards, list) and standards:
        return [str(s) for s in standards]
    return list(_DEFAULT_FRAMEWORKS)


def _fetch_attrs(conn: sqlite3.Connection, page_id: int) -> dict[str, Any]:
    """讀單一 page 的 entity_attributes → dict。值仍為 raw TEXT，由 caller 解析。"""
    rows = conn.execute(
        "SELECT key, value, value_type FROM entity_attributes WHERE page_id = ?",
        [page_id],
    ).fetchall()
    out: dict[str, Any] = {}
    for key, value, vtype in rows:
        if value is None:
            continue
        if vtype == "int":
            try:
                out[key] = int(value)
            except ValueError:
                out[key] = value
        elif vtype == "float":
            try:
                out[key] = float(value)
            except ValueError:
                out[key] = value
        elif vtype == "bool":
            out[key] = str(value).lower() in ("true", "1", "yes")
        elif vtype in ("json_array", "json_object"):
            import json as _json

            try:
                out[key] = _json.loads(value)
            except Exception:
                out[key] = value
        else:
            out[key] = value
    return out


def _load_chapters(conn: sqlite3.Connection) -> list[ChapterPayload]:
    """掃 brain 內 entity_type='chapter'，回 ordered ChapterPayload list。

    Order 由（attribute['order'] if present, else alphabetical slug index）。
    Content 從 pages.compiled_truth 讀（章節 body markdown）。
    """
    rows = conn.execute(
        "SELECT id, slug, title, compiled_truth FROM pages "
        "WHERE entity_type='chapter' AND deleted_at IS NULL ORDER BY slug"
    ).fetchall()
    out: list[ChapterPayload] = []
    for idx, (page_id, slug, title, body) in enumerate(rows, start=1):
        attrs = _fetch_attrs(conn, int(page_id))
        order_raw = attrs.get("order")
        try:
            order = int(order_raw) if order_raw is not None else idx
        except (TypeError, ValueError):
            order = idx
        framework_refs = attrs.get("framework_refs")
        if not isinstance(framework_refs, list):
            framework_refs = []
        out.append(ChapterPayload(
            title=str(title or slug),
            slug=str(slug),
            content_md=str(body or ""),
            order=order,
            framework_refs=[str(x) for x in framework_refs],
            owner=(str(attrs["owner"]) if attrs.get("owner") else None),
        ))
    # 依 order 排序，再依 slug
    out.sort(key=lambda c: (c.order, c.slug))
    return out


def _load_iros(conn: sqlite3.Connection) -> list[IroPayload]:
    """掃 brain 內 entity_type='iro'，回 IroPayload list。"""
    rows = conn.execute(
        "SELECT id, slug, title FROM pages "
        "WHERE entity_type='iro' AND deleted_at IS NULL ORDER BY slug"
    ).fetchall()
    out: list[IroPayload] = []
    for page_id, slug, title in rows:
        attrs = _fetch_attrs(conn, int(page_id))
        iro_type_raw = str(attrs.get("type") or "Impact")
        # normalise — title case
        if iro_type_raw.lower() in ("impact", "risk", "opportunity"):
            iro_type = iro_type_raw.title()
        else:
            iro_type = "Impact"
        out.append(IroPayload(
            iro_slug=str(slug).split("/")[-1],  # iros/<slug> → <slug>
            topic_slug=str(attrs.get("topic_slug") or ""),
            iro_type=iro_type,  # type: ignore[arg-type]
            category=(str(attrs["category"]) if attrs.get("category") else None),
            time_horizon=(str(attrs["time_horizon"]) if attrs.get("time_horizon") else None),
            financial_magnitude=(
                float(attrs["financial_magnitude"])
                if attrs.get("financial_magnitude") is not None
                else None
            ),
            name=str(attrs.get("iro_name") or title or ""),
        ))
    return out


def _kpi_latest_value_year(values_by_year: Any) -> tuple[Optional[float], Optional[int]]:
    """從 KPI 的 values_by_year list 抽最新一筆 (value, year)。

    values_by_year schema 慣例：``[{"year": 2024, "value": 1234.0, ...}, ...]``。
    list 為空或格式異常 → (None, None)。
    """
    if not isinstance(values_by_year, list) or not values_by_year:
        return None, None
    valid: list[tuple[int, float]] = []
    for entry in values_by_year:
        if not isinstance(entry, dict):
            continue
        try:
            y = int(entry.get("year"))
            v = float(entry.get("value"))
        except (TypeError, ValueError):
            continue
        valid.append((y, v))
    if not valid:
        return None, None
    valid.sort(key=lambda yv: yv[0], reverse=True)
    return valid[0][1], valid[0][0]


def _kpi_yoy_pct(values_by_year: Any) -> Optional[float]:
    """從 values_by_year 算最新 vs 前一年的 YoY 百分比變化；不足 2 筆 → None。"""
    if not isinstance(values_by_year, list) or len(values_by_year) < 2:
        return None
    pairs: list[tuple[int, float]] = []
    for entry in values_by_year:
        if not isinstance(entry, dict):
            continue
        try:
            y = int(entry.get("year"))
            v = float(entry.get("value"))
        except (TypeError, ValueError):
            continue
        pairs.append((y, v))
    if len(pairs) < 2:
        return None
    pairs.sort(key=lambda yv: yv[0], reverse=True)
    latest_y, latest_v = pairs[0]
    prev_y, prev_v = pairs[1]
    if prev_v == 0 or latest_y - prev_y > 5:  # 排除過大 gap
        return None
    return round(((latest_v - prev_v) / prev_v) * 100.0, 2)


def _load_kpis(conn: sqlite3.Connection) -> list[KpiPayload]:
    """掃 brain entity_type='kpi'；attach latest_value + YoY 給 deck 用。"""
    rows = conn.execute(
        "SELECT id, slug, title FROM pages "
        "WHERE entity_type='kpi' AND deleted_at IS NULL ORDER BY slug"
    ).fetchall()
    out: list[KpiPayload] = []
    for page_id, slug, title in rows:
        attrs = _fetch_attrs(conn, int(page_id))
        framework_refs = attrs.get("framework_refs")
        if not isinstance(framework_refs, list):
            framework_refs = []
        latest_v, latest_y = _kpi_latest_value_year(attrs.get("values_by_year"))
        yoy = _kpi_yoy_pct(attrs.get("values_by_year"))
        out.append(KpiPayload(
            slug=str(slug),
            name=str(attrs.get("name") or title or slug),
            unit=str(attrs.get("unit") or ""),
            topic_slug=(str(attrs["topic_slug"]) if attrs.get("topic_slug") else None),
            boundary=(str(attrs["boundary"]) if attrs.get("boundary") else None),
            formula=(str(attrs["formula"]) if attrs.get("formula") else None),
            framework_refs=[str(x) for x in framework_refs],
            latest_value=latest_v, latest_year=latest_y,
            yoy_change_pct=yoy,
        ))
    return out


def _load_targets(conn: sqlite3.Connection) -> list[TargetPayload]:
    """掃 brain entity_type='target'。"""
    rows = conn.execute(
        "SELECT id, slug FROM pages "
        "WHERE entity_type='target' AND deleted_at IS NULL ORDER BY slug"
    ).fetchall()
    out: list[TargetPayload] = []
    for page_id, slug in rows:
        attrs = _fetch_attrs(conn, int(page_id))
        out.append(TargetPayload(
            slug=str(slug),
            kpi_slug=(str(attrs["kpi_slug"]) if attrs.get("kpi_slug") else None),
            baseline_year=(int(attrs["baseline_year"]) if attrs.get("baseline_year") is not None else None),
            baseline_value=(float(attrs["baseline_value"]) if attrs.get("baseline_value") is not None else None),
            target_value=(float(attrs["target_value"]) if attrs.get("target_value") is not None else None),
            target_year=(int(attrs["target_year"]) if attrs.get("target_year") is not None else None),
            verification_path=(str(attrs["verification_path"]) if attrs.get("verification_path") else None),
            is_quantitative=bool(attrs.get("is_quantitative", True)),
        ))
    return out


def _load_core_topics(conn: sqlite3.Connection) -> list[str]:
    """掃 brain entity_type='topic' 且 materiality_tier='核心'，回 slug list。"""
    rows = conn.execute(
        "SELECT p.slug FROM pages p "
        "JOIN entity_attributes a ON a.page_id = p.id "
        "WHERE p.entity_type='topic' AND a.key='materiality_tier' "
        "AND a.value LIKE '%核心%' AND p.deleted_at IS NULL ORDER BY p.slug"
    ).fetchall()
    return [str(r[0]) for r in rows]


def _load_material_topics(conn: sqlite3.Connection) -> list[str]:
    """掃 brain entity_type='topic' 且 materiality_tier='重大'，回 slug list。"""
    rows = conn.execute(
        "SELECT p.slug FROM pages p "
        "JOIN entity_attributes a ON a.page_id = p.id "
        "WHERE p.entity_type='topic' AND a.key='materiality_tier' "
        "AND a.value LIKE '%重大%' AND p.deleted_at IS NULL ORDER BY p.slug"
    ).fetchall()
    return [str(r[0]) for r in rows]


def _load_matrix_payload(client_path: Path, project_slug: str, year: int) -> MaterialityMatrixPayload:
    """從 ``projects/<project_slug>/materiality-<year>.svg`` 抽 embedded SVG。

    若 SVG 不存在（顧問還沒跑 Phase 3 tool 3 generate_materiality_matrix），
    embedded_svg 回空字串，core_topics / material_topics 由 caller 從 brain
    補上。
    """
    svg_path = client_path / "projects" / project_slug / f"materiality-{year}.svg"
    embedded_svg = ""
    if svg_path.exists():
        try:
            embedded_svg = svg_path.read_text(encoding="utf-8")
        except OSError:
            embedded_svg = ""
    return MaterialityMatrixPayload(embedded_svg=embedded_svg)


def _load_xbrl_preview(conn: sqlite3.Connection) -> list[dict[str, str]]:
    """掃 brain pages 內 xbrl_concept 非 NULL 的 page → (slug, xbrl_concept) tuple list。

    這對應 CLAUDE.md §8 Q16 iXBRL/ESEF 預留 — 現階段不寫值不驗證，但 Phase 6
    PDF payload 預先列出已標 concept 的 pages，給 caller 之後（金管會 2028 ISSB
    強制後）填值用的 anchor 表。
    """
    rows = conn.execute(
        "SELECT slug, xbrl_concept FROM pages "
        "WHERE xbrl_concept IS NOT NULL AND xbrl_concept != '' AND deleted_at IS NULL "
        "ORDER BY slug"
    ).fetchall()
    return [{"page_slug": str(s), "xbrl_concept": str(c)} for s, c in rows]


def _select_top_kpis(kpis: list[KpiPayload], k: int = _DECK_TOP_KPIS) -> list[KpiPayload]:
    """投資人 deck top-K KPI 選擇 — 排序依 has_latest_value DESC, slug ASC。

    確保 deterministic + 含實際 datapoint 的 KPI 優先入 deck。
    """
    return sorted(
        kpis,
        key=lambda kp: (0 if kp.latest_value is not None else 1, kp.slug),
    )[:k]


def _select_top_targets(targets: list[TargetPayload], k: int = _DECK_TOP_TARGETS) -> list[TargetPayload]:
    """deck top-K target — quantitative + 有 baseline_value 優先。"""
    return sorted(
        targets,
        key=lambda t: (
            0 if (t.is_quantitative and t.baseline_value is not None) else 1,
            t.slug,
        ),
    )[:k]


def _filter_iros_by_type(iros: list[IroPayload], iro_type: str) -> list[IroPayload]:
    """從 IRO list 抽單一類型（Risk / Opportunity）— 給董事會 deck 用。"""
    return [i for i in iros if i.iro_type == iro_type]


# ---------------------------------------------------------------------------
# Tool 1: prepare_docx_payload
# ---------------------------------------------------------------------------


def prepare_docx_payload(
    client_slug: str, year: int, project_slug: Optional[str] = None,
) -> DocxPayload:
    """組裝報告書主 docx 檔的 input payload（不渲染）。

    對齊 ``references/phase6-docx-prompts.md`` §2 標準結構 + §4.1 prompt 範本。
    Caller 拿到 payload 後，自行 invoke ``document-skills:docx`` skill 把章節
    內容組進 Report_<year>.docx。susr 在此 phase 只負責資料準備。

    Args:
        client_slug: per-client workspace 目錄名（如 ``lealea-5364``）。
        year: 報告年度，用於 reporting_period + 找 materiality-svg + GRI index ref。
        project_slug: 預設 ``<year>-sustainability-report``；可顯式覆寫。

    Returns:
        ``DocxPayload`` — chapters / iros / kpis / targets / matrix svg 全部齊全；
        brain 內若空（顧問未跑 Phase 5/6 前置）回部分 payload，**不** raise。

    Raises:
        FileNotFoundError: client workspace 不存在（沒 ``_client.md``）。
    """
    client_path = find_client_workspace(client_slug)
    resolved_project = _resolve_project_slug(client_path, year, project_slug)
    client = _load_client_profile(client_path, client_slug)
    reporting_period = _load_reporting_period(client_path, year)
    frameworks = _load_frameworks(client_path)

    from susr.brain.engine import BrainEngine

    engine = BrainEngine.open(
        str(client_path / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    try:
        chapters = _load_chapters(engine.conn)
        iros = _load_iros(engine.conn)
        kpis = _load_kpis(engine.conn)
        targets = _load_targets(engine.conn)
        matrix = _load_matrix_payload(client_path, resolved_project, year)
        matrix.core_topics = _load_core_topics(engine.conn)
        matrix.material_topics = _load_material_topics(engine.conn)
    finally:
        engine.close()

    gri_ref_path = (
        client_path / "projects" / resolved_project / f"gri-content-index-{year}.md"
    )
    gri_ref = str(gri_ref_path) if gri_ref_path.exists() else None

    invocation_hint = (
        f"請呼叫 document-skills:docx skill 建立 Report_{year}.docx。\n"
        f"輸出路徑：{client_path}/projects/{resolved_project}/output/"
        f"Report_{year}.docx\n"
        "Workflow：建立新檔 → docx-js（Node）。\n"
        f"章節結構：依本 payload chapters[] 與 phase6-docx-prompts.md §2 標準。\n"
        "樣式約束：表格 WidthType.DXA、條列 LevelFormat.BULLET（不要 unicode 圓點）；"
        "中文 Noto Sans TC、英文 Arial。\n"
        f"附錄 A GRI Content Index 來源：{gri_ref or '尚未產生 — 請先跑 Phase 7'}"
    )

    return DocxPayload(
        client=client,
        reporting_period=reporting_period,
        frameworks=frameworks,
        chapters=chapters,
        materiality_matrix=matrix,
        iros=iros,
        kpis_summary=kpis,
        targets_summary=targets,
        gri_content_index_ref=gri_ref,
        annex={"project_slug": resolved_project},
        invocation_hint=invocation_hint,
    )


# ---------------------------------------------------------------------------
# Tool 2: prepare_pdf_payload
# ---------------------------------------------------------------------------


def prepare_pdf_payload(
    client_slug: str, year: int, project_slug: Optional[str] = None,
) -> PdfPayload:
    """組裝最終 PDF payload（不渲染）。

    PDF 預設來源是 docx → PDF（LibreOffice headless），所以 payload 主體大量
    複用 docx 結構，但加：

    - ``print_layout``：A4 / Letter（預設 A4，台灣慣例）
    - ``language``：zh-TW（預設）
    - ``cover_design_hints``：封面排版提示（顧問 / brand 後續填）
    - ``ixbrl_concepts_preview``：brain 內 ``xbrl_concept`` 非空的 page list
      （CLAUDE.md §8 Q16 預留 — 2028 金管會 ISSB 強制後填值）

    對齊 ``references/phase6-pdf-prompts.md`` §3 + §4.1 + §6 iXBRL/ESEF 預留段落。
    """
    docx = prepare_docx_payload(client_slug, year, project_slug)

    client_path = find_client_workspace(client_slug)
    from susr.brain.engine import BrainEngine

    engine = BrainEngine.open(
        str(client_path / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    try:
        ixbrl_preview = _load_xbrl_preview(engine.conn)
    finally:
        engine.close()

    invocation_hint = (
        f"請呼叫 document-skills:pdf skill，將 Report_{year}.docx 轉為 PDF。\n"
        f"工具：LibreOffice headless（soffice --convert-to pdf）。\n"
        f"輸出路徑：{client_path}/projects/{docx.annex.get('project_slug', '')}/"
        f"output/Report_{year}.pdf\n"
        "關鍵約束：300 dpi、字型嵌入、章節書籤自動生成、元資料 4 欄填寫。\n"
        f"iXBRL preview：本 payload 含 {len(ixbrl_preview)} 個已標 xbrl_concept 的 "
        "page，作為 2028 金管會 ISSB 強制標記時的 anchor 預留（現階段不渲染）。"
    )

    return PdfPayload(
        client=docx.client,
        reporting_period=docx.reporting_period,
        frameworks=docx.frameworks,
        chapters=docx.chapters,
        materiality_matrix=docx.materiality_matrix,
        iros=docx.iros,
        kpis_summary=docx.kpis_summary,
        targets_summary=docx.targets_summary,
        gri_content_index_ref=docx.gri_content_index_ref,
        annex=docx.annex,
        print_layout="A4",
        language="zh-TW",
        cover_design_hints={
            "title_zh": f"{docx.client.legal_name} {year} 永續報告書",
            "title_en": f"Sustainability Report {year}",
            "subtitle_hint": "依 GRI / ISSB / 金管會編製",
        },
        ixbrl_concepts_preview=ixbrl_preview,
        invocation_hint=invocation_hint,
    )


# ---------------------------------------------------------------------------
# Tool 3: prepare_pptx_investor_deck
# ---------------------------------------------------------------------------


def _build_performance_chart_hints(kpis: list[KpiPayload]) -> list[str]:
    """根據 top KPI 生成投影片 chart hint 文字（給 caller 用 pptxgenjs 渲染）。"""
    hints: list[str] = []
    for kp in kpis:
        if kp.latest_value is None or kp.latest_year is None:
            hints.append(f"`{kp.slug}` ({kp.unit}) — 資料缺，請補 Phase 4 values_by_year")
            continue
        yoy_str = (
            f"，YoY {kp.yoy_change_pct:+.1f}%"
            if kp.yoy_change_pct is not None else ""
        )
        hints.append(
            f"`{kp.slug}` ({kp.name}) — {kp.latest_year} 值 {kp.latest_value} "
            f"{kp.unit}{yoy_str}"
        )
    return hints


def prepare_pptx_investor_deck(
    client_slug: str, year: int, project_slug: Optional[str] = None,
) -> PptxInvestorPayload:
    """組裝投資人版（10-15 頁）pptx deck payload（不渲染）。

    對齊 ``references/phase6-pptx-prompts.md`` §2「投資人版」+ §3「投資人版（13 頁範本）」
    + §5.1 prompt 範本。

    Highlights 抽取規則：

    - ``key_kpis``：top 5 KPI（``_select_top_kpis`` 排序 — 有 latest_value 優先）
    - ``core_topics``：brain 內 materiality_tier='核心' 的 topic slug
    - ``key_targets``：top 5 target（``_select_top_targets`` — quantitative 優先）
    - ``performance_chart_hints``：為每個 top KPI 產一行 chart 描述

    Embed_matrix_svg 從 ``projects/<project_slug>/materiality-<year>.svg`` 讀。
    """
    client_path = find_client_workspace(client_slug)
    resolved_project = _resolve_project_slug(client_path, year, project_slug)
    client = _load_client_profile(client_path, client_slug)
    reporting_period = _load_reporting_period(client_path, year)

    from susr.brain.engine import BrainEngine

    engine = BrainEngine.open(
        str(client_path / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    try:
        kpis = _load_kpis(engine.conn)
        targets = _load_targets(engine.conn)
        core_topics = _load_core_topics(engine.conn)
        matrix = _load_matrix_payload(client_path, resolved_project, year)
    finally:
        engine.close()

    top_kpis = _select_top_kpis(kpis)
    top_targets = _select_top_targets(targets)
    chart_hints = _build_performance_chart_hints(top_kpis)

    invocation_hint = (
        f"請呼叫 document-skills:pptx skill 建立投資人版簡報 Investor_Deck_{year}.pptx。\n"
        f"Workflow：從零建立 → pptxgenjs（Node）。\n"
        f"輸出路徑：{client_path}/projects/{resolved_project}/output/"
        f"Investor_Deck_{year}.pptx\n"
        f"頁數上限：{_INVESTOR_SLIDES_MAX}。\n"
        "結構：依 phase6-pptx-prompts.md §3 投資人版（13 頁範本）。\n"
        "設計約束：配色 ≤ 4 色、標題下不加裝飾線、每頁必有視覺元素、16:9。\n"
        "視覺 QA loop 強制：render → PDF → JPG → subagent 視覺檢查 → fix（≥1 輪）。"
    )

    return PptxInvestorPayload(
        client=client,
        reporting_period=reporting_period,
        highlights=InvestorHighlights(
            key_kpis=top_kpis,
            core_topics=core_topics,
            key_targets=top_targets,
            performance_chart_hints=chart_hints,
        ),
        embed_matrix_svg=matrix.embedded_svg,
        invocation_hint=invocation_hint,
    )


# ---------------------------------------------------------------------------
# Tool 4: prepare_pptx_board_deck
# ---------------------------------------------------------------------------


def _governance_summary_from_brain(conn: sqlite3.Connection) -> str:
    """從 brain entity_type='governance' 擷取一句重點摘要。"""
    rows = conn.execute(
        "SELECT slug, title FROM pages "
        "WHERE entity_type='governance' AND deleted_at IS NULL ORDER BY slug LIMIT 5"
    ).fetchall()
    if not rows:
        return "（brain 內尚無 governance entity — 請先建立董事會 / 永續委員會頁面）"
    parts = [f"`{slug}`（{title}）" for slug, title in rows]
    return "治理結構：" + "、".join(parts)


def prepare_pptx_board_deck(
    client_slug: str, year: int, project_slug: Optional[str] = None,
) -> PptxBoardPayload:
    """組裝董事會版（5-8 頁）pptx deck payload（不渲染）。

    對齊 ``references/phase6-pptx-prompts.md`` §2「董事會版」+ §3「董事會版（7 頁範本）」
    + §5.2 prompt 範本。

    Highlights 規則：

    - ``governance_summary``：從 brain governance entity slug 拼一句
    - ``material_risks``：所有 IRO type='Risk'
    - ``material_opportunities``：所有 IRO type='Opportunity'
    - ``key_decisions_needed``：列出董事會需核准事項（placeholder — caller 補）
    - ``regulatory_compliance_status``：靜態文字「待 Phase 7 gap-analysis 回填」
    """
    client_path = find_client_workspace(client_slug)
    resolved_project = _resolve_project_slug(client_path, year, project_slug)
    client = _load_client_profile(client_path, client_slug)
    reporting_period = _load_reporting_period(client_path, year)

    from susr.brain.engine import BrainEngine

    engine = BrainEngine.open(
        str(client_path / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    try:
        iros = _load_iros(engine.conn)
        governance_summary = _governance_summary_from_brain(engine.conn)
    finally:
        engine.close()

    risks = _filter_iros_by_type(iros, "Risk")
    opportunities = _filter_iros_by_type(iros, "Opportunity")

    # placeholder — Phase 7 gap-analysis-<year>.md 可補
    gap_path = (
        client_path / "projects" / resolved_project / f"gap-analysis-{year}.md"
    )
    compliance_status = (
        f"請參考 {gap_path}（已產出）" if gap_path.exists()
        else "尚未產生 gap-analysis — 請先跑 Phase 7 run_full_gap_analysis"
    )

    invocation_hint = (
        f"請呼叫 document-skills:pptx skill 建立董事會版簡報 Board_Deck_{year}.pptx。\n"
        "Workflow：建議從 Investor_Deck 編輯精簡（unpack → 大量刪除 + 重組 → pack）。\n"
        f"輸出路徑：{client_path}/projects/{resolved_project}/output/"
        f"Board_Deck_{year}.pptx\n"
        f"頁數上限：{_BOARD_SLIDES_MAX}。\n"
        "結構：依 phase6-pptx-prompts.md §3 董事會版（7 頁範本）。\n"
        "語氣調整：投資語言 →「治理語言」（風險暴露 → 待決策點）。\n"
        "視覺 QA loop 強制：render → PDF → JPG → subagent 視覺檢查 → fix（≥1 輪）。"
    )

    return PptxBoardPayload(
        client=client,
        reporting_period=reporting_period,
        highlights=BoardHighlights(
            governance_summary=governance_summary,
            material_risks=risks,
            material_opportunities=opportunities,
            key_decisions_needed=[
                "核准本年度永續報告書草稿",
                "核准下年度永續預算與資源配置",
            ],
            regulatory_compliance_status=compliance_status,
        ),
        invocation_hint=invocation_hint,
    )


# ---------------------------------------------------------------------------
# Server registration
# ---------------------------------------------------------------------------


def register(server) -> None:  # noqa: ANN001
    """Bind all 4 Phase 6 payload-prep tools to a FastMCP server instance."""
    server.tool()(prepare_docx_payload)
    server.tool()(prepare_pdf_payload)
    server.tool()(prepare_pptx_investor_deck)
    server.tool()(prepare_pptx_board_deck)


__all__ = [
    "ChapterPayload", "IroPayload", "KpiPayload", "TargetPayload",
    "MaterialityMatrixPayload", "ClientProfilePayload",
    "DocxPayload", "PdfPayload",
    "InvestorHighlights", "PptxInvestorPayload",
    "BoardHighlights", "PptxBoardPayload",
    "prepare_docx_payload", "prepare_pdf_payload",
    "prepare_pptx_investor_deck", "prepare_pptx_board_deck",
    "register",
]
