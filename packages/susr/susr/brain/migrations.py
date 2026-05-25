"""susr.brain.migrations — DDL loader + schema version bookkeeping.

The current schema is a single file (ddl/v001_init.sql) that is
idempotent (every CREATE uses IF NOT EXISTS).  Future migrations
will add v002_*.sql files and this module will iterate them in
version order.

Public surface
--------------
- ``apply_all(conn)`` — apply every migration past the connection's
  current schema_version; returns the new version.
- ``get_current_version(conn)`` — read MAX(version) from schema_version.
- ``read_ddl(version)`` — load raw SQL text for one migration.
- ``list_migrations()`` — enumerate vNNN_*.sql files in version order.
- ``init_database(db_path, *, load_sqlite_vec=True)`` — convenience
  factory: open connection → load sqlite-vec → apply PRAGMAs → apply
  every pending migration → return the connection.  Idempotent: re-open
  on an existing DB skips DDL but re-applies PRAGMAs / extension load.

See ``docs/research/step1-spec.md`` §2.1 + §2.2.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import sqlite_vec  # type: ignore[import-untyped]

DDL_DIR = Path(__file__).parent / "ddl"
CURRENT_SCHEMA_VERSION = 1

# Matches "v001_init.sql" / "v002_foo.sql" — leading 'v', 3+ digits, underscore.
_MIGRATION_RE = re.compile(r"^v(\d{3,})_[\w\-]+\.sql$")

# PRAGMA baseline pulled from spec §2.1.  Re-applied on every open() so
# that an existing DB still gets WAL + foreign_keys + mmap etc.
_DEFAULT_PRAGMAS = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 268435456;
PRAGMA cache_size = -64000;
"""


# ---------------------------------------------------------------------------
# Migration discovery
# ---------------------------------------------------------------------------


def list_migrations() -> list[Path]:
    """傳回 DDL 目錄下所有 vNNN_*.sql，依版本序排序。

    Files that do not match the ``vNNN_<name>.sql`` pattern are ignored so
    that stray docs/READMEs in ``ddl/`` don't break startup.
    """
    if not DDL_DIR.exists():
        return []
    pairs: list[tuple[int, Path]] = []
    for path in DDL_DIR.iterdir():
        m = _MIGRATION_RE.match(path.name)
        if m:
            pairs.append((int(m.group(1)), path))
    pairs.sort(key=lambda p: p[0])
    return [p for _, p in pairs]


def read_ddl(version: int) -> str:
    """Load the raw SQL text for a specific migration version."""
    for path in list_migrations():
        m = _MIGRATION_RE.match(path.name)
        if m and int(m.group(1)) == version:
            return path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"no DDL file found for migration version v{version:03d}")


# ---------------------------------------------------------------------------
# schema_version interrogation + apply
# ---------------------------------------------------------------------------


def _schema_version_table_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_version' LIMIT 1"
    ).fetchone()
    return row is not None


def get_current_version(conn: sqlite3.Connection) -> int:
    """Return MAX(version) from schema_version, or 0 if the table is absent."""
    if not _schema_version_table_exists(conn):
        return 0
    row = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def apply_all(conn: sqlite3.Connection) -> int:
    """套用所有尚未執行的 migration，傳回最終 schema_version。

    Each DDL file is idempotent (CREATE IF NOT EXISTS / INSERT OR IGNORE) so
    re-running an already-applied version is harmless; we still skip it via
    ``get_current_version`` to keep the apply path cheap.
    """
    current = get_current_version(conn)
    target = CURRENT_SCHEMA_VERSION
    if current >= target:
        return current

    for path in list_migrations():
        m = _MIGRATION_RE.match(path.name)
        if not m:
            continue
        version = int(m.group(1))
        if version <= current:
            continue
        sql = path.read_text(encoding="utf-8")
        # executescript opens its own transaction; wrap is unnecessary.
        conn.executescript(sql)

    # Mirror to PRAGMA user_version for tooling that reads it directly.
    new_version = get_current_version(conn)
    conn.execute(f"PRAGMA user_version = {new_version}")
    conn.commit()
    return new_version


# ---------------------------------------------------------------------------
# Convenience: end-to-end DB init for new or existing files.
# ---------------------------------------------------------------------------


def _load_sqlite_vec(conn: sqlite3.Connection) -> None:
    """Load the sqlite-vec extension on a fresh connection.

    macOS system Python lacks ``enable_load_extension`` (spec §2.2 note);
    we raise a clear error in that case so the doctor command can guide
    users to Homebrew / python.org installers.
    """
    try:
        conn.enable_load_extension(True)
    except AttributeError as exc:  # pragma: no cover — platform-specific
        raise RuntimeError(
            "This Python build lacks sqlite extension loading support. "
            "Install Python via Homebrew or python.org (see step1-spec §2.2)."
        ) from exc
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)


def init_database(
    db_path: str | Path,
    *,
    load_sqlite_vec: bool = True,
) -> sqlite3.Connection:
    """開啟 / 建立 SQLite brain DB；載入 extension、套 PRAGMA、跑 migration。

    Behaviour:
        - If the file does not exist → it is created and DDL v001 applied.
        - If the file exists and schema_version is current → DDL is skipped
          (idempotent open), but extension + PRAGMAs are always re-applied.
        - Always returns a connection with ``foreign_keys = ON``.

    Args:
        db_path: Filesystem path to the SQLite file.  Parent dirs are
            created on demand.  Use ``":memory:"`` for an ephemeral DB.
        load_sqlite_vec: Disable to skip vec0 virtual-table registration —
            useful for narrow unit tests that don't touch embeddings.
    """
    path = Path(db_path) if str(db_path) != ":memory:" else None
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)

    # isolation_level=None puts sqlite3 in autocommit mode — each statement
    # is its own transaction unless wrapped in explicit BEGIN/COMMIT. This is
    # required because parts of the codebase (pages.put_page / update_page)
    # use explicit BEGIN/COMMIT, while others (versions.snapshot_page /
    # timeline.write_entry) rely on per-statement autocommit. Mixing the
    # default deferred-isolation with explicit BEGIN raises
    # "cannot start a transaction within a transaction".
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    # Allow %d-style row indexing in clients that prefer it; explicit factory
    # is up to the caller (BrainEngine sets it on construction).

    if load_sqlite_vec:
        _load_sqlite_vec(conn)

    # PRAGMA must be set BEFORE DDL on the first run so that journal_mode=WAL
    # takes effect for the initial schema creation.
    conn.executescript(_DEFAULT_PRAGMAS)

    apply_all(conn)
    return conn
