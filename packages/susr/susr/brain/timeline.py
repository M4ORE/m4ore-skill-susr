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

Restatement helper (`write_datapoint_value`):
    - Reads baseline from current entity_attributes (page_id, key='value').
    - Computes delta_pct = |new - old| / |old| (guard div-by-zero by treating
      old==0 as 100% change → always above threshold).
    - If delta_pct > threshold: append snapshot(reason='restate') +
      timeline_entries(action_type='restate') and rewrite the value.
    - If delta_pct <= threshold: rewrite value silently.  Returns None.
"""

from __future__ import annotations

import json
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


# ---------------------------------------------------------------------------
# Core writers / readers
# ---------------------------------------------------------------------------


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

    payload is JSON-serialized on the way in.  No UPDATE/DELETE is ever
    permitted by schema triggers — restating means writing a new row with
    action_type='restate'.
    """
    payload_json = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True)
    cur = conn.execute(
        """
        INSERT INTO timeline_entries
            (page_id, action_type, source_ref, confidence, actor, payload)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [page_id, action_type, source_ref, confidence, actor, payload_json],
    )
    return int(cur.lastrowid)


def timeline_for_page(
    conn: sqlite3.Connection,
    page_id: int,
    *,
    action_types: Optional[list[ActionType]] = None,
    limit: int = 100,
) -> list[TimelineEntry]:
    """Return timeline_entries for a page, newest first."""
    sql = (
        "SELECT id, page_id, ts, action_type, source_ref, confidence, actor, payload "
        "FROM timeline_entries WHERE page_id = ?"
    )
    params: list[object] = [page_id]
    if action_types:
        placeholders = ",".join("?" * len(action_types))
        sql += f" AND action_type IN ({placeholders})"
        params.extend(action_types)
    sql += " ORDER BY ts DESC, id DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    out: list[TimelineEntry] = []
    for r in rows:
        try:
            payload = json.loads(r[7]) if r[7] else {}
            if not isinstance(payload, dict):
                payload = {"_": payload}
        except (TypeError, ValueError):
            payload = {}
        out.append(
            TimelineEntry(
                id=int(r[0]),
                page_id=int(r[1]),
                ts=str(r[2]),
                action_type=str(r[3]),
                source_ref=(str(r[4]) if r[4] is not None else None),
                confidence=(float(r[5]) if r[5] is not None else None),
                actor=(str(r[6]) if r[6] is not None else None),
                payload=payload,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Restatement helper (spec §4.2)
# ---------------------------------------------------------------------------

DEFAULT_RESTATE_THRESHOLD: float = 0.05  # 5%, matches SKILL.md Phase 4 trigger


def write_datapoint_value(
    conn: sqlite3.Connection,
    page_id: int,
    *,
    new_value: float,
    actor: str,
    restate_threshold: float = DEFAULT_RESTATE_THRESHOLD,
    source_ref: Optional[str] = None,
) -> Optional[int]:
    """Update a datapoint's `value` attribute; if delta > threshold,
    auto-snapshot AND write a 'restate' timeline entry.

    Baseline read: SELECT value FROM entity_attributes WHERE page_id=? AND key='value'.
    Delta formula: |new - old| / |old|.  Old==0 fallback: any non-zero new
    counts as a restate (we report delta_pct=inf -> serialized as 'inf').

    Returns:
        timeline_entries.id of the 'restate' row if a restate occurred,
        otherwise None.
    """
    row = conn.execute(
        "SELECT value FROM entity_attributes WHERE page_id = ? AND key = 'value'",
        [page_id],
    ).fetchone()

    if row is None or row[0] is None:
        # No prior value — treat as first ingest, no restate semantics.
        _upsert_value(conn, page_id, new_value)
        return None

    try:
        old_value = float(row[0])
    except (TypeError, ValueError):
        # Non-numeric prior value: rewrite, no restate trigger.
        _upsert_value(conn, page_id, new_value)
        return None

    if old_value == 0:
        delta_pct: float = float("inf") if new_value != 0 else 0.0
    else:
        delta_pct = abs(new_value - old_value) / abs(old_value)

    _upsert_value(conn, page_id, new_value)

    if delta_pct <= restate_threshold:
        return None

    # Snapshot first so the post-rewrite frontmatter is captured.
    # Local import dodges the versions <-> timeline cycle.
    from susr.brain.versions import snapshot_page

    snapshot_page(conn, page_id, reason="restate", actor=actor)

    payload = {
        "old_value": old_value,
        "new_value": new_value,
        # JSON cannot encode inf; serialize as string sentinel.
        "delta_pct": ("inf" if delta_pct == float("inf") else delta_pct),
        "threshold": restate_threshold,
    }
    return write_entry(
        conn,
        page_id=page_id,
        action_type="restate",
        actor=actor,
        source_ref=source_ref,
        payload=payload,
    )


def _upsert_value(conn: sqlite3.Connection, page_id: int, new_value: float) -> None:
    """Set entity_attributes.value to new_value as a float attribute.

    UNIQUE(page_id, key) lets ON CONFLICT REPLACE keep things atomic without
    an extra SELECT round-trip.
    """
    conn.execute(
        """
        INSERT INTO entity_attributes (page_id, key, value, value_type)
        VALUES (?, 'value', ?, 'float')
        ON CONFLICT (page_id, key) DO UPDATE
            SET value      = excluded.value,
                value_type = excluded.value_type
        """,
        [page_id, str(new_value)],
    )
