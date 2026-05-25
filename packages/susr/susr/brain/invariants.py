"""susr.brain.invariants — 5 connectivity invariants (fail-closed, spec §2.5).

R4 split: 原本的 I1（core topic → IRO → Action 雙鏈耦合）被拆成兩段，讓
Phase 3 完成（建好 IRO 但 Action 還沒做）成為合法中間態。

Mapping:
    I1a core topic has IRO         view v_i1a_core_topic_has_iro
    I1b IRO has Action             view v_i1b_iro_has_action
    I1 (legacy)                    = I1a + I1b 同時跑（backward compat）
    I2 chapter completeness        view v_chapter_completeness
    I3 target 4 required fields    view v_target_completeness
    I4 datapoint→source_doc        app SQL (links + pages join)
    I5 emission factor in window   app SQL (date range vs datapoint.year)

API:
    assert_iX_* / assert_all     raise InvariantError on first/all failure
    check_all_invariants         return list[InvariantViolation], never raise

Phase gating (spec §2.5)：
    - Phase 3 完成後：I1a + I2 + I3 應 pass；I1b 仍 fail 屬合法中間態
    - Phase 5 完成後：I1b 也 pass（IRO 都鏈到 Action）
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional

from susr.brain.edges import InvariantError


# --- Non-raising result type (for MCP health_check) -----------------------


@dataclass(frozen=True)
class InvariantViolation:
    """One specific invariant breach found in the DB.

    Attributes:
        invariant: 廣義 invariant code（'I1' / 'I2' .. 'I5'）。
            為 backward compatibility，I1a / I1b violation 此欄位仍填 'I1'，
            細分鍵見 ``invariant_name``。
        invariant_name: 精確的 invariant 名稱（'I1a' / 'I1b' / 'I2' .. 'I5'）。
            R4 新增 — 區分拆出的子 invariant。
        page_slug: 違反的 page slug。
        detail: 人讀說明。
        group: R5-3 新增 — 細分嚴重度群組，便於 MCP UI 與顧問判斷工序。
            目前僅 I1b 套用，其他 invariant 保持 None。可能值：
                - ``"unbound"``      — IRO 無任何 outgoing edge（最緊急；新建未鏈）
                - ``"dangling"``     — 有 iro_addressed_by edge 但 action page
                    不存在（資料壞，需修補）
                - ``"deferred"``     — Opportunity 型 IRO 且 topic tier 非核心，
                    可以接受 Phase 5 之前未鏈
                - ``"pending"``      — 其他正常待辦（多數為核心 topic 下 IRO
                    尚未進入 Phase 5）
            MCP `health_check` 暴露時可以依 group 過濾，顧問不必看完整 list 也
            能優先解決 ``unbound`` / ``dangling``。
    """

    invariant: str  # 'I1' .. 'I5'（廣義 — backward compat 用）
    page_slug: str
    detail: str
    invariant_name: str = ""  # 'I1a' / 'I1b' / 'I2' / 'I3' / 'I4' / 'I5'
    group: Optional[str] = None

    def __post_init__(self) -> None:
        # 若呼叫端只給 `invariant`（舊 R3 caller），自動鏡像到 invariant_name。
        # frozen=True 用 object.__setattr__ 繞 frozen 限制。
        if not self.invariant_name:
            object.__setattr__(self, "invariant_name", self.invariant)


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


# --- I1a: core topic has IRO (view v_i1a_core_topic_has_iro) --------------


def _i1a_violations(
    conn: sqlite3.Connection, tenant_id: Optional[str] = None
) -> list[InvariantViolation]:
    """I1a：核心 topic 必有 IRO（Phase 3 後應 pass）。"""
    if tenant_id is None:
        rows = conn.execute(
            "SELECT topic_slug FROM v_i1a_core_topic_has_iro "
            "WHERE iro_count = 0 ORDER BY topic_slug"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT topic_slug FROM v_i1a_core_topic_has_iro "
            "WHERE iro_count = 0 AND tenant_id IS ? ORDER BY topic_slug",
            [tenant_id],
        ).fetchall()
    return [
        InvariantViolation(
            invariant="I1",
            page_slug=str(r[0]),
            detail="core topic has no IRO (missing topic_has_iro edge)",
            invariant_name="I1a",
        )
        for r in rows
    ]


def assert_i1a_core_topic_has_iro(
    conn: sqlite3.Connection, tenant_id: Optional[str] = None
) -> None:
    """I1a：核心 topic 必有 IRO（Phase 3 後應 pass）。

    fail-closed → raise ``InvariantError``。Phase 3 完成的合法條件之一。
    """
    _raise_if(
        _i1a_violations(conn, tenant_id),
        "I1a",
        "核心 topic(s) have no IRO (topic_has_iro edge missing)",
    )


# --- I1b: IRO has Action (view v_i1b_iro_has_action) ----------------------


def _i1b_violations(
    conn: sqlite3.Connection, tenant_id: Optional[str] = None
) -> list[InvariantViolation]:
    """I1b：IRO 必有 Action（Phase 5 後應 pass）。

    R5-3 分組（``InvariantViolation.group``）：

        - ``"unbound"``  — IRO 完全無 outgoing edge（連 ``iro_addressed_by`` 都
          沒插過）；最緊急的 case，可能是 ``link_topic_to_iro`` 完但顧問還沒
          進到 Phase 5。
        - ``"dangling"`` — 有 ``iro_addressed_by`` edge 但對端 action page
          不存在（deleted_at 不是 NULL 或 entity_type 不是 'action'）。資料
          一致性問題，需要修補。
        - ``"deferred"`` — IRO type 為 ``"Opportunity"`` 且其 topic 的
          ``materiality_tier`` 非 ``"核心"`` — Phase 5 之前未鏈可接受
          (機會型 IRO 對非核心議題優先級較低)。
        - ``"pending"``  — 其他（最常見的 happy-path 待辦：核心 topic 下的
          impact/risk IRO 尚未在 Phase 5 補 action）。
    """
    # 抓 violations + IRO 對應的 type + 父 topic 的 materiality_tier，一次撈乾淨。
    # LEFT JOIN 路徑：
    #   v_i1b_iro_has_action → pages (iro) → entity_attributes(type)
    #     → links (topic_has_iro 反向) → pages (topic) → entity_attributes(tier)
    base_sql = """
        SELECT
            v.iro_slug,
            ea_iro_type.value     AS iro_type,
            ea_topic_tier.value   AS topic_tier,
            (SELECT COUNT(*) FROM links l_any
             WHERE l_any.src_page_id = p_iro.id) AS any_out_count,
            (SELECT COUNT(*) FROM links l_addr
             JOIN pages p_act ON p_act.id = l_addr.dst_page_id
             WHERE l_addr.src_page_id = p_iro.id
               AND l_addr.edge_type = 'iro_addressed_by'
               AND (p_act.deleted_at IS NOT NULL
                    OR p_act.entity_type != 'action')
            ) AS dangling_count
        FROM v_i1b_iro_has_action v
        JOIN pages p_iro
              ON p_iro.slug = v.iro_slug
             AND p_iro.entity_type = 'iro'
             AND p_iro.deleted_at IS NULL
        LEFT JOIN entity_attributes ea_iro_type
              ON ea_iro_type.page_id = p_iro.id
             AND ea_iro_type.key = 'type'
        LEFT JOIN links l_topic
              ON l_topic.dst_page_id = p_iro.id
             AND l_topic.edge_type = 'topic_has_iro'
        LEFT JOIN pages p_topic
              ON p_topic.id = l_topic.src_page_id
             AND p_topic.entity_type = 'topic'
        LEFT JOIN entity_attributes ea_topic_tier
              ON ea_topic_tier.page_id = p_topic.id
             AND ea_topic_tier.key = 'materiality_tier'
        WHERE v.action_count = 0
    """
    if tenant_id is None:
        sql = base_sql + " ORDER BY v.iro_slug"
        params: list[object] = []
    else:
        sql = base_sql + " AND v.tenant_id IS ? ORDER BY v.iro_slug"
        params = [tenant_id]

    rows = conn.execute(sql, params).fetchall()
    out: list[InvariantViolation] = []
    for slug, iro_type, topic_tier, any_out_count, dangling_count in rows:
        if dangling_count and int(dangling_count) > 0:
            group = "dangling"
        elif not any_out_count or int(any_out_count) == 0:
            group = "unbound"
        elif (
            iro_type
            and str(iro_type).strip().lower() == "opportunity"
            and (topic_tier is None or str(topic_tier).strip() != "核心")
        ):
            group = "deferred"
        else:
            group = "pending"
        out.append(
            InvariantViolation(
                invariant="I1",
                page_slug=str(slug),
                detail="IRO has no Action (missing iro_addressed_by edge)",
                invariant_name="I1b",
                group=group,
            )
        )
    return out


def assert_i1b_iro_has_action(
    conn: sqlite3.Connection, tenant_id: Optional[str] = None
) -> None:
    """I1b：IRO 必有 Action（Phase 5 後應 pass）。

    fail-closed → raise ``InvariantError``。Phase 3 完成時此項仍 fail 屬合法
    中間態（顧問還沒做行動方案）。
    """
    _raise_if(
        _i1b_violations(conn, tenant_id),
        "I1b",
        "IRO(s) have no Action (iro_addressed_by edge missing)",
    )


# --- I1 (legacy): combined core topic action coverage --------------------


def _i1_violations(
    conn: sqlite3.Connection, tenant_id: Optional[str] = None
) -> list[InvariantViolation]:
    """[deprecated] 同時跑 I1a + I1b — 等於舊的 v_core_topic_action_coverage 語意。"""
    return [
        *_i1a_violations(conn, tenant_id),
        *_i1b_violations(conn, tenant_id),
    ]


def assert_i1_core_topic_coverage(
    conn: sqlite3.Connection, tenant_id: Optional[str] = None
) -> None:
    """[deprecated] 同時跑 I1a + I1b（向下相容 R3 caller）。

    新代碼請改用 ``assert_i1a_core_topic_has_iro`` / ``assert_i1b_iro_has_action``
    分別 check，讓 Phase 3 完成（I1a pass / I1b 仍 fail）成為可區分的合法中間態。
    """
    assert_i1a_core_topic_has_iro(conn, tenant_id)
    assert_i1b_iro_has_action(conn, tenant_id)


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


def check_all_invariants(
    conn: sqlite3.Connection, tenant_id: Optional[str] = None
) -> list[InvariantViolation]:
    """Run I1a, I1b, I2..I5; return every violation; never raises.

    R4 拆分：I1 替換為 I1a (topic→IRO) + I1b (IRO→Action)，個別 check。
    `InvariantViolation.invariant` 仍填 'I1'（backward compat MCP health_check
    payload），新增 `invariant_name` 欄位 ('I1a' / 'I1b') 區分子 invariant。
    """
    return [
        *_i1a_violations(conn, tenant_id),
        *_i1b_violations(conn, tenant_id),
        *_i2_violations(conn),
        *_i3_violations(conn),
        *_i4_violations(conn),
        *_i5_violations(conn),
    ]


def assert_all(
    conn: sqlite3.Connection, tenant_id: Optional[str] = None
) -> None:
    """Run I1a, I1b, I2..I5; aggregate every violation into one InvariantError.

    Used by BrainEngine.commit_phase as the fail-closed gate before snapshot.
    報錯 grouping 改用 ``invariant_name``（區分 I1a / I1b）。
    """
    violations = check_all_invariants(conn, tenant_id)
    if not violations:
        return
    by_name: dict[str, list[str]] = {}
    for v in violations:
        by_name.setdefault(v.invariant_name or v.invariant, []).append(v.page_slug)
    parts = [
        f"{name}({len(slugs)}): {_format(slugs)}"
        for name, slugs in sorted(by_name.items())
    ]
    raise InvariantError("invariant violations — " + " | ".join(parts))
