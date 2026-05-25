"""Layer 4 — RRF 數學 + hybrid_search smoke 測試（spec §3）。

RRF 公式：score(d) = sum_r 1 / (k + rank_r(d))，k 預設 60。

本檔對 rrf_merge 用已知 input 算 expected output 並用 pytest.approx
驗證；對 hybrid_search 用 mock_embedding_provider fixture 跑 smoke。
"""

from __future__ import annotations

import pytest

from susr.brain.search import RRF_K, SearchResult, hybrid_search, rrf_merge


# ---------------------------------------------------------------------------
# RRF math — deterministic, no DB needed
# ---------------------------------------------------------------------------


def test_rrf_empty_input_returns_empty() -> None:
    """空 input → 空 output。"""
    assert rrf_merge([]) == []
    assert rrf_merge([[]]) == []


def test_rrf_single_list_preserves_order() -> None:
    """只一條 rank list → 順序保留、score 單調遞減。"""
    result = rrf_merge([[10, 20, 30]], k=60)
    page_ids = [pid for pid, _ in result]
    assert page_ids == [10, 20, 30]
    scores = [s for _, s in result]
    assert scores[0] > scores[1] > scores[2]


def test_rrf_known_math_two_lists() -> None:
    """兩條 list 已知 input → 對照手算 expected output。

    list1 = [1, 2, 3]   (ranks 1, 2, 3)
    list2 = [3, 2, 1]   (ranks 1, 2, 3)
    k = 60

    pid 1: 1/(60+1) + 1/(60+3) = 1/61 + 1/63 ≈ 0.032266
    pid 2: 1/(60+2) + 1/(60+2) = 2/62         ≈ 0.032258
    pid 3: 1/(60+3) + 1/(60+1) = 1/63 + 1/61 ≈ 0.032266

    1 與 3 對稱，分數相等；2 略低（因為 1/61 + 1/63 > 2/62 — 凸函式效應）。
    """
    result = rrf_merge([[1, 2, 3], [3, 2, 1]], k=60)
    score_map = {pid: s for pid, s in result}
    expected_1 = 1 / 61 + 1 / 63
    expected_2 = 2 / 62
    expected_3 = 1 / 63 + 1 / 61
    assert score_map[1] == pytest.approx(expected_1, abs=1e-9)
    assert score_map[2] == pytest.approx(expected_2, abs=1e-9)
    assert score_map[3] == pytest.approx(expected_3, abs=1e-9)
    # 1 與 3 應等分
    assert score_map[1] == pytest.approx(score_map[3], abs=1e-12)
    # 2 應略低（凸函式效應 — 1/x 凸性使 extreme ranks 的和 > 中位 ranks 的和）
    assert score_map[1] > score_map[2]


def test_rrf_top_one_consensus_wins() -> None:
    """兩條 list 都把同一 pid 放第一 → 該 pid 應 score 最高。

    這是直覺上「RRF 該做的事」最乾淨的 case：consensus rank-1 拿雙倍 1/61。
    """
    result = rrf_merge([[42, 1, 2, 3], [42, 9, 8, 7]], k=60)
    assert result[0][0] == 42
    assert result[0][1] == pytest.approx(2 / 61, abs=1e-9)


def test_rrf_k_default_matches_spec() -> None:
    """RRF_K default = 60（spec §3.1）。"""
    assert RRF_K == 60


def test_rrf_custom_k() -> None:
    """改 k → 不同 score（k 越大，rank 差異被壓得越平）。"""
    r60 = rrf_merge([[1, 2]], k=60)
    r10 = rrf_merge([[1, 2]], k=10)
    s60_diff = r60[0][1] - r60[1][1]
    s10_diff = r10[0][1] - r10[1][1]
    assert s10_diff > s60_diff, "smaller k should widen top-vs-rest gap"


def test_rrf_deduplicates_within_list() -> None:
    """同 page_id 在同 list 中重複出現 → 只算第一次。

    例：[[1, 1, 2]] 中 pid=1 應只記 rank=1，不疊加 rank=2 的 score。
    """
    r_dup = rrf_merge([[1, 1, 2]], k=60)
    r_clean = rrf_merge([[1, 2]], k=60)
    score_dup = {pid: s for pid, s in r_dup}
    score_clean = {pid: s for pid, s in r_clean}
    assert score_dup[1] == pytest.approx(score_clean[1], abs=1e-12)
    assert score_dup[2] == pytest.approx(score_clean[2], abs=1e-12)


def test_rrf_three_lists() -> None:
    """三條 list → 每條都加分（驗證可變參數）。

    pid=1 出現在三條 list 的 rank=1 位置 → 應拿 3 × 1/(60+1)。
    """
    result = rrf_merge([[1], [1], [1]], k=60)
    score_map = {pid: s for pid, s in result}
    assert score_map[1] == pytest.approx(3 / 61, abs=1e-9)


# ---------------------------------------------------------------------------
# hybrid_search — needs DB + (optional) embed_provider
# ---------------------------------------------------------------------------


def test_hybrid_search_fts_only_returns_empty_for_empty_db(tmp_db) -> None:
    """空 DB → search 回空 list（不 raise）。"""
    out = hybrid_search(tmp_db, "氣候變遷", embed_provider=None, top_k=5)
    assert out == []


def test_hybrid_search_fts_finds_inserted_page(tmp_brain) -> None:
    """put_page 後 FTS-only search 應找得到（vector 走 fallback）。"""
    tmp_brain.put_page(
        slug="topics/E1",
        entity_type="topic",
        title="氣候變遷",
        compiled_truth="氣候變遷是核心議題，需要立即行動。",
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
    results = hybrid_search(tmp_brain.conn, "氣候變遷", embed_provider=None, top_k=5)
    assert len(results) >= 1
    assert all(isinstance(r, SearchResult) for r in results)
    slugs = [r.slug for r in results]
    assert "topics/E1" in slugs


def test_hybrid_search_respects_top_k(tmp_brain) -> None:
    """top_k 限制 → 結果不超過 top_k。"""
    for i in range(5):
        tmp_brain.put_page(
            slug=f"topics/T{i}",
            entity_type="topic",
            title=f"議題 {i} 永續",
            compiled_truth="永續報告書相關段落。",
            file_path=f"entities/topics/T{i}.md",
            frontmatter={
                "slug": f"T{i}",
                "name": f"議題{i}",
                "axis": "E",
                "impact_score": 3.0,
                "financial_score": 3.0,
                "materiality_tier": "重大",
            },
        )
    results = hybrid_search(tmp_brain.conn, "永續", embed_provider=None, top_k=3)
    assert len(results) <= 3


def test_hybrid_search_with_mock_embedding(tmp_brain, mock_embedding_provider) -> None:
    """掛 mock embedding provider → 不爆，正常回 results（可能含 vec leg）。"""
    tmp_brain.put_page(
        slug="topics/E1",
        entity_type="topic",
        title="氣候變遷",
        compiled_truth="氣候變遷是核心議題。",
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
    results = hybrid_search(
        tmp_brain.conn,
        "氣候",
        embed_provider=mock_embedding_provider,
        top_k=5,
    )
    # 沒插 vec_chunks，所以 vec leg 應 silently fall back；至少 FTS 找得到
    assert isinstance(results, list)
