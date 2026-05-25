"""susr.brain.versions — page_versions snapshot/restore (spec §4.1).

Reasons: manual | phase_complete | year_freeze | restate | assurance.
restore_from() captures the current live state in a fresh snapshot first,
then overwrites pages + entity_attributes from the snap, and appends a
'comment' timeline entry — the restore itself is audit-traceable.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Literal, Optional

SnapshotReason = Literal[
    "manual",
    "phase_complete",
    "year_freeze",
    "restate",
    "assurance",
]


@dataclass
class PageVersion:
    """One snapshot row (mirrors page_versions table)."""

    id: int
    page_id: int
    version_no: int
    parent_version_id: Optional[int]
    content_hash: str
    frontmatter_snap: str  # JSON
    compiled_truth_snap: str
    snapshot_reason: str
    created_at: str
    created_by: Optional[str]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _row_to_version(row: tuple) -> PageVersion:
    return PageVersion(
        id=int(row[0]),
        page_id=int(row[1]),
        version_no=int(row[2]),
        parent_version_id=int(row[3]) if row[3] is not None else None,
        content_hash=str(row[4]),
        frontmatter_snap=str(row[5]),
        compiled_truth_snap=str(row[6]),
        snapshot_reason=str(row[7]),
        created_at=str(row[8]),
        created_by=str(row[9]) if row[9] is not None else None,
    )


_VERSION_COLS = (
    "id, page_id, version_no, parent_version_id, content_hash, "
    "frontmatter_snap, compiled_truth_snap, snapshot_reason, "
    "created_at, created_by"
)


def _dump_frontmatter(conn: sqlite3.Connection, page_id: int) -> dict[str, Any]:
    """(key,value,value_type) rows → dict.  Inlined to avoid a hard dep on
    pages.py (parallel R2-A work)."""
    rows = conn.execute(
        "SELECT key, value, value_type FROM entity_attributes "
        "WHERE page_id = ? ORDER BY key",
        [page_id],
    ).fetchall()
    out: dict[str, Any] = {}
    for key, value, value_type in rows:
        if value is None:
            out[key] = None
            continue
        if value_type == "int":
            out[key] = int(value)
        elif value_type == "float":
            out[key] = float(value)
        elif value_type == "bool":
            out[key] = str(value).lower() in {"1", "true", "yes"}
        elif value_type in ("json_array", "json_object"):
            try:
                out[key] = json.loads(value)
            except (TypeError, ValueError):
                out[key] = value
        else:  # text, date
            out[key] = value
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def snapshot_page(
    conn: sqlite3.Connection,
    page_id: int,
    *,
    reason: SnapshotReason,
    actor: str,
) -> int:
    """Take a snapshot of `pages[page_id]` + its current frontmatter.

    Computes version_no = MAX(version_no) + 1 per page (monotonic).
    parent_version_id chains back to the previous snapshot, if any.

    Raises ValueError if the page does not exist or is soft-deleted.
    Returns the new page_versions.id.
    """
    page_row = conn.execute(
        "SELECT compiled_truth, source_hash FROM pages "
        "WHERE id = ? AND deleted_at IS NULL",
        [page_id],
    ).fetchone()
    if page_row is None:
        raise ValueError(f"page id={page_id} not found or soft-deleted")
    compiled_truth, source_hash = page_row

    prev = conn.execute(
        "SELECT id, version_no FROM page_versions "
        "WHERE page_id = ? ORDER BY version_no DESC LIMIT 1",
        [page_id],
    ).fetchone()
    if prev is None:
        next_no = 1
        parent_id: Optional[int] = None
    else:
        parent_id = int(prev[0])
        next_no = int(prev[1]) + 1

    frontmatter = _dump_frontmatter(conn, page_id)

    cur = conn.execute(
        """
        INSERT INTO page_versions
            (page_id, version_no, parent_version_id, content_hash,
             frontmatter_snap, compiled_truth_snap, snapshot_reason, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            page_id,
            next_no,
            parent_id,
            source_hash,
            json.dumps(frontmatter, ensure_ascii=False, sort_keys=True),
            compiled_truth,
            reason,
            actor,
        ],
    )
    return int(cur.lastrowid)


def get_version(conn: sqlite3.Connection, version_id: int) -> Optional[PageVersion]:
    """Return a single PageVersion by primary key, or None."""
    row = conn.execute(
        f"SELECT {_VERSION_COLS} FROM page_versions WHERE id = ?",
        [version_id],
    ).fetchone()
    return _row_to_version(row) if row else None


def list_versions(
    conn: sqlite3.Connection,
    page_id: int,
    *,
    limit: int = 50,
) -> list[PageVersion]:
    """Return snapshots for a page, newest first (version_no DESC)."""
    rows = conn.execute(
        f"SELECT {_VERSION_COLS} FROM page_versions "
        f"WHERE page_id = ? ORDER BY version_no DESC LIMIT ?",
        [page_id, limit],
    ).fetchall()
    return [_row_to_version(r) for r in rows]


def restore_from(
    conn: sqlite3.Connection,
    version_id: int,
    *,
    actor: str,
) -> int:
    """Overwrite live page row with snapshot content.  Steps: (1) snapshot
    current state (reason='manual') to preserve pre-restore; (2) UPDATE
    pages; (3) rebuild entity_attributes; (4) append 'comment' timeline."""
    snap = get_version(conn, version_id)
    if snap is None:
        raise ValueError(f"page_version id={version_id} not found")

    # Step 1: capture current live state in history before mutating.
    snapshot_page(conn, snap.page_id, reason="manual", actor=actor)

    # Step 2: overwrite live page.
    conn.execute(
        "UPDATE pages SET compiled_truth = ?, source_hash = ?, "
        "updated_at = datetime('now') WHERE id = ?",
        [snap.compiled_truth_snap, snap.content_hash, snap.page_id],
    )

    # Step 3: rebuild entity_attributes from frontmatter snap.
    conn.execute("DELETE FROM entity_attributes WHERE page_id = ?", [snap.page_id])
    try:
        fm = json.loads(snap.frontmatter_snap)
    except (TypeError, ValueError):
        fm = {}
    if isinstance(fm, dict):
        for key, value in fm.items():
            value_type = _infer_value_type(value)
            stored = (
                json.dumps(value, ensure_ascii=False)
                if value_type in ("json_array", "json_object")
                else (None if value is None else str(value))
            )
            conn.execute(
                "INSERT INTO entity_attributes (page_id, key, value, value_type) "
                "VALUES (?, ?, ?, ?)",
                [snap.page_id, key, stored, value_type],
            )

    # Step 4: append-only timeline note.  Local import to dodge cycle.
    from susr.brain.timeline import write_entry

    write_entry(
        conn,
        page_id=snap.page_id,
        action_type="comment",
        actor=actor,
        payload={"restored_from_version_id": version_id, "version_no": snap.version_no},
    )

    return snap.page_id


def _infer_value_type(value: Any) -> str:
    """Best-guess value_type for an attribute round-tripped from JSON."""
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, list):
        return "json_array"
    if isinstance(value, dict):
        return "json_object"
    return "text"


def diff_snapshots(
    conn: sqlite3.Connection,
    version_id_a: int,
    version_id_b: int,
) -> dict[str, Any]:
    """Shallow diff between two snapshots.  Returns content_changed +
    frontmatter_added / _removed / _changed dicts."""
    a = get_version(conn, version_id_a)
    b = get_version(conn, version_id_b)
    if a is None or b is None:
        raise ValueError("one or both version ids not found")
    try:
        fm_a = json.loads(a.frontmatter_snap) if a.frontmatter_snap else {}
    except (TypeError, ValueError):
        fm_a = {}
    try:
        fm_b = json.loads(b.frontmatter_snap) if b.frontmatter_snap else {}
    except (TypeError, ValueError):
        fm_b = {}

    keys_a = set(fm_a) if isinstance(fm_a, dict) else set()
    keys_b = set(fm_b) if isinstance(fm_b, dict) else set()
    added = {k: fm_b[k] for k in keys_b - keys_a}
    removed = {k: fm_a[k] for k in keys_a - keys_b}
    changed: dict[str, dict[str, Any]] = {}
    for k in keys_a & keys_b:
        if fm_a[k] != fm_b[k]:
            changed[k] = {"before": fm_a[k], "after": fm_b[k]}

    return {
        "page_id_a": a.page_id,
        "page_id_b": b.page_id,
        "content_changed": a.compiled_truth_snap != b.compiled_truth_snap,
        "frontmatter_added": added,
        "frontmatter_removed": removed,
        "frontmatter_changed": changed,
    }
