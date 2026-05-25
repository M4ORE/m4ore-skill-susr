"""susr.shared_kb — Bundled cross-client knowledge base.

This sub-package ships with the wheel (force-include in pyproject.toml)
so a fresh `pip install susr` is immediately useful — no separate
download step, no git submodule.  See CLAUDE.md §8 decision 3.

Layout (`data/` filled in R3 from references/):
    data/
      materiality-topics-universe.md
      ghg-protocol.md
      taiwan-fsc-sustainability-guidelines.md
      esg-glossary-zh-en.md
      compliance-checklist.md
      industry-packs/
        hotel.md
        ...

Snapshot mechanism (`snapshot.py`):
    When create_client_workspace runs, the current content of `data/` is
    COPIED into the client repo's `shared/` directory.  Each client's
    snapshot is frozen unless the consultant explicitly runs
    update_shared_kb (so newer emission factors do not auto-retroact).
"""

from __future__ import annotations

from pathlib import Path

# Resolve at import time so callers can introspect path easily.
SHARED_KB_DATA_DIR: Path = Path(__file__).parent / "data"

__all__ = ["SHARED_KB_DATA_DIR"]
