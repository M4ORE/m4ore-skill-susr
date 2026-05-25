"""susr.brain._slug — Page slug 慣例統一（R4c 收斂）。

背景
----
Brain 內 page 寫入時歷史上用了兩種 slug 慣例：

* **Prefixed**（canonical）：``topics/E1`` / ``iros/E1-001-flood-risk`` /
  ``chapters/E1-climate`` — 路徑風格，entity_type 直接從 slug 字首看出
* **Unqualified**（legacy / 顧問手打）：``E1`` / ``flood-risk-action``

問題：``get_page("E1")`` 與 ``get_page("topics/E1")`` 在不同寫入路徑下會錯
失彼此，導致 ``_resolve_page_id_for_edge`` 等 caller 要層層 fallback。

設計
----
1. **Source of truth = prefixed**。所有 brain 寫入應呼叫 ``resolve_slug``
   把 raw slug 補成 ``<plural>/<id>`` 形式。
2. **輸入端兼容**：``get_page(unqualified)`` 仍能查到 prefixed page（後綴匹配
   ``LIKE '%/<id>'``）。Ambiguous 情境 raise ``AmbiguousSlugError``。
3. **UI / 文案使用 ``slug_unqualified``** 把 ``topics/E1`` 還原為 ``E1``。

CLAUDE.md §4.6.4：本檔 < 100 行；單一 cohesive concept（slug normalization）。
"""

from __future__ import annotations

import sqlite3
from typing import Optional


class AmbiguousSlugError(LookupError):
    """Unqualified slug 在 DB 內對應 ≥2 個 entity_type 的 page。

    顧問必須改傳 prefixed slug（``topics/E1`` 而非 ``E1``）以消除歧義。
    """


# entity_type → canonical prefix（不含結尾 ``/``）
# 與 ingest._infer_entity_type_from_path 的「逆向」對齊，但這裡只有
# **canonical write form**；ingest 仍接受多個別名（如 ``peers/`` / ``peer_companies/``）
ENTITY_TYPE_PREFIX: dict[str, str] = {
    "client":          "clients",
    "report":          "reports",
    "chapter":         "chapters",
    "topic":           "topics",
    "iro":             "iros",
    "stakeholder":     "stakeholders",
    "engagement":      "engagements",
    "governance":      "governance",      # 已是「群體名稱」，不再加 -s
    "action":          "actions",
    "target":          "targets",
    "kpi":             "kpis",
    "datapoint":       "datapoints",
    "regulation":      "regulations",
    "emission_factor": "emission_factors",
    "framework":       "frameworks",
    "peer_company":    "peers",
    "source_doc":      "sourcedocs",
}


def _clean(raw_slug: str) -> str:
    """剝 leading/trailing ``/`` 與 whitespace；保留中段（``foo/bar`` 還是 ``foo/bar``）。"""
    return raw_slug.strip().strip("/")


def prefixed_slug(entity_type: str, raw_slug: str) -> str:
    """把 raw slug 補成 ``<plural>/<id>`` 形式（idempotent）。

    Rules:

    * ``entity_type`` 未知 → ``ValueError``（防護 typo）。
    * ``raw_slug`` 已是 ``<correct_prefix>/...`` → 原樣回傳（idempotent）。
    * ``raw_slug`` 已是 ``<other_prefix>/...`` → ``ValueError``（slug 與宣稱
      entity_type 矛盾，是 caller bug）。
    * 否則 → ``<prefix>/<cleaned_raw>``。
    * leading / trailing ``/`` 與 whitespace 先 strip。

    Examples:

        >>> prefixed_slug("topic", "E1")
        'topics/E1'
        >>> prefixed_slug("topic", "topics/E1")
        'topics/E1'
        >>> prefixed_slug("topic", "/E1/")
        'topics/E1'
    """
    if entity_type not in ENTITY_TYPE_PREFIX:
        raise ValueError(
            f"unknown entity_type {entity_type!r}; expected one of "
            f"{sorted(ENTITY_TYPE_PREFIX)}"
        )
    prefix = ENTITY_TYPE_PREFIX[entity_type]
    cleaned = _clean(raw_slug)
    if not cleaned:
        raise ValueError(f"raw_slug cannot be empty after stripping ('{raw_slug}')")

    if "/" in cleaned:
        head, _, _tail = cleaned.partition("/")
        if head == prefix:
            return cleaned  # already correctly prefixed → idempotent
        # 已 prefix 但 prefix 與 entity_type 不符 → caller bug，fail-loud
        # （這也覆蓋 ``slug="iros/X"`` 但 entity_type="topic" 的情境）
        # 但若 head 不在 ENTITY_TYPE_PREFIX 反向集 → 可能是合法多層 slug
        # （如 ``2024/Q4``）— 此時補 prefix 形成 ``targets/2024/Q4``。
        known_prefixes = set(ENTITY_TYPE_PREFIX.values())
        if head in known_prefixes:
            raise ValueError(
                f"slug {raw_slug!r} starts with prefix {head!r} but entity_type "
                f"is {entity_type!r} (expected prefix {prefix!r})"
            )
    return f"{prefix}/{cleaned}"


def slug_unqualified(slug: str) -> str:
    """``topics/E1`` → ``E1``（給 UI / 文案用；brain 內部不要用此函式）。

    若 slug 沒 prefix 就原樣回（idempotent）。多層 slug（``topics/sub/X``）
    剝最外層 prefix → ``sub/X``。
    """
    cleaned = _clean(slug)
    if "/" not in cleaned:
        return cleaned
    head, _, tail = cleaned.partition("/")
    if head in ENTITY_TYPE_PREFIX.values():
        return tail
    return cleaned  # head 不像 prefix，保守地原樣回


def resolve_slug(
    conn: sqlite3.Connection,
    raw_slug: str,
    *,
    entity_type: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> Optional[str]:
    """把任意 raw slug 解析成 DB 中真實存在的 prefixed slug；查不到回 None。

    解析順序：

    1. ``raw_slug`` 已含 ``/`` → 直接以 prefixed slug 查 ``pages`` 表
    2. 否則先 strip clean → 用 LIKE ``%/<cleaned>`` 找 suffix match
       * 0 match → 退而求其次以 unqualified 完全相符再查一次（legacy 寫入路徑）
       * 1 match → 回該 slug
       * ≥2 match：
           - 若提供 ``entity_type`` → 篩 entity_type 後再判斷（≤1 OK，≥2 still ambiguous）
           - 否則 raise ``AmbiguousSlugError``，要求 caller 傳完整 prefixed slug

    Args:
        raw_slug: 顧問或 caller 傳入的 slug（任一慣例）
        entity_type: 若已知，用來消歧義
        tenant_id: 同 pages 表的 tenant_id（multi-tenant 隔離）

    Returns:
        DB 中的真實 ``pages.slug``（prefixed form）或 None。

    Raises:
        AmbiguousSlugError: unqualified slug 對應多個 entity_type 的 page。
    """
    cleaned = _clean(raw_slug)
    if not cleaned:
        return None

    # ── Path A: 已是 prefixed slug → 直接查 ──────────────────────────────
    if "/" in cleaned:
        row = conn.execute(
            "SELECT slug FROM pages WHERE slug = ? AND tenant_id IS ? "
            "AND deleted_at IS NULL",
            [cleaned, tenant_id],
        ).fetchone()
        return str(row[0]) if row is not None else None

    # ── Path B: unqualified → 後綴匹配 ─────────────────────────────────
    pattern = f"%/{cleaned}"
    params: list[object] = [cleaned, pattern, tenant_id]
    sql = (
        "SELECT slug, entity_type FROM pages "
        "WHERE (slug = ? OR slug LIKE ?) AND tenant_id IS ? "
        "AND deleted_at IS NULL"
    )
    if entity_type is not None:
        sql += " AND entity_type = ?"
        params.append(entity_type)
    rows = conn.execute(sql, params).fetchall()

    if len(rows) == 0:
        return None
    if len(rows) == 1:
        return str(rows[0][0])

    # ≥2 candidates — 若全屬同一 entity_type 仍 ambiguous（同 entity 多 page）
    # 但更常見的是「topics/E1 與 iros/E1 同存」的歧義
    raise AmbiguousSlugError(
        f"slug {raw_slug!r} is ambiguous; matches {len(rows)} pages: "
        + ", ".join(f"{r[0]} ({r[1]})" for r in rows)
        + ". Pass the fully-prefixed slug (e.g. 'topics/<id>') to disambiguate."
    )


__all__ = [
    "AmbiguousSlugError",
    "ENTITY_TYPE_PREFIX",
    "prefixed_slug",
    "slug_unqualified",
    "resolve_slug",
]
