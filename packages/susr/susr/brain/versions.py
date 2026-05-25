"""susr.brain.versions — page_versions snapshot create + restore.

Snapshot triggers (spec §4.1):
    manual         — consultant asks Claude to "freeze the matrix now"
    phase_complete — BrainEngine.commit_phase finishes invariants
    year_freeze    — fork prior year project pre-mutation
    restate        — auto-fired when DataPoint.value moves >5% (spec §4.2)
    assurance      — third-party assurance approval

Snapshots are write-only history; "restore" works by writing a NEW page row
with the snapshot's content (we do not rewind the live row).

R1: dataclass + signatures.  R2: implement.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Literal, Optional

SnapshotReason = Literal[
    "manual",
    "phase_complete",
    "year_freeze",
    "restate",
    "assurance",
]


@dataclass
class PageVersion:
    """One snapshot row (mirrors page_versions table)."""

    id: int
    page_id: int
    version_no: int
    parent_version_id: Optional[int]
    content_hash: str
    frontmatter_snap: str  # JSON
    compiled_truth_snap: str
    snapshot_reason: str
    created_at: str
    created_by: Optional[str]


def snapshot_page(
    conn: sqlite3.Connection,
    page_id: int,
    *,
    reason: SnapshotReason,
    actor: str,
) -> int:
    """Take a snapshot of `pages[page_id]` + its current frontmatter.

    Computes version_no = MAX(version_no) + 1 per page (monotonic).
    parent_version_id chains back to the previous snapshot, if any.

    Returns the new page_versions.id.
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §4.1")


def get_version(conn: sqlite3.Connection, version_id: int) -> Optional[PageVersion]:
    """Return a single PageVersion by primary key, or None."""
    raise NotImplementedError("Step 1 R2")


def list_versions(
    conn: sqlite3.Connection,
    page_id: int,
    *,
    limit: int = 50,
) -> list[PageVersion]:
    """Return snapshots for a page, newest first (version_no DESC)."""
    raise NotImplementedError("Step 1 R2")


def restore_from(
    conn: sqlite3.Connection,
    version_id: int,
    *,
    actor: str,
) -> int:
    """Restore a snapshot by overwriting the live page row with the snap data.

    A `comment` timeline entry is appended marking the restore source.
    Returns the page_id that was restored.
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §4.1")
