"""Layer 4 — pages.py CRUD 單元測試（spec §2.2 + §2.3）。

驗證：
    - put_page 對新 slug → insert；同 slug 再 put → upsert（不重複 row）
    - entity_attributes 攤平：put 後可 get_frontmatter 還原成同 dict
    - get_page / get_page_by_id 查得到 Page；soft-delete 後讀不到
    - frontmatter schema validation（缺必備欄位 → ValidationError）
    - FTS5 trigger：put 後 fts_pages 同步有對應 row
"""

from __future__ import annotations

import pytest

from susr.brain.pages import (
    Page,
    get_frontmatter,
    get_page,
    get_page_by_id,
    put_page,
    soft_delete,
    update_page,
)


def _minimal_topic_fm(slug: str = "E1") -> dict:
    """Return a minimal-valid TopicFrontmatter dict for tests."""
    return {
        "slug": slug,
        "name": "氣候變遷",
        "axis": "E",
        "impact_score": 4.5,
        "financial_score": 4.0,
        "materiality_tier": "核心",
    }


def test_put_page_inserts_row(tmp_db) -> None:
    """put_page 對新 slug → 寫一筆 pages row。"""
    pid = put_page(
        tmp_db,
        slug="topics/E1",
        entity_type="topic",
        title="氣候變遷",
        compiled_truth="",
        file_path="entities/topics/E1.md",
        frontmatter=_minimal_topic_fm(),
    )
    assert isinstance(pid, int) and pid > 0
    row = tmp_db.execute(
        "SELECT slug, entity_type FROM pages WHERE id=?", [pid]
    ).fetchone()
    assert row == ("topics/E1", "topic")


def test_put_page_upserts_on_same_slug(tmp_db) -> None:
    """同 slug 二度 put → 不重複建 row（UNIQUE(slug, tenant_id) 在 DDL §2）。"""
    pid1 = put_page(
        tmp_db,
        slug="topics/E1",
        entity_type="topic",
        title="氣候變遷 v1",
        compiled_truth="version 1",
        file_path="entities/topics/E1.md",
        frontmatter=_minimal_topic_fm(),
    )
    pid2 = put_page(
        tmp_db,
        slug="topics/E1",
        entity_type="topic",
        title="氣候變遷 v2",
        compiled_truth="version 2",
        file_path="entities/topics/E1.md",
        frontmatter=_minimal_topic_fm(),
    )
    assert pid1 == pid2, "upsert should re-use the same id"
    count = tmp_db.execute(
        "SELECT COUNT(*) FROM pages WHERE slug='topics/E1'"
    ).fetchone()[0]
    assert count == 1


def test_get_page_returns_page_object(tmp_db) -> None:
    """get_page(slug) → 對應的 Page dataclass。"""
    put_page(
        tmp_db,
        slug="topics/E1",
        entity_type="topic",
        title="氣候變遷",
        compiled_truth="body",
        file_path="entities/topics/E1.md",
        frontmatter=_minimal_topic_fm(),
    )
    page = get_page(tmp_db, "topics/E1")
    assert page is not None
    assert isinstance(page, Page)
    assert page.slug == "topics/E1"
    assert page.entity_type == "topic"
    assert page.title == "氣候變遷"


def test_get_page_missing_returns_none(tmp_db) -> None:
    """get_page on unknown slug → None（不是 raise）。"""
    assert get_page(tmp_db, "topics/does-not-exist") is None


def test_get_frontmatter_roundtrip(tmp_db) -> None:
    """put_page 的 frontmatter dict 與 get_frontmatter 回的應等值。"""
    fm = _minimal_topic_fm()
    pid = put_page(
        tmp_db,
        slug="topics/E1",
        entity_type="topic",
        title="氣候變遷",
        compiled_truth="",
        file_path="entities/topics/E1.md",
        frontmatter=fm,
    )
    rt = get_frontmatter(tmp_db, pid)
    # 子集斷言：rt 必須包含 fm 的每個鍵值（rt 可能多帶 xbrl_concept=None 之類）
    for k, v in fm.items():
        assert rt.get(k) == v, f"roundtrip mismatch on {k}: {rt.get(k)!r} != {v!r}"


def test_put_page_validates_frontmatter_schema(tmp_db) -> None:
    """缺必備欄位（axis）的 frontmatter → 應 raise（Pydantic ValidationError）。"""
    bad_fm = _minimal_topic_fm()
    bad_fm.pop("axis")  # axis 是必備
    with pytest.raises(Exception):
        # 接受 ValidationError / ValueError / KeyError 任一 — 主要是 fail-closed
        put_page(
            tmp_db,
            slug="topics/E-bad",
            entity_type="topic",
            title="壞欄位",
            compiled_truth="",
            file_path="entities/topics/E-bad.md",
            frontmatter=bad_fm,
        )


def test_update_page_modifies_body(tmp_db) -> None:
    """update_page(compiled_truth=) → DB 內 body 改變。"""
    pid = put_page(
        tmp_db,
        slug="topics/E1",
        entity_type="topic",
        title="氣候變遷",
        compiled_truth="original",
        file_path="entities/topics/E1.md",
        frontmatter=_minimal_topic_fm(),
    )
    update_page(tmp_db, pid, compiled_truth="updated body", actor="test")
    page = get_page_by_id(tmp_db, pid)
    assert page is not None
    assert page.compiled_truth == "updated body"


def test_soft_delete_hides_page(tmp_db) -> None:
    """soft_delete 後，get_page 應回 None（已 soft-deleted）。"""
    pid = put_page(
        tmp_db,
        slug="topics/E1",
        entity_type="topic",
        title="氣候變遷",
        compiled_truth="",
        file_path="entities/topics/E1.md",
        frontmatter=_minimal_topic_fm(),
    )
    soft_delete(tmp_db, pid)
    assert get_page(tmp_db, "topics/E1") is None
    # 但底層 row 仍在（audit 用途）
    raw = tmp_db.execute(
        "SELECT deleted_at FROM pages WHERE id=?", [pid]
    ).fetchone()
    assert raw is not None and raw[0] is not None


def test_put_page_syncs_fts_pages(tmp_db) -> None:
    """DDL trigger trg_pages_fts_insert：put_page 後 fts_pages 應同步有 row。"""
    pid = put_page(
        tmp_db,
        slug="topics/E1",
        entity_type="topic",
        title="氣候變遷",
        compiled_truth="這是內文",
        file_path="entities/topics/E1.md",
        frontmatter=_minimal_topic_fm(),
    )
    row = tmp_db.execute(
        "SELECT title FROM fts_pages WHERE rowid=?", [pid]
    ).fetchone()
    assert row is not None, "fts_pages trigger did not fire"
    assert row[0] == "氣候變遷"
