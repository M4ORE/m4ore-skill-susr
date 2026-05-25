"""Layer 4 — MCP KPI ranking tool 單元測試（R6+ Agent C 新模組）。

對應 ``packages/susr/susr/mcp/tools/kpi.py``：``list_top_kpis`` 單一 tool。

測試覆蓋（10 個）：
    1. test_returns_required_fields                — payload 結構正確
    2. test_orders_by_priority_ascending            — priority 升冪
    3. test_priority_defaults_to_100                — 不帶 priority 欄位的 KPI fallback 100
    4. test_tiebreak_by_yoy_delta_desc              — priority 並列時看 YoY abs delta
    5. test_tiebreak_by_slug_when_no_yoy            — 兩條都並列時看 slug
    6. test_limit_clamps_to_max_200_and_min_1       — limit 邊界保護
    7. test_filters_by_topic_slug                   — topic_slug 過濾
    8. test_empty_workspace_returns_empty           — 沒 KPI 時回空 list
    9. test_sort_by_yoy_delta_brings_volatile_first — sort='yoy_delta'
    10. test_rank_field_is_one_based                — items[i].rank = i+1

不靠 spawn MCP server — 直接呼叫 tool function + brain engine。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from susr.brain.engine import BrainEngine
from susr.mcp.tools.kpi import (
    KpiRankingItem,
    KpiRankingResult,
    list_top_kpis,
)


def _ws_path(tmp_client_workspace: Any) -> Path:
    if isinstance(tmp_client_workspace, dict):
        return Path(tmp_client_workspace["workspace_path"])
    return Path(tmp_client_workspace)


# ---------------------------------------------------------------------------
# Helpers — seed brain with KPI pages
# ---------------------------------------------------------------------------


def _seed_kpi(
    engine: BrainEngine,
    slug: str,
    name: str,
    *,
    priority: int | None = None,
    topic_slug: str = "E1-climate",
    unit: str = "tCO2e",
    framework_refs: list[str] | None = None,
    values_by_year: list[dict] | None = None,
) -> None:
    """寫一筆 minimal KPI page；priority=None → 不帶該欄位（測 fallback 100）。"""
    fm: dict[str, Any] = {
        "slug": slug,
        "name": name,
        "unit": unit,
        "topic_slug": topic_slug,
        "framework_refs": framework_refs or ["GRI 305-1"],
        "boundary": "合併",
        "formula": "sum(values)",
        "values_by_year": values_by_year or [],
    }
    if priority is not None:
        fm["priority"] = priority
    engine.put_page(
        slug=slug,
        entity_type="kpi",
        title=name,
        compiled_truth=f"# {name}\n",
        file_path=f"kpis/{slug}.md",
        frontmatter=fm,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_required_fields(tmp_client_workspace) -> None:
    """payload 結構應含 items + total_scanned + limit + sort + filters。"""
    ws = _ws_path(tmp_client_workspace)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        _seed_kpi(engine, "k-a", "KPI A", priority=10)
    finally:
        engine.close()

    res = list_top_kpis(client_slug="test-client", limit=5)
    assert isinstance(res, KpiRankingResult)
    assert isinstance(res.items, list) and len(res.items) == 1
    item = res.items[0]
    assert isinstance(item, KpiRankingItem)
    assert item.slug == "k-a"
    assert item.priority == 10
    assert item.rank == 1
    assert res.total_scanned == 1
    assert res.limit == 5
    assert res.sort == "priority"


def test_orders_by_priority_ascending(tmp_client_workspace) -> None:
    """priority lower → 前面。"""
    ws = _ws_path(tmp_client_workspace)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        _seed_kpi(engine, "k-default", "Default", priority=100)
        _seed_kpi(engine, "k-critical", "Critical", priority=10)
        _seed_kpi(engine, "k-mid", "Mid", priority=30)
    finally:
        engine.close()

    res = list_top_kpis(client_slug="test-client", limit=10)
    slugs = [it.slug for it in res.items]
    assert slugs == ["k-critical", "k-mid", "k-default"]
    assert [it.priority for it in res.items] == [10, 30, 100]


def test_priority_defaults_to_100(tmp_client_workspace) -> None:
    """KPI 未帶 priority 欄位時，回傳 priority 應為 100（schema 預設）。"""
    ws = _ws_path(tmp_client_workspace)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        _seed_kpi(engine, "k-no-prio", "No Priority Set", priority=None)
        _seed_kpi(engine, "k-explicit", "Explicit", priority=10)
    finally:
        engine.close()

    res = list_top_kpis(client_slug="test-client", limit=10)
    by_slug = {it.slug: it for it in res.items}
    assert by_slug["k-no-prio"].priority == 100
    assert by_slug["k-explicit"].priority == 10
    # 排序仍正確
    assert res.items[0].slug == "k-explicit"


def test_tiebreak_by_yoy_delta_desc(tmp_client_workspace) -> None:
    """priority 並列時，YoY abs delta 大的優先。"""
    ws = _ws_path(tmp_client_workspace)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        # 兩 KPI 都 priority=10；A 有 +50% YoY，B 有 -10% YoY → A 先
        _seed_kpi(
            engine, "k-volatile", "Volatile", priority=10,
            values_by_year=[
                {"year": 2024, "value": 150.0},
                {"year": 2023, "value": 100.0},
            ],
        )
        _seed_kpi(
            engine, "k-steady", "Steady", priority=10,
            values_by_year=[
                {"year": 2024, "value": 90.0},
                {"year": 2023, "value": 100.0},
            ],
        )
    finally:
        engine.close()

    res = list_top_kpis(client_slug="test-client", limit=10)
    assert res.items[0].slug == "k-volatile"  # |+50%| > |-10%|
    assert res.items[1].slug == "k-steady"


def test_tiebreak_by_slug_when_no_yoy(tmp_client_workspace) -> None:
    """priority + YoY 都並列時，slug 字典序。"""
    ws = _ws_path(tmp_client_workspace)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        _seed_kpi(engine, "k-zeta", "Zeta", priority=10)
        _seed_kpi(engine, "k-alpha", "Alpha", priority=10)
    finally:
        engine.close()

    res = list_top_kpis(client_slug="test-client", limit=10)
    assert [it.slug for it in res.items] == ["k-alpha", "k-zeta"]


def test_limit_clamps(tmp_client_workspace) -> None:
    """limit < 1 → 1；limit > 200 → 200。"""
    ws = _ws_path(tmp_client_workspace)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        for i in range(5):
            _seed_kpi(engine, f"k-{i:02d}", f"KPI {i}", priority=100)
    finally:
        engine.close()

    # limit=0 → clamp 到 1
    res = list_top_kpis(client_slug="test-client", limit=0)
    assert res.limit == 1
    assert len(res.items) == 1

    # limit=999 → clamp 到 200（但實際只有 5 筆）
    res = list_top_kpis(client_slug="test-client", limit=999)
    assert res.limit == 200
    assert len(res.items) == 5  # total scanned 限制下，不會超過實際數


def test_filters_by_topic_slug(tmp_client_workspace) -> None:
    """topic_slug 給定時，只回該議題下的 KPI。"""
    ws = _ws_path(tmp_client_workspace)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        _seed_kpi(engine, "k-e1-a", "Climate A", priority=10, topic_slug="E1-climate")
        _seed_kpi(engine, "k-e2-a", "Energy A", priority=10, topic_slug="E2-energy")
        _seed_kpi(engine, "k-e1-b", "Climate B", priority=20, topic_slug="E1-climate")
    finally:
        engine.close()

    res = list_top_kpis(client_slug="test-client", topic_slug="E1-climate", limit=10)
    slugs = {it.slug for it in res.items}
    assert slugs == {"k-e1-a", "k-e1-b"}
    assert res.topic_slug_filter == "E1-climate"
    # total_scanned 是過濾**後**的數（_scan_kpis 在 helper 內就過濾掉了）
    assert res.total_scanned == 2


def test_empty_workspace_returns_empty(tmp_client_workspace) -> None:
    """沒任何 KPI page 時，items 為空 list，不 raise。"""
    res = list_top_kpis(client_slug="test-client", limit=5)
    assert res.items == []
    assert res.total_scanned == 0


def test_sort_by_yoy_delta(tmp_client_workspace) -> None:
    """sort='yoy_delta' 時，volatile 優先（priority 退到 tiebreak）。"""
    ws = _ws_path(tmp_client_workspace)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        # 高 priority（不重要）但 YoY 巨大
        _seed_kpi(
            engine, "k-low-prio-volatile", "Low Prio Volatile",
            priority=100,
            values_by_year=[
                {"year": 2024, "value": 200.0},
                {"year": 2023, "value": 100.0},
            ],
        )
        # 低 priority（重要）但無 YoY data
        _seed_kpi(engine, "k-high-prio-steady", "High Prio Steady", priority=10)
    finally:
        engine.close()

    res = list_top_kpis(client_slug="test-client", sort="yoy_delta", limit=10)
    assert res.sort == "yoy_delta"
    # YoY = +100% (abs 100) > 0 (no data) → low-prio-volatile 先
    assert res.items[0].slug == "k-low-prio-volatile"
    assert res.items[1].slug == "k-high-prio-steady"


def test_rank_field_is_one_based(tmp_client_workspace) -> None:
    """items[i].rank 應為 i+1（1-based ranking 給 UI / log 用）。"""
    ws = _ws_path(tmp_client_workspace)
    engine = BrainEngine.open(str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False)
    try:
        for i in range(3):
            _seed_kpi(engine, f"k-{i:02d}", f"KPI {i}", priority=10 * (i + 1))
    finally:
        engine.close()

    res = list_top_kpis(client_slug="test-client", limit=10)
    assert [it.rank for it in res.items] == [1, 2, 3]


def test_workspace_not_found_raises() -> None:
    """client_slug 不存在 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        list_top_kpis(client_slug="nonexistent-client", limit=5)
