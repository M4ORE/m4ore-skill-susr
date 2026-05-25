"""susr.brain.ingest — 真實 markdown → brain 的容忍層。

R3 P0a 修補：Step 2-B walkthrough 揭露的「真實 markdown 100% ingest 失敗」
問題（見 docs/walkthroughs/lealea-5364-phase3.md §0.42 + §7 #1）。

設計動機
--------
brain 的 ``put_page`` 走 Pydantic strict-mode：

* ``ClientFrontmatter.boundary`` 是 ``Literal["合併","營運控制","股權法"]``，但
  SP1-004 試做版的 ``_client.md`` 寫的是 ``operational_control`` 英文 token；
* ``TopicFrontmatter.assessed_at`` 是 ``Optional[str]``，但 PyYAML 自動把
  ``2025-01-15`` parse 成 ``datetime.date``；
* ``StakeholderFrontmatter.influence_on_company`` 是 ``float``，但實務 markdown
  常常寫 ``高 / 中 / 低`` 字串。

put_page 之前不可能要求顧問手動把所有 markdown 改成 brain canonical form，所以
本模組做**最薄一層 normalization**：

1. ``normalize_frontmatter`` — 純函式，把已知英文 / type-coerced 值改成
   brain schema 接受的形態，idempotent 且 forward-compatible。
2. ``ingest_markdown_file`` — 切 frontmatter / body、normalize、呼叫 put_page。
3. ``ingest_directory`` — bulk ingest，依路徑推斷 entity_type，預設跳過
   ``_legacy/`` 與專案 / client 主檔。

CLAUDE.md §4.6.4：本檔 < 300 行；單一 cohesive concept（ingest tolerance）。
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from susr.brain.entities import ENTITY_SCHEMAS
from susr.brain.pages import put_page


# ---------------------------------------------------------------------------
# Literal token 對應表 — 英文 / 別稱 → brain canonical（中文）。
# 同時接受中文 identity，使 normalize 為 idempotent。
# ---------------------------------------------------------------------------

# ClientFrontmatter.boundary
_BOUNDARY_MAP: dict[str, str] = {
    "operational_control": "營運控制",
    "operational control": "營運控制",
    "financial_control": "合併",
    "financial control": "合併",
    "consolidation": "合併",
    "equity_share": "股權法",
    "equity share": "股權法",
    "equity": "股權法",
    # identity（中文輸入直通）
    "合併": "合併",
    "營運控制": "營運控制",
    "股權法": "股權法",
}

# TopicFrontmatter.axis
_AXIS_MAP: dict[str, str] = {
    "E": "E", "S": "S", "G": "G",
    "e": "E", "s": "S", "g": "G",
    "environmental": "E", "environment": "E",
    "social": "S",
    "governance": "G",
}

# TopicFrontmatter.materiality_tier
_TIER_MAP: dict[str, str] = {
    "core": "核心", "material": "重大", "boundary": "邊界",
    "Core": "核心", "Material": "重大", "Boundary": "邊界",
    "核心": "核心", "重大": "重大", "邊界": "邊界",
}

# IroFrontmatter.type / IroFrontmatter.time_horizon
_IRO_TYPE_MAP: dict[str, str] = {
    "I": "Impact", "R": "Risk", "O": "Opportunity",
    "impact": "Impact", "risk": "Risk", "opportunity": "Opportunity",
    "Impact": "Impact", "Risk": "Risk", "Opportunity": "Opportunity",
}
_TIME_HORIZON_MAP: dict[str, str] = {
    "S": "S", "M": "M", "L": "L",
    "short": "S", "medium": "M", "long": "L",
    "short_term": "S", "medium_term": "M", "long_term": "L",
    "短期": "S", "中期": "M", "長期": "L",
}

# StakeholderFrontmatter.influence_on_company / affected_by_company
# 顧問實務常用「高/中/低」字串標 Likert，brain schema 要 float ∈ [1,5]
_STAKEHOLDER_SCALE: dict[str, float] = {
    "高": 5.0, "中": 3.0, "低": 1.0,
    "high": 5.0, "medium": 3.0, "low": 1.0,
    "High": 5.0, "Medium": 3.0, "Low": 1.0,
}

# ClientFrontmatter.embedding_policy
_EMBEDDING_POLICY_MAP: dict[str, str] = {
    "twostage": "twostage", "two-stage": "twostage", "two_stage": "twostage",
    "local": "local", "cloud": "cloud",
}


# 每個 entity_type 的「Literal 欄位 → token map」
_LITERAL_FIELDS: dict[str, dict[str, dict[str, str]]] = {
    "client":      {"boundary": _BOUNDARY_MAP, "embedding_policy": _EMBEDDING_POLICY_MAP},
    "topic":       {"axis": _AXIS_MAP, "materiality_tier": _TIER_MAP},
    "iro":         {"type": _IRO_TYPE_MAP, "time_horizon": _TIME_HORIZON_MAP},
}

# 每個 entity_type 的「應為 str 但 PyYAML 可能 parse 成 date/datetime 的欄位」
_DATE_TO_STR_FIELDS: dict[str, tuple[str, ...]] = {
    "topic":       ("assessed_at",),
    "engagement":  ("date",),
    "regulation":  ("effective_from", "effective_to"),
    "emission_factor": ("effective_from",),
    "datapoint":   ("last_assessed",),
    "source_doc":  ("ingest_date",),
}

# 每個 entity_type 的「Likert 字串 → float」欄位
_LIKERT_TO_FLOAT_FIELDS: dict[str, tuple[str, ...]] = {
    "stakeholder": ("influence_on_company", "affected_by_company"),
}


# Field alias → canonical 欄名（R6 patch；R3-A「symptom out the source」精神）。
# 只 map 語意明確等價別名；模糊 alias（如 ``target_value_pct`` /
# ``baseline_value_pct``，「絕對 %」vs「reduction %」語意不同）surface 但不 map，
# 留給 Pydantic 報錯。來源：lealea-5364 fixture entities/targets/*.md diff。
_TARGET_FIELD_ALIASES: dict[str, str] = {
    "target_value_pct_reduction": "target_value",  # 真實 lealea 命中
    "target_value_pct": "target_value",             # 真實 lealea 命中（green-electricity）
    "baseline_value_pct": "baseline_value",          # 真實 lealea 命中（green-electricity）
    # forward-compat 預列（顧問另一種命名可能）
    "by_year": "target_year",
    "target_year_by": "target_year",
    "baseline_year_value": "baseline_value",
}


def _normalize_field_aliases(
    fm: dict[str, Any], aliases: dict[str, str],
) -> dict[str, Any]:
    """套用 ``alias → canonical`` 欄名映射；不 mutate 輸入。

    Rules:
        * alias 存在且 canonical 不存在 → rename。
        * alias 與 canonical 同時存在 → preserve canonical、drop alias
          （fixture 同時寫了兩個衝突欄位的 symptom，但不該 crash）。
        * 未列在 ``aliases`` 的 key 原樣保留（forward-compat）。
    """
    out = dict(fm)
    for alias, canonical in aliases.items():
        if alias not in out:
            continue
        if canonical in out:
            out.pop(alias)  # 衝突：preserve canonical
        else:
            out[canonical] = out.pop(alias)
    return out


# ---------------------------------------------------------------------------
# Public normalize API
# ---------------------------------------------------------------------------


def _date_to_str(v: Any) -> Any:
    """date / datetime → ISO 字串；其他型別原樣回傳。"""
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return v


def _coerce_int_str(v: Any) -> Any:
    """int → str（純數字 stock_code 等欄位常被 PyYAML 解成 int）。"""
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return str(v)
    return v


def normalize_frontmatter(fm: dict[str, Any], entity_type: str) -> dict[str, Any]:
    """把真實 markdown 的 frontmatter 修正成 brain canonical form。

    規則：

    * **Field alias → canonical**：例如 target entity 的 ``target_value_pct_reduction``
      → ``target_value``（lealea fixture 命名 vs ``TargetFrontmatter`` schema）。
      只 map 語意明確等價的別名；模糊 alias（如 ``target_value_pct``）surface
      但不 map，留給 Pydantic 報錯。
    * **Literal token 對應**：英文 / 別稱 token → brain schema 接受的值（多半中文）。
      未知 token 原樣保留，留給 Pydantic 報錯 — 不靜默吞掉。
    * **PyYAML auto-parsed date 還原成 str**：``assessed_at: 2025-01-15``
      被 PyYAML parse 成 ``datetime.date``，但 schema 是 ``Optional[str]``。
    * **Likert 字串 → float**：``高/中/低`` → ``5/3/1``，給 stakeholder
      influence / affected 欄位用。
    * **stock_code int → str**：``stock_code: "5364"`` 沒加引號時被 parse 成 int。
    * **未知 key 保留**：forward-compatible — 後續 schema 加欄位不會被吃掉。
    * **Idempotent**：``normalize(normalize(x)) == normalize(x)``。

    Args:
        fm: 從 YAML safe_load 出來的 frontmatter dict。
        entity_type: 對應 ``ENTITY_SCHEMAS`` 的 key（``"topic"`` / ``"client"`` …）。

    Returns:
        新 dict（不 mutate 輸入）。

    Note:
        本函式**不**呼叫 Pydantic 驗證，只做形態轉換；驗證在 put_page 內部。
    """
    out: dict[str, Any] = dict(fm)  # shallow copy；list/dict value 不深拷

    # 0. Field alias 對應（先做，因為後續 Literal/date coerce 用 canonical 欄名）
    if entity_type == "target":
        out = _normalize_field_aliases(out, _TARGET_FIELD_ALIASES)

    # 1. Literal token 對應
    for field, token_map in _LITERAL_FIELDS.get(entity_type, {}).items():
        if field in out and out[field] is not None:
            key = str(out[field]).strip()
            mapped = token_map.get(key)
            if mapped is not None:
                out[field] = mapped
            # 未命中 → 原樣保留，讓 Pydantic 報錯（symptom 出在源頭，不是這層）

    # 2. date / datetime → ISO str
    for field in _DATE_TO_STR_FIELDS.get(entity_type, ()):
        if field in out:
            out[field] = _date_to_str(out[field])

    # 3. Likert 字串 → float（stakeholder 專用）
    for field in _LIKERT_TO_FLOAT_FIELDS.get(entity_type, ()):
        if field in out:
            v = out[field]
            if isinstance(v, str):
                v_clean = v.strip()
                if v_clean in _STAKEHOLDER_SCALE:
                    out[field] = _STAKEHOLDER_SCALE[v_clean]
            # 已是 numeric 則 identity

    # 4. stock_code 純數字 int → str（client schema 要 Optional[str]）
    if entity_type == "client" and "stock_code" in out:
        out["stock_code"] = _coerce_int_str(out["stock_code"])

    return out


# ---------------------------------------------------------------------------
# Markdown parse helpers
# ---------------------------------------------------------------------------


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """切 ``---\\n<yaml>\\n---\\n<body>``；無 frontmatter 回 (空 dict, full text)。"""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    try:
        fm = yaml.safe_load(text[3:end].strip()) or {}
    except yaml.YAMLError:
        fm = {}
    if not isinstance(fm, dict):
        fm = {}
    body = text[end + 4:].lstrip("\n")
    return fm, body


def _infer_entity_type_from_path(path: Path) -> Optional[str]:
    """從 ``entities/<type>s/<slug>.md`` 路徑推斷 entity_type。

    Looks for the closest ancestor folder named ``<type>s``（如
    ``topics`` / ``stakeholders`` / ``kpis``）並轉回 brain canonical 單數型
    （``"topic"`` / ``"stakeholder"`` / ``"kpi"``）。
    """
    plural_to_singular = {
        "topics": "topic",
        "stakeholders": "stakeholder",
        "engagements": "engagement",
        "governance": "governance",  # 已是單數
        "actions": "action",
        "targets": "target",
        "kpis": "kpi",
        "datapoints": "datapoint",
        "regulations": "regulation",
        "emission_factors": "emission_factor",
        "frameworks": "framework",
        "peers": "peer_company",
        "peer_companies": "peer_company",
        "source_docs": "source_doc",
        "sourcedocs": "source_doc",
        "chapters": "chapter",
        "reports": "report",
        "iros": "iro", "iro": "iro",
    }
    for part in reversed(path.parts):
        if part in plural_to_singular:
            return plural_to_singular[part]
    return None


# ---------------------------------------------------------------------------
# Public ingest API
# ---------------------------------------------------------------------------


def ingest_markdown_file(
    conn: sqlite3.Connection,
    file_path: Path | str,
    *,
    slug: str | None = None,
    entity_type: str | None = None,
    tenant_id: str | None = None,
    project_slug: str | None = None,
    auto_link_edges: bool = True,
) -> int:
    """讀 ``.md`` 檔，切 frontmatter+body，normalize 後寫進 brain。

    推斷規則：

    * ``slug``：``frontmatter['slug']`` > 檔名 stem
    * ``entity_type``：``frontmatter['entity_type']`` > 路徑推斷
      （``entities/topics/X.md`` → ``"topic"``）

    Returns:
        ``page_id``（int）— 新插入或既有 row 的 id。

    Raises:
        ValueError: 無法解析 entity_type 或檔案無 frontmatter。
        pydantic.ValidationError: normalize 後 frontmatter 仍不符 schema
            （例如必填欄位缺、未知 Literal token 未被 map 表收錄）。
    """
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(text)
    if not fm:
        raise ValueError(
            f"{path} has no parseable YAML frontmatter; refuse to ingest "
            f"(brain pages require frontmatter for schema validation)"
        )

    # 推斷 entity_type
    et = entity_type or fm.get("entity_type") or _infer_entity_type_from_path(path)
    if et is None or et not in ENTITY_SCHEMAS:
        raise ValueError(
            f"{path}: cannot infer entity_type "
            f"(frontmatter has none and path has no recognised folder)"
        )

    # 推斷 slug
    actual_slug = slug or fm.get("slug") or path.stem

    # entity_type 不入 frontmatter（不是 schema 欄位），先剝掉
    fm_for_norm = {k: v for k, v in fm.items() if k != "entity_type"}
    fm_clean = normalize_frontmatter(fm_for_norm, et)
    fm_clean["slug"] = actual_slug  # 確保 slug 一致

    title = fm_clean.get("name") or fm_clean.get("legal_name") or actual_slug
    page_id = put_page(
        conn,
        slug=actual_slug,
        entity_type=et,
        title=str(title),
        compiled_truth=body,
        file_path=str(path),
        frontmatter=fm_clean,
        tenant_id=tenant_id,
        project_slug=project_slug,
    )

    # R8-1：依 frontmatter 宣告的關係自動建 edges（lenient — target 不存在 skip）
    if auto_link_edges:
        _auto_create_edges_for_page(
            conn, page_id, et, fm_clean, tenant_id=tenant_id,
        )

    return page_id


# 預設略過：legacy SOP 試做檔（已過時，schema 不對齊）、project / client 主檔
# （由專門 helper 處理，因為 frontmatter 不一定符合「常駐 entity」結構）。
_DEFAULT_SKIP_PARTS: frozenset[str] = frozenset({"_legacy", ".susr", ".git"})
_DEFAULT_SKIP_FILES: frozenset[str] = frozenset({"_project.md", "_client.md"})


# ---------------------------------------------------------------------------
# R8-1 — Auto-edge creation rules
# ---------------------------------------------------------------------------
# 修 R6 walkthrough §7 R8-1 揭露 — IRO ingest 進 brain 為 page 但
# topic_has_iro edge 沒建，導致 I1a invariant 9 violations.
#
# 規則格式：(entity_type, frontmatter_key) → (edge_type, target_entity_type, list)
#   - direction always "external_is_src": frontmatter[key] 指 src page，
#     本 ingested page 是 dst（呼應 EDGE_REGISTRY 內 spec 的 src/dst entity_type）
#   - list=True 表 frontmatter[key] 是 list，每個元素建一條 edge
#
# 為何不 forward direction（本 page 是 src）：實務上 frontmatter declared edge
# 通常是「我屬於誰」（child-to-parent 指 parent slug），src 必須是被指的那邊。

_AutoEdgeRule = tuple[str, str, bool]  # (edge_type, target_entity_type, is_list)
_AUTO_EDGE_RULES: dict[tuple[str, str], _AutoEdgeRule] = {
    # IRO ingest → topic_has_iro from topic (frontmatter.topic_slug) to this IRO
    ("iro",         "topic_slug"):       ("topic_has_iro",          "topic",       False),
    # Action ingest → iro_addressed_by from IRO(s) (frontmatter.iro_addressed list) to this Action
    # Note: ActionFrontmatter schema uses iro_addressed: Sequence[str]
    ("action",      "iro_addressed"):    ("iro_addressed_by",       "iro",         True),
    # DataPoint ingest → kpi_reported_as from KPI to this DataPoint
    ("datapoint",   "kpi_slug"):         ("kpi_reported_as",        "kpi",         False),
    # DataPoint ingest → datapoint_derived_from from source_doc to this DataPoint (list)
    ("datapoint",   "source_refs"):      ("datapoint_derived_from", "source_doc",  True),
    # Engagement ingest → stakeholder_engaged_via from stakeholder to this Engagement
    ("engagement",  "stakeholder_slug"): ("stakeholder_engaged_via", "stakeholder", False),
    # Engagement ingest → engagement_raised_topic per topic in topic_slugs (list)
    ("engagement",  "topic_slugs"):      ("engagement_raised_topic", "topic",      True),
    # Chapter ingest → discloses_topic for each topic in discloses_topics (list)
    ("chapter",     "discloses_topics"): ("discloses_topic",        "topic",       True),
    # Target ingest → target_measures (target → kpi); kpi_slug from frontmatter,
    # but EdgeSpec is target→kpi so this is FORWARD. Special-cased below.
    # Action ingest → action_tracks (action → target); not yet wired (Phase 5 範疇)
}

# Forward rules: ingested page is SRC, frontmatter[key] is DST slug.
_AutoEdgeForwardRule = tuple[str, str, bool]  # (edge_type, dst_entity_type, is_list)
_AUTO_EDGE_FORWARD_RULES: dict[tuple[str, str], _AutoEdgeForwardRule] = {
    # Target.kpi_slug → target_measures (target → kpi)
    ("target", "kpi_slug"): ("target_measures", "kpi", False),
}


def _resolve_page_id_for_edge(
    conn: sqlite3.Connection,
    slug: str,
    expected_entity_type: str,
    *,
    tenant_id: Optional[str] = None,
) -> Optional[int]:
    """找 slug 對應 page_id，兼容雙慣例（``X`` / ``<type>s/X`` / ``<type>/X``）。

    Returns page_id (int) or None 若找不到。R8+ R4c 議題未收斂前的兼容層。
    """
    # 嘗試多種 slug 形式（brain slug 雙慣例 — R4c backlog）
    plural = f"{expected_entity_type}s/"
    singular = f"{expected_entity_type}/"
    candidates: list[str] = [
        slug,
        plural + slug if not slug.startswith(plural) else slug,
        singular + slug if not slug.startswith(singular) else slug,
    ]
    seen: set[str] = set()
    for cand in candidates:
        if cand in seen:
            continue
        seen.add(cand)
        if tenant_id is None:
            row = conn.execute(
                "SELECT id FROM pages WHERE slug = ? AND tenant_id IS NULL "
                "AND deleted_at IS NULL",
                [cand],
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT id FROM pages WHERE slug = ? AND tenant_id = ? "
                "AND deleted_at IS NULL",
                [cand, tenant_id],
            ).fetchone()
        if row is not None:
            return int(row[0])
    return None


def _auto_create_edges_for_page(
    conn: sqlite3.Connection,
    page_id: int,
    entity_type: str,
    frontmatter: dict[str, Any],
    *,
    tenant_id: Optional[str] = None,
) -> int:
    """依 _AUTO_EDGE_RULES + _AUTO_EDGE_FORWARD_RULES 建 edges。

    Returns count of edges created (不含已存在的 — idempotent via ON CONFLICT).
    Skip silently 若 target page 不存在（lenient 容忍 — 未來補上時可重 ingest）。
    """
    created = 0

    # Reverse rules: frontmatter slug 是 src，page_id 是 dst
    for (et, key), (edge_type, src_et, is_list) in _AUTO_EDGE_RULES.items():
        if et != entity_type or key not in frontmatter:
            continue
        raw = frontmatter[key]
        if raw is None:
            continue
        target_slugs: list[str] = raw if is_list and isinstance(raw, list) else [raw]
        for t_slug in target_slugs:
            if not isinstance(t_slug, str) or not t_slug.strip():
                continue
            src_id = _resolve_page_id_for_edge(
                conn, t_slug.strip(), src_et, tenant_id=tenant_id
            )
            if src_id is None:
                continue  # target 尚未 ingest，skip 容忍
            try:
                cur = conn.execute(
                    "INSERT INTO links (src_page_id, dst_page_id, edge_type, properties) "
                    "VALUES (?, ?, ?, '{}') "
                    "ON CONFLICT(src_page_id, dst_page_id, edge_type) DO NOTHING",
                    [src_id, page_id, edge_type],
                )
                if cur.rowcount > 0:
                    created += 1
            except sqlite3.Error:
                continue  # invariant validate 等錯誤一律 swallow（lenient）

    # Forward rules: page_id 是 src，frontmatter slug 是 dst
    for (et, key), (edge_type, dst_et, is_list) in _AUTO_EDGE_FORWARD_RULES.items():
        if et != entity_type or key not in frontmatter:
            continue
        raw = frontmatter[key]
        if raw is None:
            continue
        target_slugs = raw if is_list and isinstance(raw, list) else [raw]
        for t_slug in target_slugs:
            if not isinstance(t_slug, str) or not t_slug.strip():
                continue
            dst_id = _resolve_page_id_for_edge(
                conn, t_slug.strip(), dst_et, tenant_id=tenant_id
            )
            if dst_id is None:
                continue
            try:
                cur = conn.execute(
                    "INSERT INTO links (src_page_id, dst_page_id, edge_type, properties) "
                    "VALUES (?, ?, ?, '{}') "
                    "ON CONFLICT(src_page_id, dst_page_id, edge_type) DO NOTHING",
                    [page_id, dst_id, edge_type],
                )
                if cur.rowcount > 0:
                    created += 1
            except sqlite3.Error:
                continue
    return created


def ingest_directory(
    conn: sqlite3.Connection,
    root: Path | str,
    *,
    glob: str = "**/*.md",
    tenant_id: str | None = None,
    include_legacy: bool = False,
    include_project_and_client: bool = False,
    strict: bool = False,
) -> dict[str, int]:
    """Bulk ingest ``root`` 底下所有 ``.md`` 檔；回傳 ``{file_path: page_id}``。

    預設 skip 規則（``CLAUDE.md`` decision「Option C 結構」對齊）：

    * ``_legacy/``：SP1-004 試做檔，schema 與 brain canonical 不對齊
    * ``_project.md`` / ``_client.md``：主檔有特殊 fields（如 ``year`` /
      ``group_parent``）不符合單純 entity ingest
    * ``.susr/`` / ``.git/``：基礎設施目錄

    Args:
        include_legacy: 若 True，連 ``_legacy/`` 內檔一起 ingest。
        include_project_and_client: 若 True，連 ``_project.md`` / ``_client.md``
            一起 ingest（顧問已手動 normalize 過時用）。
        strict: 若 True，任一檔 ingest 失敗時 raise；若 False（預設），
            個別檔失敗只是不出現在 ``results`` 裡，繼續處理其他檔。
            這對應「容忍層」精神 — 真實 markdown 多半有 1-2 個極端不完整檔
            （如 ``target_value_pct_reduction`` 命名 vs schema 要 ``target_value``），
            不該讓整個 bulk ingest 中斷。

    Returns:
        ``{absolute_file_path_str: page_id}``。``strict=False`` 時不含失敗檔。

    Note:
        若需要看哪些檔失敗，用 ``strict=True``；或在 caller 端對比
        ``glob`` 與 ``results`` 的差集。
    """
    root_path = Path(root).resolve()
    results: dict[str, int] = {}
    skip_parts = set() if include_legacy else set(_DEFAULT_SKIP_PARTS) | {"_legacy"}
    if include_legacy:
        skip_parts.discard("_legacy")
    skip_parts = skip_parts | {".susr", ".git"}
    skip_files = set() if include_project_and_client else set(_DEFAULT_SKIP_FILES)

    # R8-1：兩階段 ingest — pass 1 全 put_page（auto_link_edges=False），pass 2
    # 統一補 edges。理由：file glob alphabetical 順序可能讓 iros/ 在 topics/ 前
    # 處理，IRO ingest 時 topic 尚未進 brain，edge 建不起來。
    ingested: list[tuple[str, int, str, dict[str, Any]]] = []
    for md_path in sorted(root_path.glob(glob)):
        if not md_path.is_file():
            continue
        rel_parts = md_path.relative_to(root_path).parts
        if any(part in skip_parts for part in rel_parts):
            continue
        if md_path.name in skip_files:
            continue
        # Pass 1: put_page only（不建 edges，避免目標 page 還沒 ingest）
        try:
            # Re-parse here so we can keep frontmatter for pass 2
            text = md_path.read_text(encoding="utf-8")
            fm, body = _split_frontmatter(text)
            if not fm:
                if strict:
                    raise ValueError(f"{md_path} has no frontmatter")
                continue
            et = fm.get("entity_type") or _infer_entity_type_from_path(md_path)
            if et is None or et not in ENTITY_SCHEMAS:
                if strict:
                    raise ValueError(f"{md_path} cannot infer entity_type")
                continue
            page_id = ingest_markdown_file(
                conn, md_path, tenant_id=tenant_id, auto_link_edges=False,
            )
            # Re-read normalized fm for pass 2 (avoid re-normalize)
            fm_for_norm = {k: v for k, v in fm.items() if k != "entity_type"}
            fm_clean = normalize_frontmatter(fm_for_norm, et)
            ingested.append((str(md_path), page_id, et, fm_clean))
            results[str(md_path)] = page_id
        except Exception:
            if strict:
                raise
            continue

    # Pass 2: 補建所有 ingested pages 的 edges（此時所有 target pages 已存在）
    for _path, page_id, et, fm_clean in ingested:
        try:
            _auto_create_edges_for_page(
                conn, page_id, et, fm_clean, tenant_id=tenant_id,
            )
        except Exception:
            if strict:
                raise
            continue

    return results


__all__ = [
    "normalize_frontmatter",
    "ingest_markdown_file",
    "ingest_directory",
]
