"""susr.mcp.tools.kpi — Phase 4/6 KPI ranking helper（R6+ Agent C 新檔）。

**TL;DR（30 秒）**：給 ``list_top_kpis`` MCP tool 讓顧問問「lealea-5364 2025
最重要的 5 個 KPI 是哪些？」時，brain 回的順序不是按 ``latest_value`` 數字大小，
而是按 ``KpiFrontmatter.priority``（lower = more important，預設 100）+ YoY
變化幅度 + slug。這對應顧問實務上「E1 範疇 1+2 排放、E2 水資源、S1 工安」這類
critical KPI 不論數值大小都該浮在前面的需求。

**為何不放 phase6.py**：phase6.py 已 ~960 行，CLAUDE.md §4.6.4 軟門檻 300、硬
門檻 500。R6+ KPI ranking 與 Phase 6 payload prep 邏輯彼此正交（前者是「給我前 N
重要的 KPI」，後者是「組投資人 / 董事會 deck payload」），拆獨立模組讓兩者各
自演化不互相黏住。

**排序鍵（三層）**：
    1. ``priority`` ASC      ← schema 內 explicit signal，顧問定義
    2. ``yoy_delta_abs`` DESC ← 變動越劇烈越值得放前面（缺資料 → 0）
    3. ``slug`` ASC          ← deterministic tiebreak

**設計選項對齊**：
    - 純讀 brain SQLite，不寫 filesystem（與 IRO tool 雙寫策略不同 —— ranking
      不會修 KPI 本體，沒必要寫 markdown）
    - 不 emit timeline_entry（讀操作）
    - ``topic_slug`` 過濾可選 —— 顧問問「E 軸 KPI top-3」常見
    - 與 phase6 ``_select_top_kpis`` 不直接共用：那邊是 deck-internal 排序、
      硬碼 5；這邊是 tool-level、limit 可調、含 priority 欄位。重複的代價是
      ~60 行幫忙 + 介面穩定（phase6 內部排序變動時這邊不破）

**與 Agent A / B 的相容性**：
    - 不碰 ``pages.py`` / ``ingest.py``（Agent A）：本工具只讀 ``pages`` 表 +
      ``entity_attributes``，schema 是只讀對齊
    - 不碰 ``timeline.py`` / ``invariants.py`` / ``iro.py`` / ``action.py``
      （Agent B）：純讀，沒有 timeline 寫入需求
    - 對 ``KpiFrontmatter.priority`` 預設 100 — 既有不帶 priority 的 KPI page
      會收到 None 從 ``entity_attributes``，本檔 ``_coerce_priority`` fallback
      到 100，與 schema 預設一致
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from susr.workspace import find_client_workspace


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class KpiRankingItem(BaseModel):
    """``list_top_kpis`` 回傳的單一 KPI rank row。

    Attributes:
        slug: brain page slug（per-client unique，含可能的 ``kpis/`` prefix）。
        name: KPI 顯示名稱（``frontmatter.name`` 或 fallback ``page.title`` 或 slug）。
        topic_slug: 對應的議題 slug；無對應或 frontmatter 缺欄 → None。
        unit: 計量單位（如 ``tCO2e`` / ``%`` / ``count``）。
        priority: ``KpiFrontmatter.priority``（lower = more important）。
            預設 100；critical KPI 通常 10-30。
        latest_value: ``values_by_year`` 最新一年的數值；list 為空 → None。
        latest_year: 最新一年的年份；list 為空 → None。
        yoy_change_pct: 最新 vs 前一年的 YoY 百分比變化；不足兩筆 → None。
        framework_refs: 對應的框架引用清單（如 ``["GRI 305-1", "ISSB S2"]``）。
        rank: 1-based ranking（已套用排序後位置；用於 UI / log）。
    """

    slug: str
    name: str
    topic_slug: Optional[str] = None
    unit: str = ""
    priority: int = 100
    latest_value: Optional[float] = None
    latest_year: Optional[int] = None
    yoy_change_pct: Optional[float] = None
    framework_refs: list[str] = Field(default_factory=list)
    rank: int


class KpiRankingResult(BaseModel):
    """``list_top_kpis`` 完整回傳結構 — items + 排序策略 + 篩選紀錄。"""

    items: list[KpiRankingItem]
    total_scanned: int
    limit: int
    sort: Literal["priority", "yoy_delta", "slug"] = "priority"
    topic_slug_filter: Optional[str] = None
    project_filter: Optional[str] = None  # 預留：未來 cross-project 支援；MVP None


# ---------------------------------------------------------------------------
# Helpers — brain SQLite 純讀
# ---------------------------------------------------------------------------


def _fetch_attrs(conn: sqlite3.Connection, page_id: int) -> dict[str, Any]:
    """Read entity_attributes for a single page → dict。值仍為 raw TEXT，由 caller 解析。

    與 phase6._fetch_attrs 重複是刻意 — 兩邊各自演化不互相牽動。Helper 約 30 行，
    純粹 mechanical SQL → dict，沒有業務邏輯，dup 成本可忽略。
    """
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
            except (TypeError, ValueError):
                out[key] = value
        elif vtype == "float":
            try:
                out[key] = float(value)
            except (TypeError, ValueError):
                out[key] = value
        elif vtype in ("json", "json_array", "json_object"):
            try:
                import json

                out[key] = json.loads(value)
            except (TypeError, ValueError):
                out[key] = value
        elif vtype == "bool":
            out[key] = str(value).lower() in ("true", "1", "yes")
        else:
            out[key] = value
    return out


def _coerce_priority(raw: Any) -> int:
    """KpiFrontmatter.priority 預設 100；不在 entity_attributes 內或型別不合 → 100。"""
    if raw is None:
        return 100
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 100


def _latest_value_year(values_by_year: Any) -> tuple[Optional[float], Optional[int]]:
    """從 KPI 的 values_by_year list 抽最新一筆 (value, year)。

    與 phase6._kpi_latest_value_year 等效；獨立寫一份避免 import 緊耦合
    （phase6 模組內部排序行為可能演化）。
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


def _yoy_pct(values_by_year: Any) -> Optional[float]:
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
    if prev_v == 0 or latest_y - prev_y > 5:
        return None
    return round(((latest_v - prev_v) / prev_v) * 100.0, 2)


# ---------------------------------------------------------------------------
# Main tool
# ---------------------------------------------------------------------------


def list_top_kpis(
    client_slug: str,
    project: Optional[str] = None,
    topic_slug: Optional[str] = None,
    limit: int = 10,
    sort: Literal["priority", "yoy_delta", "slug"] = "priority",
) -> KpiRankingResult:
    """回 per-client brain 內 top-K KPI（依 priority + YoY + slug 排序）。

    顧問用例：
        - 「lealea-5364 2025 前 5 個重要 KPI」→ ``limit=5, sort='priority'``
        - 「E1 議題下 KPI」→ ``topic_slug='E1-climate'``
        - 「變動最大的 3 個 KPI」→ ``sort='yoy_delta', limit=3``

    Args:
        client_slug: per-client workspace 目錄名稱。
        project: 預留 cross-project 過濾；MVP 不使用 — KPI 是 client-level entity
            （values_by_year 自帶年份），不綁 project_slug。傳值僅紀錄於 result。
        topic_slug: 若提供，只回該 topic 下的 KPI（透過 ``KpiFrontmatter.topic_slug``
            欄位匹配）。
        limit: 回幾筆；clip 到 [1, 200]。
        sort: 排序策略。
            - ``priority``（預設）：priority ASC, yoy_delta_abs DESC, slug ASC
            - ``yoy_delta``：yoy_delta_abs DESC, priority ASC, slug ASC
            - ``slug``：slug ASC（純字典序，用於 deterministic dump）

    Returns:
        ``KpiRankingResult`` — items（已套用 limit）+ total_scanned（過濾前總數）
        + sort + 篩選欄位。

    Raises:
        FileNotFoundError: client workspace 不存在。
    """
    # ---- guard rails ----
    limit = max(1, min(200, int(limit)))

    client_path = find_client_workspace(client_slug)
    db_path = client_path / ".susr" / "db.sqlite"

    # 直接走 sqlite3（避開 BrainEngine 的 vec extension load — 純讀 ranking
    # 用不到 embedding；保持 cold-start 輕量）
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT id, slug, title FROM pages "
            "WHERE entity_type='kpi' AND deleted_at IS NULL ORDER BY slug"
        ).fetchall()

        items_raw: list[KpiRankingItem] = []
        for page_id, slug, title in rows:
            attrs = _fetch_attrs(conn, int(page_id))

            # topic_slug 過濾（caller 給定時才執行）
            kpi_topic = attrs.get("topic_slug")
            if topic_slug is not None and str(kpi_topic) != str(topic_slug):
                continue

            framework_refs = attrs.get("framework_refs")
            if not isinstance(framework_refs, list):
                framework_refs = []

            latest_v, latest_y = _latest_value_year(attrs.get("values_by_year"))
            yoy = _yoy_pct(attrs.get("values_by_year"))

            items_raw.append(KpiRankingItem(
                slug=str(slug),
                name=str(attrs.get("name") or title or slug),
                topic_slug=str(kpi_topic) if kpi_topic else None,
                unit=str(attrs.get("unit") or ""),
                priority=_coerce_priority(attrs.get("priority")),
                latest_value=latest_v,
                latest_year=latest_y,
                yoy_change_pct=yoy,
                framework_refs=[str(x) for x in framework_refs],
                rank=0,  # 排序後填
            ))
    finally:
        conn.close()

    total_scanned = len(items_raw)

    # ---- 排序 ----
    def _abs_yoy(it: KpiRankingItem) -> float:
        return abs(it.yoy_change_pct) if it.yoy_change_pct is not None else 0.0

    if sort == "priority":
        items_raw.sort(key=lambda it: (it.priority, -_abs_yoy(it), it.slug))
    elif sort == "yoy_delta":
        items_raw.sort(key=lambda it: (-_abs_yoy(it), it.priority, it.slug))
    else:  # "slug"
        items_raw.sort(key=lambda it: it.slug)

    # ---- limit + 填 rank ----
    limited = items_raw[:limit]
    for idx, it in enumerate(limited, start=1):
        it.rank = idx

    return KpiRankingResult(
        items=limited,
        total_scanned=total_scanned,
        limit=limit,
        sort=sort,
        topic_slug_filter=topic_slug,
        project_filter=project,
    )


def register(server) -> None:  # noqa: ANN001
    """Bind ``list_top_kpis`` to a FastMCP server instance."""
    server.tool()(list_top_kpis)


__all__ = [
    "KpiRankingItem",
    "KpiRankingResult",
    "list_top_kpis",
    "register",
]
