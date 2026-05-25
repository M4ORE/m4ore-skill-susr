"""susr.mcp.tools.phase3 — 4 Phase-3 materiality assessment tools.

MVP v0.1 deliverable: end-to-end materiality assessment driven from
Claude Desktop chat.  Tools (spec §6.2):

    search_topics_universe         — pull candidate topics from shared_kb + client
    score_topic_dual_axis          — write impact + financial scores → tier
    generate_materiality_matrix    — render matrix .md + .svg, run invariants
    stakeholder_engagement_helper  — record an engagement event + links

Markdown files in the per-client repo are source of truth (CLAUDE.md §8
decision 1); these tools write markdown directly.

TOC (4.6.1 (b)：硬門檻 500 行使用 TL;DR+index 對應)：
    L1   — module docstring + imports + _FRONTMATTER_RE
    L30+ — md helpers: _read_md / _write_md / _now / _append_timeline_md
    L58+ — tier resolution: _classify_tier / resolve_materiality_tier
    L120+ — Tool 1: search_topics_universe + TopicCandidate
    L230+ — Tool 2: score_topic_dual_axis + ImpactScores/FinancialScores
    L330+ — Tool 3: generate_materiality_matrix + MaterialityMatrix + TierOverride
    L520+ — Tool 4: stakeholder_engagement_helper + EngagementRecord
    L580+ — register(server) + __all__

R3 收斂：frontmatter explicit tier vs `_classify_tier` 二套標準衝突
（walkthroughs/lealea-5364-phase3.md §3.265 + §7 backlog #3）由
``resolve_materiality_tier`` 統一仲裁，顧問 explicit 優先 + 不一致時
emit warning 收進 ``MaterialityMatrix.tier_overrides``。
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

from susr.workspace import find_client_workspace

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def _read_md(path: Path) -> tuple[dict, str]:
    if not path.exists():
        return {}, ""
    text = path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    import yaml  # type: ignore

    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, m.group(2) or ""


def _write_md(path: Path, frontmatter: dict, body: str) -> None:
    import yaml  # type: ignore

    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
    path.write_text(f"---\n{serialized}---\n\n{body.lstrip()}", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _classify_tier(impact: float, financial: float) -> Literal["核心", "重大", "邊界"]:
    """嚴格雙軸 auto-suggest：兩軸皆 ≥4 才為核心，任一軸 ≥3.5 為重大。"""
    if impact >= 4 and financial >= 4:
        return "核心"
    if impact >= 3.5 or financial >= 3.5:
        return "重大"
    return "邊界"


_VALID_TIERS: tuple[str, ...] = ("核心", "重大", "邊界")


def resolve_materiality_tier(
    frontmatter_tier: Optional[str],
    impact_score: Optional[float],
    financial_score: Optional[float],
) -> tuple[Literal["核心", "重大", "邊界"], Optional[str]]:
    """收斂 frontmatter explicit tier 與 `_classify_tier` 自動建議的兩套標準。

    回傳 ``(resolved_tier, warning_message_or_None)``。

    決策樹（5 條）：

    1. 兩軸分數任一為 None → 視為尚未評分，回 ``("邊界", None)``。
    2. frontmatter_tier 為 None → 直接採 auto_tier（無 warning）。
    3. frontmatter_tier 為非法值（不在 {"核心","重大","邊界"}）→ fallback
       回 auto_tier 並附 warning「無效 tier，已退回 auto-suggested」。
    4. frontmatter_tier == auto_tier → 採 frontmatter（無 warning）。
    5. frontmatter_tier != auto_tier → **顧問 explicit 優先**（honor frontmatter），
       但 emit warning 標記與 auto-suggested 不一致，供 timeline / 矩陣審計用。

    為何「顧問覆寫」優先而非 auto 優先：
        SP1-004 SOP §4 的「核心(Impact 軸)」/「核心(Financial 軸)」是顧問
        基於行業特殊性 + 利害關係人議合脈絡做出的判斷，自動式 ≥4 嚴格門檻
        無法表達這層 nuance。susr 定位為 co-pilot（CLAUDE.md §1），顧問
        判斷在前；但「靜默接受」會掩蓋衝突，故仍 emit warning 上 audit trail。
    """
    if impact_score is None or financial_score is None:
        return "邊界", None
    auto_tier = _classify_tier(float(impact_score), float(financial_score))

    if frontmatter_tier is None:
        return auto_tier, None

    fm = str(frontmatter_tier).strip()
    if fm not in _VALID_TIERS:
        return auto_tier, (
            f'frontmatter materiality_tier="{frontmatter_tier}" 為非法值，'
            f'已退回 auto-suggested "{auto_tier}"'
        )

    if fm == auto_tier:
        return auto_tier, None  # type: ignore[return-value]

    return fm, (  # type: ignore[return-value]
        f'顧問 explicit "{fm}" vs auto-suggested "{auto_tier}" '
        f'(impact={impact_score:.2f}, financial={financial_score:.2f}) — kept explicit'
    )


def _append_timeline_md(body: str, action: str, payload: dict, actor: str) -> tuple[str, int]:
    """Append a timeline_entry line to a markdown body; return (new_body, synthetic id).

    R4d 收斂後本函式為 ``brain.timeline.append_timeline_md_body`` 的薄 wrapper —
    歷史 caller（``score_topic_dual_axis`` / ``stakeholder_engagement_helper``）
    仍可直接用此名稱不需大改。實際的字串格式（``- [ts] action=… actor=… payload=…``）
    由 brain 端統一定義，確保 ``iro.py`` / ``action.py`` / ``phase3.py`` 三處
    MD body trail 與 ``timeline_entries`` table 內容對齊。

    回傳的 synthetic id 是 1-based MD line 計數（與舊行為相容）；若 phase3 工具
    未來改走 brain DB（P1a backlog），可直接切換到 ``append_dual``。
    """
    # Local import — keep the timeline module dependency lazy so the
    # phase3 import path isn't slowed by sqlite3 chain at cold-start.
    from susr.brain.timeline import append_timeline_md_body

    return append_timeline_md_body(body, action, payload, actor)


# ---------- Tool 1: search_topics_universe ----------


class TopicCandidate(BaseModel):
    slug: str
    name: str
    axis: Literal["E", "S", "G"]
    industry_specificity: Optional[str] = None
    source_kb: Literal["shared", "client"]


def _load_industry_pack(client_path: Optional[Path], industry: str) -> list[TopicCandidate]:
    from susr.shared_kb import SHARED_KB_DATA_DIR

    paths = []
    if client_path is not None:
        paths += [
            client_path / "shared" / "industry_packs" / f"{industry}.md",
            client_path / "shared" / "industry-packs" / f"{industry}.md",
        ]
    paths += [
        SHARED_KB_DATA_DIR / "industry_packs" / f"{industry}.md",
        SHARED_KB_DATA_DIR / "industry-packs" / f"{industry}.md",
    ]
    found = next((p for p in paths if p.exists()), None)
    if found is None:
        return []
    fm, body = _read_md(found)
    out: list[TopicCandidate] = []
    if isinstance(fm.get("topics"), list):
        for t in fm["topics"]:
            if not isinstance(t, dict):
                continue
            slug, name, axis = (
                str(t.get("slug") or "").strip(),
                str(t.get("name") or "").strip(),
                str(t.get("axis") or "").strip(),
            )
            if slug and name and axis in ("E", "S", "G"):
                out.append(
                    TopicCandidate(
                        slug=slug, name=name, axis=axis,  # type: ignore[arg-type]
                        industry_specificity=industry, source_kb="shared",
                    )
                )
    else:
        for line in body.splitlines():
            line = line.strip()
            if not line.startswith("-"):
                continue
            parts = [p.strip() for p in line.lstrip("-").split("|")]
            if len(parts) >= 3 and parts[2] in ("E", "S", "G"):
                out.append(
                    TopicCandidate(
                        slug=parts[0], name=parts[1], axis=parts[2],  # type: ignore[arg-type]
                        industry_specificity=industry, source_kb="shared",
                    )
                )
    return out


def _load_client_topics(client_path: Path) -> list[TopicCandidate]:
    topics_dir = client_path / "entities" / "topics"
    if not topics_dir.exists():
        return []
    out: list[TopicCandidate] = []
    for md in sorted(topics_dir.glob("*.md")):
        fm, _ = _read_md(md)
        if fm.get("axis") not in ("E", "S", "G"):
            continue
        out.append(
            TopicCandidate(
                slug=str(fm.get("slug") or md.stem),
                name=str(fm.get("name") or md.stem),
                axis=fm["axis"],
                industry_specificity=fm.get("industry_specificity"),
                source_kb="client",
            )
        )
    return out


def search_topics_universe(
    industry: str,
    framework: Literal["GRI", "ISSB", "ESRS", "TW_FSC", "SASB"] = "GRI",
    client_slug: Optional[str] = None,
    top_k: int = 40,
) -> list[TopicCandidate]:
    """Phase 3 step 1 — merge shared_kb industry pack + client.entities/topics/*."""
    client_path: Optional[Path] = None
    if client_slug:
        try:
            client_path = find_client_workspace(client_slug)
        except FileNotFoundError:
            client_path = None
    merged: dict[str, TopicCandidate] = {c.slug: c for c in _load_industry_pack(client_path, industry)}
    if client_path:
        for c in _load_client_topics(client_path):
            merged[c.slug] = c
    return list(merged.values())[:top_k]


# ---------- Tool 2: score_topic_dual_axis ----------


class ImpactScores(BaseModel):
    severity: float = Field(ge=1, le=5)
    scope: float = Field(ge=1, le=5)
    irreversibility: float = Field(ge=1, le=5)
    likelihood: float = Field(ge=1, le=5)


class FinancialScores(BaseModel):
    magnitude: float = Field(ge=1, le=5)
    time_horizon: Literal["S", "M", "L"]
    probability: float = Field(ge=1, le=5)


class TopicScoreResult(BaseModel):
    topic_slug: str
    impact_score: float
    financial_score: float
    materiality_tier: Literal["核心", "重大", "邊界"]
    page_file: str
    timeline_entry_id: int
    tier_resolution_warning: Optional[str] = None


def score_topic_dual_axis(
    client_slug: str,
    topic_slug: str,
    impact: ImpactScores,
    financial: FinancialScores,
    actor: str,
    rationale: Optional[str] = None,
) -> TopicScoreResult:
    """Phase 3 step 2 — 寫入雙軸評分並透過 ``resolve_materiality_tier`` 收斂 tier。

    R4a 修補（lealea-5364-phase3-r3.md §5.1）：原實作直接 `_classify_tier()`
    把自動算法結果硬寫回 frontmatter，會靜默吞掉顧問先前 explicit 設定的
    `materiality_tier`（例如 SP1-004 SOP §4 顧問 nuanced 標 "核心"）。
    現改為先讀既有 frontmatter tier → 透過 resolver 與自動建議收斂；若顧問
    explicit 與 auto-suggested 不一致則 honor explicit + emit warning，並
    額外寫一筆 ``action='verify', payload.detail=warning`` 的 timeline 條目
    供 audit trail（同時 response 多出 ``tier_resolution_warning`` 欄位）。
    """
    client_path = find_client_workspace(client_slug)
    page = client_path / "entities" / "topics" / f"{topic_slug}.md"
    fm, body = _read_md(page)
    impact_score = round(
        (impact.severity + impact.scope + impact.irreversibility + impact.likelihood) / 4.0, 3
    )
    financial_score = round((financial.magnitude + financial.probability) / 2.0, 3)
    existing_tier_raw = fm.get("materiality_tier")
    existing_tier = str(existing_tier_raw) if existing_tier_raw is not None else None
    tier, warning = resolve_materiality_tier(existing_tier, impact_score, financial_score)
    fm.update(
        {
            "slug": topic_slug, "name": fm.get("name", topic_slug), "axis": fm.get("axis", "E"),
            "impact_score": impact_score, "financial_score": financial_score,
            "materiality_tier": tier, "assessed_at": _now(), "assessed_by": actor,
        }
    )
    payload = {
        "impact": impact.model_dump(), "financial": financial.model_dump(),
        "impact_score": impact_score, "financial_score": financial_score,
        "tier": tier, "rationale": rationale,
    }
    body, tl_id = _append_timeline_md(body, "verify", payload, actor)
    if warning:
        # 額外 audit-trail 條目：明標 tier resolution warning，方便 timeline
        # 過濾出「顧問 explicit vs auto-suggested 不一致」的歷史事件。
        body, _ = _append_timeline_md(
            body, "verify",
            {"detail": warning, "frontmatter_tier": existing_tier,
             "auto_tier": _classify_tier(impact_score, financial_score),
             "resolved_tier": tier},
            actor,
        )
    _write_md(page, fm, body)
    return TopicScoreResult(
        topic_slug=topic_slug, impact_score=impact_score, financial_score=financial_score,
        materiality_tier=tier, page_file=str(page), timeline_entry_id=tl_id,
        tier_resolution_warning=warning,
    )


# ---------- Tool 3: generate_materiality_matrix ----------


class TierOverride(BaseModel):
    """顧問 frontmatter explicit tier 與 `_classify_tier` auto-suggest 不一致的紀錄。

    每筆代表一個 topic 的覆寫事件 — 顧問 explicit 已被 honor，但 auto-suggested
    被保留作 audit footnote，方便在矩陣 .md 與 timeline 兩處重複驗證。
    """

    slug: str
    resolved_tier: Literal["核心", "重大", "邊界"]
    auto_suggested_tier: Literal["核心", "重大", "邊界"]
    frontmatter_tier: Optional[str] = None
    impact_score: float
    financial_score: float
    warning: str


class MaterialityMatrix(BaseModel):
    matrix_md_path: str
    matrix_svg_path: str
    core_topics: list[str]
    material_topics: list[str]
    border_topics: list[str]
    invariants_passed: bool
    invariant_violations: list[str] = []
    tier_overrides: list[TierOverride] = []


def _render_svg(rows: list[dict]) -> str:
    """Pure-string SVG scatter (impact vs financial, 5x5 grid)."""
    W, H, M = 540, 540, 70
    pw, ph = W - 2 * M, H - 2 * M
    x = lambda s: M + (max(0.0, min(5.0, s)) / 5.0) * pw  # noqa: E731
    y = lambda s: M + ph - (max(0.0, min(5.0, s)) / 5.0) * ph  # noqa: E731
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect x="{x(4):.1f}" y="{y(4):.1f}" width="{M+pw-x(4):.1f}" '
        f'height="{M+ph-y(4):.1f}" fill="#ffeaea" stroke="#e88" stroke-dasharray="4,2"/>',
    ]
    for i in range(6):
        gx, gy = M + (i / 5.0) * pw, M + (i / 5.0) * ph
        parts.append(f'<line x1="{gx:.1f}" y1="{M}" x2="{gx:.1f}" y2="{M+ph}" stroke="#ddd"/>')
        parts.append(f'<line x1="{M}" y1="{gy:.1f}" x2="{M+pw}" y2="{gy:.1f}" stroke="#ddd"/>')
        parts.append(
            f'<text x="{gx:.1f}" y="{M+ph+18}" font-size="10" text-anchor="middle">{i}</text>'
        )
        parts.append(
            f'<text x="{M-12:.1f}" y="{M+ph-(i/5.0)*ph+3:.1f}" font-size="10" '
            f'text-anchor="end">{i}</text>'
        )
    parts.append(
        f'<text x="{M+pw/2:.1f}" y="{H-20}" font-size="13" text-anchor="middle">'
        f'Impact (對外部之影響)</text>'
    )
    parts.append(
        f'<text x="20" y="{M+ph/2:.1f}" font-size="13" text-anchor="middle" '
        f'transform="rotate(-90 20 {M+ph/2:.1f})">Financial (對企業之財務)</text>'
    )
    colors = {"核心": "#c0392b", "重大": "#e67e22", "邊界": "#7f8c8d"}
    for r in rows:
        cx, cy = x(float(r["impact_score"])), y(float(r["financial_score"]))
        c = colors.get(r.get("tier", "邊界"), "#7f8c8d")
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="{c}" stroke="#fff" stroke-width="1.5"/>'
            f'<text x="{cx+8:.1f}" y="{cy+4:.1f}" font-size="11">{r["slug"]}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _collect_scored_topics(client_path: Path) -> list[dict]:
    """掃過 entities/topics/*.md，逐檔透過 ``resolve_materiality_tier`` 收斂 tier。

    每筆 dict 帶四個 tier-related 欄位：

    - ``tier``：最終採用的 tier（honor frontmatter explicit，若有的話）
    - ``auto_tier``：由 ``_classify_tier`` 純粹基於兩軸分數算出的建議
    - ``frontmatter_tier``：原始 frontmatter 值（可能為 None）
    - ``tier_warning``：若 frontmatter 與 auto 不一致或為非法值才有值，否則 None
    """
    topics_dir = client_path / "entities" / "topics"
    out: list[dict] = []
    if not topics_dir.exists():
        return out
    for md in sorted(topics_dir.glob("*.md")):
        fm, _ = _read_md(md)
        if "impact_score" not in fm or "financial_score" not in fm:
            continue
        try:
            i_s, f_s = float(fm["impact_score"]), float(fm["financial_score"])
        except (TypeError, ValueError):
            continue
        slug = fm.get("slug", md.stem)
        iro_dir = topics_dir / slug / "iro"
        fm_tier_raw = fm.get("materiality_tier")
        fm_tier = str(fm_tier_raw) if fm_tier_raw is not None else None
        resolved_tier, warning = resolve_materiality_tier(fm_tier, i_s, f_s)
        out.append(
            {
                "slug": slug,
                "name": fm.get("name", md.stem),
                "axis": fm.get("axis", ""),
                "impact_score": i_s,
                "financial_score": f_s,
                "tier": resolved_tier,
                "auto_tier": _classify_tier(i_s, f_s),
                "frontmatter_tier": fm_tier,
                "tier_warning": warning,
                "iro_link_count": sum(1 for _ in iro_dir.glob("*.md")) if iro_dir.exists() else 0,
            }
        )
    return out


def generate_materiality_matrix(
    client_slug: str, year: int, include_svg: bool = True,
) -> MaterialityMatrix:
    """Phase 3 step 3 — render matrix .md/.svg + best-effort invariant check.

    Tier 收斂行為：`_collect_scored_topics` 透過 ``resolve_materiality_tier``
    把 frontmatter explicit tier 與 ``_classify_tier`` auto-suggest 對齊；
    若顧問 explicit 與 auto-suggested 不一致則 honor explicit 但收進
    ``tier_overrides`` 欄位（並寫入矩陣 .md 的「Tier 覆寫」段落供審計）。
    """
    client_path = find_client_workspace(client_slug)
    rows = _collect_scored_topics(client_path)
    core = sorted(r["slug"] for r in rows if r["tier"] == "核心")
    material = sorted(r["slug"] for r in rows if r["tier"] == "重大")
    border = sorted(r["slug"] for r in rows if r["tier"] == "邊界")
    violations = [
        f"I1: core topic {r['slug']} has no IRO chain"
        for r in rows
        if r["tier"] == "核心" and r["iro_link_count"] == 0
    ]
    tier_overrides = [
        TierOverride(
            slug=r["slug"],
            resolved_tier=r["tier"],
            auto_suggested_tier=r["auto_tier"],
            frontmatter_tier=r.get("frontmatter_tier"),
            impact_score=r["impact_score"],
            financial_score=r["financial_score"],
            warning=r["tier_warning"],
        )
        for r in rows
        if r.get("tier_warning")
    ]
    project_dir = client_path / "projects" / f"{year}-sustainability-report"
    project_dir.mkdir(parents=True, exist_ok=True)
    md_path = project_dir / f"materiality-{year}.md"
    svg_path = project_dir / f"materiality-{year}.svg"
    lines = [
        f"# {year} 雙重重大性矩陣 — {client_slug}",
        "",
        f"_由 susr `generate_materiality_matrix` 自動產出於 {_now()}_",
        "",
        f"- 核心議題：{len(core)} / 重大議題：{len(material)} / 邊界議題：{len(border)}",
        f"- 不變量檢查：{'通過' if not violations else '失敗 ('+str(len(violations))+')'}",
        f"- Tier 覆寫：{len(tier_overrides)}（顧問 explicit ≠ auto-suggested）",
        "",
        "## 議題評分表",
        "",
        "| slug | name | axis | impact | financial | tier |",
        "|------|------|------|-------:|----------:|------|",
    ]
    for r in sorted(rows, key=lambda x: (-x["impact_score"], -x["financial_score"])):
        lines.append(
            f"| {r['slug']} | {r['name']} | {r['axis']} | "
            f"{r['impact_score']:.2f} | {r['financial_score']:.2f} | {r['tier']} |"
        )
    if violations:
        lines += ["", "## 不變量違反", ""] + [f"- {v}" for v in violations]
    if tier_overrides:
        lines += ["", "## Tier 覆寫（顧問 explicit honored）", ""]
        for ov in tier_overrides:
            lines.append(f"- `{ov.slug}`：{ov.warning}")
    if include_svg:
        lines += ["", "## 矩陣圖", "", f"![matrix]({svg_path.name})"]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if include_svg:
        svg_path.write_text(_render_svg(rows), encoding="utf-8")
    return MaterialityMatrix(
        matrix_md_path=str(md_path),
        matrix_svg_path=str(svg_path) if include_svg else "",
        core_topics=core, material_topics=material, border_topics=border,
        invariants_passed=not violations, invariant_violations=violations,
        tier_overrides=tier_overrides,
    )


# ---------- Tool 4: stakeholder_engagement_helper ----------


class EngagementRecord(BaseModel):
    engagement_slug: str
    page_file: str
    topics_raised: list[str]
    timeline_entry_id: int


def stakeholder_engagement_helper(
    client_slug: str,
    stakeholder_slug: str,
    method: Literal["問卷", "訪談", "焦點", "說明會"],
    date: str,
    sample_size: Optional[int],
    topics_raised: list[str],
    findings_summary: str,
    evidence_refs: Optional[list[str]] = None,
    actor: str = "consultant",
) -> EngagementRecord:
    """Phase 3 step 4 — record one engagement event + back-link topics."""
    client_path = find_client_workspace(client_slug)
    engagement_slug = f"{date}-{method}"
    page = (
        client_path / "entities" / "stakeholders" / stakeholder_slug
        / "engagements" / f"{engagement_slug}.md"
    )
    fm = {
        "slug": engagement_slug, "stakeholder_slug": stakeholder_slug,
        "topic_slugs": list(topics_raised), "date": date, "method": method,
        "sample_size": sample_size, "findings_summary": findings_summary,
        "evidence_refs": list(evidence_refs or []),
    }
    body = (
        f"# 議合事件 {engagement_slug}\n\n"
        f"- 利害關係人：`{stakeholder_slug}`\n"
        f"- 方法：{method}\n"
        f"- 樣本數：{sample_size if sample_size is not None else 'N/A'}\n\n"
        f"## Findings\n\n{findings_summary}\n\n## Topics Raised\n\n"
        + "\n".join(f"- `{t}`" for t in topics_raised) + "\n"
    )
    body, tl_id = _append_timeline_md(
        body, "iro_link",
        {"stakeholder": stakeholder_slug, "method": method, "date": date, "topics": list(topics_raised)},
        actor,
    )
    _write_md(page, fm, body)
    for t in topics_raised:
        tp = client_path / "entities" / "topics" / f"{t}.md"
        if tp.exists():
            tfm, tbody = _read_md(tp)
            ids = list(tfm.get("identified_by_stakeholders") or [])
            if stakeholder_slug not in ids:
                ids.append(stakeholder_slug)
                tfm["identified_by_stakeholders"] = ids
                _write_md(tp, tfm, tbody)
    return EngagementRecord(
        engagement_slug=engagement_slug, page_file=str(page),
        topics_raised=list(topics_raised), timeline_entry_id=tl_id,
    )


def register(server) -> None:  # noqa: ANN001
    """Bind the 4 Phase-3 tools to a FastMCP server instance."""
    server.tool()(search_topics_universe)
    server.tool()(score_topic_dual_axis)
    server.tool()(generate_materiality_matrix)
    server.tool()(stakeholder_engagement_helper)


__all__ = [
    "TopicCandidate", "ImpactScores", "FinancialScores", "TopicScoreResult",
    "MaterialityMatrix", "TierOverride", "EngagementRecord",
    "search_topics_universe", "score_topic_dual_axis",
    "generate_materiality_matrix", "stakeholder_engagement_helper",
    "resolve_materiality_tier", "register",
]
