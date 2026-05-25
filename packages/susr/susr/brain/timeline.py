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
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
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


# ---------------------------------------------------------------------------
# Markdown-body timeline helpers (R4d — collapse phase3._append_timeline_md
# into a single canonical implementation under brain/).
# ---------------------------------------------------------------------------

_TIMELINE_MD_MARKER = "## Timeline"
_TIMELINE_MD_LINE_RE = re.compile(r"^- \[", re.MULTILINE)


def _now_iso() -> str:
    """Current UTC timestamp as ISO-8601 seconds string (shared MD + DB)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append_timeline_md_body(
    body: str,
    action: str,
    payload: dict[str, Any],
    actor: str,
    *,
    ts: Optional[str] = None,
) -> tuple[str, int]:
    """Append one ``- [ts] action=... actor=... payload={..}\\n`` line to a
    page's markdown body under a ``## Timeline`` section.

    Args:
        body: existing markdown body (may or may not already contain the
            ``## Timeline`` marker; will be added if missing).
        action: short action token (e.g. ``"verify"``, ``"ingest"``,
            ``"iro_link"``); free-text, no enum enforcement here so callers
            can use both ActionType values and finer-grained labels.
        payload: dict, JSON-serialised inline with ``ensure_ascii=False`` so
            CJK stays human-readable in diffs.
        actor: who triggered the entry (consultant / agent id / "consultant:王").
        ts: optional ISO timestamp; defaults to ``_now_iso()``.  Pass an
            explicit value when ``append_dual`` wants MD and DB rows to
            share a timestamp.

    Returns:
        ``(new_body, synthetic_id)`` where synthetic_id is 1-based count of
        timeline lines in the resulting body — useful as a stable id when
        no brain DB row exists (e.g. phase3 tools in MD-only mode).
    """
    if ts is None:
        ts = _now_iso()
    body = body or ""
    if _TIMELINE_MD_MARKER not in body:
        body = body.rstrip() + f"\n\n---\n\n{_TIMELINE_MD_MARKER}\n\n"
    new_id = len(_TIMELINE_MD_LINE_RE.findall(body)) + 1
    line = (
        f"- [{ts}] action={action} actor={actor} payload="
        f"{json.dumps(payload, ensure_ascii=False, sort_keys=True)}\n"
    )
    return body + line, new_id


def append_dual(
    engine: Any,
    page_slug: Optional[str],
    action: str,
    payload: dict[str, Any],
    actor: str,
    *,
    body: str = "",
    source_ref: Optional[str] = None,
    confidence: Optional[float] = None,
    ts: Optional[str] = None,
) -> tuple[int, str]:
    """Unified timeline writer — DB ``timeline_entries`` + markdown body.

    R4d 收斂 (CLAUDE.md §8 decisions log)：原本兩處（``iro.py`` /
    ``action.py`` 直寫 brain DB；``phase3._append_timeline_md`` 只寫 markdown
    body）各自漂移欄位名 / 順序 / actor 寫法。本 helper 確保：

    1. 同一 ``ts`` 同時寫入 DB row 與 MD body line（顧問 ``git diff`` 與
       ``SELECT ... FROM timeline_entries`` 看到同樣 payload + actor）。
    2. payload 在 DB（JSON column）與 MD body（inline JSON）為相同字串
       (``json.dumps(payload, ensure_ascii=False, sort_keys=True)``)，方便
       audit trail 跨來源比對。
    3. 容錯：若 ``engine`` 為 ``None`` 或 ``page_slug`` 未在 brain DB（phase3
       tools 還沒 ingest 該 page 時的 MD-only fallback），DB 寫入被跳過，
       回傳 ``(synthetic_id, new_body)`` — synthetic_id = MD body 內 timeline
       line 的 1-based 計數，與舊 ``_append_timeline_md`` 行為相容。

    Args:
        engine: ``BrainEngine`` instance（要有 ``.conn`` 與 ``.get_page``）
            或 None（MD-only mode）。
        page_slug: brain DB 內 page slug（如 ``"iros/E1-impact-…"``）；None →
            略過 DB 寫入。
        action: action token（``"ingest"`` / ``"verify"`` / ``"iro_link"``…）；
            DB 端會被 CHECK 約束（見 ActionType 與 DDL §5）；MD 端任意字串。
        payload: 寫入 DB 與 MD 同一份字典。
        actor: ``"consultant"`` / ``"consultant:王"`` / agent id；同寫兩端。
        body: 既有的 markdown body 字串；若 ``"##Timeline"`` 標頭不存在會自動加。
        source_ref: 可選 source_ref（檔案路徑 / URL / ERP record id）。
        confidence: 可選 confidence (0..1)；MD 端不顯示，只進 DB。
        ts: 可選 ISO timestamp；預設 ``_now_iso()``，兩端共用。

    Returns:
        ``(id_or_synthetic, new_body)``：DB 寫成功時為 ``timeline_entries.id``，
        否則為 synthetic 1-based 計數。
    """
    if ts is None:
        ts = _now_iso()
    # MD body first — always succeeds (pure string op).
    new_body, synthetic_id = append_timeline_md_body(
        body, action, payload, actor, ts=ts
    )
    # DB write — best-effort; skipped silently if engine missing / slug unknown.
    db_id: Optional[int] = None
    if engine is not None and page_slug:
        try:
            page = engine.get_page(page_slug)
        except Exception:  # pragma: no cover — defensive
            page = None
        if page is not None:
            try:
                db_id = write_entry(
                    engine.conn,
                    page_id=int(page.id),
                    action_type=action,  # type: ignore[arg-type]
                    actor=actor,
                    source_ref=source_ref,
                    confidence=confidence,
                    payload=payload,
                )
                engine.conn.commit()
            except sqlite3.Error:  # pragma: no cover — defensive
                db_id = None
    return (db_id if db_id is not None else synthetic_id), new_body


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
