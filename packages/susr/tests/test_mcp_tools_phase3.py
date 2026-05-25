"""Layer 4 — MCP Phase 3 tools 單元測試（spec §6.2）。

不真的 spawn MCP server / 走 stdio transport。直接 call tool function
+ 驗 return value 結構正確。Pydantic input models 也驗一下 field 約束。

Tools:
    1. search_topics_universe
    2. score_topic_dual_axis        (ImpactScores / FinancialScores / TopicScoreResult)
    3. generate_materiality_matrix  (MaterialityMatrix)
    4. stakeholder_engagement_helper (EngagementRecord)

R3 收斂測試：tier resolution（``resolve_materiality_tier`` + ``tier_overrides``）
針對 walkthroughs/lealea-5364-phase3.md §3.265 / §7 backlog #3 的「9 核心 vs
3 核心」雙標準衝突 — frontmatter explicit > auto-suggested 但同時 emit warning。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from susr.mcp.tools.phase3 import (
    EngagementRecord,
    FinancialScores,
    ImpactScores,
    MaterialityMatrix,
    TierOverride,
    TopicCandidate,
    TopicScoreResult,
    _collect_scored_topics,
    generate_materiality_matrix,
    resolve_materiality_tier,
    score_topic_dual_axis,
    search_topics_universe,
    stakeholder_engagement_helper,
)


# ---------------------------------------------------------------------------
# Tool 1 — search_topics_universe
# ---------------------------------------------------------------------------


def test_topic_candidate_model_basic() -> None:
    """TopicCandidate 必備欄位。"""
    tc = TopicCandidate(
        slug="E1",
        name="氣候變遷",
        axis="E",
        industry_specificity="hotel",
        source_kb="shared",
    )
    assert tc.slug == "E1"
    assert tc.axis == "E"


def test_topic_candidate_rejects_invalid_axis() -> None:
    """axis 必須 ∈ {E, S, G}。"""
    with pytest.raises(ValidationError):
        TopicCandidate(slug="X", name="x", axis="Z", source_kb="shared")  # type: ignore[arg-type]


def test_search_topics_universe_returns_list(tmp_client_workspace) -> None:
    """正常呼叫應回 list[TopicCandidate]（R2 完成後）。"""
    out = search_topics_universe(industry="hospitality", framework="GRI", top_k=10)
    assert isinstance(out, list)
    for item in out:
        assert isinstance(item, TopicCandidate)


# ---------------------------------------------------------------------------
# Tool 2 — score_topic_dual_axis
# ---------------------------------------------------------------------------


def test_impact_scores_validates_range() -> None:
    """ImpactScores 每軸 ∈ [1, 5]。"""
    ImpactScores(severity=5, scope=4, irreversibility=3, likelihood=2)
    with pytest.raises(ValidationError):
        ImpactScores(severity=6, scope=1, irreversibility=1, likelihood=1)
    with pytest.raises(ValidationError):
        ImpactScores(severity=0, scope=1, irreversibility=1, likelihood=1)


def test_financial_scores_validates_time_horizon() -> None:
    """time_horizon ∈ {S, M, L}。"""
    FinancialScores(magnitude=4, time_horizon="M", probability=3)
    with pytest.raises(ValidationError):
        FinancialScores(magnitude=4, time_horizon="XL", probability=3)  # type: ignore[arg-type]


def test_topic_score_result_tier_literal() -> None:
    """TopicScoreResult.materiality_tier ∈ {核心, 重大, 邊界}。"""
    TopicScoreResult(
        topic_slug="E1",
        impact_score=4.5,
        financial_score=4.0,
        materiality_tier="核心",
        page_file="entities/topics/E1.md",
        timeline_entry_id=1,
    )
    with pytest.raises(ValidationError):
        TopicScoreResult(
            topic_slug="E1",
            impact_score=4.5,
            financial_score=4.0,
            materiality_tier="不存在的層級",  # type: ignore[arg-type]
            page_file="x",
            timeline_entry_id=1,
        )


def test_score_topic_dual_axis_returns_result(tmp_client_workspace) -> None:
    """正常呼叫 → 回 TopicScoreResult，tier 應在合法集合內。"""
    result = score_topic_dual_axis(
        client_slug="test-client",
        topic_slug="E1",
        impact=ImpactScores(severity=5, scope=5, irreversibility=4, likelihood=4),
        financial=FinancialScores(magnitude=4, time_horizon="L", probability=4),
        actor="consultant:test",
    )
    assert isinstance(result, TopicScoreResult)
    assert result.materiality_tier in ("核心", "重大", "邊界")


# ---------------------------------------------------------------------------
# Tool 3 — generate_materiality_matrix
# ---------------------------------------------------------------------------


def test_materiality_matrix_model_basic() -> None:
    """MaterialityMatrix 預設 invariant_violations = []。"""
    mm = MaterialityMatrix(
        matrix_md_path="materiality-2025.md",
        matrix_svg_path="materiality-2025.svg",
        core_topics=["E1"],
        material_topics=["E2", "S1"],
        border_topics=[],
        invariants_passed=True,
    )
    assert mm.invariant_violations == []


def test_generate_materiality_matrix_returns_matrix(tmp_client_workspace) -> None:
    """generate_materiality_matrix → 回 MaterialityMatrix 結構。"""
    result = generate_materiality_matrix(
        client_slug="test-client", year=2025, include_svg=True
    )
    assert isinstance(result, MaterialityMatrix)
    assert isinstance(result.core_topics, list)
    assert isinstance(result.invariant_violations, list)


# ---------------------------------------------------------------------------
# Tool 4 — stakeholder_engagement_helper
# ---------------------------------------------------------------------------


def test_engagement_record_model_basic() -> None:
    """EngagementRecord 結構。"""
    er = EngagementRecord(
        engagement_slug="2025-03-employee-survey",
        page_file="entities/stakeholders/員工/engagements/2025-03.md",
        topics_raised=["S1", "S2"],
        timeline_entry_id=42,
    )
    assert er.engagement_slug == "2025-03-employee-survey"
    assert len(er.topics_raised) == 2


def test_stakeholder_engagement_helper_creates_record(tmp_client_workspace) -> None:
    """stakeholder_engagement_helper → 回 EngagementRecord。"""
    result = stakeholder_engagement_helper(
        client_slug="test-client",
        stakeholder_slug="員工",
        method="問卷",
        date="2025-03-15",
        sample_size=254,
        topics_raised=["S1", "S2"],
        findings_summary="流動率高、夜班疲勞",
        evidence_refs=["survey-2025-q1"],
        actor="consultant:test",
    )
    assert isinstance(result, EngagementRecord)
    assert "S1" in result.topics_raised


# ---------------------------------------------------------------------------
# R3 — Tier resolution（walkthrough §3.265 / §7 backlog #3 P0c 收斂）
# ---------------------------------------------------------------------------


def _ws_path(tmp_client_workspace) -> Path:
    """從 tmp_client_workspace fixture（dict 回傳值）取出 workspace 根目錄 Path。"""
    if isinstance(tmp_client_workspace, dict):
        return Path(tmp_client_workspace["workspace_path"])
    return Path(tmp_client_workspace)


def _write_topic(client_path: Path, slug: str, fm: dict) -> Path:
    """測試 helper：在 tmp client workspace 內寫一個 minimal topic md。"""
    import yaml

    page = client_path / "entities" / "topics" / f"{slug}.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    base = {"slug": slug, "name": fm.get("name", slug), "axis": fm.get("axis", "E")}
    base.update(fm)
    serialized = yaml.safe_dump(base, allow_unicode=True, sort_keys=False)
    page.write_text(f"---\n{serialized}---\n\n# {slug}\n", encoding="utf-8")
    return page


def test_resolve_tier_both_high_auto_returns_core() -> None:
    """impact=5, financial=5, fm=None → auto_tier=核心，無 warning。"""
    tier, warning = resolve_materiality_tier(None, 5.0, 5.0)
    assert tier == "核心"
    assert warning is None


def test_resolve_tier_frontmatter_overrides_auto() -> None:
    """impact=2, financial=2, fm=核心 → 採核心（顧問 explicit 優先）+ warning。"""
    tier, warning = resolve_materiality_tier("核心", 2.0, 2.0)
    assert tier == "核心"
    assert warning is not None
    assert "顧問 explicit" in warning
    assert "kept explicit" in warning
    assert "auto-suggested" in warning


def test_resolve_tier_explicit_matches_auto_no_warning() -> None:
    """fm 與 auto 一致 → 無 warning。"""
    # Both auto and fm say 核心
    tier, warning = resolve_materiality_tier("核心", 4.5, 4.0)
    assert tier == "核心"
    assert warning is None
    # Both say 重大
    tier, warning = resolve_materiality_tier("重大", 3.5, 3.0)
    assert tier == "重大"
    assert warning is None
    # Both say 邊界
    tier, warning = resolve_materiality_tier("邊界", 2.0, 2.0)
    assert tier == "邊界"
    assert warning is None


def test_resolve_tier_no_frontmatter_uses_auto() -> None:
    """fm=None → 直接採 auto_tier。"""
    tier, warning = resolve_materiality_tier(None, 4.5, 4.5)
    assert tier == "核心"
    assert warning is None

    tier, warning = resolve_materiality_tier(None, 3.5, 2.0)
    assert tier == "重大"
    assert warning is None

    tier, warning = resolve_materiality_tier(None, 1.5, 2.0)
    assert tier == "邊界"
    assert warning is None


def test_resolve_tier_invalid_fm_value_falls_back_to_auto() -> None:
    """fm 為非法字串 → fallback 回 auto + warning。"""
    tier, warning = resolve_materiality_tier("invalid-tier", 5.0, 5.0)
    assert tier == "核心"
    assert warning is not None
    assert "非法值" in warning
    assert "auto-suggested" in warning


def test_collect_scored_topics_uses_resolved_tier(tmp_client_workspace) -> None:
    """寫一個 fm=核心 但 score=2,2 的 topic → collect 後仍為核心但 tier_warning 有值。"""
    ws = _ws_path(tmp_client_workspace)
    _write_topic(
        ws,
        "X1-test",
        {
            "name": "test topic",
            "axis": "E",
            "impact_score": 2.0,
            "financial_score": 2.0,
            "materiality_tier": "核心",
        },
    )
    rows = _collect_scored_topics(ws)
    assert len(rows) == 1
    r = rows[0]
    assert r["slug"] == "X1-test"
    assert r["tier"] == "核心"  # frontmatter explicit honored
    assert r["auto_tier"] == "邊界"  # auto-suggested would have been 邊界
    assert r["frontmatter_tier"] == "核心"
    assert r["tier_warning"] is not None
    assert "kept explicit" in r["tier_warning"]


def test_materiality_matrix_emits_tier_overrides(tmp_client_workspace) -> None:
    """generate_materiality_matrix 輸出含 tier_overrides 欄位列舉差異 topics。"""
    ws = _ws_path(tmp_client_workspace)
    # Topic A: explicit override (fm=核心, scores low → auto 邊界) — 應入 overrides
    _write_topic(
        ws,
        "A-override",
        {
            "name": "override sample",
            "axis": "S",
            "impact_score": 2.0,
            "financial_score": 2.0,
            "materiality_tier": "核心",
        },
    )
    # Topic B: fm matches auto (scores high, fm=核心) — 不入 overrides
    _write_topic(
        ws,
        "B-match",
        {
            "name": "match sample",
            "axis": "E",
            "impact_score": 4.5,
            "financial_score": 4.5,
            "materiality_tier": "核心",
        },
    )
    # Topic C: no fm tier, scores moderate — 不入 overrides
    _write_topic(
        ws,
        "C-auto-only",
        {
            "name": "auto-only sample",
            "axis": "G",
            "impact_score": 3.5,
            "financial_score": 3.0,
            # no materiality_tier
        },
    )
    result = generate_materiality_matrix(
        client_slug="test-client", year=2025, include_svg=False
    )
    assert isinstance(result, MaterialityMatrix)
    assert isinstance(result.tier_overrides, list)
    slugs_in_overrides = {ov.slug for ov in result.tier_overrides}
    assert "A-override" in slugs_in_overrides
    assert "B-match" not in slugs_in_overrides
    assert "C-auto-only" not in slugs_in_overrides

    a = next(ov for ov in result.tier_overrides if ov.slug == "A-override")
    assert a.resolved_tier == "核心"
    assert a.auto_suggested_tier == "邊界"
    assert a.frontmatter_tier == "核心"
    assert "kept explicit" in a.warning

    # Matrix .md 應提到 Tier 覆寫段落
    md_text = Path(result.matrix_md_path).read_text(encoding="utf-8")
    assert "Tier 覆寫" in md_text
    assert "A-override" in md_text


def test_lealea_3_vs_9_core_after_resolve(tmp_client_workspace) -> None:
    """用 lealea entities/topics/ 複製進 tmp workspace，跑 _collect_scored_topics。

    SP1-004 顧問 explicit 在 9 個 topic 標「核心」（E1/E2/G2/G3/S1/S4/S6/S7/S8）。
    在 hybrid 收斂方案下，顧問 explicit 優先 → resolved core 仍然 = 9，
    但其中 6 個 (S1/S4/S7/S8/G2/G3) 會帶 warning（impact<4 或 financial<4）。

    斷言：
    - resolved 核心數 == 9（honor SP1-004 顧問判斷）
    - warning 數 == 6（auto-suggested 算嚴格 ≥4 才核心，只有 E1/E2/S6 兩軸全 ≥4）
    - 三個「無 warning 的核心」（E1/E2/S6）對齊 SP1-004 §5 原版的 3 核心
    """
    ws = _ws_path(tmp_client_workspace)
    repo_root = Path(__file__).resolve().parents[3]
    src_topics = repo_root / "examples" / "lealea-5364" / "entities" / "topics"
    assert src_topics.exists(), f"lealea fixture not found: {src_topics}"

    selected = [
        "E1-climate.md", "E2-energy.md", "E3-water.md", "E7-biodiversity.md",
        "S1-labor-conditions.md", "S4-occupational-health.md",
        "S6-food-safety.md", "S7-customer-privacy.md", "S8-customer-experience.md",
        "S12-indigenous-culture.md",
        "G1-governance-structure.md", "G2-integrity.md", "G3-compliance.md",
    ]
    dst = ws / "entities" / "topics"
    dst.mkdir(parents=True, exist_ok=True)
    for fn in selected:
        # Strip the assessed_at line — PyYAML auto-parses YYYY-MM-DD to date,
        # but _read_md only reads frontmatter, not validates TopicFrontmatter,
        # so this only matters in the lealea brain walkthrough (not here).
        (dst / fn).write_text(
            (src_topics / fn).read_text(encoding="utf-8"), encoding="utf-8"
        )

    rows = _collect_scored_topics(ws)
    assert len(rows) == 13, f"expected 13 lealea topics, got {len(rows)}"

    resolved_core = [r["slug"] for r in rows if r["tier"] == "核心"]
    warnings = [r for r in rows if r["tier_warning"] is not None]
    no_warning_core = [
        r for r in rows if r["tier"] == "核心" and r["tier_warning"] is None
    ]

    # SP1-004 explicit: 9 topics 標核心
    assert len(resolved_core) == 9, (
        f"expected 9 resolved core (SP1-004 顧問 explicit), got {len(resolved_core)}: "
        f"{resolved_core}"
    )

    # 嚴格 auto: 只有 E1/E2/S6 兩軸都 ≥4 — 其餘 6 個核心都帶 warning
    no_warn_slugs = {r["slug"] for r in no_warning_core}
    assert no_warn_slugs == {"E1-climate", "E2-energy", "S6-food-safety"}, (
        f"expected SP1-004 §5 'strict 3 core' to be the no-warning subset, "
        f"got {no_warn_slugs}"
    )
    # 對應 6 個 explicit override warning
    assert len(warnings) == 6, f"expected 6 tier overrides warned, got {len(warnings)}"


# ---------------------------------------------------------------------------
# R4a — score_topic_dual_axis 走 resolve_materiality_tier 而非直接覆寫
# （walkthroughs/lealea-5364-phase3-r3.md §5.1 P1 修補）
# ---------------------------------------------------------------------------


def test_score_topic_preserves_explicit_tier_with_warning(tmp_client_workspace) -> None:
    """顧問先 explicit `materiality_tier='核心'`，後 scoring 低分不該被自動結果吞掉。

    R4a 場景：先 put_page Topic E1 frontmatter `materiality_tier='核心'`，
    再 score_topic_dual_axis 給 impact=2 financial=2。score path 必須走
    resolve_materiality_tier → honor explicit "核心" 並 emit warning，**不**
    把 frontmatter overwrite 成 auto-suggested 的「邊界」。
    """
    ws = _ws_path(tmp_client_workspace)
    _write_topic(
        ws,
        "E1",
        {"name": "氣候變遷", "axis": "E", "materiality_tier": "核心"},
    )
    result = score_topic_dual_axis(
        client_slug="test-client",
        topic_slug="E1",
        impact=ImpactScores(severity=2, scope=2, irreversibility=2, likelihood=2),
        financial=FinancialScores(magnitude=2, time_horizon="S", probability=2),
        actor="consultant:test",
    )

    # 1) 顧問 explicit 仍為核心（不被吞）
    assert result.materiality_tier == "核心"
    # 2) Response 含 warning，指出與 auto 不一致
    assert result.tier_resolution_warning is not None
    assert "kept explicit" in result.tier_resolution_warning
    assert "auto-suggested" in result.tier_resolution_warning

    # 3) frontmatter 寫回的 materiality_tier 仍為核心
    from susr.mcp.tools.phase3 import _read_md

    fm, body = _read_md(ws / "entities" / "topics" / "E1.md")
    assert fm["materiality_tier"] == "核心"

    # 4) timeline body 含 warning detail（額外 verify 條目，supports audit trail）
    #    note: warning 在 JSON payload 中字串字面會 escape 引號，故用核心 substring 偵測
    assert "kept explicit" in body
    assert "auto_tier" in body  # 額外 audit 條目的 payload key
    assert "resolved_tier" in body
    # 應有兩個 timeline entry（一個 scoring 主條目 + 一個 warning audit 條目）
    import re as _re

    entries = _re.findall(r"^- \[", body, _re.MULTILINE)
    assert len(entries) == 2, f"expected 2 timeline entries (score + warning), got {len(entries)}"


def test_score_topic_no_warning_when_aligned(tmp_client_workspace) -> None:
    """fm 無 explicit tier 且 score 對齊 auto → 不該 emit warning，timeline 無 warning 條目。"""
    ws = _ws_path(tmp_client_workspace)
    # 故意不寫 materiality_tier
    _write_topic(ws, "E1", {"name": "氣候變遷", "axis": "E"})

    result = score_topic_dual_axis(
        client_slug="test-client",
        topic_slug="E1",
        impact=ImpactScores(severity=5, scope=5, irreversibility=5, likelihood=5),
        financial=FinancialScores(magnitude=5, time_horizon="L", probability=5),
        actor="consultant:test",
    )

    assert result.materiality_tier == "核心"
    assert result.tier_resolution_warning is None

    # frontmatter 寫入核心
    from susr.mcp.tools.phase3 import _read_md

    fm, body = _read_md(ws / "entities" / "topics" / "E1.md")
    assert fm["materiality_tier"] == "核心"

    # timeline 僅有單一 scoring 條目，無 warning audit
    import re as _re

    entries = _re.findall(r"^- \[", body, _re.MULTILINE)
    assert len(entries) == 1, f"expected exactly 1 timeline entry (no warning), got {len(entries)}"
    assert "kept explicit" not in body


def test_score_topic_then_matrix_shows_tier_overrides(tmp_client_workspace) -> None:
    """先 score 6 個 explicit-vs-auto 衝突的 topic，再生成矩陣 → tier_overrides=6。

    這是 R3-verify §5.1 揭露 bug 的回歸測試：在原 R4a bug 下，score path 直接
    把顧問 explicit 覆寫成 auto，導致後續 matrix 看不到任何衝突；現在 score path
    走 resolve_materiality_tier，6 個衝突會被完整保留並在 matrix 顯示。

    對照 lealea SP1-004 § scoring：6 個顧問 explicit "核心" 但 auto 算「重大」
    的 topic（G2/G3/S1/S4/S7/S8 模式）。
    """
    ws = _ws_path(tmp_client_workspace)
    # 6 個 topic：顧問 explicit "核心"，但 score 算出來 auto-suggested 是「重大」
    # （impact 或 financial 其中一軸 <4，另一軸 ≥3.5 → 重大）
    conflict_topics = [
        ("G2-integrity",  3.5, 4.0),
        ("G3-compliance", 3.5, 4.0),
        ("S1-labor",      4.0, 3.5),
        ("S4-health",     4.0, 3.5),
        ("S7-privacy",    3.5, 4.0),
        ("S8-experience", 3.0, 4.0),
    ]
    for slug, _i, _f in conflict_topics:
        _write_topic(
            ws,
            slug,
            {"name": slug, "axis": "S", "materiality_tier": "核心"},
        )

    # score 6 次（impact severity/scope/irreversibility/likelihood 平均 → impact_score；
    # financial magnitude/probability 平均 → financial_score）。為了精確命中目標分數，
    # 直接給四項相同 severity 等於目標 impact_score；兩項 magnitude/probability 等於 financial。
    for slug, target_impact, target_financial in conflict_topics:
        score_topic_dual_axis(
            client_slug="test-client",
            topic_slug=slug,
            impact=ImpactScores(
                severity=target_impact, scope=target_impact,
                irreversibility=target_impact, likelihood=target_impact,
            ),
            financial=FinancialScores(
                magnitude=target_financial, time_horizon="M", probability=target_financial,
            ),
            actor="consultant:test",
        )

    # 額外加 1 個 aligned topic（score=核心 / fm=核心）— 不該算 override
    _write_topic(
        ws,
        "E1-aligned",
        {"name": "對齊樣本", "axis": "E", "materiality_tier": "核心"},
    )
    score_topic_dual_axis(
        client_slug="test-client",
        topic_slug="E1-aligned",
        impact=ImpactScores(severity=5, scope=5, irreversibility=5, likelihood=5),
        financial=FinancialScores(magnitude=5, time_horizon="L", probability=5),
        actor="consultant:test",
    )

    matrix = generate_materiality_matrix(
        client_slug="test-client", year=2025, include_svg=False
    )

    # 6 個衝突全部以 override 形式被保留（R4a bug 修補前會是 0）
    override_slugs = {ov.slug for ov in matrix.tier_overrides}
    expected = {slug for slug, _i, _f in conflict_topics}
    assert override_slugs == expected, (
        f"expected 6 explicit-vs-auto overrides {expected}, got {override_slugs}"
    )
    assert len(matrix.tier_overrides) == 6
    # aligned 不該入 overrides
    assert "E1-aligned" not in override_slugs
    # 所有 override 的 resolved_tier 仍為核心（honor explicit），auto 為重大
    for ov in matrix.tier_overrides:
        assert ov.resolved_tier == "核心"
        assert ov.auto_suggested_tier == "重大"
        assert ov.frontmatter_tier == "核心"
