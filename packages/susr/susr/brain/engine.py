"""susr.brain.engine — BrainEngine façade orchestrating the SQLite brain.

BrainEngine is the single entry point above the brain sub-modules
(pages / entity_attributes / links / timeline / versions / search).
MCP tools (susr.mcp.tools.*) NEVER touch SQLite directly; they go
through BrainEngine to ensure invariants + timeline writes happen.

Lifecycle:
    BrainEngine.create_new(db_path, tenant_id=None)  → fresh DB, runs DDL v001
    BrainEngine.open(db_path)                         → existing DB, asserts schema_version >= 1
    engine.close()                                    → flushes WAL + closes connection

See ``docs/research/step1-spec.md`` §2.1 (PRAGMAs) + §4 (snapshot / timeline)
+ §3 (search).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from susr.brain import edges as _edges_mod
from susr.brain import migrations as _migrations
from susr.brain import pages as _pages_mod
from susr.brain.pages import Page

# Default PRAGMAs from spec §2.1 — kept here for documentation but the
# actual application lives in susr.brain.migrations.init_database so the
# rules don't drift across two callsites.
_DEFAULT_PRAGMAS = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 268435456;
PRAGMA cache_size = -64000;
"""


@dataclass
class BrainEngineConfig:
    """Construction parameters for a BrainEngine.

    Attributes:
        db_path: Absolute path to the SQLite file (per-client .susr/db.sqlite).
        tenant_id: NULL today for single-consultant local workspaces; reserved
            for future team-edition multi-tenant rows. CLAUDE.md §8 decision 9.
        load_sqlite_vec: When False, the engine refuses to register the vec0
            virtual table — useful for unit tests that don't need vectors.
        embedding_provider: Optional EmbeddingProvider used by ``search()``.
            Lazy / loose-typed so importing engine does not pull torch.
        llm_provider: Optional LLMProvider passed to MCP tool handlers.
    """

    db_path: str
    tenant_id: Optional[str] = None
    load_sqlite_vec: bool = True
    embedding_provider: Optional[Any] = None
    llm_provider: Optional[Any] = None


class BrainEngine:
    """Orchestration façade over the SQLite brain. See module docstring."""

    def __init__(self, conn: sqlite3.Connection, config: BrainEngineConfig) -> None:
        """Direct constructor — prefer ``create_new`` / ``open`` factories."""
        self.conn = conn
        self.config = config

    # ---- factory methods ----------------------------------------------------

    @classmethod
    def create_new(
        cls,
        db_path: str | Path,
        *,
        tenant_id: Optional[str] = None,
        load_sqlite_vec: bool = True,
        embedding_provider: Optional[Any] = None,
        llm_provider: Optional[Any] = None,
    ) -> "BrainEngine":
        """Create a fresh brain DB at ``db_path`` and apply DDL v001.

        Idempotent: re-opening an already-initialised file works (the DDL
        uses IF NOT EXISTS throughout and migrations skip when current).
        """
        conn = _migrations.init_database(db_path, load_sqlite_vec=load_sqlite_vec)
        config = BrainEngineConfig(
            db_path=str(db_path),
            tenant_id=tenant_id,
            load_sqlite_vec=load_sqlite_vec,
            embedding_provider=embedding_provider,
            llm_provider=llm_provider,
        )
        return cls(conn, config)

    @classmethod
    def open(
        cls,
        db_path: str | Path,
        *,
        tenant_id: Optional[str] = None,
        load_sqlite_vec: bool = True,
        embedding_provider: Optional[Any] = None,
        llm_provider: Optional[Any] = None,
    ) -> "BrainEngine":
        """Open an existing brain DB; assert schema_version row exists."""
        # init_database is idempotent so create_new and open share the path.
        conn = _migrations.init_database(db_path, load_sqlite_vec=load_sqlite_vec)
        current = _migrations.get_current_version(conn)
        if current < 1:
            conn.close()
            raise RuntimeError(
                f"brain DB at {db_path} is missing schema_version >= 1 "
                "(corrupted or never initialised)"
            )
        config = BrainEngineConfig(
            db_path=str(db_path),
            tenant_id=tenant_id,
            load_sqlite_vec=load_sqlite_vec,
            embedding_provider=embedding_provider,
            llm_provider=llm_provider,
        )
        return cls(conn, config)

    # ---- lifecycle ----------------------------------------------------------

    @property
    def connection(self) -> sqlite3.Connection:
        """Public alias for the underlying sqlite3.Connection (test fixtures)."""
        return self.conn

    def close(self) -> None:
        """Flush WAL and close the underlying connection.  Safe to call twice."""
        if self.conn is None:
            return
        try:
            # Best-effort WAL checkpoint so the .db file is self-contained on disk.
            self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self.conn.commit()
        except sqlite3.Error:
            pass
        try:
            self.conn.close()
        finally:
            self.conn = None  # type: ignore[assignment]

    def __enter__(self) -> "BrainEngine":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ---- high-level operations (delegated to sub-modules) ------------------

    def put_page(self, slug: str, **kwargs: Any) -> int:
        """Insert or upsert a page; returns page_id.  Delegates to brain.pages.

        The tenant_id is taken from the engine config unless explicitly
        overridden in ``kwargs``.
        """
        kwargs.setdefault("tenant_id", self.config.tenant_id)
        return _pages_mod.put_page(self.conn, slug=slug, **kwargs)

    def get_page(self, slug: str, *, tenant_id: Optional[str] = None) -> Optional[Page]:
        """Read a page by slug; tenant_id defaults to engine config."""
        if tenant_id is None:
            tenant_id = self.config.tenant_id
        return _pages_mod.get_page(self.conn, slug, tenant_id=tenant_id)

    def list_pages(self, **kwargs: Any) -> list[Page]:
        """List pages with optional filters; tenant_id defaults to config."""
        kwargs.setdefault("tenant_id", self.config.tenant_id)
        return _pages_mod.list_pages(self.conn, **kwargs)

    def link(self, src_slug: str, edge_type: str, dst_slug: str, **props: Any) -> int:
        """Create a typed edge after ``validate_edge``; returns link id.

        Resolves slugs → page_ids, validates (src_type, edge_type, dst_type)
        against EDGE_REGISTRY, then inserts a links row.  Duplicate edges
        are short-circuited via ON CONFLICT DO UPDATE (UNIQUE index).
        """
        import json as _json

        tenant = self.config.tenant_id
        src = _pages_mod.get_page(self.conn, src_slug, tenant_id=tenant)
        dst = _pages_mod.get_page(self.conn, dst_slug, tenant_id=tenant)
        if src is None:
            raise LookupError(f"src page {src_slug!r} not found (tenant={tenant!r})")
        if dst is None:
            raise LookupError(f"dst page {dst_slug!r} not found (tenant={tenant!r})")

        _edges_mod.validate_edge(src.entity_type, edge_type, dst.entity_type)  # type: ignore[arg-type]

        properties_json = _json.dumps(props, ensure_ascii=False, sort_keys=True, default=str)
        cur = self.conn.execute(
            """
            INSERT INTO links (src_page_id, dst_page_id, edge_type, properties)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(src_page_id, dst_page_id, edge_type) DO UPDATE SET
                properties = excluded.properties
            """,
            [src.id, dst.id, edge_type, properties_json],
        )
        self.conn.commit()
        # cur.lastrowid is 0 on upsert path; re-query for stable id.
        row = self.conn.execute(
            "SELECT id FROM links WHERE src_page_id = ? AND dst_page_id = ? AND edge_type = ?",
            [src.id, dst.id, edge_type],
        ).fetchone()
        return int(row[0]) if row else int(cur.lastrowid or 0)

    def search(self, query: str, **kwargs: Any) -> list[Any]:
        """Hybrid retrieval; delegates to ``susr.brain.search.hybrid_search``.

        Imported lazily so an engine without an embedding provider still
        works (FTS-only fallback handled inside hybrid_search).
        """
        from susr.brain.search import hybrid_search  # local import keeps cold-start light

        kwargs.setdefault("embed_provider", self.config.embedding_provider)
        kwargs.setdefault("tenant_id", self.config.tenant_id)
        return hybrid_search(self.conn, query, **kwargs)

    def snapshot(self, page_id: int, *, reason: str, actor: str) -> int:
        """Snapshot the page; delegates to ``susr.brain.versions.snapshot_page``.

        Note: the underlying ``versions`` module is still an R3 stub at the
        time of writing — calling this raises NotImplementedError until R3
        lands.  The façade is wired so MCP tools can already reference it.
        """
        from susr.brain.versions import snapshot_page

        return snapshot_page(self.conn, page_id, reason=reason, actor=actor)  # type: ignore[arg-type]

    def commit_phase(self, phase: int, *, actor: str) -> dict[str, Any]:  # noqa: ARG002 — actor wired to R3
        """Run invariants for a phase; on success, return a result summary.

        Phase 3 MVP gate (spec §2.5): I1 + I2 + I3.  This method does NOT
        currently snapshot — that's handled per-page by the caller / R3
        ``versions`` once landed.  We return the violation list so MCP
        callers can show partial progress instead of a single exception.
        """
        from susr.brain.invariants import check_all_invariants

        violations = check_all_invariants(self.conn)
        return {
            "phase": phase,
            "violation_count": len(violations),
            "violations": [
                {"invariant": v.invariant, "page_slug": v.page_slug, "detail": v.detail}
                for v in violations
            ],
        }


__all__ = [
    "BrainEngine",
    "BrainEngineConfig",
]
