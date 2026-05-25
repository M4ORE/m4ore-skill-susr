"""susr.brain.invariants — 5 connectivity invariants (fail-closed, spec §2.5).

Mapping:
    I1 core topic→Action chain    view v_core_topic_action_coverage
    I2 chapter completeness       view v_chapter_completeness
    I3 target 4 required fields   view v_target_completeness
    I4 datapoint→source_doc       app SQL (links + pages join)
    I5 emission factor in window  app SQL (date range vs datapoint.year)

API:
    assert_iX_* / assert_all     raise InvariantError on first/all failure
    check_all_invariants         return list[InvariantViolation], never raise
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from susr.brain.edges import InvariantError


# --- Non-raising result type (for MCP health_check) -----------------------


@dataclass(frozen=True)
class InvariantViolation:
    """One specific invariant breach found in the DB."""

    invariant: str  # 'I1' .. 'I5'
    page_slug: str
    detail: str


# --- Helpers ---------------------------------------------------------------


def _format(rows: list[str], cap: int = 5) -> str:
    head = rows[:cap]
    extra = "" if len(rows) <= cap else f" (+{len(rows) - cap} more)"
    return ", ".join(head) + extra


def _raise_if(violations: list[InvariantViolation], code: str, headline: str) -> None:
    """Common 'collect→raise InvariantError with slug list' tail for each assert_iX."""
    if not violations:
        return
    slugs = [v.page_slug for v in violations]
    raise InvariantError(f"{code} violated: {len(slugs)} {headline}: {_format(slugs)}")


# --- I1: core topic action coverage (view v_core_topic_action_coverage) ---


def _i1_violations(conn: sqlite3.Connection) -> list[InvariantViolation]:
    rows = conn.execute(
        "SELECT topic_slug FROM v_core_topic_action_coverage "
        "WHERE action_count = 0 ORDER BY topic_slug"
    ).fetchall()
    return [
        InvariantViolation(
            invariant="I1",
            page_slug=str(r[0]),
            detail="core topic has no Action via topic_has_iro→iro_addressed_by chain",
        )
        for r in rows
    ]


def assert_i1_core_topic_coverage(conn: sqlite3.Connection) -> None:
    """I1: every materiality_tier='核心' topic must reach an Action via IRO chain."""
    _raise_if(_i1_violations(conn), "I1", "核心 topic(s) have no Action via IRO chain")


# --- I2: chapter completeness (view v_chapter_completeness) ---------------


def _i2_violations(conn: sqlite3.Connection) -> list[InvariantViolation]:
    rows = conn.execute(
        "SELECT slug, framework_count, topic_count FROM v_chapter_completeness "
        "WHERE framework_count = 0 OR topic_count = 0 ORDER BY slug"
    ).fetchall()
    out: list[InvariantViolation] = []
    for slug, fw_count, tp_count in rows:
        missing = []
        if not fw_count:
            missing.append("chapter_conforms_to(framework)")
        if not tp_count:
            missing.append("discloses_topic(topic)")
        out.append(
            InvariantViolation(
                invariant="I2",
                page_slug=str(slug),
                detail=f"chapter missing required edges: {', '.join(missing)}",
            )
        )
    return out


def assert_i2_chapter_completeness(conn: sqlite3.Connection) -> None:
    """I2: every chapter must have >=1 chapter_conforms_to AND >=1 discloses_topic."""
    _raise_if(_i2_violations(conn), "I2", "chapter(s) missing framework or topic linkage")


# --- I3: target completeness (view v_target_completeness) -----------------

_I3_REQUIRED_FIELDS = (
    "baseline_year",
    "baseline_value",
    "target_year",
    "verification_path",
)


def _i3_violations(conn: sqlite3.Connection) -> list[InvariantViolation]:
    rows = conn.execute(
        "SELECT slug, has_baseline_year, has_baseline_value, "
        "has_target_year, has_verification_path FROM v_target_completeness"
    ).fetchall()
    out: list[InvariantViolation] = []
    for slug, has_by, has_bv, has_ty, has_vp in rows:
        flags = (has_by, has_bv, has_ty, has_vp)
        missing = [name for name, flag in zip(_I3_REQUIRED_FIELDS, flags) if not flag]
        if missing:
            out.append(
                InvariantViolation(
                    invariant="I3",
                    page_slug=str(slug),
                    detail=f"target missing frontmatter: {', '.join(missing)}",
                )
            )
    return out


def assert_i3_target_completeness(conn: sqlite3.Connection) -> None:
    """I3: every target frontmatter must declare 4 anti-greenwashing fields."""
    _raise_if(
        _i3_violations(conn),
        "I3",
        "target(s) missing required fields (anti-greenwashing)",
    )


# --- I4: datapoint source traceability (app SQL) --------------------------


def _i4_violations(conn: sqlite3.Connection) -> list[InvariantViolation]:
    """Quantitative datapoint (value_type int/float) must have >=1
    datapoint_derived_from→source_doc link.  Qualitative rows skipped."""
    rows = conn.execute(
        """
        SELECT p.slug
        FROM pages p
        JOIN entity_attributes a
          ON a.page_id = p.id AND a.key = 'value'
        WHERE p.entity_type = 'datapoint'
          AND p.deleted_at IS NULL
          AND a.value_type IN ('int', 'float')
          AND NOT EXISTS (
              SELECT 1
              FROM links l
              JOIN pages src ON src.id = l.dst_page_id
              WHERE l.src_page_id = p.id
                AND l.edge_type = 'datapoint_derived_from'
                AND src.entity_type = 'source_doc'
                AND src.deleted_at IS NULL
          )
        ORDER BY p.slug
        """
    ).fetchall()
    return [
        InvariantViolation(
            invariant="I4",
            page_slug=str(r[0]),
            detail="quantitative datapoint has no datapoint_derived_from→source_doc link",
        )
        for r in rows
    ]


def assert_i4_datapoint_source(conn: sqlite3.Connection) -> None:
    """I4: every quantitative datapoint must derive_from >=1 source_doc."""
    _raise_if(_i4_violations(conn), "I4", "quantitative datapoint(s) lack source traceability")


# --- I5: emission factor temporal validity (app SQL) ----------------------


def _i5_violations(conn: sqlite3.Connection) -> list[InvariantViolation]:
    """Emission datapoint (has datapoint_calculated_with edge) must reference
    >=1 emission_factor where effective_from..effective_to covers datapoint.year.
    Comparison uses the leftmost 4 chars (YYYY) of effective_from/to, which is
    safe for both ISO-8601 dates and bare 4-digit years."""
    rows = conn.execute(
        """
        WITH dp AS (
            SELECT p.id    AS page_id,
                   p.slug  AS slug,
                   a.value AS year_str
            FROM pages p
            JOIN entity_attributes a
              ON a.page_id = p.id AND a.key = 'year'
            WHERE p.entity_type = 'datapoint'
              AND p.deleted_at IS NULL
              AND EXISTS (
                  SELECT 1 FROM links l
                  WHERE l.src_page_id = p.id
                    AND l.edge_type = 'datapoint_calculated_with'
              )
        )
        SELECT dp.slug, dp.year_str, ef_eff_from.value, ef_eff_to.value
        FROM dp
        LEFT JOIN links l
               ON l.src_page_id = dp.page_id
              AND l.edge_type   = 'datapoint_calculated_with'
        LEFT JOIN pages ef       ON ef.id = l.dst_page_id
                                AND ef.entity_type = 'emission_factor'
                                AND ef.deleted_at IS NULL
        LEFT JOIN entity_attributes ef_eff_from
               ON ef_eff_from.page_id = ef.id
              AND ef_eff_from.key = 'effective_from'
        LEFT JOIN entity_attributes ef_eff_to
               ON ef_eff_to.page_id = ef.id
              AND ef_eff_to.key = 'effective_to'
        """
    ).fetchall()

    # Aggregate per datapoint: if NONE of its factors is in window, violate.
    seen_dp: dict[str, list[tuple[str, str | None, str | None]]] = {}
    for slug, year_str, eff_from, eff_to in rows:
        if slug is None:
            continue
        seen_dp.setdefault(str(slug), []).append((str(year_str), eff_from, eff_to))

    out: list[InvariantViolation] = []
    for slug, candidates in seen_dp.items():
        year_token = (candidates[0][0] or "")[:4]
        if not year_token:
            continue
        in_window = any(
            eff_from
            and str(eff_from)[:4] <= year_token
            and (not eff_to or str(eff_to)[:4] >= year_token)
            for _y, eff_from, eff_to in candidates
        )
        if not in_window:
            out.append(
                InvariantViolation(
                    invariant="I5",
                    page_slug=slug,
                    detail=f"datapoint year={year_token} has no calculated_with factor whose effective_from..effective_to covers it",
                )
            )
    out.sort(key=lambda v: v.page_slug)
    return out


def assert_i5_emission_factor_validity(conn: sqlite3.Connection) -> None:
    """I5: every emission datapoint must be linked to a temporally valid factor."""
    _raise_if(
        _i5_violations(conn),
        "I5",
        "emission datapoint(s) reference an out-of-window factor",
    )


# --- Aggregate runners -----------------------------------------------------


def check_all_invariants(conn: sqlite3.Connection) -> list[InvariantViolation]:
    """Run I1..I5; return every violation; never raises.  Used by MCP health_check."""
    return [
        *_i1_violations(conn),
        *_i2_violations(conn),
        *_i3_violations(conn),
        *_i4_violations(conn),
        *_i5_violations(conn),
    ]


def assert_all(conn: sqlite3.Connection) -> None:
    """Run I1..I5; aggregate every violation into one InvariantError.
    Used by BrainEngine.commit_phase as the fail-closed gate before snapshot."""
    violations = check_all_invariants(conn)
    if not violations:
        return
    by_invariant: dict[str, list[str]] = {}
    for v in violations:
        by_invariant.setdefault(v.invariant, []).append(v.page_slug)
    parts = [
        f"{name}({len(slugs)}): {_format(slugs)}"
        for name, slugs in sorted(by_invariant.items())
    ]
    raise InvariantError("invariant violations — " + " | ".join(parts))
