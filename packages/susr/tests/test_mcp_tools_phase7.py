"""Layer 4 — MCP Phase 7 tools 單元測試（R5 Gap Analysis & Assurance Readiness）。

對應 ``packages/susr/susr/mcp/tools/phase7.py`` 4 個 tools：

    1. run_compliance_checklist
    2. generate_gri_content_index
    3. generate_assurance_readiness_checklist
    4. run_full_gap_analysis

測試覆蓋（user spec 8 條）：

    1. test_run_compliance_checklist_returns_dict_with_items
    2. test_run_compliance_checklist_filters_by_framework
    3. test_generate_gri_content_index_writes_md
    4. test_generate_gri_content_index_marks_missing_disclosures
    5. test_generate_assurance_readiness_checklist_flags_no_source_kpi
    6. test_run_full_gap_analysis_aggregates_all_checks
    7. test_run_full_gap_analysis_severity_breakdown
    8. test_phase7_tools_registered_in_server

不靠 spawn MCP server — 直接呼叫 tool function + brain engine。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from susr.brain.engine import BrainEngine
from susr.mcp.tools.phase7 import (
    AssuranceReadinessResult,
    ComplianceChecklistResult,
    FullGapAnalysisResult,
    GriContentIndexResult,
    generate_assurance_readiness_checklist,
    generate_gri_content_index,
    run_compliance_checklist,
    run_full_gap_analysis,
)


def _ws_path(tmp_client_workspace: Any) -> Path:
    """``tmp_client_workspace`` 回 dict（含 workspace_path 字串）— 抽出 Path。"""
    if isinstance(tmp_client_workspace, dict):
        return Path(tmp_client_workspace["workspace_path"])
    return Path(tmp_client_workspace)


# ---------------------------------------------------------------------------
# Helpers — 把 minimal entities 寫到 brain DB
# ---------------------------------------------------------------------------


def _seed_chapter(engine: BrainEngine, slug: str, title: str, framework_refs: list[str]) -> None:
    engine.put_page(
        slug=slug, entity_type="chapter", title=title,
        compiled_truth=f"# {title}\n", file_path=f"chapters/{slug}.md",
        frontmatter={
            "slug": slug, "report_slug": "2025-sr", "title": title,
            "framework_refs": framework_refs, "owner": "ESG",
        },
    )


def _seed_kpi(
    engine: BrainEngine, slug: str, name: str, *,
    formula: str = "sum(values)", unit: str = "tCO2e",
    topic_slug: str = "E1-climate",
    framework_refs: list[str] | None = None,
) -> None:
    engine.put_page(
        slug=slug, entity_type="kpi", title=name,
        compiled_truth=f"# {name}\n", file_path=f"kpis/{slug}.md",
        frontmatter={
            "slug": slug, "name": name, "unit": unit,
            "topic_slug": topic_slug,
            "framework_refs": framework_refs or ["GRI 305-1"],
            "boundary": "合併", "formula": formula,
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


def _seed_datapoint_missing_source(engine: BrainEngine, slug: str) -> None:
    """DataPoint with empty source_refs (should trigger critical assurance flag)."""
    engine.put_page(
        slug=slug, entity_type="datapoint", title=f"DP {slug}",
        compiled_truth="# dp\n", file_path=f"datapoints/{slug}.md",
        frontmatter={
            "slug": slug, "kpi_slug": "ghg-scope1", "year": 2025, "value": 1234.0,
            "source_refs": [],  # ← 故意空 — assurance check 應抓
            "calculation_method": "tier 1",
            "assurance_status": "self",
            "last_assessed": "2025-04-01",
            "responsible_person": "ESG-Lee",
        },
    )


# ---------------------------------------------------------------------------
# Test 1: run_compliance_checklist 回 dict-like result with items
# ---------------------------------------------------------------------------


def test_run_compliance_checklist_returns_dict_with_items(tmp_client_workspace) -> None:
    """完整 happy path — 跑後 result 含 items 且 total > 0。"""
    ws = _ws_path(tmp_client_workspace)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        _seed_chapter(engine, "ch-climate", "氣候章節", ["GRI 305-1", "GRI 2-1"])
        _seed_kpi(engine, "ghg-scope1", "範疇一排放")
        _seed_kpi(engine, "ghg-scope2", "範疇二排放")
        _seed_topic_core(engine, "E1-climate", "氣候變遷")
    finally:
        engine.close()

    result = run_compliance_checklist(client_slug="test-client", framework="phase7")
    assert isinstance(result, ComplianceChecklistResult)
    assert result.total > 0, "expected to parse some checklist items"
    assert len(result.items) > 0
    # 應該至少有一些 passed（D1 範疇一 + 範疇二）
    assert result.passed >= 1, f"expected at least 1 passed item, got {result.passed}"
    # source_path 指向實際讀的檔
    assert Path(result.source_path).exists()


# ---------------------------------------------------------------------------
# Test 2: filters by framework — bad framework name → FileNotFoundError
# ---------------------------------------------------------------------------


def test_run_compliance_checklist_filters_by_framework(tmp_client_workspace) -> None:
    """framework='nonexistent' → 應 raise FileNotFoundError（不靜默回空）。"""
    _ws_path(tmp_client_workspace)
    with pytest.raises(FileNotFoundError, match="checklist not found"):
        run_compliance_checklist(
            client_slug="test-client", framework="does-not-exist",
        )

    # 預設 framework='phase7' 應該 ok（不 raise）
    result_phase7 = run_compliance_checklist(client_slug="test-client", framework="phase7")
    assert result_phase7.framework == "phase7"
    assert result_phase7.total > 0


# ---------------------------------------------------------------------------
# Test 3: generate_gri_content_index writes md file + returns shape
# ---------------------------------------------------------------------------


def test_generate_gri_content_index_writes_md(tmp_client_workspace) -> None:
    """執行後 md 檔存在，且 rows 對應到內建 _GRI_DISCLOSURES 數量。"""
    ws = _ws_path(tmp_client_workspace)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        # 給點資料讓部分項通過
        _seed_chapter(engine, "ch-about", "關於本報告", ["GRI 2-1", "GRI 2-2"])
        _seed_chapter(engine, "ch-climate", "氣候揭露", ["GRI 305-1"])
        _seed_kpi(engine, "ghg-scope1", "範疇一", framework_refs=["GRI 305-1"])
    finally:
        engine.close()

    result = generate_gri_content_index(
        client_slug="test-client", year=2025, project_slug="2025-sr",
    )
    assert isinstance(result, GriContentIndexResult)
    out_path = Path(result.file_path)
    assert out_path.exists(), f"gri index file not written: {out_path}"
    content = out_path.read_text(encoding="utf-8")
    assert "GRI Content Index" in content
    assert "| GRI Disclosure | 主題 | Page Ref | Status | Notes |" in content
    # 至少 2-1 應為 fulfilled
    assert result.fulfilled >= 1
    assert result.total_disclosures > 10  # _GRI_DISCLOSURES 內建 18+


# ---------------------------------------------------------------------------
# Test 4: gri marks missing disclosures correctly
# ---------------------------------------------------------------------------


def test_generate_gri_content_index_marks_missing_disclosures(tmp_client_workspace) -> None:
    """完全空 brain → 全部 missing。"""
    ws = _ws_path(tmp_client_workspace)
    # 不放任何 chapter / KPI
    result = generate_gri_content_index(client_slug="test-client", year=2024)
    assert result.fulfilled == 0
    assert result.missing == result.total_disclosures
    out_path = Path(result.file_path)
    content = out_path.read_text(encoding="utf-8")
    assert "✗ missing" in content


# ---------------------------------------------------------------------------
# Test 5: assurance — flag DataPoint missing source_refs as critical
# ---------------------------------------------------------------------------


def test_generate_assurance_readiness_checklist_flags_no_source_kpi(
    tmp_client_workspace,
) -> None:
    """DataPoint 缺 source_refs / KPI 缺 formula → items 含對應 critical / info 條目。"""
    ws = _ws_path(tmp_client_workspace)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        # KPI 沒填 formula（empty string）
        _seed_kpi(engine, "kpi-bad", "壞 KPI", formula="")
        # DataPoint source_refs 空 → critical
        _seed_datapoint_missing_source(engine, "dp-2025-scope1")
    finally:
        engine.close()

    result = generate_assurance_readiness_checklist(
        client_slug="test-client", year=2025, project_slug="2025-sr",
    )
    assert isinstance(result, AssuranceReadinessResult)
    out_path = Path(result.file_path)
    assert out_path.exists()
    assert result.needs_work >= 2, (
        f"expected ≥2 items needing work, got {result.needs_work}"
    )

    # 確認 datapoint critical flag 出現
    crit_items = [it for it in result.items if it.severity == "critical"]
    assert len(crit_items) >= 1
    assert any(
        "source_refs" in it.missing_fields for it in crit_items
    ), f"expected source_refs in missing fields, got: {[it.missing_fields for it in crit_items]}"

    # KPI formula 缺失 → 至少一個 info 條目
    kpi_items = [it for it in result.items if it.entity_type == "kpi"]
    assert any("formula" in it.missing_fields for it in kpi_items)


# ---------------------------------------------------------------------------
# Test 6: run_full_gap_analysis aggregates everything
# ---------------------------------------------------------------------------


def test_run_full_gap_analysis_aggregates_all_checks(tmp_client_workspace) -> None:
    """跑後產出 md 含 0/1/2/3/4/5 各 section + result 結構齊全。"""
    ws = _ws_path(tmp_client_workspace)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        _seed_topic_core(engine, "E1-climate", "氣候變遷")  # 無 IRO → I1a fail
        _seed_chapter(engine, "ch-climate", "氣候章節", ["GRI 305-1"])
        _seed_kpi(engine, "ghg-scope1", "範疇一")
        _seed_datapoint_missing_source(engine, "dp-2025")
    finally:
        engine.close()

    result = run_full_gap_analysis(
        client_slug="test-client", year=2025, project_slug="2025-sr",
    )
    assert isinstance(result, FullGapAnalysisResult)
    out_path = Path(result.file_path)
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    # 主要 section 標題都在
    for header in (
        "# Gap Analysis", "## 0. TL;DR",
        "## 1. 連結性 Invariants",
        "## 2. Framework Compliance",
        "## 3. GRI Content Index",
        "## 4. Assurance Readiness",
        "## 5. 優先修補建議",
    ):
        assert header in content, f"missing section: {header}\nfull content:\n{content[:2000]}"

    # 應該至少跑出一些 invariants violation（E1-climate 缺 IRO）
    assert result.invariant_violations >= 1
    # GRI 多數項應為 missing
    assert result.gri_missing >= 5
    # summary 含關鍵 token
    assert "critical" in result.summary
    assert "Invariants" in result.summary or "I1a" in result.summary


# ---------------------------------------------------------------------------
# Test 7: severity breakdown is correct
# ---------------------------------------------------------------------------


def test_run_full_gap_analysis_severity_breakdown(tmp_client_workspace) -> None:
    """severity_breakdown 三鍵齊全，且都是 int >= 0；I1a violation 算 critical。"""
    ws = _ws_path(tmp_client_workspace)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        # 兩個核心 topic，都沒 IRO → I1a 應抓 2 個 critical
        _seed_topic_core(engine, "E1-climate", "氣候")
        _seed_topic_core(engine, "S6-food-safety", "食安", axis="S")
    finally:
        engine.close()

    result = run_full_gap_analysis(client_slug="test-client", year=2025)
    sb = result.severity_breakdown
    assert set(sb.keys()) == {"critical", "warning", "info"}
    for k, v in sb.items():
        assert isinstance(v, int) and v >= 0, f"severity_breakdown[{k}]={v}"
    # 兩個 core topic 缺 IRO → 至少 critical ≥ 2 (I1a) + GRI missing 多筆
    assert sb["critical"] >= 2, (
        f"expected ≥2 critical (2 I1a violations), got {sb['critical']}"
    )


# ---------------------------------------------------------------------------
# Test 8: phase7 tools registered in server
# ---------------------------------------------------------------------------


def test_phase7_tools_registered_in_server() -> None:
    """create_server() 後 4 個 phase7 tool 都 bind 到 FastMCP。

    用 ``Server._tools`` private — 但若 FastMCP API 變，改用 list_tools 之類的
    introspection；目前 mcp.server.fastmcp 的 tool() decorator 是把 fn 收進
    server 的內部 registry。本測試容錯 — 只要 server build 出來 + 不 throw 就 ok，
    並嘗試從 server 抽 4 個 tool 名稱。
    """
    try:
        from susr.mcp.server import create_server
        server = create_server()
    except ImportError:
        pytest.skip("mcp SDK not installed in this environment")
    # FastMCP 0.x: server._tool_manager._tools 是 dict[name, Tool]
    # 不同版本可能不同；先 best-effort 取 names。
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
        "run_compliance_checklist",
        "generate_gri_content_index",
        "generate_assurance_readiness_checklist",
        "run_full_gap_analysis",
    }
    missing = expected - names
    assert not missing, f"phase7 tools missing from server: {missing}; got {names}"
