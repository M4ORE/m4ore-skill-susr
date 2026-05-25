"""Layer 4 — MCP Action linkage tool 單元測試（R4 為 I1b 鋪路）。

對應 ``packages/susr/susr/mcp/tools/action.py``：``link_iro_to_action``
單一 tool — 對既有 IRO 建立 Action entity + ``iro_addressed_by`` typed edge
+ timeline_entry，雙寫 filesystem + brain DB。

測試覆蓋（user spec 6 條）：
    1. test_link_iro_to_action_creates_action_page  — Action page 寫入 brain + md
    2. test_link_iro_to_action_creates_edge          — iro_addressed_by edge 存在
    3. test_link_iro_to_action_writes_timeline       — timeline_entries 有對應 entry
    4. test_link_iro_to_action_idempotent            — 重複呼叫不複製
    5. test_link_iro_to_action_invalid_iro_raises    — 不存在 IRO 應 raise
    6. test_i1b_passes_after_link_action             — 對 lealea 9 IRO 補 action 後 I1b pass

不靠 spawn MCP server — 直接呼叫 tool function + brain engine。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from susr.brain.engine import BrainEngine
from susr.brain.invariants import (
    assert_i1a_core_topic_has_iro,
    assert_i1b_iro_has_action,
    check_all_invariants,
)
from susr.mcp.tools.action import LinkedActionResult, link_iro_to_action
from susr.mcp.tools.iro import link_topic_to_iro


def _ws_path(tmp_client_workspace: Any) -> Path:
    """``tmp_client_workspace`` 回 dict（含 workspace_path 字串）— 抽出 Path。"""
    if isinstance(tmp_client_workspace, dict):
        return Path(tmp_client_workspace["workspace_path"])
    return Path(tmp_client_workspace)


# ---------------------------------------------------------------------------
# Helpers — 重用 iro 測試的 topic setup pattern
# ---------------------------------------------------------------------------


def _write_topic_md(client_path: Path, slug: str, name: str, axis: str = "E") -> None:
    """minimal topic markdown，讓 link_topic_to_iro 的 filesystem check 通過。"""
    import yaml

    page = client_path / "entities" / "topics" / f"{slug}.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    fm = {
        "slug": slug, "name": name, "axis": axis,
        "impact_score": 4.5, "financial_score": 4.0,
        "materiality_tier": "核心",
    }
    page.write_text(
        "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)
        + "---\n\n# " + name + "\n",
        encoding="utf-8",
    )


def _ingest_topic_to_brain(client_path: Path, slug: str, name: str, axis: str = "E") -> None:
    """put_page topic，模擬已 ingest 過。"""
    engine = BrainEngine.open(
        str(client_path / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    try:
        engine.put_page(
            slug=slug, entity_type="topic", title=name,
            compiled_truth=f"# {name}\n",
            file_path=str(client_path / "entities" / "topics" / f"{slug}.md"),
            frontmatter={
                "slug": slug, "name": name, "axis": axis,
                "impact_score": 4.5, "financial_score": 4.0,
                "materiality_tier": "核心",
            },
        )
    finally:
        engine.close()


def _setup_topic(client_path: Path, slug: str, name: str = "氣候變遷", axis: str = "E") -> None:
    _write_topic_md(client_path, slug, name, axis=axis)
    _ingest_topic_to_brain(client_path, slug, name, axis=axis)


def _setup_topic_and_iro(
    client_path: Path,
    topic_slug: str,
    topic_name: str = "氣候變遷",
    iro_name: str = "碳費",
    iro_type: str = "risk",
) -> str:
    """準備 1 個 topic + 1 個 IRO（透過 link_topic_to_iro）— 回 IRO 短 slug。"""
    _setup_topic(client_path, topic_slug, topic_name)
    r = link_topic_to_iro(
        client_slug="test-client",
        topic_slug=topic_slug,
        iro_type=iro_type,  # type: ignore[arg-type]
        iro_name=iro_name,
        description=f"{iro_name} 描述",
        category="transition",
        time_horizon="M",
        financial_magnitude=4.0,
    )
    return r.iro_slug


# ---------------------------------------------------------------------------
# Test 1: Action page 寫入 brain + filesystem
# ---------------------------------------------------------------------------


def test_link_iro_to_action_creates_action_page(tmp_client_workspace) -> None:
    """呼叫後 (a) Action markdown 檔在預期位置存在，(b) brain DB 內有 action page。"""
    ws = _ws_path(tmp_client_workspace)
    iro_slug = _setup_topic_and_iro(ws, "E1-climate")

    result = link_iro_to_action(
        iro_slug=iro_slug,
        action_name="2025 能耗減量計畫",
        description="冷氣機汰換 + 智慧電表佈建，預估減 12% 範疇 2 排放。",
        client_slug="test-client",
        project_slug="2025-sr",
        budget=2_500_000.0,
        progress_pct=0.15,
        owner_department="ESG",
        period="2025",
    )

    assert isinstance(result, LinkedActionResult)
    assert result.created is True
    assert result.iro_slug == iro_slug
    assert result.action_name == "2025 能耗減量計畫"

    # filesystem
    action_md = Path(result.page_file)
    assert action_md.exists(), f"Action markdown not written: {action_md}"
    assert action_md.parent.name == "actions"
    assert action_md.parent.parent.name == "2025-sr"

    # brain DB — action page 存在
    engine = BrainEngine.open(
        str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    try:
        action_page = engine.get_page(f"actions/{result.action_slug}")
        assert action_page is not None
        assert action_page.entity_type == "action"
    finally:
        engine.close()


# ---------------------------------------------------------------------------
# Test 2: iro_addressed_by edge 存在於 brain DB
# ---------------------------------------------------------------------------


def test_link_iro_to_action_creates_edge(tmp_client_workspace) -> None:
    """呼叫後 ``links`` 表存在 (iro → action, edge_type='iro_addressed_by') 一筆。"""
    ws = _ws_path(tmp_client_workspace)
    iro_slug = _setup_topic_and_iro(ws, "S6-food-safety", "食品安全", "HACCP 失效衝擊", "impact")

    result = link_iro_to_action(
        iro_slug=iro_slug,
        action_name="HACCP 全鏈再認證",
        description="2025 H2 對所有據點 HACCP 流程 third-party reaudit",
        client_slug="test-client",
        project_slug="2025-sr",
        budget=800_000.0,
        progress_pct=0.0,
        owner_department="餐飲事業部",
        period="2025-H2",
    )
    assert result.edge_id > 0

    engine = BrainEngine.open(
        str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    try:
        row = engine.conn.execute(
            """
            SELECT l.edge_type, src.slug, dst.slug, dst.entity_type
            FROM links l
            JOIN pages src ON src.id = l.src_page_id
            JOIN pages dst ON dst.id = l.dst_page_id
            WHERE l.id = ?
            """,
            [result.edge_id],
        ).fetchone()
        assert row is not None
        edge_type, src_slug, dst_slug, dst_type = row
        assert edge_type == "iro_addressed_by"
        assert src_slug == f"iros/{iro_slug}"
        assert dst_slug == f"actions/{result.action_slug}"
        assert dst_type == "action"
    finally:
        engine.close()


# ---------------------------------------------------------------------------
# Test 3: timeline_entries 有對應 entry
# ---------------------------------------------------------------------------


def test_link_iro_to_action_writes_timeline(tmp_client_workspace) -> None:
    """呼叫後 ``timeline_entries`` 表有對應 row（payload 含 action 資訊）。"""
    ws = _ws_path(tmp_client_workspace)
    iro_slug = _setup_topic_and_iro(ws, "G2-integrity", "誠信經營", "採購弊端罰款", "risk")

    result = link_iro_to_action(
        iro_slug=iro_slug,
        action_name="採購流程升級",
        description="導入 e-procurement + 雙人覆核",
        client_slug="test-client",
        project_slug="2025-sr",
        budget=600_000.0,
        owner_department="採購",
        period="2025-Q3",
        actor="consultant:王",
    )
    assert result.timeline_entry_id > 0

    engine = BrainEngine.open(
        str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    try:
        row = engine.conn.execute(
            "SELECT page_id, action_type, actor, payload FROM timeline_entries "
            "WHERE id = ?",
            [result.timeline_entry_id],
        ).fetchone()
        assert row is not None
        page_id, action_type, actor, payload = row
        assert page_id == result.brain_page_id
        assert action_type == "ingest"
        assert actor == "consultant:王"
        decoded = json.loads(payload)
        assert decoded["tool"] == "link_iro_to_action"
        assert decoded["iro_slug"] == iro_slug
        assert decoded["action_name"] == "採購流程升級"
        assert decoded["owner_department"] == "採購"
    finally:
        engine.close()


# ---------------------------------------------------------------------------
# Test 4: idempotent — 重複呼叫不複製
# ---------------------------------------------------------------------------


def test_link_iro_to_action_idempotent(tmp_client_workspace) -> None:
    """同 (iro, action_name) 重複呼叫 → 第二次 created=False，Action page 只有 1 個。"""
    ws = _ws_path(tmp_client_workspace)
    iro_slug = _setup_topic_and_iro(
        ws, "S7-customer-privacy", "客戶隱私", "個資洩漏", "risk",
    )

    r1 = link_iro_to_action(
        iro_slug=iro_slug, action_name="個資治理升級",
        description="第一次", client_slug="test-client",
        project_slug="2025-sr", budget=400_000.0,
    )
    r2 = link_iro_to_action(
        iro_slug=iro_slug, action_name="個資治理升級",
        description="第二次（內容不同也不複製）", client_slug="test-client",
        project_slug="2025-sr", budget=999_999.0,
    )

    assert r1.created is True
    assert r2.created is False
    assert r1.action_slug == r2.action_slug  # deterministic
    assert r1.brain_page_id == r2.brain_page_id

    engine = BrainEngine.open(
        str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    try:
        n_actions = engine.conn.execute(
            "SELECT COUNT(*) FROM pages WHERE entity_type = 'action' "
            "AND deleted_at IS NULL"
        ).fetchone()[0]
        assert n_actions == 1
        n_edges = engine.conn.execute(
            "SELECT COUNT(*) FROM links WHERE edge_type = 'iro_addressed_by'"
        ).fetchone()[0]
        assert n_edges == 1
    finally:
        engine.close()


# ---------------------------------------------------------------------------
# Test 5: invalid IRO — IRO 不存在於 brain → LookupError
# ---------------------------------------------------------------------------


def test_link_iro_to_action_invalid_iro_raises(tmp_client_workspace) -> None:
    """IRO 不在 brain DB → 應 raise LookupError。"""
    _ws_path(tmp_client_workspace)  # 觸發 workspace 建立
    with pytest.raises(LookupError, match="not found in brain DB"):
        link_iro_to_action(
            iro_slug="DOES-NOT-EXIST",
            action_name="ghost",
            description="",
            client_slug="test-client",
        )


# ---------------------------------------------------------------------------
# Test 6: I1b — 對 lealea 9 個 core topic 補 IRO + Action 後 I1b pass
# ---------------------------------------------------------------------------


def _lealea_core_topics() -> list[tuple[str, str, str]]:
    """walkthrough §3 跑出的 9 個 core topics (slug, name, axis)。"""
    return [
        ("E1-climate", "氣候變遷與低碳轉型", "E"),
        ("E2-energy", "能源管理", "E"),
        ("G2-integrity", "商業道德與誠信經營", "G"),
        ("G3-compliance", "法令遵循與風險管理", "G"),
        ("S1-labor-conditions", "員工權益與勞動條件", "S"),
        ("S4-occupational-health", "員工健康安全", "S"),
        ("S6-food-safety", "客戶健康安全（食品安全）", "S"),
        ("S7-customer-privacy", "客戶隱私與資料保護", "S"),
        ("S8-customer-experience", "客戶體驗與滿意度", "S"),
    ]


def test_i1b_passes_after_link_action(tmp_client_workspace) -> None:
    """walkthrough §5 9/9 I1 fail 的 R4 收束驗證：

    (1) 對 9 個 core topic 用 link_topic_to_iro 補 IRO → I1a pass / I1b 仍 fail
        （Phase 3 合法中間態）。
    (2) 再對每個 IRO 用 link_iro_to_action 補 Action → I1b 也 pass。
    """
    ws = _ws_path(tmp_client_workspace)
    core_topics = _lealea_core_topics()

    # 1. ingest 9 個 core topics
    for slug, name, axis in core_topics:
        _setup_topic(ws, slug, name, axis=axis)

    # 2. 對每個 topic 建一個 IRO
    iro_slugs: list[str] = []
    for slug, name, _axis in core_topics:
        r = link_topic_to_iro(
            client_slug="test-client", topic_slug=slug,
            iro_type="impact", iro_name=f"{name} 影響",
            description=f"{slug} 主要 impact",
            category="operational", time_horizon="M", financial_magnitude=4.0,
        )
        iro_slugs.append(r.iro_slug)

    engine = BrainEngine.open(
        str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    try:
        # 中段：I1a pass / I1b fail（合法 Phase 3 中間態）
        assert_i1a_core_topic_has_iro(engine.conn)  # 應不 raise
        with pytest.raises(Exception, match="I1b"):
            assert_i1b_iro_has_action(engine.conn)

        # 確認 v_i1b_iro_has_action 中 9 個 IRO 都 action_count=0
        rows = engine.conn.execute(
            "SELECT iro_slug, action_count FROM v_i1b_iro_has_action "
            "ORDER BY iro_slug"
        ).fetchall()
        assert len(rows) == 9, f"expected 9 IROs, got {len(rows)}"
        for _slug, cnt in rows:
            assert cnt == 0
    finally:
        engine.close()

    # 3. 對每個 IRO 補一個 Action
    for iro_slug in iro_slugs:
        r_action = link_iro_to_action(
            iro_slug=iro_slug,
            action_name=f"行動 {iro_slug[:8]}",
            description="R4 收束 — Phase 5 行動方案",
            client_slug="test-client",
            project_slug="2025-sr",
            budget=500_000.0,
            progress_pct=0.1,
            owner_department="ESG",
            period="2025",
        )
        assert r_action.created is True

    # 4. I1b 應 pass
    engine = BrainEngine.open(
        str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    try:
        assert_i1a_core_topic_has_iro(engine.conn)
        assert_i1b_iro_has_action(engine.conn)

        violations = check_all_invariants(engine.conn)
        i1_violations = [v for v in violations if v.invariant_name in ("I1a", "I1b")]
        assert i1_violations == [], (
            f"I1a/I1b should pass after IRO + Action chain, got: {i1_violations}"
        )
    finally:
        engine.close()


# ---------------------------------------------------------------------------
# R4d — Action markdown body should contain ## Timeline section
# ---------------------------------------------------------------------------


def test_link_iro_to_action_writes_md_timeline(tmp_client_workspace) -> None:
    """R4d 驗證：Action markdown body 應含 '## Timeline' + action=ingest 行 (dual write)。"""
    ws = _ws_path(tmp_client_workspace)
    iro_slug = _setup_topic_and_iro(
        ws, "E1-climate", "氣候變遷", "碳費", "risk",
    )

    r = link_iro_to_action(
        iro_slug=iro_slug,
        action_name="2025 能耗減量計畫",
        description="冷氣機汰換 + 智慧電表佈建",
        client_slug="test-client",
        project_slug="2025-sr",
        budget=2_500_000.0,
        actor="consultant:李",
    )
    action_md = Path(r.page_file)
    text = action_md.read_text(encoding="utf-8")
    # MD body 含 timeline section + 行
    assert "## Timeline" in text
    assert "action=ingest" in text
    assert "actor=consultant:李" in text
    # 同步 DB 內容
    engine = BrainEngine.open(
        str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    try:
        row = engine.conn.execute(
            "SELECT actor, payload FROM timeline_entries WHERE id=?",
            [r.timeline_entry_id],
        ).fetchone()
        assert row is not None
        actor_db, payload_db = row
        assert actor_db == "consultant:李"
        decoded = json.loads(payload_db)
        assert decoded["tool"] == "link_iro_to_action"
        assert decoded["action_name"] == "2025 能耗減量計畫"
    finally:
        engine.close()
