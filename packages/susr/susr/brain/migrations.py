"""susr.brain.migrations — DDL loader + schema version bookkeeping.

The current schema is a single file (ddl/v001_init.sql) that is
idempotent (every CREATE uses IF NOT EXISTS).  Future migrations
will add v002_*.sql files and this module will iterate them in
version order.

R1: signatures + loader stub.  R2: actually executescript the DDL
and assert schema_version row after.

See docs/research/step1-spec.md §2.1 + §2.2.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

DDL_DIR = Path(__file__).parent / "ddl"
CURRENT_SCHEMA_VERSION = 1


def list_migrations() -> list[Path]:
    """Return DDL files in version order (v001_*.sql, v002_*.sql, ...)."""
    raise NotImplementedError("Step 1 R2 — sort DDL_DIR/v*.sql by leading vNNN prefix")


def apply_all(conn: sqlite3.Connection) -> int:
    """Apply every migration past the connection's current schema_version.

    Returns the new schema_version after application.
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §2.2")


def get_current_version(conn: sqlite3.Connection) -> int:
    """Return MAX(version) from schema_version, or 0 if the table is absent."""
    raise NotImplementedError("Step 1 R2")


def read_ddl(version: int) -> str:
    """Load the raw SQL text for a specific migration version."""
    raise NotImplementedError("Step 1 R2")
