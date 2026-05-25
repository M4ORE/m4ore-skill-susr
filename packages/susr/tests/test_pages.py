"""Layer 4 — pages.py slug 兼容性測試（R4c 收斂）。

對應 ``CLAUDE.md §8 R4c — brain page slug 雙慣例統一``：

* prefixed slug（``topics/E1`` / ``iros/E1-001``）= source of truth
* unqualified slug（``E1``）作為**輸入端兼容**仍能查到 prefixed page
* ambiguous slug raise ``AmbiguousSlugError``
* ingest 自動補 prefix（``frontmatter.slug`` 保留 unqualified，
  ``pages.slug`` 為 canonical prefixed）

本檔只測 slug 行為；CRUD / FTS / soft-delete 仍在 ``test_pages_crud.py``。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from susr.brain._slug import (
    AmbiguousSlugError,
    ENTITY_TYPE_PREFIX,
    prefixed_slug,
    resolve_slug,
    slug_unqualified,
)
from susr.brain.ingest import ingest_directory, ingest_markdown_file
from susr.brain.pages import get_page, put_page


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_topic_fm(slug: str = "E1") -> dict:
    return {
        "slug": slug,
        "name": f"Topic {slug}",
        "axis": "E",
        "impact_score": 4.5,
        "financial_score": 4.0,
        "materiality_tier": "核心",
    }


def _minimal_iro_fm(slug: str = "E1-001") -> dict:
    return {
        "slug": slug,
        "topic_slug": "E1",
        "type": "Impact",
        "category": "physical",
        "time_horizon": "M",
        "financial_magnitude": 1_000_000.0,
    }


# ---------------------------------------------------------------------------
# prefixed_slug — 補前綴
# ---------------------------------------------------------------------------


def test_prefixed_slug_basic() -> None:
    """``prefixed_slug("topic", "E1")`` → ``"topics/E1"``。"""
    assert prefixed_slug("topic", "E1") == "topics/E1"
    assert prefixed_slug("iro", "E1-001") == "iros/E1-001"
    assert prefixed_slug("chapter", "E1-climate") == "chapters/E1-climate"
    assert prefixed_slug("framework", "GRI-305") == "frameworks/GRI-305"


def test_prefixed_slug_all_entity_types_covered() -> None:
    """ENTITY_TYPE_PREFIX 覆蓋所有 ENTITY_SCHEMAS（lock-step 對齊）。"""
    from susr.brain.entities import ENTITY_SCHEMAS
    assert set(ENTITY_TYPE_PREFIX.keys()) == set(ENTITY_SCHEMAS.keys()), (
        "ENTITY_TYPE_PREFIX 與 ENTITY_SCHEMAS 必須一致，否則新 entity_type "
        "ingest 時會 ValueError"
    )


def test_prefixed_slug_idempotent() -> None:
    """已 prefixed 的 slug 不重複加 prefix（``prefixed_slug(x) == prefixed_slug(prefixed_slug(x))``）。"""
    once = prefixed_slug("topic", "E1")
    twice = prefixed_slug("topic", once)
    assert once == twice == "topics/E1"


def test_prefixed_slug_strips_leading_trailing_slash() -> None:
    """``"/E1/"`` → ``"topics/E1"``（顧問手打容忍）。"""
    assert prefixed_slug("topic", "/E1") == "topics/E1"
    assert prefixed_slug("topic", "E1/") == "topics/E1"
    assert prefixed_slug("topic", "  /E1/  ") == "topics/E1"


def test_prefixed_slug_unknown_entity_type_raises() -> None:
    """``entity_type`` 不在 ``ENTITY_SCHEMAS`` → ``ValueError``（防 typo）。"""
    with pytest.raises(ValueError, match="unknown entity_type"):
        prefixed_slug("topix", "E1")  # 故意 typo


def test_prefixed_slug_empty_raises() -> None:
    """空 slug → ``ValueError``。"""
    with pytest.raises(ValueError):
        prefixed_slug("topic", "")
    with pytest.raises(ValueError):
        prefixed_slug("topic", "  ")
    with pytest.raises(ValueError):
        prefixed_slug("topic", "/")


def test_prefixed_slug_mismatch_prefix_raises() -> None:
    """``slug="iros/X"`` 但 ``entity_type="topic"`` → ``ValueError``（caller bug）。"""
    with pytest.raises(ValueError, match="entity_type"):
        prefixed_slug("topic", "iros/X")


def test_prefixed_slug_multi_segment_path_ok() -> None:
    """``"2024/Q4"`` 不是已知 prefix → 補成 ``"targets/2024/Q4"``。

    覆蓋顧問用「年/季」做 target slug 的多層命名習慣。
    """
    assert prefixed_slug("target", "2024/Q4") == "targets/2024/Q4"


def test_prefixed_slug_governance_no_pluralization() -> None:
    """``governance`` entity_type 已是群體名 → 不再 +s。"""
    assert prefixed_slug("governance", "esg-committee") == "governance/esg-committee"


# ---------------------------------------------------------------------------
# slug_unqualified — 還原為 UI form
# ---------------------------------------------------------------------------


def test_slug_unqualified_strips_prefix() -> None:
    """``"topics/E1"`` → ``"E1"``。"""
    assert slug_unqualified("topics/E1") == "E1"
    assert slug_unqualified("iros/E1-001") == "E1-001"
    assert slug_unqualified("chapters/E1-climate") == "E1-climate"


def test_slug_unqualified_no_prefix_identity() -> None:
    """無 prefix 的 slug 不被改（``E1`` → ``E1``）。"""
    assert slug_unqualified("E1") == "E1"
    assert slug_unqualified("flood-risk-action") == "flood-risk-action"


def test_slug_unqualified_multi_segment_strips_outermost() -> None:
    """``"targets/2024/Q4"`` → ``"2024/Q4"``（只剝最外層 prefix）。"""
    assert slug_unqualified("targets/2024/Q4") == "2024/Q4"


# ---------------------------------------------------------------------------
# resolve_slug — DB 查詢含後綴匹配
# ---------------------------------------------------------------------------


def test_resolve_slug_prefixed_finds_page(tmp_db) -> None:
    """``resolve_slug("topics/E1")`` → ``"topics/E1"``（直接命中）。"""
    put_page(
        tmp_db, slug="topics/E1", entity_type="topic", title="氣候",
        compiled_truth="", file_path="x.md", frontmatter=_minimal_topic_fm(),
    )
    assert resolve_slug(tmp_db, "topics/E1") == "topics/E1"


def test_resolve_slug_unqualified_finds_prefixed(tmp_db) -> None:
    """``resolve_slug("E1")`` 在 ``topics/E1`` 存在時 → 仍能找到。"""
    put_page(
        tmp_db, slug="topics/E1", entity_type="topic", title="氣候",
        compiled_truth="", file_path="x.md", frontmatter=_minimal_topic_fm(),
    )
    assert resolve_slug(tmp_db, "E1") == "topics/E1"


def test_resolve_slug_unqualified_with_entity_type_filter(tmp_db) -> None:
    """同 ``E1`` 在 topics 與 iros 都存在時，``entity_type="topic"`` 仍能消歧。"""
    put_page(
        tmp_db, slug="topics/E1", entity_type="topic", title="氣候",
        compiled_truth="", file_path="x.md", frontmatter=_minimal_topic_fm("E1"),
    )
    # 用不同的 IRO slug 避開「同 slug 雙 entity_type」更困難的情境
    put_page(
        tmp_db, slug="iros/E1", entity_type="iro", title="氣候 IRO",
        compiled_truth="", file_path="y.md", frontmatter=_minimal_iro_fm("E1"),
    )
    assert resolve_slug(tmp_db, "E1", entity_type="topic") == "topics/E1"
    assert resolve_slug(tmp_db, "E1", entity_type="iro") == "iros/E1"


def test_resolve_slug_ambiguous_raises(tmp_db) -> None:
    """unqualified slug 對應 ≥2 entity_type pages 且無 entity_type filter → raise。"""
    put_page(
        tmp_db, slug="topics/E1", entity_type="topic", title="氣候",
        compiled_truth="", file_path="x.md", frontmatter=_minimal_topic_fm("E1"),
    )
    put_page(
        tmp_db, slug="iros/E1", entity_type="iro", title="氣候 IRO",
        compiled_truth="", file_path="y.md", frontmatter=_minimal_iro_fm("E1"),
    )
    with pytest.raises(AmbiguousSlugError, match="ambiguous"):
        resolve_slug(tmp_db, "E1")  # 沒給 entity_type → 應 raise


def test_resolve_slug_missing_returns_none(tmp_db) -> None:
    """slug 不存在 → ``None``（不 raise）。"""
    assert resolve_slug(tmp_db, "E999") is None
    assert resolve_slug(tmp_db, "topics/E999") is None


def test_resolve_slug_skips_soft_deleted(tmp_db) -> None:
    """soft-deleted 的 page 不該被 resolve 找到。"""
    from susr.brain.pages import soft_delete
    pid = put_page(
        tmp_db, slug="topics/E1", entity_type="topic", title="氣候",
        compiled_truth="", file_path="x.md", frontmatter=_minimal_topic_fm(),
    )
    soft_delete(tmp_db, pid)
    assert resolve_slug(tmp_db, "E1") is None
    assert resolve_slug(tmp_db, "topics/E1") is None


def test_resolve_slug_handles_whitespace_and_slashes(tmp_db) -> None:
    """``"  /E1/  "`` → ``"topics/E1"``（清洗後查得到）。"""
    put_page(
        tmp_db, slug="topics/E1", entity_type="topic", title="氣候",
        compiled_truth="", file_path="x.md", frontmatter=_minimal_topic_fm(),
    )
    assert resolve_slug(tmp_db, "  E1  ") == "topics/E1"
    assert resolve_slug(tmp_db, "/E1/") == "topics/E1"


# ---------------------------------------------------------------------------
# get_page — 雙慣例輸入兼容
# ---------------------------------------------------------------------------


def test_get_page_prefixed_roundtrip(tmp_db) -> None:
    """put_page("topics/E1") → get_page("topics/E1") OK（既有行為 regression）。"""
    put_page(
        tmp_db, slug="topics/E1", entity_type="topic", title="氣候",
        compiled_truth="", file_path="x.md", frontmatter=_minimal_topic_fm(),
    )
    page = get_page(tmp_db, "topics/E1")
    assert page is not None
    assert page.slug == "topics/E1"


def test_get_page_unqualified_finds_prefixed(tmp_db) -> None:
    """put_page("topics/E1") → get_page("E1") 也能找到（R4c 新行為）。"""
    put_page(
        tmp_db, slug="topics/E1", entity_type="topic", title="氣候",
        compiled_truth="", file_path="x.md", frontmatter=_minimal_topic_fm(),
    )
    page = get_page(tmp_db, "E1")
    assert page is not None
    assert page.slug == "topics/E1"  # 回傳的 page.slug 仍是 canonical prefixed


def test_get_page_ambiguous_unqualified_raises(tmp_db) -> None:
    """unqualified slug 在 DB 有多 entity_type page → propagate AmbiguousSlugError。"""
    put_page(
        tmp_db, slug="topics/E1", entity_type="topic", title="氣候",
        compiled_truth="", file_path="x.md", frontmatter=_minimal_topic_fm("E1"),
    )
    put_page(
        tmp_db, slug="iros/E1", entity_type="iro", title="氣候 IRO",
        compiled_truth="", file_path="y.md", frontmatter=_minimal_iro_fm("E1"),
    )
    with pytest.raises(AmbiguousSlugError):
        get_page(tmp_db, "E1")


def test_get_page_unknown_returns_none(tmp_db) -> None:
    """既有 contract regression — 不存在的 slug 仍回 None（不 raise）。"""
    assert get_page(tmp_db, "topics/E999") is None
    assert get_page(tmp_db, "E999") is None


# ---------------------------------------------------------------------------
# ingest_markdown_file — 自動補 prefix
# ---------------------------------------------------------------------------


def test_ingest_markdown_file_writes_prefixed_slug(tmp_db, tmp_path: Path) -> None:
    """ingest ``entities/topics/E1.md``（frontmatter.slug=E1） → ``pages.slug=topics/E1``。"""
    topic_md = tmp_path / "entities" / "topics" / "E1.md"
    topic_md.parent.mkdir(parents=True)
    topic_md.write_text(
        "---\n"
        "slug: E1\n"
        "entity_type: topic\n"
        "name: 氣候變遷\n"
        "axis: E\n"
        "impact_score: 4.5\n"
        "financial_score: 4.0\n"
        "materiality_tier: 核心\n"
        "---\n# E1\n",
        encoding="utf-8",
    )
    pid = ingest_markdown_file(tmp_db, topic_md)
    row = tmp_db.execute("SELECT slug FROM pages WHERE id=?", [pid]).fetchone()
    assert row[0] == "topics/E1", f"expected canonical prefixed slug, got {row[0]!r}"


def test_ingest_markdown_file_already_prefixed_is_idempotent(
    tmp_db, tmp_path: Path,
) -> None:
    """frontmatter.slug 已是 ``topics/E1`` → 不雙重 prefix（不變成 ``topics/topics/E1``）。"""
    topic_md = tmp_path / "entities" / "topics" / "E1.md"
    topic_md.parent.mkdir(parents=True)
    topic_md.write_text(
        "---\n"
        "slug: topics/E1\n"
        "entity_type: topic\n"
        "name: 氣候變遷\n"
        "axis: E\n"
        "impact_score: 4.5\n"
        "financial_score: 4.0\n"
        "materiality_tier: 核心\n"
        "---\n# E1\n",
        encoding="utf-8",
    )
    pid = ingest_markdown_file(tmp_db, topic_md)
    row = tmp_db.execute("SELECT slug FROM pages WHERE id=?", [pid]).fetchone()
    assert row[0] == "topics/E1"


def test_ingest_directory_lealea_all_pages_prefixed(
    tmp_db, REPO_ROOT: Path,
) -> None:
    """ingest 完整 lealea entities/ 後，**所有** ``pages.slug`` 都是 prefixed 形式。

    驗證 R4c 主要目標：brain 內部 source of truth 統一成 ``<plural>/<id>``。
    """
    lealea_entities = REPO_ROOT / "examples" / "lealea-5364" / "entities"
    if not lealea_entities.exists():
        pytest.skip("lealea-5364 fixture not present")
    ingest_directory(tmp_db, lealea_entities, strict=False)

    rows = tmp_db.execute(
        "SELECT slug, entity_type FROM pages WHERE deleted_at IS NULL"
    ).fetchall()
    assert len(rows) > 0, "expected non-empty ingest"

    unqualified: list[tuple[str, str]] = []
    for slug, etype in rows:
        if "/" not in slug:
            unqualified.append((slug, etype))
    assert unqualified == [], (
        f"expected all pages.slug to be prefixed (<plural>/<id>) but found "
        f"{len(unqualified)} unqualified: {unqualified[:5]}..."
    )

    # 抽幾條確認 entity_type 與 prefix 對齊
    for slug, etype in rows:
        prefix, _, _tail = slug.partition("/")
        expected_prefix = ENTITY_TYPE_PREFIX[etype]
        assert prefix == expected_prefix, (
            f"page slug {slug!r} prefix {prefix!r} mismatches "
            f"entity_type {etype!r} (expected {expected_prefix!r})"
        )
