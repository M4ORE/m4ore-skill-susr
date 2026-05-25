"""susr.brain.pages — CRUD over the pages + entity_attributes tables.

Owns the markdown <-> DB round-trip:
    - markdown file path → pages row
    - YAML frontmatter dict → entity_attributes rows (one per key)
    - compiled_truth (text above '---') → pages.compiled_truth
    - timeline section (below '---') → timeline_entries (delegated)

Pages are the unit of:
    - FTS5 indexing (via trigger from §2.2 of DDL)
    - vec_chunks (via separate chunk+embed pipeline, R2)
    - snapshot (page_versions)

Layout
------
- ``Page`` dataclass mirrors the pages table (does NOT carry frontmatter;
  frontmatter rounds through ``entity_attributes`` via ``get_frontmatter``).
- ``put_page`` — insert or upsert with full frontmatter validation.
- ``get_page`` / ``get_page_by_id`` — read; skips soft-deleted rows.
- ``get_frontmatter`` — reassemble entity_attributes back into a dict.
- ``update_page`` — patch body and/or frontmatter; bumps updated_at.
- ``soft_delete`` — sets deleted_at; links retained for audit trail.
- ``list_pages`` — filter by entity_type / project_slug / tenant_id.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

from susr.brain._slug import resolve_slug
from susr.brain.entities import validate_frontmatter


@dataclass
class Page:
    """In-memory page record (mirrors pages table; see DDL §2)."""

    id: int
    slug: str
    entity_type: str
    title: str
    compiled_truth: str
    file_path: str
    source_hash: str
    tenant_id: Optional[str] = None
    project_slug: Optional[str] = None
    xbrl_concept: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None


# Columns selected when hydrating a Page; kept in one place so SELECT order
# matches the dataclass field order verbatim.
_PAGE_COLS = (
    "id, slug, entity_type, title, compiled_truth, file_path, source_hash, "
    "tenant_id, project_slug, xbrl_concept, created_at, updated_at, deleted_at"
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _row_to_page(row: tuple[Any, ...] | None) -> Optional[Page]:
    """SELECT row → Page dataclass; ``None`` passthrough."""
    if row is None:
        return None
    return Page(*row)


def _detect_value_type(value: Any) -> str:
    """將 Python 值對應到 entity_attributes.value_type CHECK enum。"""
    # bool 必須先檢查（bool 是 int 的子類）
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, datetime):
        return "date"
    if isinstance(value, date):
        return "date"
    if isinstance(value, dict):
        return "json_object"
    if isinstance(value, (list, tuple, set)):
        return "json_array"
    return "text"


def _encode_value(value: Any, value_type: str) -> str:
    """將 Python 值序列化為 entity_attributes.value 的 TEXT 形態。"""
    if value_type in ("json_array", "json_object"):
        return json.dumps(list(value) if isinstance(value, (set, tuple)) else value,
                          ensure_ascii=False, sort_keys=False)
    if value_type == "bool":
        return "true" if value else "false"
    if value_type == "date":
        return value.isoformat() if isinstance(value, (date, datetime)) else str(value)
    return str(value)


def _decode_value(value: Optional[str], value_type: str) -> Any:
    """value_type 感知地把 TEXT 還原回 Python 值。"""
    if value is None:
        return None
    if value_type == "int":
        return int(value)
    if value_type == "float":
        return float(value)
    if value_type == "bool":
        return value.lower() in ("true", "1", "yes")
    if value_type in ("json_array", "json_object"):
        return json.loads(value)
    # 'text' / 'date' — keep as string (consumers decide whether to parse).
    return value


def _write_attributes(
    conn: sqlite3.Connection,
    page_id: int,
    frontmatter: dict[str, Any],
    *,
    replace: bool,
) -> None:
    """寫 entity_attributes；``replace=True`` 時先清空再 insert（put_page 用）。

    For ``update_page`` callers we use ``replace=False`` + upsert per key so
    that a partial patch doesn't drop untouched keys.
    """
    if replace:
        conn.execute("DELETE FROM entity_attributes WHERE page_id = ?", [page_id])

    for key, value in frontmatter.items():
        if value is None:
            # Treat None as "absent" — skip rather than store empty rows.
            # update_page patches use _delete_attribute() explicitly.
            continue
        vtype = _detect_value_type(value)
        encoded = _encode_value(value, vtype)
        conn.execute(
            """
            INSERT INTO entity_attributes (page_id, key, value, value_type)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(page_id, key) DO UPDATE SET
                value = excluded.value,
                value_type = excluded.value_type
            """,
            [page_id, key, encoded, vtype],
        )


def _compute_source_hash(*parts: str) -> str:
    """穩定的 source_hash（前後 trim 後 SHA-256）— 用於 idempotent re-ingest。"""
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Public CRUD
# ---------------------------------------------------------------------------


def put_page(
    conn: sqlite3.Connection,
    *,
    slug: str,
    entity_type: str,
    title: str,
    compiled_truth: str,
    file_path: str,
    frontmatter: dict[str, Any],
    tenant_id: Optional[str] = None,
    project_slug: Optional[str] = None,
    xbrl_concept: Optional[str] = None,
) -> int:
    """Insert or upsert a page + its entity_attributes rows.

    Validates ``frontmatter`` via ``ENTITY_SCHEMAS[entity_type]`` BEFORE any
    write — pydantic.ValidationError propagates with no DB mutation.

    Upsert key: ``(slug, tenant_id)`` (matches the UNIQUE index in DDL §2).
    The whole operation runs inside a transaction so a frontmatter write
    failure rolls back the pages row as well.
    """
    # ── validate BEFORE touching the DB ────────────────────────────────────
    validate_frontmatter(entity_type, frontmatter)

    source_hash = _compute_source_hash(title, compiled_truth, json.dumps(
        frontmatter, ensure_ascii=False, sort_keys=True, default=str,
    ))

    cur = conn.cursor()
    try:
        cur.execute("BEGIN")
        # NOTE: SQLite UNIQUE(slug, tenant_id) treats NULL as distinct, so
        # ON CONFLICT(slug, tenant_id) does NOT fire when tenant_id IS NULL.
        # Explicit SELECT-then-INSERT/UPDATE handles both NULL and non-NULL
        # tenant_id uniformly.
        existing = cur.execute(
            "SELECT id FROM pages WHERE slug = ? AND tenant_id IS ?",
            [slug, tenant_id],
        ).fetchone()
        if existing is not None:
            page_id = int(existing[0])
            cur.execute(
                """
                UPDATE pages SET
                    entity_type    = ?,
                    title          = ?,
                    compiled_truth = ?,
                    file_path      = ?,
                    source_hash    = ?,
                    project_slug   = ?,
                    xbrl_concept   = ?,
                    updated_at     = datetime('now'),
                    deleted_at     = NULL
                WHERE id = ?
                """,
                [entity_type, title, compiled_truth, file_path, source_hash,
                 project_slug, xbrl_concept, page_id],
            )
        else:
            cur.execute(
                """
                INSERT INTO pages
                    (slug, entity_type, title, compiled_truth, file_path, source_hash,
                     tenant_id, project_slug, xbrl_concept)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [slug, entity_type, title, compiled_truth, file_path, source_hash,
                 tenant_id, project_slug, xbrl_concept],
            )
            page_id = int(cur.lastrowid)

        _write_attributes(conn, page_id, frontmatter, replace=True)
        cur.execute("COMMIT")
    except Exception:
        cur.execute("ROLLBACK")
        raise
    return page_id


def get_page(
    conn: sqlite3.Connection,
    slug: str,
    *,
    tenant_id: Optional[str] = None,
) -> Optional[Page]:
    """Return the Page by ``(slug, tenant_id)`` or ``None``.

    Slug 雙慣例兼容（R4c）：

    * 優先精準匹配傳入的 ``slug``（含 ``/`` 的 prefixed form 走這條）
    * 若無精準匹配且 ``slug`` 不含 ``/`` → 透過 :func:`susr.brain._slug.resolve_slug`
      做後綴匹配（``%/<slug>``），讓顧問手打 ``"E1"`` 仍能找到 ``topics/E1``。
    * 後綴匹配若命中多 entity_type 的 page → ``AmbiguousSlugError`` 直接 propagate。

    Soft-deleted 行不可見（``deleted_at IS NULL`` 過濾）。
    """
    # Path A: literal match — preserve fast path for prefixed slug callers
    row = conn.execute(
        f"SELECT {_PAGE_COLS} FROM pages "
        f"WHERE slug = ? AND tenant_id IS ? AND deleted_at IS NULL",
        [slug, tenant_id],
    ).fetchone()
    if row is not None:
        return _row_to_page(row)

    # Path B: 兼容 unqualified slug — 只在 slug 不含 ``/`` 時嘗試 fallback。
    # 含 ``/`` 但查不到代表 caller 已指定 prefixed slug 但 page 不存在 — return None。
    if "/" not in slug.strip().strip("/"):
        resolved = resolve_slug(conn, slug, tenant_id=tenant_id)
        if resolved is not None:
            row = conn.execute(
                f"SELECT {_PAGE_COLS} FROM pages "
                f"WHERE slug = ? AND tenant_id IS ? AND deleted_at IS NULL",
                [resolved, tenant_id],
            ).fetchone()
            return _row_to_page(row)
    return None


def get_page_by_id(conn: sqlite3.Connection, page_id: int) -> Optional[Page]:
    """Return the Page by primary key or None (skips soft-deleted rows)."""
    row = conn.execute(
        f"SELECT {_PAGE_COLS} FROM pages WHERE id = ? AND deleted_at IS NULL",
        [page_id],
    ).fetchone()
    return _row_to_page(row)


def get_frontmatter(conn: sqlite3.Connection, page_id: int) -> dict[str, Any]:
    """Reassemble entity_attributes rows back into a frontmatter dict.

    Empty dict when the page has no attributes (or doesn't exist).
    """
    rows = conn.execute(
        "SELECT key, value, value_type FROM entity_attributes WHERE page_id = ? ORDER BY key",
        [page_id],
    ).fetchall()
    return {key: _decode_value(value, vtype) for key, value, vtype in rows}


def update_page(
    conn: sqlite3.Connection,
    page_id: int,
    *,
    compiled_truth: Optional[str] = None,
    frontmatter_patch: Optional[dict[str, Any]] = None,
    actor: str = "unknown",  # noqa: ARG001 — reserved for timeline_entries hook
) -> None:
    """更新 body 與/或合併 frontmatter patch；同時 bump ``updated_at``。

    Notes:
        - Patch semantics: keys with non-None values upsert; keys mapped to
          ``None`` *delete* that attribute row.
        - Validation: when ``frontmatter_patch`` is supplied we merge it
          with the existing frontmatter and re-validate against the
          entity's Pydantic schema — partial breakages still fail-close.
        - source_hash is recomputed from the merged state.
        - timeline_entries(action_type='verify') write is deferred to R3
          (current ``actor`` parameter is wired through but unused).
    """
    if compiled_truth is None and frontmatter_patch is None:
        return

    cur = conn.cursor()
    try:
        cur.execute("BEGIN")
        row = cur.execute(
            "SELECT entity_type, title, compiled_truth FROM pages "
            "WHERE id = ? AND deleted_at IS NULL",
            [page_id],
        ).fetchone()
        if row is None:
            raise LookupError(f"page id={page_id} not found or soft-deleted")
        entity_type, title, existing_body = row
        body = compiled_truth if compiled_truth is not None else existing_body

        # Merge & validate frontmatter when a patch is supplied.
        merged_fm = get_frontmatter(conn, page_id)
        if frontmatter_patch is not None:
            for k, v in frontmatter_patch.items():
                if v is None:
                    merged_fm.pop(k, None)
                else:
                    merged_fm[k] = v
            validate_frontmatter(entity_type, merged_fm)

        new_hash = _compute_source_hash(title, body, json.dumps(
            merged_fm, ensure_ascii=False, sort_keys=True, default=str,
        ))

        cur.execute(
            "UPDATE pages SET compiled_truth = ?, source_hash = ?, "
            "updated_at = datetime('now') WHERE id = ?",
            [body, new_hash, page_id],
        )

        if frontmatter_patch is not None:
            # Apply key-level patch: delete-then-insert for upserted keys,
            # explicit DELETE for keys mapped to None.
            for k, v in frontmatter_patch.items():
                if v is None:
                    cur.execute(
                        "DELETE FROM entity_attributes WHERE page_id = ? AND key = ?",
                        [page_id, k],
                    )
                else:
                    vtype = _detect_value_type(v)
                    cur.execute(
                        """
                        INSERT INTO entity_attributes (page_id, key, value, value_type)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(page_id, key) DO UPDATE SET
                            value = excluded.value,
                            value_type = excluded.value_type
                        """,
                        [page_id, k, _encode_value(v, vtype), vtype],
                    )

        cur.execute("COMMIT")
    except Exception:
        cur.execute("ROLLBACK")
        raise


def soft_delete(conn: sqlite3.Connection, page_id: int) -> None:
    """Set ``pages.deleted_at = now``.  Does NOT cascade — links stay for audit."""
    conn.execute(
        "UPDATE pages SET deleted_at = datetime('now') WHERE id = ?",
        [page_id],
    )
    conn.commit()


def list_pages(
    conn: sqlite3.Connection,
    *,
    entity_type: Optional[str] = None,
    project_slug: Optional[str] = None,
    tenant_id: Optional[str] = None,
    include_deleted: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[Page]:
    """List pages with optional filters; most-recently-updated first."""
    where: list[str] = []
    params: list[Any] = []
    if entity_type is not None:
        where.append("entity_type = ?")
        params.append(entity_type)
    if project_slug is not None:
        where.append("project_slug = ?")
        params.append(project_slug)
    if tenant_id is not None:
        where.append("tenant_id = ?")
        params.append(tenant_id)
    if not include_deleted:
        where.append("deleted_at IS NULL")

    sql = f"SELECT {_PAGE_COLS} FROM pages"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    return [Page(*row) for row in conn.execute(sql, params).fetchall()]


__all__ = [
    "Page",
    "put_page",
    "get_page",
    "get_page_by_id",
    "get_frontmatter",
    "update_page",
    "soft_delete",
    "list_pages",
]
