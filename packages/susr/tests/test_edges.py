"""Layer 4 — edges.py 19 typed edges 註冊 + validate_edge 單元測試。

驗證：
    - EDGE_REGISTRY 確實有 19 條（spec §2.4 lock）
    - validate_edge 接受合法 (src, edge_type, dst) 組合
    - validate_edge 對未知 edge_type → raise InvariantError
    - validate_edge 對 src/dst entity_type 對不上 → raise InvariantError
    - list_edge_types 回所有 edge keys
    - Edge dataclass round-trip
"""

from __future__ import annotations

import pytest

from susr.brain.edges import (
    EDGE_REGISTRY,
    Edge,
    EdgeSpec,
    InvariantError,
    list_edge_types,
    validate_edge,
)


def test_edge_registry_has_19_entries() -> None:
    """EDGE_REGISTRY 必須剛好 19 條（與 spec §2.4 鎖定）。"""
    assert len(EDGE_REGISTRY) == 19


def test_edge_registry_contains_phase3_critical_edges() -> None:
    """Phase 3 端到端必要 edges 必須存在。"""
    must_have = {
        "topic_has_iro",
        "iro_addressed_by",
        "action_tracks",
        "target_measures",
        "chapter_conforms_to",
        "discloses_topic",
        "stakeholder_engaged_via",
        "engagement_raised_topic",
        "topic_identified_by",
    }
    missing = must_have - set(EDGE_REGISTRY)
    assert not missing, f"missing critical edges: {missing}"


def test_edge_registry_entries_are_edgespec() -> None:
    """每筆 EDGE_REGISTRY value 都是 EdgeSpec namedtuple。"""
    for k, v in EDGE_REGISTRY.items():
        assert isinstance(v, EdgeSpec), f"{k} not EdgeSpec"
        assert isinstance(v.src, str) and isinstance(v.dst, str)
        assert isinstance(v.description, str) and len(v.description) > 0


def test_list_edge_types_returns_all_keys() -> None:
    """list_edge_types 應回所有 registered key（順序穩定）。"""
    keys = list_edge_types()
    assert set(keys) == set(EDGE_REGISTRY.keys())
    assert len(keys) == 19


def test_validate_edge_accepts_valid_combination() -> None:
    """合法 (topic, topic_has_iro, iro) → 不 raise。"""
    validate_edge("topic", "topic_has_iro", "iro")  # type: ignore[arg-type]
    validate_edge("iro", "iro_addressed_by", "action")  # type: ignore[arg-type]
    validate_edge("chapter", "chapter_conforms_to", "framework")  # type: ignore[arg-type]


def test_validate_edge_rejects_unknown_edge_type() -> None:
    """未知 edge_type → InvariantError。"""
    with pytest.raises(InvariantError, match="unknown edge_type"):
        validate_edge("topic", "not_a_real_edge", "iro")  # type: ignore[arg-type]


def test_validate_edge_rejects_mismatched_src() -> None:
    """src entity_type 對不上 → InvariantError。"""
    with pytest.raises(InvariantError, match="expects"):
        # topic_has_iro 預期 src=topic，給 action 應 fail
        validate_edge("action", "topic_has_iro", "iro")  # type: ignore[arg-type]


def test_validate_edge_rejects_mismatched_dst() -> None:
    """dst entity_type 對不上 → InvariantError。"""
    with pytest.raises(InvariantError, match="expects"):
        # iro_addressed_by 預期 dst=action，給 topic 應 fail
        validate_edge("iro", "iro_addressed_by", "topic")  # type: ignore[arg-type]


def test_edge_dataclass_default_properties_is_empty_dict() -> None:
    """Edge.properties 預設應是 empty dict。"""
    e = Edge(src_slug="topics/E1", dst_slug="iros/x", edge_type="topic_has_iro")
    assert e.properties == {}


def test_edge_validate_convenience_method() -> None:
    """Edge.validate 應 forward 到 validate_edge。"""
    e = Edge(src_slug="topics/E1", dst_slug="iros/x", edge_type="topic_has_iro")
    e.validate("topic", "iro")  # type: ignore[arg-type]

    bad = Edge(src_slug="x", dst_slug="y", edge_type="topic_has_iro")
    with pytest.raises(InvariantError):
        bad.validate("action", "iro")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Engine-level edge writing — depends on BrainEngine.link (R2)
# ---------------------------------------------------------------------------


def test_brain_link_writes_links_row(tmp_brain) -> None:
    """BrainEngine.link 對合法組合應寫 links row。"""
    tmp_brain.put_page(
        slug="topics/E1",
        entity_type="topic",
        title="氣候變遷",
        compiled_truth="",
        file_path="entities/topics/E1.md",
        frontmatter={
            "slug": "E1",
            "name": "氣候變遷",
            "axis": "E",
            "impact_score": 4.5,
            "financial_score": 4.0,
            "materiality_tier": "核心",
        },
    )
    tmp_brain.put_page(
        slug="iros/E1-impact",
        entity_type="iro",
        title="E1 impact",
        compiled_truth="",
        file_path="entities/topics/E1/iro/impact.md",
        frontmatter={
            "slug": "E1-impact",
            "topic_slug": "E1",
            "type": "Impact",
            "category": "op",
            "time_horizon": "M",
            "financial_magnitude": 3.0,
        },
    )
    link_id = tmp_brain.link("topics/E1", "topic_has_iro", "iros/E1-impact")
    assert isinstance(link_id, int) and link_id > 0
    count = tmp_brain.conn.execute(
        "SELECT COUNT(*) FROM links WHERE edge_type='topic_has_iro'"
    ).fetchone()[0]
    assert count == 1


def test_brain_link_rejects_type_mismatch(tmp_brain) -> None:
    """BrainEngine.link 應跑 validate_edge → 不合法組合應 raise。"""
    tmp_brain.put_page(
        slug="topics/E1",
        entity_type="topic",
        title="氣候變遷",
        compiled_truth="",
        file_path="entities/topics/E1.md",
        frontmatter={
            "slug": "E1",
            "name": "氣候變遷",
            "axis": "E",
            "impact_score": 4.5,
            "financial_score": 4.0,
            "materiality_tier": "核心",
        },
    )
    tmp_brain.put_page(
        slug="topics/E2",
        entity_type="topic",
        title="水資源",
        compiled_truth="",
        file_path="entities/topics/E2.md",
        frontmatter={
            "slug": "E2",
            "name": "水資源",
            "axis": "E",
            "impact_score": 3.0,
            "financial_score": 3.0,
            "materiality_tier": "重大",
        },
    )
    # topic_has_iro 預期 dst=iro，給 topic 應 fail
    with pytest.raises(InvariantError):
        tmp_brain.link("topics/E1", "topic_has_iro", "topics/E2")
