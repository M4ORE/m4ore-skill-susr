"""Layer 4 — MCP Phase 3 tools 單元測試（spec §6.2）。

不真的 spawn MCP server / 走 stdio transport。直接 call tool function
+ 驗 return value 結構正確。Pydantic input models 也驗一下 field 約束。

Tools:
    1. search_topics_universe
    2. score_topic_dual_axis        (ImpactScores / FinancialScores / TopicScoreResult)
    3. generate_materiality_matrix  (MaterialityMatrix)
    4. stakeholder_engagement_helper (EngagementRecord)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from susr.mcp.tools.phase3 import (
    EngagementRecord,
    FinancialScores,
    ImpactScores,
    MaterialityMatrix,
    TopicCandidate,
    TopicScoreResult,
    generate_materiality_matrix,
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
