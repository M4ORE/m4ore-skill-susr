"""Layer 4 — page_versions snapshot / diff / restore 測試（spec §4.1）。

驗證：
    - snapshot_page → version_no monotonic（1, 2, 3...）
    - parent_version_id 串起鏈
    - snap → update_page → 內容仍可從 snap 取回
    - restore_from 把 live row 寫回 snap 時點
    - list_versions newest-first
    - snapshot_reason 全部合法值都可被接受
"""

from __future__ import annotations

import pytest

from susr.brain.pages import get_page_by_id, update_page
from susr.brain.versions import (
    PageVersion,
    get_version,
    list_versions,
    restore_from,
    snapshot_page,
)


def _put_topic(tmp_brain, slug: str = "topics/E1", body: str = "v1 body"):
    """Helper: 建一個最小 topic page，回 page_id。"""
    return tmp_brain.put_page(
        slug=slug,
        entity_type="topic",
        title="氣候變遷",
        compiled_truth=body,
        file_path="entities/topics/E1.md",
        frontmatter={
            "slug": slug.split("/")[-1],
            "name": "氣候變遷",
            "axis": "E",
            "impact_score": 4.5,
            "financial_score": 4.0,
            "materiality_tier": "核心",
        },
    )


def test_snapshot_creates_version_no_one(tmp_brain) -> None:
    """首次 snapshot → version_no = 1。"""
    pid = _put_topic(tmp_brain)
    vid = snapshot_page(tmp_brain.conn, pid, reason="manual", actor="test")
    assert isinstance(vid, int) and vid > 0
    v = get_version(tmp_brain.conn, vid)
    assert v is not None
    assert isinstance(v, PageVersion)
    assert v.version_no == 1
    assert v.parent_version_id is None
    assert v.snapshot_reason == "manual"


def test_snapshot_monotonic_version_no(tmp_brain) -> None:
    """連續 snapshot 同 page → version_no 為 1, 2, 3..."""
    pid = _put_topic(tmp_brain)
    v1 = snapshot_page(tmp_brain.conn, pid, reason="manual", actor="test")
    v2 = snapshot_page(tmp_brain.conn, pid, reason="phase_complete", actor="test")
    v3 = snapshot_page(tmp_brain.conn, pid, reason="manual", actor="test")
    assert get_version(tmp_brain.conn, v1).version_no == 1  # type: ignore[union-attr]
    assert get_version(tmp_brain.conn, v2).version_no == 2  # type: ignore[union-attr]
    assert get_version(tmp_brain.conn, v3).version_no == 3  # type: ignore[union-attr]


def test_snapshot_parent_chain(tmp_brain) -> None:
    """第二次 snapshot.parent_version_id 應指向第一次。"""
    pid = _put_topic(tmp_brain)
    v1 = snapshot_page(tmp_brain.conn, pid, reason="manual", actor="test")
    v2 = snapshot_page(tmp_brain.conn, pid, reason="phase_complete", actor="test")
    assert get_version(tmp_brain.conn, v2).parent_version_id == v1  # type: ignore[union-attr]


def test_snapshot_preserves_body_before_update(tmp_brain) -> None:
    """snapshot → update_page → snap 內容仍是 update 前的版本。"""
    pid = _put_topic(tmp_brain, body="version-A")
    vid = snapshot_page(tmp_brain.conn, pid, reason="manual", actor="test")
    update_page(tmp_brain.conn, pid, compiled_truth="version-B", actor="test")
    snap = get_version(tmp_brain.conn, vid)
    assert snap is not None
    assert snap.compiled_truth_snap == "version-A"


def test_list_versions_returns_newest_first(tmp_brain) -> None:
    """list_versions 應 version_no DESC 排序。"""
    pid = _put_topic(tmp_brain)
    snapshot_page(tmp_brain.conn, pid, reason="manual", actor="test")
    snapshot_page(tmp_brain.conn, pid, reason="phase_complete", actor="test")
    snapshot_page(tmp_brain.conn, pid, reason="assurance", actor="test")
    versions = list_versions(tmp_brain.conn, pid)
    assert len(versions) == 3
    version_nos = [v.version_no for v in versions]
    assert version_nos == [3, 2, 1]


def test_restore_writes_back_snapshot_content(tmp_brain) -> None:
    """restore_from → live page row 回到 snap 時的 body。"""
    pid = _put_topic(tmp_brain, body="version-A")
    vid = snapshot_page(tmp_brain.conn, pid, reason="manual", actor="test")
    update_page(tmp_brain.conn, pid, compiled_truth="version-B", actor="test")
    update_page(tmp_brain.conn, pid, compiled_truth="version-C", actor="test")
    restored_pid = restore_from(tmp_brain.conn, vid, actor="test")
    assert restored_pid == pid
    page = get_page_by_id(tmp_brain.conn, pid)
    assert page is not None
    assert page.compiled_truth == "version-A"


def test_get_version_missing_returns_none(tmp_brain) -> None:
    """不存在的 version_id → None（不是 raise）。"""
    assert get_version(tmp_brain.conn, 999_999) is None


@pytest.mark.parametrize(
    "reason",
    ["manual", "phase_complete", "year_freeze", "restate", "assurance"],
)
def test_snapshot_accepts_all_valid_reasons(tmp_brain, reason: str) -> None:
    """5 種 snapshot_reason 都應被接受（DDL CHECK §6）。"""
    pid = _put_topic(tmp_brain, slug=f"topics/T-{reason}")
    vid = snapshot_page(tmp_brain.conn, pid, reason=reason, actor="test")  # type: ignore[arg-type]
    assert get_version(tmp_brain.conn, vid).snapshot_reason == reason  # type: ignore[union-attr]


def test_snapshot_rejects_invalid_reason(tmp_brain) -> None:
    """DDL CHECK 應擋下 invalid snapshot_reason。"""
    import sqlite3

    pid = _put_topic(tmp_brain)
    with pytest.raises((sqlite3.IntegrityError, ValueError)):
        snapshot_page(tmp_brain.conn, pid, reason="bogus_reason", actor="test")  # type: ignore[arg-type]
