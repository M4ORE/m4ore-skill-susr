"""susr package-level shared fixtures.

Aligned with the repo-level `tests/conftest.py` style (Path-based,
session-scoped where idempotent, no cwd reliance).  Shared with the
Layer 3 + Layer 4 tests added in R2.

R1: only the universal fixtures are wired (PACKAGE_ROOT, repo_root,
ddl_path).  R2 will add `tmp_brain` / `tmp_brain_with_fixtures` once
BrainEngine is implemented (see spec §8.1 fixture pattern).
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Path fixtures — mirror repo-level conftest style (session-scoped, absolute).
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def PACKAGE_ROOT() -> Path:
    """Absolute path to the packages/susr/ directory."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def REPO_ROOT(PACKAGE_ROOT: Path) -> Path:
    """Absolute path to the mono-repo root (two levels above this file)."""
    return PACKAGE_ROOT.parent.parent


@pytest.fixture(scope="session")
def ddl_path(PACKAGE_ROOT: Path) -> Path:
    """Absolute path to the current DDL (ddl/v001_init.sql).

    Layer 4 schema tests (R2) will read + executescript this file against
    a fresh `:memory:` SQLite connection to assert it loads clean.
    """
    return PACKAGE_ROOT / "susr" / "brain" / "ddl" / "v001_init.sql"


@pytest.fixture(scope="session")
def shared_kb_data_dir(PACKAGE_ROOT: Path) -> Path:
    """Path to the bundled shared_kb data tree (empty in R1; filled R3)."""
    return PACKAGE_ROOT / "susr" / "shared_kb" / "data"


# ---------------------------------------------------------------------------
# Per-test temp paths.
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """Per-test SQLite file path under pytest's tmp_path.

    R2 fixtures `tmp_brain` / `tmp_brain_with_fixtures` will build on top
    of this (BrainEngine.create_new(tmp_db_path)).
    """
    return tmp_path / "test_brain.sqlite"
