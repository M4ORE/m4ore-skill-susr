"""susr.brain.timeline — Append-only timeline_entries writer/reader.

The timeline is the "evidence chain" below the horizontal separator in
each markdown file (gbrain pattern).  Schema-enforced append-only:
trigger trg_timeline_no_update + trg_timeline_no_delete in DDL §5.

Action types (CHECK in DDL §5):
    ingest   — first write / re-ingest of source data
    verify   — consultant double-check
    restate  — value restatement (>5% delta auto-triggered, spec §4.2)
    assure   — third-party assurance pass
    comment  — consultant annotation
    iro_link — IRO mapping established
    gap_flag — gap-analysis flag

R1: dataclass + signatures.  R2: implement.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

ActionType = Literal[
    "ingest",
    "verify",
    "restate",
    "assure",
    "comment",
    "iro_link",
    "gap_flag",
]


@dataclass
class TimelineEntry:
    """One row of timeline_entries."""

    id: int
    page_id: int
    ts: str
    action_type: str
    source_ref: Optional[str] = None
    confidence: Optional[float] = None
    actor: Optional[str] = None
    payload: dict[str, Any] = field(default_factory=dict)


def write_entry(
    conn: sqlite3.Connection,
    *,
    page_id: int,
    action_type: ActionType,
    actor: str,
    source_ref: Optional[str] = None,
    confidence: Optional[float] = None,
    payload: Optional[dict[str, Any]] = None,
) -> int:
    """Append a timeline_entries row; returns new id.

    payload is JSON-serialized on the way in.  No update/delete is ever
    permitted — restating means writing a new row with action_type='restate'.
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §4.2")


def timeline_for_page(
    conn: sqlite3.Connection,
    page_id: int,
    *,
    action_types: Optional[list[ActionType]] = None,
    limit: int = 100,
) -> list[TimelineEntry]:
    """Return timeline_entries for a page, newest first."""
    raise NotImplementedError("Step 1 R2")


def write_datapoint_value(
    conn: sqlite3.Connection,
    page_id: int,
    *,
    new_value: float,
    actor: str,
    restate_threshold: float = 0.05,
) -> Optional[int]:
    """Update a datapoint's `value` attribute; if delta > threshold,
    auto-snapshot and write a 'restate' timeline entry.

    Returns the timeline entry id if a restate occurred, else None.
    See spec §4.2 for the threshold rationale (matches SKILL.md Phase 4).
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §4.2")
