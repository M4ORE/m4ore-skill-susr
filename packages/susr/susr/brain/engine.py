"""susr.brain.engine — BrainEngine façade orchestrating the SQLite brain.

BrainEngine is the single entry point above the brain sub-modules
(pages / entity_attributes / links / timeline / versions / search).
MCP tools (susr.mcp.tools.*) NEVER touch SQLite directly; they go
through BrainEngine to ensure invariants + timeline writes happen.

Lifecycle:
    BrainEngine.create_new(db_path, tenant_id=None)  → fresh DB, runs DDL v001
    BrainEngine.open(db_path)                         → existing DB, asserts schema_version >= 1
    engine.close()                                    → flushes WAL + closes connection

R1: signatures only.  R2: implement against docs/research/step1-spec.md §2.1 (PRAGMAs)
+ §4 (snapshot / timeline) + §3 (search).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


# Default PRAGMAs from spec §2.1
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
    """

    db_path: str
    tenant_id: Optional[str] = None
    load_sqlite_vec: bool = True


class BrainEngine:
    """Orchestration façade over the SQLite brain. See module docstring."""

    def __init__(self, conn: sqlite3.Connection, config: BrainEngineConfig) -> None:
        """Direct constructor — prefer create_new / open factory methods."""
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
    ) -> "BrainEngine":
        """Create a fresh brain DB at db_path and apply DDL v001.

        See docs/research/step1-spec.md §2.1 for PRAGMAs and §2.2 for DDL.
        """
        raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §2.1 + §2.2")

    @classmethod
    def open(
        cls,
        db_path: str | Path,
        *,
        tenant_id: Optional[str] = None,
        load_sqlite_vec: bool = True,
    ) -> "BrainEngine":
        """Open an existing brain DB; assert schema_version row exists."""
        raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §2.1")

    # ---- lifecycle ----------------------------------------------------------

    def close(self) -> None:
        """Flush WAL and close the underlying connection."""
        raise NotImplementedError("Step 1 R2")

    def __enter__(self) -> "BrainEngine":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ---- high-level operations (delegated to sub-modules in R2) -------------

    def put_page(self, slug: str, **kwargs: Any) -> int:
        """Insert or upsert a page; returns page_id. Delegates to brain.pages."""
        raise NotImplementedError("Step 1 R2 — see susr.brain.pages")

    def link(self, src_slug: str, edge_type: str, dst_slug: str, **props: Any) -> int:
        """Create a typed edge after validate_edge(); returns link id."""
        raise NotImplementedError("Step 1 R2 — see susr.brain.edges")

    def search(self, query: str, **kwargs: Any) -> list[Any]:
        """Hybrid retrieval; delegates to susr.brain.search.hybrid_search."""
        raise NotImplementedError("Step 1 R2 — see susr.brain.search")

    def snapshot(self, page_id: int, *, reason: str, actor: str) -> int:
        """Snapshot the page; delegates to susr.brain.versions."""
        raise NotImplementedError("Step 1 R2 — see susr.brain.versions")

    def commit_phase(self, phase: int, *, actor: str) -> dict[str, Any]:
        """Run all invariants for a phase and snapshot affected pages.

        Phase 3 (MVP) runs I1 + I2 (and I3 for any targets touched).
        See docs/research/step1-spec.md §2.5 + §4.1.
        """
        raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §2.5")
