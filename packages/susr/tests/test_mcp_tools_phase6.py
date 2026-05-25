"""Layer 4 — MCP Phase 6 tools 單元測試（document-skills payload prep）。

對應 ``packages/susr/susr/mcp/tools/phase6.py`` 4 個 tools：

    1. prepare_docx_payload
    2. prepare_pdf_payload
    3. prepare_pptx_investor_deck
    4. prepare_pptx_board_deck

測試覆蓋（user spec 7 條，至少 6 個必須）：

    1. test_prepare_docx_payload_returns_required_fields
    2. test_prepare_docx_payload_includes_chapters_from_brain
    3. test_prepare_docx_payload_embeds_materiality_matrix
    4. test_prepare_pdf_payload_includes_ixbrl_preview
    5. test_prepare_pptx_investor_deck_slides_max_15
    6. test_prepare_pptx_board_deck_includes_iro_risks_and_opportunities
    7. test_phase6_tools_registered_in_server (skip if mcp SDK missing)

susr Phase 6 v0.1 **不渲染** docx/pdf/pptx — 只 prep payload。所以這些測試
不檢查 file output 存在；只檢查 payload dict / Pydantic 模型結構正確。

不靠 spawn MCP server — 直接呼叫 tool function + brain engine。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from susr.brain.engine import BrainEngine
from susr.mcp.tools.phase6 import (
    BoardHighlights,
    DocxPayload,
    InvestorHighlights,
    PdfPayload,
    PptxBoardPayload,
    PptxInvestorPayload,
    prepare_docx_payload,
    prepare_pdf_payload,
    prepare_pptx_board_deck,
    prepare_pptx_investor_deck,
)


# ---------------------------------------------------------------------------
# Helpers — minimal brain seeding（與 phase7 test 風格一致）
# ---------------------------------------------------------------------------


def _ws_path(tmp_client_workspace: Any) -> Path:
    """``tmp_client_workspace`` 回 dict（含 workspace_path 字串）— 抽出 Path。"""
    if isinstance(tmp_client_workspace, dict):
        return Path(tmp_client_workspace["workspace_path"])
    return Path(tmp_client_workspace)


def _seed_chapter(
    engine: BrainEngine, slug: str, title: str,
    framework_refs: list[str], body: str = "",
) -> None:
    engine.put_page(
        slug=slug, entity_type="chapter", title=title,
        compiled_truth=body or f"# {title}\n\n章節內容...\n",
        file_path=f"chapters/{slug}.md",
        frontmatter={
            "slug": slug, "report_slug": "2025-sr", "title": title,
            "framework_refs": framework_refs, "owner": "ESG",
        },
    )


def _seed_topic_core(engine: BrainEngine, slug: str, name: str, axis: str = "E") -> None:
    engine.put_page(
        slug=slug, entity_type="topic", title=name,
        compiled_truth=f"# {name}\n", file_path=f"topics/{slug}.md",
        frontmatter={
            "slug": slug, "name": name, "axis": axis,
            "impact_score": 4.5, "financial_score": 4.0,
            "materiality_tier": "核心",
        },
    )


def _seed_iro(
    engine: BrainEngine, slug: str, topic_slug: str, iro_type: str, name: str,
    category: str = "operational", time_horizon: str = "M",
    financial_magnitude: float = 3.5,
) -> None:
    engine.put_page(
        slug=slug, entity_type="iro", title=f"{iro_type}: {name}",
        compiled_truth=f"# {iro_type}: {name}\n", file_path=f"iros/{slug}.md",
        frontmatter={
            "slug": slug, "topic_slug": topic_slug, "type": iro_type,
            "category": category, "time_horizon": time_horizon,
            "financial_magnitude": financial_magnitude, "iro_name": name,
        },
    )


def _seed_kpi(
    engine: BrainEngine, slug: str, name: str, *,
    unit: str = "tCO2e", topic_slug: str = "E1-climate",
    framework_refs: list[str] | None = None,
    values_by_year: list[dict] | None = None,
    xbrl_concept: str | None = None,
) -> None:
    engine.put_page(
        slug=slug, entity_type="kpi", title=name,
        compiled_truth=f"# {name}\n", file_path=f"kpis/{slug}.md",
        frontmatter={
            "slug": slug, "name": name, "unit": unit,
            "topic_slug": topic_slug,
            "framework_refs": framework_refs or ["GRI 305-1"],
            "boundary": "合併", "formula": "sum(values)",
            "values_by_year": values_by_year or [],
        },
        xbrl_concept=xbrl_concept,
    )


def _seed_target(
    engine: BrainEngine, slug: str, kpi_slug: str,
    baseline_year: int = 2023, baseline_value: float = 1000.0,
    target_value: float = 750.0, target_year: int = 2030,
) -> None:
    engine.put_page(
        slug=slug, entity_type="target", title=f"Target: {slug}",
        compiled_truth="# target\n", file_path=f"targets/{slug}.md",
        frontmatter={
            "slug": slug, "kpi_slug": kpi_slug,
            "baseline_year": baseline_year, "baseline_value": baseline_value,
            "target_value": target_value, "target_year": target_year,
            "verification_path": "第三方有限確信",
        },
    )


def _seed_governance(engine: BrainEngine, slug: str, body: str = "董事會") -> None:
    engine.put_page(
        slug=slug, entity_type="governance", title=f"治理: {body}",
        compiled_truth=f"# {body}\n", file_path=f"governance/{slug}.md",
        frontmatter={
            "slug": slug, "body": body,
            "oversight_topics": ["E1-climate"],
            "meeting_frequency": "quarterly",
            "kpi_linkage": ["ghg-scope1"],
        },
    )


def _write_materiality_svg(ws_path: Path, year: int) -> Path:
    """寫一個假 SVG 到 projects/<year>-sustainability-report/materiality-<year>.svg。"""
    project_dir = ws_path / "projects" / f"{year}-sustainability-report"
    project_dir.mkdir(parents=True, exist_ok=True)
    svg_path = project_dir / f"materiality-{year}.svg"
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="540" height="540">'
        '<rect width="100%" height="100%" fill="#ffeaea"/></svg>',
        encoding="utf-8",
    )
    return svg_path


# ---------------------------------------------------------------------------
# Test 1: docx payload returns all required top-level fields
# ---------------------------------------------------------------------------


def test_prepare_docx_payload_returns_required_fields(tmp_client_workspace) -> None:
    """payload 應含 document_type / client / chapters / iros / kpis / targets /
    materiality_matrix / frameworks / reporting_period / invocation_hint。"""
    ws = _ws_path(tmp_client_workspace)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        _seed_chapter(engine, "ch-about", "關於本報告", ["GRI 2-1"])
    finally:
        engine.close()

    payload = prepare_docx_payload(
        client_slug="test-client", year=2025, project_slug="2025-sustainability-report",
    )
    assert isinstance(payload, DocxPayload)
    assert payload.document_type == "sustainability_report"
    # 對齊 references/phase6-docx-prompts.md 內 docx skill 期望
    assert payload.client.slug == "test-client"
    assert payload.client.legal_name  # _client.md 內 legal_name 應抽出
    assert isinstance(payload.frameworks, list) and len(payload.frameworks) >= 1
    assert isinstance(payload.chapters, list)
    assert isinstance(payload.iros, list)
    assert isinstance(payload.kpis_summary, list)
    assert isinstance(payload.targets_summary, list)
    assert payload.materiality_matrix is not None
    assert payload.reporting_period  # 非空
    assert payload.invocation_hint  # caller 用的 prompt 雛形
    assert "document-skills:docx" in payload.invocation_hint


# ---------------------------------------------------------------------------
# Test 2: docx payload includes chapters from brain
# ---------------------------------------------------------------------------


def test_prepare_docx_payload_includes_chapters_from_brain(tmp_client_workspace) -> None:
    """seed 3 個 chapter；payload.chapters 應全部包含。"""
    ws = _ws_path(tmp_client_workspace)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        _seed_chapter(
            engine, "ch-about", "關於本報告", ["GRI 2-1"],
            body="# 關於本報告\n\n本公司 2025 年度...\n",
        )
        _seed_chapter(
            engine, "ch-governance", "公司治理", ["GRI 2-9", "GRI 2-12"],
            body="# 公司治理\n\n董事會...\n",
        )
        _seed_chapter(
            engine, "ch-climate", "氣候揭露", ["GRI 305-1", "ISSB S2"],
            body="# 氣候揭露\n\nTCFD 四構面...\n",
        )
    finally:
        engine.close()

    payload = prepare_docx_payload(
        client_slug="test-client", year=2025, project_slug="2025-sustainability-report",
    )
    slugs = [c.slug for c in payload.chapters]
    assert {"ch-about", "ch-governance", "ch-climate"}.issubset(set(slugs))
    # content_md 從 brain.compiled_truth 帶回
    climate_ch = next(c for c in payload.chapters if c.slug == "ch-climate")
    assert "TCFD" in climate_ch.content_md
    # framework_refs 也帶過來
    assert "GRI 305-1" in climate_ch.framework_refs
    # order 為正整數
    assert all(c.order > 0 for c in payload.chapters)


# ---------------------------------------------------------------------------
# Test 3: docx payload embeds materiality matrix SVG
# ---------------------------------------------------------------------------


def test_prepare_docx_payload_embeds_materiality_matrix(tmp_client_workspace) -> None:
    """seed 核心 topic + 寫一個假 materiality SVG；payload.materiality_matrix 應抓到。"""
    ws = _ws_path(tmp_client_workspace)
    _write_materiality_svg(ws, 2025)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        _seed_topic_core(engine, "E1-climate", "氣候變遷")
        _seed_topic_core(engine, "S6-food-safety", "食品安全", axis="S")
    finally:
        engine.close()

    payload = prepare_docx_payload(
        client_slug="test-client", year=2025, project_slug="2025-sustainability-report",
    )
    matrix = payload.materiality_matrix
    assert matrix.embedded_svg, "expected svg embed string non-empty"
    assert "<svg" in matrix.embedded_svg
    # core_topics 應從 brain 抓到
    assert set(matrix.core_topics) >= {"E1-climate", "S6-food-safety"}


# ---------------------------------------------------------------------------
# Test 4: pdf payload includes iXBRL preview list (Q16 預留)
# ---------------------------------------------------------------------------


def test_prepare_pdf_payload_includes_ixbrl_preview(tmp_client_workspace) -> None:
    """seed KPI with xbrl_concept；pdf payload.ixbrl_concepts_preview 應抓到。"""
    ws = _ws_path(tmp_client_workspace)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        # 一個有 xbrl_concept，一個沒有 — preview 只應抓到前者
        _seed_kpi(
            engine, "ghg-scope1", "範疇一",
            xbrl_concept="ifrs-issb:GreenhouseGasEmissionsScope1",
        )
        _seed_kpi(engine, "ghg-scope2", "範疇二", xbrl_concept=None)
    finally:
        engine.close()

    payload = prepare_pdf_payload(
        client_slug="test-client", year=2025, project_slug="2025-sustainability-report",
    )
    assert isinstance(payload, PdfPayload)
    assert payload.document_type == "sustainability_report_pdf"
    assert payload.print_layout == "A4"
    assert payload.language == "zh-TW"
    assert isinstance(payload.ixbrl_concepts_preview, list)
    # 應該至少抓到 ghg-scope1
    concepts = [item["page_slug"] for item in payload.ixbrl_concepts_preview]
    assert "ghg-scope1" in concepts, (
        f"expected ghg-scope1 in ixbrl preview; got: {concepts}"
    )
    # ghg-scope2 不應在裡面（沒設 xbrl_concept）
    assert "ghg-scope2" not in concepts
    # 確認 cover hints 有填
    assert payload.cover_design_hints.get("title_zh"), "cover_design_hints.title_zh 應填入"


# ---------------------------------------------------------------------------
# Test 5: investor deck slides_max == 15 + highlights structure
# ---------------------------------------------------------------------------


def test_prepare_pptx_investor_deck_slides_max_15(tmp_client_workspace) -> None:
    """投資人 deck 上限 15 頁；highlights 結構齊全；top KPI 不超過 5。"""
    ws = _ws_path(tmp_client_workspace)
    _write_materiality_svg(ws, 2025)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        _seed_topic_core(engine, "E1-climate", "氣候")
        # 8 個 KPI 確認 top-K cap 有作用
        for i in range(1, 9):
            _seed_kpi(
                engine, f"kpi-{i:02d}", f"KPI #{i}",
                values_by_year=[
                    {"year": 2023, "value": 100.0 * i},
                    {"year": 2024, "value": 95.0 * i},
                ],
            )
        _seed_target(engine, "tg-2030", "kpi-01")
    finally:
        engine.close()

    payload = prepare_pptx_investor_deck(
        client_slug="test-client", year=2025, project_slug="2025-sustainability-report",
    )
    assert isinstance(payload, PptxInvestorPayload)
    assert payload.deck_type == "investor"
    assert payload.slides_max == 15
    assert isinstance(payload.highlights, InvestorHighlights)
    # top KPI ≤ 5（_DECK_TOP_KPIS）
    assert len(payload.highlights.key_kpis) <= 5
    # core_topics 抓到
    assert "E1-climate" in payload.highlights.core_topics
    # chart hints 也產生了
    assert isinstance(payload.highlights.performance_chart_hints, list)
    assert len(payload.highlights.performance_chart_hints) == len(payload.highlights.key_kpis)
    # matrix svg embed 抓到
    assert "<svg" in payload.embed_matrix_svg
    # tone 文字符合投資人視角
    assert "投資人" in payload.tone


# ---------------------------------------------------------------------------
# Test 6: board deck includes risks + opportunities from IRO
# ---------------------------------------------------------------------------


def test_prepare_pptx_board_deck_includes_iro_risks_and_opportunities(
    tmp_client_workspace,
) -> None:
    """seed Risk + Opportunity IRO；board deck highlights 分別抽到。"""
    ws = _ws_path(tmp_client_workspace)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        _seed_topic_core(engine, "E1-climate", "氣候")
        _seed_iro(
            engine, "iro-carbon-fee", "E1-climate", "Risk", "碳費徵收",
            category="transition", time_horizon="S", financial_magnitude=4.0,
        )
        _seed_iro(
            engine, "iro-extreme-weather", "E1-climate", "Risk", "極端氣候",
            category="physical", time_horizon="M", financial_magnitude=3.5,
        )
        _seed_iro(
            engine, "iro-sustain-premium", "E1-climate", "Opportunity", "永續溢價",
            category="market", time_horizon="M", financial_magnitude=3.0,
        )
        _seed_governance(engine, "board", "董事會")
        _seed_governance(engine, "sustainability-committee", "永續委員會")
    finally:
        engine.close()

    payload = prepare_pptx_board_deck(
        client_slug="test-client", year=2025, project_slug="2025-sustainability-report",
    )
    assert isinstance(payload, PptxBoardPayload)
    assert payload.deck_type == "board"
    assert payload.slides_max == 8
    assert isinstance(payload.highlights, BoardHighlights)
    # Risks 應抓到 2 個
    risk_slugs = [r.iro_slug for r in payload.highlights.material_risks]
    assert "iro-carbon-fee" in risk_slugs
    assert "iro-extreme-weather" in risk_slugs
    # Opportunities 應抓到 1 個
    opp_slugs = [o.iro_slug for o in payload.highlights.material_opportunities]
    assert "iro-sustain-premium" in opp_slugs
    # 治理摘要應提及董事會
    assert "board" in payload.highlights.governance_summary or "董事會" in payload.highlights.governance_summary
    # 決策需求預填
    assert len(payload.highlights.key_decisions_needed) >= 1
    # tone 為治理語言
    assert "董事會" in payload.tone or "治理" in payload.tone


# ---------------------------------------------------------------------------
# Test 7: phase6 tools registered in server (skip if mcp SDK missing)
# ---------------------------------------------------------------------------


def test_phase6_tools_registered_in_server() -> None:
    """create_server() 後 4 個 phase6 tool 都 bind 到 FastMCP。

    與 phase7 test 同模式 — 若 mcp SDK 未裝直接 skip。
    """
    try:
        from susr.mcp.server import create_server
        server = create_server()
    except ImportError:
        pytest.skip("mcp SDK not installed in this environment")

    names: set[str] = set()
    for attr_path in (
        ("_tool_manager", "_tools"),
        ("_tools",),
    ):
        obj: Any = server
        try:
            for a in attr_path:
                obj = getattr(obj, a)
            if isinstance(obj, dict):
                names = set(obj.keys())
                break
        except AttributeError:
            continue

    if not names:
        pytest.skip("FastMCP internal registry不可內省 — 跳過此 layer 4 introspection")

    expected = {
        "prepare_docx_payload",
        "prepare_pdf_payload",
        "prepare_pptx_investor_deck",
        "prepare_pptx_board_deck",
    }
    missing = expected - names
    assert not missing, f"phase6 tools missing from server: {missing}; got {names}"
