"""susr.shared_kb.snapshot — Snapshot the shipped KB into a client repo.

Plain file copy (not git submodule).  CLAUDE.md §8 decision 3:
"shared-kb 留在主 mono-repo 內，透過 snapshot copy 機制進 client repo".

Why not symlink:
    - Windows + git compatibility friction
    - We want the client repo to be self-contained for audit / reproducibility
    - Consultants want to control upgrade cadence (no surprise mid-year change)

R1: signatures.  R2: implement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def snapshot_into(
    client_repo_root: Path,
    *,
    subdir: str = "shared",
    overwrite: bool = False,
) -> dict:
    """Copy SHARED_KB_DATA_DIR into <client_repo_root>/<subdir>/.

    Returns {files_copied, files_skipped, target_path, source_version}.

    overwrite=False: refuses if target exists and is non-empty.
    overwrite=True : replaces target tree (used by update_shared_kb).
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §1.1 + §6.3")


def diff_against(client_repo_root: Path, *, subdir: str = "shared") -> dict:
    """Compare client's shared/ snapshot against the currently shipped KB.

    Returns {added, removed, modified} file lists.  Used by update_shared_kb
    in dry-run mode so the consultant can review changes before accepting.
    """
    raise NotImplementedError("Step 1 R2")


def get_shipped_version() -> Optional[str]:
    """Read a VERSION marker (or fall back to package __version__).

    R2 will define a VERSION file format inside data/ to make snapshot
    drift visible.
    """
    raise NotImplementedError("Step 1 R2")
