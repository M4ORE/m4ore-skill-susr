"""Layer 4 — MCP IRO linkage tool 單元測試（補 walkthrough §5 P0b）。

對應 ``packages/susr/susr/mcp/tools/iro.py``：``link_topic_to_iro``
單一 tool，補上 Phase 3 MVP 4 個 tools 缺的 IRO 建立功能。

測試覆蓋（user spec 6 條）：
    1. test_link_topic_to_iro_creates_iro_page         — IRO page 寫入 brain
    2. test_link_topic_to_iro_creates_edge             — topic_has_iro edge 存在
    3. test_link_topic_to_iro_writes_timeline          — timeline_entries 有對應 entry
    4. test_link_topic_to_iro_idempotent               — 重複呼叫不複製
    5. test_link_topic_to_iro_invalid_topic_raises     — 不存在 topic_slug 應 raise
    6. test_i1_invariant_passes_after_link             — link IRO + action 後 I1 pass

不靠 spawn MCP server — 直接呼叫 tool function + brain engine。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from susr.brain.engine import BrainEngine
from susr.brain.invariants import (
    assert_i1_core_topic_coverage,
    check_all_invariants,
)
from susr.mcp.tools.iro import (
    LinkedIroResult,
    link_topic_to_iro,
)


def _ws_path(tmp_client_workspace: Any) -> Path:
    """``tmp_client_workspace`` 回 dict（含 workspace_path 字串）— 抽出 Path。"""
    if isinstance(tmp_client_workspace, dict):
        return Path(tmp_client_workspace["workspace_path"])
    return Path(tmp_client_workspace)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_topic_md(client_path: Path, slug: str, name: str, axis: str = "E") -> None:
    """在 tmp client workspace 寫一個 minimal topic markdown（讓 link_topic_to_iro
    的 filesystem check 通過）。"""
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
    """打開 brain engine + put_page topic，模擬已 ingest 過。"""
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


def _setup_topic(
    client_path: Path, slug: str, name: str = "氣候變遷", axis: str = "E",
) -> None:
    """同時寫 markdown + ingest brain（測試 fixture 常用組合）。"""
    _write_topic_md(client_path, slug, name, axis=axis)
    _ingest_topic_to_brain(client_path, slug, name, axis=axis)


# ---------------------------------------------------------------------------
# Test 1: IRO page 寫入 brain（filesystem + DB 雙寫）
# ---------------------------------------------------------------------------


def test_link_topic_to_iro_creates_iro_page(tmp_client_workspace) -> None:
    """呼叫後 (a) IRO markdown 檔在預期位置存在，(b) brain DB 內有 iro entity page。"""
    ws = _ws_path(tmp_client_workspace)
    _setup_topic(ws, "E1-climate", "氣候變遷")

    result = link_topic_to_iro(
        client_slug="test-client",
        topic_slug="E1-climate",
        iro_type="risk",
        iro_name="碳費",
        description="台灣 2025+ 碳費分階段加徵；山區據點冬季能源費對毛利的壓力。",
        category="transition",
        time_horizon="L",
        financial_magnitude=4.0,
        actor="consultant:test",
    )

    assert isinstance(result, LinkedIroResult)
    assert result.created is True
    assert result.iro_type == "Risk"
    assert result.topic_slug == "E1-climate"

    # filesystem
    iro_md = Path(result.page_file)
    assert iro_md.exists(), f"IRO markdown not written: {iro_md}"
    assert iro_md.parent.name == "iro"
    assert iro_md.parent.parent.name == "E1-climate"

    # brain DB — iro page 存在
    engine = BrainEngine.open(
        str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    try:
        iro_page = engine.get_page(f"iros/{result.iro_slug}")
        assert iro_page is not None
        assert iro_page.entity_type == "iro"
    finally:
        engine.close()


# ---------------------------------------------------------------------------
# Test 2: topic_has_iro edge 存在於 brain DB
# ---------------------------------------------------------------------------


def test_link_topic_to_iro_creates_edge(tmp_client_workspace) -> None:
    """呼叫後 ``links`` 表存在 (topic → iro, edge_type='topic_has_iro') 一筆。"""
    ws = _ws_path(tmp_client_workspace)
    _setup_topic(ws, "S6-food-safety", "食品安全")

    result = link_topic_to_iro(
        client_slug="test-client", topic_slug="S6-food-safety",
        iro_type="impact", iro_name="客戶健康",
        description="HACCP 失效情境下對顧客健康的直接衝擊",
        category="operational", time_horizon="S", financial_magnitude=4.5,
    )
    assert result.edge_id > 0

    engine = BrainEngine.open(
        str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    try:
        # edge_type='topic_has_iro' 且 dst 是新建的 iro
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
        assert edge_type == "topic_has_iro"
        assert src_slug == "S6-food-safety"
        assert dst_slug == f"iros/{result.iro_slug}"
        assert dst_type == "iro"
    finally:
        engine.close()


# ---------------------------------------------------------------------------
# Test 3: timeline_entries 有對應 entry
# ---------------------------------------------------------------------------


def test_link_topic_to_iro_writes_timeline(tmp_client_workspace) -> None:
    """呼叫後 ``timeline_entries`` 表有對應 row（action_type='ingest', payload 含 iro 資訊）。"""
    ws = _ws_path(tmp_client_workspace)
    _setup_topic(ws, "G2-integrity", "誠信經營", axis="G")

    result = link_topic_to_iro(
        client_slug="test-client", topic_slug="G2-integrity",
        iro_type="risk", iro_name="採購弊端罰款",
        description="採購流程稽核不足導致罰款與商譽損失",
        category="legal", time_horizon="M", financial_magnitude=3.5,
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
        import json
        decoded = json.loads(payload)
        assert decoded["tool"] == "link_topic_to_iro"
        assert decoded["topic_slug"] == "G2-integrity"
        assert decoded["iro_type"] == "Risk"
        assert decoded["iro_name"] == "採購弊端罰款"
    finally:
        engine.close()


# ---------------------------------------------------------------------------
# Test 4: idempotent — 重複呼叫不複製
# ---------------------------------------------------------------------------


def test_link_topic_to_iro_idempotent(tmp_client_workspace) -> None:
    """同 (topic, type, name) 重複呼叫 → 第二次 created=False，IRO page 只有 1 個。"""
    ws = _ws_path(tmp_client_workspace)
    _setup_topic(ws, "S7-customer-privacy", "客戶隱私")

    r1 = link_topic_to_iro(
        client_slug="test-client", topic_slug="S7-customer-privacy",
        iro_type="risk", iro_name="個資洩漏",
        description="第一次", category="reputational", time_horizon="M",
    )
    r2 = link_topic_to_iro(
        client_slug="test-client", topic_slug="S7-customer-privacy",
        iro_type="risk", iro_name="個資洩漏",
        description="第二次（內容不同也不複製）", category="reputational",
        time_horizon="M",
    )

    assert r1.created is True
    assert r2.created is False
    assert r1.iro_slug == r2.iro_slug  # deterministic slug
    assert r1.brain_page_id == r2.brain_page_id

    engine = BrainEngine.open(
        str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    try:
        # 該 topic 下只有 1 個 IRO page
        n_iros = engine.conn.execute(
            "SELECT COUNT(*) FROM pages WHERE entity_type = 'iro' AND deleted_at IS NULL"
        ).fetchone()[0]
        assert n_iros == 1
        # topic_has_iro edge 也只有 1 條（put_page 用 ON CONFLICT 升級而非重複插）
        n_edges = engine.conn.execute(
            "SELECT COUNT(*) FROM links WHERE edge_type = 'topic_has_iro'"
        ).fetchone()[0]
        assert n_edges == 1
    finally:
        engine.close()


# ---------------------------------------------------------------------------
# Test 5: invalid topic — markdown 不存在 → FileNotFoundError
# ---------------------------------------------------------------------------


def test_link_topic_to_iro_invalid_topic_raises(tmp_client_workspace) -> None:
    """topic markdown 不存在 → 應 raise FileNotFoundError。"""
    with pytest.raises(FileNotFoundError, match="topic markdown not found"):
        link_topic_to_iro(
            client_slug="test-client",
            topic_slug="DOES-NOT-EXIST",
            iro_type="impact", iro_name="ghost",
        )


def test_link_topic_to_iro_topic_missing_in_brain_raises(tmp_client_workspace) -> None:
    """topic markdown 存在但 brain 內沒 ingest → 應 raise LookupError。"""
    ws = _ws_path(tmp_client_workspace)
    # 只寫 markdown，不 ingest 到 brain
    _write_topic_md(ws, "X1-orphan", "孤兒 topic")

    with pytest.raises(LookupError, match="not found in brain DB"):
        link_topic_to_iro(
            client_slug="test-client",
            topic_slug="X1-orphan",
            iro_type="risk", iro_name="any",
        )


# ---------------------------------------------------------------------------
# Test 6: I1 invariant — link IRO + action 後 9 個 core topic 全 pass
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


def test_i1_invariant_passes_after_link(tmp_client_workspace) -> None:
    """walkthrough §5.385 9/9 fail 的關鍵驗證 — 對 lealea 9 個 core topic 建 IRO +
    Action 後 I1 應 pass。

    驗 link_topic_to_iro 真的補上 walkthrough P0b 的 IRO 缺口。Action chain 是 R3
    範圍外（沒有 link_iro_to_action tool 還沒做），但 I1 view 同時要求 IRO 與 Action
    存在，所以本測也 inline 建 action 確保整條鏈 ready，驗證 link_topic_to_iro
    在這條鏈上的契約正確。
    """
    ws = _ws_path(tmp_client_workspace)
    core_topics = _lealea_core_topics()

    # 1. ingest 9 個 core topics + write markdown
    for slug, name, axis in core_topics:
        _write_topic_md(ws, slug, name, axis=axis)
        _ingest_topic_to_brain(ws, slug, name, axis=axis)

    # 2. 對每個 topic 建一個 IRO (透過 link_topic_to_iro)
    iro_slugs: list[str] = []
    for slug, name, _axis in core_topics:
        r = link_topic_to_iro(
            client_slug="test-client", topic_slug=slug,
            iro_type="impact", iro_name=f"{name} 影響",
            description=f"{slug} 主要 impact 描述",
            category="operational", time_horizon="M", financial_magnitude=4.0,
        )
        assert r.created is True
        iro_slugs.append(r.iro_slug)

    # 中段驗證：此時 I1 仍 fail（缺 action chain）— 確認 link_topic_to_iro 本身
    # 已把 topic→iro 一半補上，但 v_core_topic_action_coverage 還會要求 iro→action
    engine = BrainEngine.open(
        str(ws / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    try:
        # 直接查 view — 此時每個 core topic 應有 1 個 iro 但 action_count 仍 0
        rows = engine.conn.execute(
            "SELECT topic_slug, action_count FROM v_core_topic_action_coverage "
            "ORDER BY topic_slug"
        ).fetchall()
        assert len(rows) == 9, f"expected 9 core topics in coverage view, got {len(rows)}"
        for slug, action_count in rows:
            assert action_count == 0, (
                f"topic {slug} action_count={action_count} — should still be 0 "
                f"before action chain"
            )

        # 3. 為每個 IRO inline 建一個 action（不靠 link_topic_to_iro，這是 R3 後續工作）
        for iro_slug in iro_slugs:
            action_slug = f"action-{iro_slug}"
            engine.put_page(
                slug=f"actions/{action_slug}", entity_type="action",
                title=f"action {action_slug}",
                compiled_truth="", file_path=f"projects/2025-sr/actions/{action_slug}.md",
                frontmatter={
                    "slug": action_slug, "chapter_slug": "ch-test",
                    "iro_addressed": [iro_slug],
                    "budget": 100_000.0, "progress_pct": 0.1,
                    "owner_department": "ESG", "period": "2025",
                },
            )
            engine.link(
                f"iros/{iro_slug}", "iro_addressed_by", f"actions/{action_slug}",
            )

        # 4. 跑 I1 — 應 pass（不 raise）
        assert_i1_core_topic_coverage(engine.conn)

        # 5. check_all_invariants — I1 沒有 violation（其他空集 vacuously true）
        violations = check_all_invariants(engine.conn)
        i1 = [v for v in violations if v.invariant == "I1"]
        assert i1 == [], f"I1 should pass after IRO + action chain, got: {i1}"
    finally:
        engine.close()


# ---------------------------------------------------------------------------
# Test 7: unknown iro_type raises
# ---------------------------------------------------------------------------


def test_link_topic_to_iro_unknown_type_raises(tmp_client_workspace) -> None:
    """iro_type 不在 {impact, risk, opportunity} → KeyError。

    Pydantic Literal 在 function 簽章只是 type hint，runtime 不會自動驗 — 我們
    手動在 tool 內 raise KeyError 來 fail-fast。
    """
    ws = _ws_path(tmp_client_workspace)
    _setup_topic(ws, "E1-climate", "氣候變遷")

    with pytest.raises(KeyError, match="unknown iro_type"):
        link_topic_to_iro(
            client_slug="test-client",
            topic_slug="E1-climate",
            iro_type="threat",  # type: ignore[arg-type]
            iro_name="x",
        )


# ---------------------------------------------------------------------------
# R4e — slug-based idempotency
# ---------------------------------------------------------------------------


def test_link_topic_to_iro_explicit_slug_used(tmp_client_workspace) -> None:
    """caller 顯式給 slug → IRO 使用該 slug（去除非 ascii 後 kebab）。"""
    ws = _ws_path(tmp_client_workspace)
    _setup_topic(ws, "E1-climate", "氣候變遷")

    r = link_topic_to_iro(
        client_slug="test-client",
        topic_slug="E1-climate",
        iro_type="risk",
        iro_name="碳費",
        slug="ESG-IRO-2025-001",
    )
    # Slug cleanup: 顯式 slug 走 kebab-case sanitiser → lower-case
    assert r.iro_slug == "esg-iro-2025-001"


def test_link_topic_to_iro_explicit_slug_idempotent(tmp_client_workspace) -> None:
    """同 explicit slug 重複呼叫 → 第二次 created=False，即使 iro_name 不同。"""
    ws = _ws_path(tmp_client_workspace)
    _setup_topic(ws, "E1-climate", "氣候變遷")

    r1 = link_topic_to_iro(
        client_slug="test-client", topic_slug="E1-climate",
        iro_type="risk", iro_name="碳費",
        slug="esg-iro-2025-001",
    )
    # 不同 iro_name + 同 slug → 仍然 idempotent
    r2 = link_topic_to_iro(
        client_slug="test-client", topic_slug="E1-climate",
        iro_type="risk", iro_name="不一樣的名字（不應建新 IRO）",
        slug="esg-iro-2025-001",
    )
    assert r1.created is True
    assert r2.created is False
    assert r1.iro_slug == r2.iro_slug == "esg-iro-2025-001"
    assert r1.brain_page_id == r2.brain_page_id


def test_link_topic_to_iro_writes_md_timeline(tmp_client_workspace) -> None:
    """R4d 驗證：IRO markdown body 應含 '## Timeline' + action=ingest 行 (dual write)。"""
    ws = _ws_path(tmp_client_workspace)
    _setup_topic(ws, "E1-climate", "氣候變遷")

    r = link_topic_to_iro(
        client_slug="test-client", topic_slug="E1-climate",
        iro_type="risk", iro_name="碳費",
        description="台灣 2025+ 碳費分階段加徵",
        actor="consultant:王",
    )
    iro_md = Path(r.page_file)
    text = iro_md.read_text(encoding="utf-8")
    # MD body 含 timeline section + 行
    assert "## Timeline" in text
    assert "action=ingest" in text
    assert "actor=consultant:王" in text
    # DB 同步 — payload 一致
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
        assert actor_db == "consultant:王"
        import json
        decoded = json.loads(payload_db)
        assert decoded["tool"] == "link_topic_to_iro"
        assert decoded["iro_name"] == "碳費"
    finally:
        engine.close()
