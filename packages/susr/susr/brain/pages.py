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

R1: dataclasses + signatures.  R2: implement.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Optional


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

    Returns page_id. Validates frontmatter via ENTITY_SCHEMAS[entity_type]
    before any writes.  Writes inside a single transaction.
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §2.2 + §2.3")


def get_page(conn: sqlite3.Connection, slug: str, *, tenant_id: Optional[str] = None) -> Optional[Page]:
    """Return the Page by (slug, tenant_id) or None if absent / soft-deleted."""
    raise NotImplementedError("Step 1 R2")


def get_page_by_id(conn: sqlite3.Connection, page_id: int) -> Optional[Page]:
    """Return the Page by primary key or None."""
    raise NotImplementedError("Step 1 R2")


def get_frontmatter(conn: sqlite3.Connection, page_id: int) -> dict[str, Any]:
    """Reassemble entity_attributes rows back into a frontmatter dict."""
    raise NotImplementedError("Step 1 R2 — type-aware: respect value_type column")


def update_page(
    conn: sqlite3.Connection,
    page_id: int,
    *,
    compiled_truth: Optional[str] = None,
    frontmatter_patch: Optional[dict[str, Any]] = None,
    actor: str = "unknown",
) -> None:
    """Update body and/or merge a frontmatter patch.  Bumps updated_at."""
    raise NotImplementedError("Step 1 R2")


def soft_delete(conn: sqlite3.Connection, page_id: int) -> None:
    """Set pages.deleted_at = now.  Does not cascade — links remain for audit."""
    raise NotImplementedError("Step 1 R2")
