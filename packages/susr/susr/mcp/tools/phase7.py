"""susr.mcp.tools.phase7 — Phase 7 Gap Analysis & Assurance Readiness tools.

TL;DR（顧問速讀）：
    Phase 7 = 顧問把 Phase 1-6 跑完的 client brain 拿來做「揭露品質體檢」。本模組
    提供 4 個 MCP tool：

    1. ``run_compliance_checklist``         — 跑 60+ 項框架合規 checklist
    2. ``generate_gri_content_index``       — 產 GRI Content Index 表
    3. ``generate_assurance_readiness_checklist`` — KPI / DataPoint 確信前置檢查
    4. ``run_full_gap_analysis``            — 整合 invariants + 上述 3 個 → 一份 md

TOC:
    - Helpers (load/parse checklist; brain lookups)
    - Pydantic result models
    - Tool 1: run_compliance_checklist
    - Tool 2: generate_gri_content_index
    - Tool 3: generate_assurance_readiness_checklist
    - Tool 4: run_full_gap_analysis (aggregator)
    - register()

設計選項：
    - parsing checklist 用 simple regex（``- [ ]`` / ``- [x]`` / 編號項目），
      不做 markdown AST。對非標準格式寬鬆失敗（skip 不抓不出來的項）。
    - checklist 來源優先順序：
        (a) ``packages/susr/susr/shared_kb/data/checklists/compliance-phase7.md``
            （Step 3 已搬過去 — 顧問常駐 KB）
        (b) ``skills/sustainability-report/references/compliance-checklist.md``
            （legacy fallback — Step 3 之前的位置）
    - fulfillment 判斷對應到 brain：
        * 「GRI 2-1 組織概況」→ 找 entity_type='chapter' 且 framework_refs 含 'GRI 2-1'
        * 「範疇一排放量」     → 找 entity_type='kpi' slug 含 'scope1' / 'ghg-scope1'
        * 「重大性矩陣」      → 找 chapter 含 'materiality' 或 topic 有評分
      對抓不到的項回 ``unverifiable``（讓顧問自己最後核對）。
    - GRI Content Index 用內建 ``_GRI_DISCLOSURES``（Universal 2021 + 305 系列子集）—
      非完整 GRI 但覆蓋金管會強制 + Phase 7 walkthrough 表列項。
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel

from susr.workspace import find_client_workspace

# ---------------------------------------------------------------------------
# Constants & embedded reference data
# ---------------------------------------------------------------------------

# 解析 checklist - matches:  - [ ] X1 ...  /  - [x] X1 ...
_CHECKLIST_ITEM_RE = re.compile(r"^\s*-\s*\[(?P<chk>[ xX])\]\s*(?P<body>.+?)\s*$")
_SECTION_RE = re.compile(r"^##\s+(?P<title>[A-Z])\.\s*(?P<name>[^—\-]+)")
_ITEM_CODE_RE = re.compile(r"^([A-Z]\d+)\s+(.*)$")

ItemStatus = Literal["passed", "failed", "unverifiable"]
Severity = Literal["critical", "warning", "info"]

# GRI Universal 2021 + 環境主題（305 系列）— 用於 generate_gri_content_index。
# Tuple structure: (disclosure_code, zh_label, framework_ref_token, kpi_slug_hint)
# kpi_slug_hint = 若這項對應到 KPI（量化），給 substring 用來在 entity_attributes
# 內搜尋；None 代表這項是敘事章節（找 chapter / framework_refs）。
_GRI_DISCLOSURES: tuple[tuple[str, str, str, Optional[str]], ...] = (
    # GRI 2 — Universal 2021 General Disclosures
    ("2-1", "組織與其報告實務 / 組織概況", "GRI 2-1", None),
    ("2-2", "報告組織邊界", "GRI 2-2", None),
    ("2-3", "報告期間 / 頻率 / 聯絡窗口", "GRI 2-3", None),
    ("2-4", "資訊重述", "GRI 2-4", None),
    ("2-5", "外部確信", "GRI 2-5", None),
    ("2-9", "治理結構與組成", "GRI 2-9", None),
    ("2-12", "董事會永續監督", "GRI 2-12", None),
    ("2-22", "永續發展策略聲明", "GRI 2-22", None),
    ("2-23", "政策承諾", "GRI 2-23", None),
    ("2-26", "道德管道", "GRI 2-26", None),
    ("2-29", "利害關係人議合方法", "GRI 2-29", None),
    # GRI 3 — Material Topics 2021
    ("3-1", "重大議題的決定程序", "GRI 3-1", None),
    ("3-2", "重大議題清單", "GRI 3-2", None),
    ("3-3", "重大議題管理方針", "GRI 3-3", None),
    # GRI 305 — Emissions 2016 (Climate core)
    ("305-1", "直接溫室氣體排放（範疇一）", "GRI 305-1", "scope1"),
    ("305-2", "間接溫室氣體排放（範疇二）", "GRI 305-2", "scope2"),
    ("305-3", "其他間接溫室氣體排放（範疇三）", "GRI 305-3", "scope3"),
    ("305-4", "溫室氣體排放強度", "GRI 305-4", "intensity"),
    ("305-5", "溫室氣體排放減量", "GRI 305-5", None),
)


# ---------------------------------------------------------------------------
# Pydantic result models
# ---------------------------------------------------------------------------


class ChecklistItem(BaseModel):
    """一條 compliance checklist 項目 + brain 查詢後的狀態。"""

    code: str  # 例如 'A1' / 'D2' / 'F5'
    section: str  # 例如 '治理' / '指標與目標'
    text: str  # 完整描述
    status: ItemStatus
    evidence_refs: list[str] = []  # brain page slugs / file paths 作證
    suggestion: str = ""  # 對 failed / unverifiable 給後續動作建議


class ComplianceChecklistResult(BaseModel):
    """``run_compliance_checklist`` 回傳結構。"""

    framework: str
    total: int
    passed: int
    failed: int
    unverifiable: int
    items: list[ChecklistItem]  # detail（若 limit 切過則為前 N 項）
    truncated: bool = False
    source_path: str


class GriDisclosureRow(BaseModel):
    """GRI Content Index 一列。"""

    disclosure: str  # 例如 '2-1'
    zh_label: str
    framework_ref: str  # 例如 'GRI 2-1'
    status: Literal["fulfilled", "partial", "missing"]
    page_ref: str  # chapter slug / KPI slug / '--'
    notes: str = ""


class GriContentIndexResult(BaseModel):
    """``generate_gri_content_index`` 回傳結構。"""

    file_path: str
    total_disclosures: int
    fulfilled: int
    partial: int
    missing: int
    rows: list[GriDisclosureRow]


class AssuranceItem(BaseModel):
    """確信前置 checklist 一筆 KPI / DataPoint。"""

    page_slug: str
    entity_type: str  # 'kpi' / 'datapoint'
    missing_fields: list[str]  # 例如 ['source_refs', 'responsible_person']
    severity: Severity


class AssuranceReadinessResult(BaseModel):
    """``generate_assurance_readiness_checklist`` 回傳結構。"""

    file_path: str
    total_pages: int
    ready: int  # 0 fields missing
    needs_work: int  # 1+ fields missing
    items: list[AssuranceItem]


class FullGapAnalysisResult(BaseModel):
    """``run_full_gap_analysis`` 回傳結構。"""

    file_path: str
    severity_breakdown: dict[str, int]  # critical / warning / info
    invariant_violations: int
    compliance_failed: int
    compliance_unverifiable: int
    gri_missing: int
    assurance_needs_work: int
    summary: str  # TL;DR 5 行內


# ---------------------------------------------------------------------------
# Helpers — checklist load & parse
# ---------------------------------------------------------------------------


def _resolve_checklist_path(framework: str) -> Path:
    """Try (a) shared_kb path first, (b) skills/references/ fallback.

    framework 目前只支援 'phase7'（compliance-phase7.md）；未來可加 'gri-2021'
    / 'issb' / 'fsc' 等獨立 checklist。
    """
    # (a) shared_kb（Step 3 已搬）
    pkg_root = Path(__file__).resolve().parents[2]  # packages/susr/susr/
    shared_path = pkg_root / "shared_kb" / "data" / "checklists" / f"compliance-{framework}.md"
    if shared_path.exists():
        return shared_path

    # (b) legacy references fallback
    # PACKAGE_ROOT/../../skills/sustainability-report/references/
    repo_root = pkg_root.parent.parent  # mono-repo root
    legacy_path = (
        repo_root / "skills" / "sustainability-report" / "references"
        / "compliance-checklist.md"
    )
    if legacy_path.exists():
        return legacy_path

    raise FileNotFoundError(
        f"compliance checklist not found in shared_kb or skills references "
        f"(searched: {shared_path}, {legacy_path})"
    )


def _parse_checklist(path: Path) -> list[tuple[str, str, str, bool]]:
    """Parse markdown checklist → list of (code, section_name, text, is_checked).

    section_name = ``## X. 治理...`` 的中文名稱（去掉編號與項數註）。
    code         = 行首的 ``A1`` / ``D2`` 字首；無 code 的項以行內前 8 字當 code。
    is_checked   = ``- [x]`` 為 True / ``- [ ]`` 為 False。
    """
    text = path.read_text(encoding="utf-8")
    items: list[tuple[str, str, str, bool]] = []
    current_section = "未分類"
    for raw_line in text.splitlines():
        sec_m = _SECTION_RE.match(raw_line)
        if sec_m:
            # 取 "## A. 治理（Governance）— 8 項" 的中文名（去掉項數註）
            name = sec_m.group("name").strip()
            current_section = re.split(r"[（(]", name)[0].strip() or current_section
            continue
        m = _CHECKLIST_ITEM_RE.match(raw_line)
        if not m:
            continue
        is_checked = m.group("chk").lower() == "x"
        body = m.group("body").strip()
        code_m = _ITEM_CODE_RE.match(body)
        if code_m:
            code = code_m.group(1)
            rest = code_m.group(2).strip()
        else:
            code = body[:8].replace(" ", "_") or "item"
            rest = body
        items.append((code, current_section, rest, is_checked))
    return items


# ---------------------------------------------------------------------------
# Helpers — brain lookups for fulfilment checks
# ---------------------------------------------------------------------------


def _has_entity_with_attr(
    conn: sqlite3.Connection,
    *,
    entity_type: str,
    attr_key: str,
    value_substr: str,
) -> list[str]:
    """Return slugs of pages whose entity_attributes (key, value) contains ``value_substr``."""
    rows = conn.execute(
        """
        SELECT DISTINCT p.slug FROM pages p
        JOIN entity_attributes a ON a.page_id = p.id
        WHERE p.entity_type = ?
          AND p.deleted_at IS NULL
          AND a.key = ?
          AND a.value LIKE ?
        ORDER BY p.slug LIMIT 5
        """,
        [entity_type, attr_key, f"%{value_substr}%"],
    ).fetchall()
    return [str(r[0]) for r in rows]


def _has_entity_with_slug_substr(
    conn: sqlite3.Connection, *, entity_type: str, slug_substr: str
) -> list[str]:
    rows = conn.execute(
        """
        SELECT slug FROM pages
        WHERE entity_type = ? AND deleted_at IS NULL AND slug LIKE ?
        ORDER BY slug LIMIT 5
        """,
        [entity_type, f"%{slug_substr}%"],
    ).fetchall()
    return [str(r[0]) for r in rows]


# Mapping checklist code → (matcher_fn(conn) → list[slug], suggestion text)
# 對於沒列入 mapping 的 code → unverifiable（顧問需自行核對）。
def _check_item_fulfilled(
    conn: sqlite3.Connection, code: str, text: str
) -> tuple[ItemStatus, list[str], str]:
    """對 code/text 對應到 brain 查詢，回 (status, evidence_refs, suggestion)。

    啟發式覆蓋率 ~50% — 顯然在 brain 內可查到的（KPI / chapter / topic 評分等）
    都嘗試，剩下偏程序性 / 敘事的（如「吹哨者管道」）回 unverifiable。
    """
    text_lower = text.lower()

    # F-section: GRI 2-x 對應到 chapter framework_refs
    if code.startswith("F"):
        # 嘗試從 text 抓 'GRI 2-X' token
        gri_m = re.search(r"GRI\s*(\d+-?\d*)", text)
        if gri_m:
            token = f"GRI {gri_m.group(1)}"
            slugs = _has_entity_with_attr(
                conn, entity_type="chapter", attr_key="framework_refs",
                value_substr=token,
            )
            if slugs:
                return "passed", slugs, ""
            return "failed", [], (
                f"未找到 chapter 的 framework_refs 含 {token!r}；"
                f"Phase 5/6 章節須在 frontmatter 標 framework_refs。"
            )

    # D1: 範疇一、範疇二排放量 → 找 KPI slug 含 scope1 / scope2
    if code == "D1" or "範疇一" in text or "scope 1" in text_lower:
        s1 = _has_entity_with_slug_substr(conn, entity_type="kpi", slug_substr="scope1")
        s2 = _has_entity_with_slug_substr(conn, entity_type="kpi", slug_substr="scope2")
        if s1 and s2:
            return "passed", [*s1, *s2][:5], ""
        if s1 or s2:
            return "failed", [*s1, *s2], (
                "找到部分 scope 排放 KPI，但範疇一 + 範疇二應同時揭露。"
            )
        return "failed", [], "未找到 scope1 / scope2 KPI；Phase 4 應建立。"

    # D2: 範疇三主要類別 → 找 scope3 KPI
    if code == "D2" or "範疇三" in text:
        s3 = _has_entity_with_slug_substr(conn, entity_type="kpi", slug_substr="scope3")
        if len(s3) >= 5:
            return "passed", s3, ""
        if s3:
            return "failed", s3, (
                "找到 Scope 3 KPI 但不足 5 類；金管會建議至少揭露 5 主要類別。"
            )
        return "failed", [], "未找到 scope3 KPI；Phase 4 必補。"

    # D5: 每個目標含基線年、目標年、達成時程 → I3 invariant view
    if code == "D5":
        rows = conn.execute(
            "SELECT slug FROM v_target_completeness "
            "WHERE has_baseline_year=1 AND has_baseline_value=1 "
            "AND has_target_year=1 AND has_verification_path=1 LIMIT 5"
        ).fetchall()
        if rows:
            return "passed", [str(r[0]) for r in rows], ""
        return "failed", [], "無 target 同時具備 baseline_year/value + target_year + verification_path。"

    # E-section: 重大性 → 找有 impact_score 的 topic
    if code.startswith("E") and code not in ("E1c",):
        if "矩陣" in text or "清單" in text or "雙重重大性" in text:
            rows = conn.execute(
                "SELECT p.slug FROM pages p "
                "JOIN entity_attributes a ON a.page_id = p.id "
                "WHERE p.entity_type='topic' AND a.key='materiality_tier' "
                "AND a.value LIKE '%核心%' AND p.deleted_at IS NULL LIMIT 5"
            ).fetchall()
            if rows:
                return "passed", [str(r[0]) for r in rows], ""
            return "failed", [], "未找到 materiality_tier='核心' 的 topic；Phase 3 應產出。"

    # A-section: 治理 → 找 governance entity 或 chapter 含 'governance'
    if code.startswith("A"):
        govs = _has_entity_with_slug_substr(
            conn, entity_type="governance", slug_substr=""
        )
        if govs:
            return "passed", govs, ""
        # 不一定能在 brain 直接查到 — 例如 A4「薪酬與 ESG 連結」常在敘事章節
        return "unverifiable", [], "治理敘事項目，請顧問人工核對章節敘述。"

    # I-section: 數據品質 → 對應 I3 / I4 invariant
    if code == "I2":  # 每個 KPI 標單位、公式、來源
        rows = conn.execute(
            "SELECT p.slug FROM pages p WHERE p.entity_type='kpi' AND p.deleted_at IS NULL "
            "AND EXISTS (SELECT 1 FROM entity_attributes a "
            "WHERE a.page_id=p.id AND a.key='formula' AND a.value != '') LIMIT 5"
        ).fetchall()
        if rows:
            return "passed", [str(r[0]) for r in rows], ""
        return "failed", [], "KPI 未填 formula；Phase 4 frontmatter 必補。"

    # Default — unverifiable，避免亂報 false negative
    return "unverifiable", [], (
        f"自動化未涵蓋此項（{code}）；請顧問依 brain 敘事章節人工核對。"
    )


# ---------------------------------------------------------------------------
# Tool 1: run_compliance_checklist
# ---------------------------------------------------------------------------


def run_compliance_checklist(
    client_slug: str,
    framework: str = "phase7",
    project_slug: Optional[str] = None,  # noqa: ARG001 — reserved；本 tool 跑全 brain
    *,
    detail_limit: int = 30,
) -> ComplianceChecklistResult:
    """跑 framework checklist 對 brain 做 fulfilment check（Phase 7 主入口之一）。

    Args:
        client_slug: per-client workspace 目錄名。
        framework: 'phase7'（預設 — GRI/ISSB/金管會合併版）。未來可加 'gri-2021'
            / 'issb' / 'fsc-twse' 等獨立 checklist。
        project_slug: 預留 — 未來若要 scope 到單年 project 用；目前 ignored。
        detail_limit: 回傳 ``items`` 的最大筆數（保護 MCP payload size）；
            ``truncated=True`` 時顧問可分批跑。

    Returns:
        ``ComplianceChecklistResult`` — summary + 前 N 項 detail。
    """
    checklist_path = _resolve_checklist_path(framework)
    parsed = _parse_checklist(checklist_path)
    if not parsed:
        return ComplianceChecklistResult(
            framework=framework, total=0, passed=0, failed=0, unverifiable=0,
            items=[], truncated=False, source_path=str(checklist_path),
        )

    client_path = find_client_workspace(client_slug)
    from susr.brain.engine import BrainEngine
    engine = BrainEngine.open(
        str(client_path / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    try:
        items: list[ChecklistItem] = []
        n_pass = n_fail = n_unverif = 0
        for code, section, text, _checked in parsed:
            status, evidence, suggestion = _check_item_fulfilled(engine.conn, code, text)
            items.append(ChecklistItem(
                code=code, section=section, text=text, status=status,
                evidence_refs=evidence, suggestion=suggestion,
            ))
            if status == "passed":
                n_pass += 1
            elif status == "failed":
                n_fail += 1
            else:
                n_unverif += 1
    finally:
        engine.close()

    truncated = len(items) > detail_limit
    return ComplianceChecklistResult(
        framework=framework, total=len(parsed),
        passed=n_pass, failed=n_fail, unverifiable=n_unverif,
        items=items[:detail_limit], truncated=truncated,
        source_path=str(checklist_path),
    )


# ---------------------------------------------------------------------------
# Tool 2: generate_gri_content_index
# ---------------------------------------------------------------------------


def _check_gri_disclosure(
    conn: sqlite3.Connection, disclosure: str, framework_ref: str,
    kpi_slug_hint: Optional[str],
) -> tuple[str, str, str]:
    """Return (status, page_ref, notes) for one GRI disclosure.

    Status:
        'fulfilled' — chapter 含 framework_ref 且（如有 kpi_hint）對應 KPI 存在
        'partial'   — chapter 含 framework_ref 但量化 KPI 缺
        'missing'   — 完全沒對應
    """
    # 查 chapter 的 framework_refs
    chapter_slugs = _has_entity_with_attr(
        conn, entity_type="chapter", attr_key="framework_refs",
        value_substr=framework_ref,
    )

    if kpi_slug_hint is not None:
        # 量化揭露：需同時有 chapter + KPI
        kpi_slugs = _has_entity_with_slug_substr(
            conn, entity_type="kpi", slug_substr=kpi_slug_hint,
        )
        if chapter_slugs and kpi_slugs:
            return "fulfilled", chapter_slugs[0], f"KPI: {kpi_slugs[0]}"
        if kpi_slugs and not chapter_slugs:
            return "partial", kpi_slugs[0], "KPI 已建立但章節未標 framework_ref"
        if chapter_slugs and not kpi_slugs:
            return "partial", chapter_slugs[0], f"章節有但缺 {kpi_slug_hint!r} KPI"
        return "missing", "--", "缺 chapter 與 KPI"

    # 敘事揭露：只看 chapter framework_refs
    if chapter_slugs:
        return "fulfilled", chapter_slugs[0], ""
    return "missing", "--", "未找到含此 framework_ref 的 chapter"


def generate_gri_content_index(
    client_slug: str, year: int, project_slug: Optional[str] = None,
) -> GriContentIndexResult:
    """產 GRI Content Index markdown 並寫到 ``projects/<project_slug>/``。

    Args:
        client_slug: per-client workspace 目錄名。
        year: 報告年度（用於檔名與 metadata）。
        project_slug: 預設 ``<year>-sr``。

    Returns:
        ``GriContentIndexResult`` — file_path + 統計 + rows detail。
    """
    if not project_slug:
        project_slug = f"{year}-sr"
    client_path = find_client_workspace(client_slug)

    from susr.brain.engine import BrainEngine
    engine = BrainEngine.open(
        str(client_path / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    rows: list[GriDisclosureRow] = []
    try:
        for disclosure, zh_label, fw_ref, kpi_hint in _GRI_DISCLOSURES:
            status, page_ref, notes = _check_gri_disclosure(
                engine.conn, disclosure, fw_ref, kpi_hint,
            )
            rows.append(GriDisclosureRow(
                disclosure=disclosure, zh_label=zh_label,
                framework_ref=fw_ref, status=status,  # type: ignore[arg-type]
                page_ref=page_ref, notes=notes,
            ))
    finally:
        engine.close()

    n_fulfilled = sum(1 for r in rows if r.status == "fulfilled")
    n_partial = sum(1 for r in rows if r.status == "partial")
    n_missing = sum(1 for r in rows if r.status == "missing")

    # 寫 markdown
    out_path = client_path / "projects" / project_slug / f"gri-content-index-{year}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        f"# GRI Content Index — {year}",
        "",
        f"- 產出時間：{datetime.now().isoformat(timespec='seconds')}",
        f"- 涵蓋揭露：{len(rows)} 項（GRI Universal 2021 + 305 系列子集）",
        f"- 已揭露：{n_fulfilled} / 部分：{n_partial} / 未揭露：{n_missing}",
        "",
        "| GRI Disclosure | 主題 | Page Ref | Status | Notes |",
        "|---|---|---|---|---|",
    ]
    _status_symbol = {"fulfilled": "✓", "partial": "△", "missing": "✗"}
    for r in rows:
        sym = _status_symbol[r.status]
        lines.append(
            f"| {r.framework_ref} | {r.zh_label} | `{r.page_ref}` | "
            f"{sym} {r.status} | {r.notes} |"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return GriContentIndexResult(
        file_path=str(out_path),
        total_disclosures=len(rows),
        fulfilled=n_fulfilled, partial=n_partial, missing=n_missing,
        rows=rows,
    )


# ---------------------------------------------------------------------------
# Tool 3: generate_assurance_readiness_checklist
# ---------------------------------------------------------------------------


# 對 KPI / DataPoint 確信前置：每個 entity 應具備這些 frontmatter key
_ASSURANCE_FIELDS = {
    "kpi": ["formula", "unit", "boundary", "topic_slug", "framework_refs"],
    "datapoint": [
        "source_refs", "calculation_method", "responsible_person",
        "assurance_status", "last_assessed",
    ],
}


def generate_assurance_readiness_checklist(
    client_slug: str, year: int, project_slug: Optional[str] = None,
) -> AssuranceReadinessResult:
    """對 brain 內 KPI / DataPoint 跑確信前置 checklist。

    每個 entity 檢查 _ASSURANCE_FIELDS 列出的 frontmatter key 是否齊全；
    缺漏者列入 ``items``。對 datapoint 缺 ``source_refs`` 為 critical（I4 也會抓），
    缺其他欄位為 warning。

    Args:
        client_slug: per-client workspace 目錄名。
        year: 報告年度（用於檔名）。
        project_slug: 預設 ``<year>-sr``。

    Returns:
        ``AssuranceReadinessResult`` — file_path + 統計 + items detail。
    """
    if not project_slug:
        project_slug = f"{year}-sr"
    client_path = find_client_workspace(client_slug)

    from susr.brain.engine import BrainEngine
    engine = BrainEngine.open(
        str(client_path / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    items: list[AssuranceItem] = []
    try:
        for entity_type, required_fields in _ASSURANCE_FIELDS.items():
            rows = engine.conn.execute(
                "SELECT id, slug FROM pages "
                "WHERE entity_type = ? AND deleted_at IS NULL ORDER BY slug",
                [entity_type],
            ).fetchall()
            for page_id, slug in rows:
                attrs = engine.conn.execute(
                    "SELECT key, value FROM entity_attributes WHERE page_id = ?",
                    [page_id],
                ).fetchall()
                present = {str(k): str(v or "") for k, v in attrs}
                missing = [
                    f for f in required_fields
                    if not present.get(f) or present[f] in ("[]", "{}", "")
                ]
                if missing:
                    severity: Severity
                    if entity_type == "datapoint" and "source_refs" in missing:
                        severity = "critical"
                    elif entity_type == "datapoint":
                        severity = "warning"
                    else:
                        severity = "info"
                    items.append(AssuranceItem(
                        page_slug=str(slug), entity_type=entity_type,
                        missing_fields=missing, severity=severity,
                    ))
    finally:
        engine.close()

    # 寫 markdown
    out_path = (
        client_path / "projects" / project_slug / f"assurance-readiness-{year}.md"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        f"# Assurance Readiness Checklist — {year}",
        "",
        f"- 產出時間：{datetime.now().isoformat(timespec='seconds')}",
        f"- 檢查 entity：KPI + DataPoint",
        f"- 需補件項目：{len(items)} 條",
        "",
    ]
    if not items:
        lines.append("> 所有 KPI / DataPoint 必填欄位齊全 — 可進入第三方確信前置會議。")
    else:
        lines += [
            "| Slug | Type | Missing | Severity |",
            "|---|---|---|---|",
        ]
        _sev_sym = {"critical": "🔴", "warning": "🟠", "info": "🟡"}
        for it in items:
            lines.append(
                f"| `{it.page_slug}` | {it.entity_type} | "
                f"{', '.join(it.missing_fields)} | "
                f"{_sev_sym[it.severity]} {it.severity} |"
            )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ready = 未在 items 出現的 page 數（這裡只算 items 統計，未列入即視為 ready）
    return AssuranceReadinessResult(
        file_path=str(out_path),
        total_pages=len(items),  # items 是「需補件」的 count
        ready=0,  # 簡化：不單獨計 ready 數 — 顧問看 items 反向就知道
        needs_work=len(items),
        items=items,
    )


# ---------------------------------------------------------------------------
# Tool 4: run_full_gap_analysis (aggregator)
# ---------------------------------------------------------------------------


def _summarize_invariants(violations: list) -> dict[str, list[str]]:
    """Group invariants by ``invariant_name`` for the gap analysis md."""
    by_name: dict[str, list[str]] = {}
    for v in violations:
        key = getattr(v, "invariant_name", v.invariant)
        by_name.setdefault(key, []).append(v.page_slug)
    return by_name


def run_full_gap_analysis(
    client_slug: str, year: int, project_slug: Optional[str] = None,
) -> FullGapAnalysisResult:
    """Phase 7 主 aggregator — 整合 invariants + compliance + GRI + assurance。

    寫 ``projects/<project_slug>/gap-analysis-<year>.md``，結構：
        0. TL;DR
        1. 連結性 Invariants（I1a/I1b/I2/I3/I4/I5）
        2. Framework Compliance（passed/failed/unverifiable + top failed）
        3. GRI Content Index summary
        4. Assurance Readiness summary
        5. 優先修補建議（依嚴重度排序）

    Args:
        client_slug: per-client workspace 目錄名。
        year: 報告年度。
        project_slug: 預設 ``<year>-sr``。

    Returns:
        ``FullGapAnalysisResult`` — file_path + severity_breakdown + 短 summary。
    """
    if not project_slug:
        project_slug = f"{year}-sr"
    client_path = find_client_workspace(client_slug)

    # 1. invariants
    from susr.brain.engine import BrainEngine
    from susr.brain.invariants import check_all_invariants

    engine = BrainEngine.open(
        str(client_path / ".susr" / "db.sqlite"), load_sqlite_vec=False,
    )
    try:
        violations = check_all_invariants(engine.conn)
    finally:
        engine.close()
    by_inv = _summarize_invariants(violations)

    # 2. compliance + 3. GRI + 4. assurance（各自開 engine — KISS，量小無妨）
    compliance = run_compliance_checklist(client_slug, framework="phase7")
    gri = generate_gri_content_index(client_slug, year, project_slug=project_slug)
    assurance = generate_assurance_readiness_checklist(
        client_slug, year, project_slug=project_slug,
    )

    # severity breakdown
    critical = (
        len([v for v in violations if getattr(v, "invariant_name", v.invariant)
             in ("I1a", "I1b", "I4")])  # IRO/Action/source 缺 = 紅
        + sum(1 for it in assurance.items if it.severity == "critical")
        + gri.missing
    )
    warning = (
        len([v for v in violations if getattr(v, "invariant_name", v.invariant)
             in ("I2", "I3", "I5")])
        + sum(1 for it in assurance.items if it.severity == "warning")
        + gri.partial
        + compliance.failed
    )
    info = (
        sum(1 for it in assurance.items if it.severity == "info")
        + compliance.unverifiable
    )

    # 寫 markdown
    out_path = client_path / "projects" / project_slug / f"gap-analysis-{year}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tl_dr = (
        f"報告期間：{year}。本 gap analysis 跑出："
        f"🔴 {critical} critical / 🟠 {warning} warning / 🟡 {info} info。"
        f" Invariants 違反 {len(violations)} 條"
        f"（I1a={len(by_inv.get('I1a', []))} I1b={len(by_inv.get('I1b', []))}"
        f" I2={len(by_inv.get('I2', []))} I3={len(by_inv.get('I3', []))}"
        f" I4={len(by_inv.get('I4', []))} I5={len(by_inv.get('I5', []))}）；"
        f" GRI Index 缺 {gri.missing}/{gri.total_disclosures}；"
        f" 確信前置缺件 {assurance.needs_work} 筆；"
        f" Compliance 未通過 {compliance.failed}/{compliance.total}。"
    )

    lines: list[str] = [
        f"# Gap Analysis — {year}",
        "",
        f"- 產出時間：{datetime.now().isoformat(timespec='seconds')}",
        "",
        "## 0. TL;DR",
        "",
        tl_dr,
        "",
        "## 1. 連結性 Invariants",
        "",
    ]
    for inv_name in ("I1a", "I1b", "I2", "I3", "I4", "I5"):
        slugs = by_inv.get(inv_name, [])
        title_map = {
            "I1a": "核心 topic 必有 IRO（Phase 3）",
            "I1b": "IRO 必有 Action（Phase 5）",
            "I2": "Chapter 必有 framework + topic edge",
            "I3": "Target 4 項必填欄位",
            "I4": "Datapoint 必有 source_doc",
            "I5": "Emission factor 時效窗",
        }
        n = len(slugs)
        status = "✅ pass" if n == 0 else f"❌ {n} 違反"
        lines.append(f"### {inv_name} {title_map[inv_name]} — {status}")
        if slugs:
            lines.append("")
            for s in slugs[:10]:
                lines.append(f"- `{s}`")
            if len(slugs) > 10:
                lines.append(f"- ... (+{len(slugs)-10} more)")
        lines.append("")

    lines += [
        "## 2. Framework Compliance",
        "",
        f"- Source: `{compliance.source_path}`",
        f"- 總項：{compliance.total} / passed: {compliance.passed} / "
        f"failed: {compliance.failed} / unverifiable: {compliance.unverifiable}",
        "",
        "### Top failed",
        "",
    ]
    failed_items = [it for it in compliance.items if it.status == "failed"][:10]
    if failed_items:
        for it in failed_items:
            lines.append(f"- **{it.code}** {it.text} — {it.suggestion}")
    else:
        lines.append("（無 failed 項目）")
    lines += [
        "",
        "## 3. GRI Content Index",
        "",
        f"- 檔案：`{gri.file_path}`",
        f"- 已揭露：{gri.fulfilled} / 部分：{gri.partial} / 未揭露：{gri.missing}",
        "",
        "## 4. Assurance Readiness",
        "",
        f"- 檔案：`{assurance.file_path}`",
        f"- 需補件 KPI / DataPoint：{assurance.needs_work} 筆",
        "",
        "## 5. 優先修補建議",
        "",
    ]
    fix_items: list[tuple[str, str]] = []
    # critical first
    for v in violations:
        name = getattr(v, "invariant_name", v.invariant)
        if name in ("I1a", "I1b", "I4"):
            fix_items.append(("🔴", f"{name}: {v.page_slug} — {v.detail}"))
    for it in assurance.items:
        if it.severity == "critical":
            fix_items.append(("🔴", f"DataPoint `{it.page_slug}` 缺 {', '.join(it.missing_fields)}"))
    for r in gri.rows:
        if r.status == "missing":
            fix_items.append(("🔴", f"GRI {r.framework_ref}（{r.zh_label}）未揭露"))
    # warnings
    for v in violations:
        name = getattr(v, "invariant_name", v.invariant)
        if name in ("I2", "I3", "I5"):
            fix_items.append(("🟠", f"{name}: {v.page_slug} — {v.detail}"))
    for it in compliance.items:
        if it.status == "failed":
            fix_items.append(("🟠", f"Compliance {it.code}: {it.suggestion}"))

    for sym, text in fix_items[:30]:
        lines.append(f"- {sym} {text}")
    if len(fix_items) > 30:
        lines.append(f"- ... (+{len(fix_items)-30} more, 詳見上方各 section)")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return FullGapAnalysisResult(
        file_path=str(out_path),
        severity_breakdown={"critical": critical, "warning": warning, "info": info},
        invariant_violations=len(violations),
        compliance_failed=compliance.failed,
        compliance_unverifiable=compliance.unverifiable,
        gri_missing=gri.missing,
        assurance_needs_work=assurance.needs_work,
        summary=tl_dr,
    )


# ---------------------------------------------------------------------------
# Server registration
# ---------------------------------------------------------------------------


def register(server) -> None:  # noqa: ANN001
    """Bind all 4 Phase 7 tools to a FastMCP server instance."""
    server.tool()(run_compliance_checklist)
    server.tool()(generate_gri_content_index)
    server.tool()(generate_assurance_readiness_checklist)
    server.tool()(run_full_gap_analysis)


__all__ = [
    "ChecklistItem", "ComplianceChecklistResult",
    "GriDisclosureRow", "GriContentIndexResult",
    "AssuranceItem", "AssuranceReadinessResult",
    "FullGapAnalysisResult",
    "run_compliance_checklist",
    "generate_gri_content_index",
    "generate_assurance_readiness_checklist",
    "run_full_gap_analysis",
    "register",
]
