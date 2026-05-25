"""Layer 4 — init_database + BrainEngine smoke tests (spec §2.1 + §2.2)。

驗證：
    - init_database 對全新檔案 → 成功建表、schema_version=1、FK on
    - 同檔再 open → idempotent，不重建表
    - DDL 內所有 view（v_target_completeness 等）已建好
    - sqlite-vec extension 已 load（vec_chunks virtual table 可用）
    - BrainEngine.create_new 對外 facade smoke
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


def test_init_database_creates_schema_version_one(tmp_path: Path) -> None:
    """新檔 init_database → schema_version = 1。"""
    from susr.brain.migrations import init_database

    conn = init_database(tmp_path / "fresh.db")
    try:
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        assert row[0] == 1, f"expected schema_version=1, got {row[0]}"
    finally:
        conn.close()


def test_init_database_is_idempotent(tmp_path: Path) -> None:
    """同檔 open 兩次 → 不出錯、schema_version 不變。"""
    from susr.brain.migrations import init_database

    db = tmp_path / "idem.db"
    conn1 = init_database(db)
    conn1.close()
    conn2 = init_database(db)
    try:
        row = conn2.execute("SELECT MAX(version) FROM schema_version").fetchone()
        assert row[0] == 1
    finally:
        conn2.close()


def test_init_database_enables_foreign_keys(tmp_path: Path) -> None:
    """foreign_keys PRAGMA 必須為 ON（否則 ON DELETE CASCADE 不會生效）。"""
    from susr.brain.migrations import init_database

    conn = init_database(tmp_path / "fk.db")
    try:
        row = conn.execute("PRAGMA foreign_keys").fetchone()
        assert row[0] == 1, "foreign_keys must be ON; got 0"
    finally:
        conn.close()


def test_init_database_creates_all_core_tables(tmp_path: Path) -> None:
    """DDL §2-§8 的核心表 + view + virtual table 都應建好。"""
    from susr.brain.migrations import init_database

    conn = init_database(tmp_path / "tables.db")
    try:
        names = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
            ).fetchall()
        }
        # core tables (spec §2.2)
        for t in (
            "schema_version",
            "pages",
            "entity_attributes",
            "links",
            "timeline_entries",
            "page_versions",
        ):
            assert t in names, f"missing table {t!r}; have {sorted(names)}"
        # invariant helper views (spec §2.5 §9-§11)
        for v in (
            "v_target_completeness",
            "v_core_topic_action_coverage",
            "v_chapter_completeness",
        ):
            assert v in names, f"missing view {v!r}"
    finally:
        conn.close()


def test_init_database_creates_vec_chunks_virtual_table(tmp_path: Path) -> None:
    """vec_chunks (sqlite-vec vec0 virtual table) 必須 register 成功。"""
    from susr.brain.migrations import init_database

    conn = init_database(tmp_path / "vec.db")
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE name='vec_chunks'"
        ).fetchone()
        assert row is not None, "vec_chunks virtual table missing — sqlite-vec not loaded?"
    finally:
        conn.close()


def test_init_database_creates_fts_pages_virtual_table(tmp_path: Path) -> None:
    """fts_pages (FTS5 virtual table) 必須 register 成功。"""
    from susr.brain.migrations import init_database

    conn = init_database(tmp_path / "fts.db")
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE name='fts_pages'"
        ).fetchone()
        assert row is not None, "fts_pages virtual table missing"
    finally:
        conn.close()


def test_tmp_db_fixture_yields_usable_connection(tmp_db) -> None:
    """tmp_db fixture（在 conftest）→ 應回有 schema_version=1 的連線。"""
    row = tmp_db.execute("SELECT MAX(version) FROM schema_version").fetchone()
    assert row[0] == 1


def test_brain_engine_create_new_smoke(tmp_path: Path) -> None:
    """BrainEngine.create_new → returns engine with usable conn."""
    from susr.brain.engine import BrainEngine

    engine = BrainEngine.create_new(tmp_path / "engine.db")
    try:
        assert engine.conn is not None
        row = engine.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        assert row[0] == 1
    finally:
        engine.close()


def test_brain_engine_open_existing(tmp_path: Path) -> None:
    """BrainEngine.open 對已存在的 DB → 不重建、schema_version 保留。"""
    from susr.brain.engine import BrainEngine

    db = tmp_path / "open.db"
    BrainEngine.create_new(db).close()
    engine = BrainEngine.open(db)
    try:
        row = engine.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        assert row[0] == 1
    finally:
        engine.close()
