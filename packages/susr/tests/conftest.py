"""susr package-level shared fixtures.

Aligned with the repo-level `tests/conftest.py` style (Path-based,
session-scoped where idempotent, no cwd reliance).  Shared with the
Layer 3 + Layer 4 tests added in R2.

R2: adds tmp_db / tmp_brain / tmp_client_workspace / mock_embedding_provider
on top of the R1 universal fixtures (PACKAGE_ROOT, REPO_ROOT, ddl_path).
The brain-related fixtures intentionally call into the R1 stubs — they
will raise NotImplementedError until R2-A/B/C/D complete; that is the
expected behaviour and is what the §6.1 hard-rule contract requires.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Sequence

import numpy as np
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


# ---------------------------------------------------------------------------
# R2 fixtures — DB / engine / workspace / mock provider.
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_db(tmp_path: Path):
    """產生空 SQLite DB（已跑 DDL）給單元測試用。

    Yields the raw sqlite3 connection so 低階測試（schema / trigger / view）
    可以直接 execute SQL，不必繞 BrainEngine.
    """
    from susr.brain.migrations import init_database

    conn = init_database(tmp_path / "test.db")
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


@pytest.fixture
def tmp_brain(tmp_path: Path):
    """產生空 BrainEngine 給高階單元測試用（put_page / link / snapshot）。

    R2 BrainEngine.create_new 完成後此 fixture 即可被使用；在 R2 完成前
    呼叫端會看到 NotImplementedError，這是預期行為（測試是契約）。
    """
    from susr.brain.engine import BrainEngine

    engine = BrainEngine.create_new(tmp_path / "test_brain.sqlite", tenant_id=None)
    try:
        yield engine
    finally:
        try:
            engine.close()
        except Exception:
            pass


@pytest.fixture
def tmp_client_workspace(tmp_path: Path, monkeypatch):
    """產生空 client workspace skeleton 給 workspace ops 測試。

    Wraps susr.workspace.create_client_workspace + 同時 monkeypatch
    SUSR_WORKSPACE_ROOT，讓 MCP workspace tools（用 env var lookup
    workspace path 的）也能找到此 tmp 路徑。
    """
    monkeypatch.setenv("SUSR_WORKSPACE_ROOT", str(tmp_path))
    from susr.workspace import create_client_workspace

    return create_client_workspace(
        root=tmp_path,
        name="test-client",
        legal_name="Test Client Co., Ltd.",
        industry="hospitality",
        standards=["GRI", "ISSB"],
        boundary="合併",
        reporting_period="2025-01-01..2025-12-31",
    )


# ---------------------------------------------------------------------------
# Mock embedding provider — deterministic, no real model load.
# ---------------------------------------------------------------------------


class _MockEmbeddingProvider:
    """假 embedding provider 回固定向量，避免測試載入真模型。

    Implements the susr.embeddings.provider.EmbeddingProvider Protocol
    (runtime_checkable) with deterministic hash-based vectors so two
    identical inputs produce identical outputs across test runs.
    """

    name = "mock:deterministic"
    dimension = 1024
    hosting = "local"

    def embed_query(self, text: str) -> np.ndarray:
        """編碼單一字串 → (dimension,) ndarray，hash-based 確定性結果。"""
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # repeat digest until it fills the dimension; cast to float32 in [-1, 1]
        repeats = (self.dimension // len(digest)) + 1
        raw = (digest * repeats)[: self.dimension]
        arr = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
        # Normalise to roughly unit-ish range so downstream distance maths
        # stays well-behaved; we don't care about real semantic distance here.
        arr = (arr - 127.5) / 127.5
        return arr

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        """批次編碼 → (len(texts), dimension) ndarray。

        空 input 回 shape ``(0, dimension)``,避免 np.stack 對空 list 噴。
        """
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        return np.stack([self.embed_query(t) for t in texts])


@pytest.fixture
def mock_embedding_provider() -> _MockEmbeddingProvider:
    """假 embedding provider 回固定向量，避免測試載入真模型。"""
    return _MockEmbeddingProvider()
