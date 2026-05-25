"""Layer 4 — timeline_entries append-only + restate threshold 測試（spec §4.2）。

驗證：
    - write_entry 成功插入 timeline_entries row
    - timeline 對 UPDATE / DELETE 應 raise（DDL trigger trg_timeline_no_*）
    - timeline_for_page 回 newest-first
    - write_datapoint_value：delta > 5% → 觸發 snapshot + restate entry
    - write_datapoint_value：delta <= 5% → 不觸發
    - boundary case：5.1% / 5.0% / 4.9%
"""

from __future__ import annotations

import sqlite3

import pytest

from susr.brain.pages import put_page
from susr.brain.timeline import (
    TimelineEntry,
    timeline_for_page,
    write_datapoint_value,
    write_entry,
)


def _put_dp(tmp_db, *, slug: str = "datapoints/scope1-2024", value: float = 100.0) -> int:
    """Helper：建一個最小 datapoint page，回 page_id。"""
    return put_page(
        tmp_db,
        slug=slug,
        entity_type="datapoint",
        title="範疇 1 排放",
        compiled_truth="",
        file_path=f"projects/2025-sr/{slug}.md",
        frontmatter={
            "slug": slug.split("/")[-1],
            "kpi_slug": "scope1-emissions",
            "year": 2024,
            "value": value,
            "source_refs": ["erp-2024"],
            "calculation_method": "GHG Protocol",
            "assurance_status": "internal",
            "last_assessed": "2025-03-15",
            "responsible_person": "ESG team",
        },
    )


# ---------------------------------------------------------------------------
# write_entry — basic insert
# ---------------------------------------------------------------------------


def test_write_entry_inserts_row(tmp_db) -> None:
    """write_entry → timeline_entries 多一筆。"""
    pid = _put_dp(tmp_db)
    eid = write_entry(
        tmp_db,
        page_id=pid,
        action_type="ingest",
        actor="test",
        payload={"src": "erp"},
    )
    assert isinstance(eid, int) and eid > 0
    row = tmp_db.execute(
        "SELECT page_id, action_type, actor FROM timeline_entries WHERE id=?", [eid]
    ).fetchone()
    assert row == (pid, "ingest", "test")


def test_timeline_for_page_returns_newest_first(tmp_db) -> None:
    """timeline_for_page 應 ts DESC 排序。"""
    pid = _put_dp(tmp_db)
    e1 = write_entry(tmp_db, page_id=pid, action_type="ingest", actor="a")
    e2 = write_entry(tmp_db, page_id=pid, action_type="verify", actor="b")
    e3 = write_entry(tmp_db, page_id=pid, action_type="comment", actor="c")
    entries = timeline_for_page(tmp_db, pid)
    assert len(entries) == 3
    assert all(isinstance(e, TimelineEntry) for e in entries)
    ids = [e.id for e in entries]
    # 最新 (e3) 應在前
    assert ids[0] == e3
    assert ids[-1] == e1


def test_timeline_filter_by_action_types(tmp_db) -> None:
    """timeline_for_page(action_types=['restate']) → 只回該類型。"""
    pid = _put_dp(tmp_db)
    write_entry(tmp_db, page_id=pid, action_type="ingest", actor="a")
    write_entry(tmp_db, page_id=pid, action_type="restate", actor="b")
    write_entry(tmp_db, page_id=pid, action_type="verify", actor="c")
    only_restate = timeline_for_page(tmp_db, pid, action_types=["restate"])
    assert len(only_restate) == 1
    assert only_restate[0].action_type == "restate"


# ---------------------------------------------------------------------------
# Append-only — DDL trigger 攔截 UPDATE / DELETE
# ---------------------------------------------------------------------------


def test_timeline_update_blocked_by_trigger(tmp_db) -> None:
    """UPDATE timeline_entries → DDL trigger raise。"""
    pid = _put_dp(tmp_db)
    eid = write_entry(tmp_db, page_id=pid, action_type="ingest", actor="a")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        tmp_db.execute(
            "UPDATE timeline_entries SET actor='evil' WHERE id=?", [eid]
        )


def test_timeline_delete_blocked_by_trigger(tmp_db) -> None:
    """DELETE timeline_entries → DDL trigger raise。"""
    pid = _put_dp(tmp_db)
    eid = write_entry(tmp_db, page_id=pid, action_type="ingest", actor="a")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        tmp_db.execute("DELETE FROM timeline_entries WHERE id=?", [eid])


def test_timeline_check_constraint_on_action_type(tmp_db) -> None:
    """DDL CHECK 應擋下未定義的 action_type。"""
    pid = _put_dp(tmp_db)
    with pytest.raises((sqlite3.IntegrityError, ValueError)):
        write_entry(tmp_db, page_id=pid, action_type="not_an_action", actor="a")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# write_datapoint_value — restate threshold（5%）
# ---------------------------------------------------------------------------


def test_write_datapoint_value_above_threshold_triggers_restate(tmp_db) -> None:
    """value 變 5.1% → 觸發 restate entry + snapshot。"""
    pid = _put_dp(tmp_db, value=100.0)
    # 100 → 105.1 = 5.1% delta
    restate_eid = write_datapoint_value(
        tmp_db, pid, new_value=105.1, actor="test"
    )
    assert restate_eid is not None
    # 應該在 timeline 寫 restate entry
    entries = timeline_for_page(tmp_db, pid, action_types=["restate"])
    assert len(entries) >= 1


def test_write_datapoint_value_at_threshold_does_not_restate(tmp_db) -> None:
    """value 變 5.0% (剛好) → 不觸發（threshold 是嚴格 >）。"""
    pid = _put_dp(tmp_db, value=100.0)
    result = write_datapoint_value(
        tmp_db, pid, new_value=105.0, actor="test"
    )
    assert result is None, "5.0% delta should NOT trigger restate (threshold is strict >)"
    entries = timeline_for_page(tmp_db, pid, action_types=["restate"])
    assert len(entries) == 0


def test_write_datapoint_value_below_threshold_does_not_restate(tmp_db) -> None:
    """value 變 4.9% → 不觸發。"""
    pid = _put_dp(tmp_db, value=100.0)
    result = write_datapoint_value(
        tmp_db, pid, new_value=104.9, actor="test"
    )
    assert result is None
    entries = timeline_for_page(tmp_db, pid, action_types=["restate"])
    assert len(entries) == 0


def test_write_datapoint_value_negative_delta_above_threshold(tmp_db) -> None:
    """value 從 100 降到 90 (-10%) → 仍應觸發 restate（abs delta）。"""
    pid = _put_dp(tmp_db, value=100.0)
    result = write_datapoint_value(
        tmp_db, pid, new_value=90.0, actor="test"
    )
    assert result is not None, "abs(delta) > 5% should trigger regardless of sign"


def test_write_datapoint_value_custom_threshold(tmp_db) -> None:
    """改 restate_threshold=0.10 → 7% 不觸發。"""
    pid = _put_dp(tmp_db, value=100.0)
    result = write_datapoint_value(
        tmp_db, pid, new_value=107.0, actor="test", restate_threshold=0.10
    )
    assert result is None


def test_write_datapoint_value_updates_entity_attributes(tmp_db) -> None:
    """write_datapoint_value 必須真的把 value 寫進 entity_attributes。"""
    pid = _put_dp(tmp_db, value=100.0)
    write_datapoint_value(tmp_db, pid, new_value=120.0, actor="test")
    row = tmp_db.execute(
        "SELECT value FROM entity_attributes WHERE page_id=? AND key='value'",
        [pid],
    ).fetchone()
    assert row is not None
    # value 攤平為 string，比對時容許 numeric 解析
    assert float(row[0]) == pytest.approx(120.0)
