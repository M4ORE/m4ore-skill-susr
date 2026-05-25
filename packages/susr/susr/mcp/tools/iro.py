"""susr.mcp.tools.iro — Phase 3 IRO linkage tool（補 Step 2-B walkthrough P0b）。

MVP v0.1 Phase 3 原本 4 個 tools 全部沒處理 IRO 建立，導致 walkthrough §5 invariant
I1（核心 topic → IRO → Action 鏈）對 lealea 5364 出 9/9 fail（見
``docs/walkthroughs/lealea-5364-phase3.md`` §5.385 + §7 R3 backlog #2）。

本模組補上 ``link_topic_to_iro`` — 對既有 topic 建立 IRO entity + ``topic_has_iro``
typed edge，雙寫到（a）per-client markdown filesystem（tool 3
``_collect_scored_topics`` 抓 ``entities/topics/<slug>/iro/*.md``），與（b）brain
SQLite（IRO entity page + 對應 edge），讓兩條 I1 路徑同時收斂。

設計選項採 Option 1（獨立 tool，純粹、可組合）— 不修 ``score_topic_dual_axis``
語意，顧問評分完成後再決定何時建 IRO。

phase3.py 已 452 行（接近 CLAUDE.md §4.6.4 硬門檻 500），新 tool 拆此檔。
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel

from susr.workspace import find_client_workspace

# Pydantic Literal 用 Title case 對應 IroFrontmatter schema（brain/entities.py 第 133 行）。
_IRO_TYPE_MAP: dict[str, str] = {
    "impact": "Impact", "risk": "Risk", "opportunity": "Opportunity",
}

# 預設 category 對應表 — IroFrontmatter.category 是 free-text str，
# 但這裡列常用 CSRD/ESRS + TCFD 風格枚舉，幫 UI / Claude prompt 對齊。
IroCategory = Literal[
    "physical", "transition", "reputational", "legal",
    "operational", "supply_chain", "market", "technology",
]

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def _read_md(path: Path) -> tuple[dict, str]:
    """讀 markdown，回 (frontmatter dict, body)。檔案不存在 → ({}, "")."""
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
    """寫 markdown，附 YAML frontmatter。父目錄不存在會自動建。"""
    import yaml  # type: ignore

    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
    path.write_text(f"---\n{serialized}---\n\n{body.lstrip()}", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _iro_short_hash(topic_slug: str, iro_type_title: str, iro_name: str) -> str:
    """deterministic 8-char hash，作為 IRO slug 後綴 → 同 (topic, type, name) 永遠同 slug。"""
    h = hashlib.sha256(f"{topic_slug}|{iro_type_title}|{iro_name}".encode("utf-8"))
    return h.hexdigest()[:8]


# ---------- Pydantic models ----------


class LinkedIroResult(BaseModel):
    """``link_topic_to_iro`` 回傳結構。

    Attributes:
        iro_slug: deterministic 產出的 IRO slug（per-client unique）。
        page_file: IRO entity 的 markdown 絕對路徑（filesystem source of truth）。
        topic_slug: 連結到的 topic slug。
        iro_type: 'Impact' / 'Risk' / 'Opportunity'（已 normalize 為 Title case）。
        brain_page_id: brain SQLite ``pages.id``（同 iro_slug + tenant_id unique）。
        edge_id: ``links`` 表的 row id（``topic_has_iro`` typed edge）。
        timeline_entry_id: brain ``timeline_entries`` 表的 row id。
        created: 此次呼叫是否真的新建（False → idempotent no-op，回既有 IRO）。
    """

    iro_slug: str
    page_file: str
    topic_slug: str
    iro_type: Literal["Impact", "Risk", "Opportunity"]
    brain_page_id: int
    edge_id: int
    timeline_entry_id: int
    created: bool


# ---------- helpers ----------


def _find_topic_brain_page(engine, topic_slug: str):
    """brain 內 topic page 的 slug 可能是 ``<slug>`` 或 ``topics/<slug>``（測試用兩種）。

    回 ``Page`` 或 None；同時回傳實際用到的 brain slug，供後續 ``engine.link()`` 用。
    """
    page = engine.get_page(topic_slug)
    if page is not None:
        return page, topic_slug
    prefixed = f"topics/{topic_slug}"
    page = engine.get_page(prefixed)
    if page is not None:
        return page, prefixed
    return None, None


def _build_iro_body(
    iro_slug: str, iro_type_title: str, iro_name: str, description: str,
    *, category: Optional[str], time_horizon: str,
    financial_magnitude: Optional[float], topic_slug: str,
) -> str:
    """組 IRO entity markdown body（compiled_truth）。"""
    return (
        f"# {iro_type_title}: {iro_name}\n\n"
        f"- 議題：`{topic_slug}`\n"
        f"- 類型：{iro_type_title}\n"
        f"- 分類：{category or '—'}\n"
        f"- 時間軸：{time_horizon}\n"
        f"- 財務量級：{financial_magnitude if financial_magnitude is not None else '—'}\n\n"
        f"## 描述\n\n{description.strip() or '_<待顧問補充>_'}\n"
    )


# ---------- main tool ----------


def link_topic_to_iro(
    client_slug: str,
    topic_slug: str,
    iro_type: Literal["impact", "risk", "opportunity"],
    iro_name: str,
    description: str = "",
    category: Optional[IroCategory] = None,
    time_horizon: Literal["S", "M", "L"] = "M",
    financial_magnitude: float = 3.0,
    *,
    actor: str = "consultant",
) -> LinkedIroResult:
    """Phase 3 補充工具 — 對既有 topic 建立 IRO entity + ``topic_has_iro`` edge。

    補的是 walkthrough §5 暴露的 I1 invariant 缺口：原 4 個 phase 3 tools
    沒有任何一個處理 IRO 建立，導致 lealea 5364 跑出 9/9 核心 topic 缺 IRO。

    雙寫保證 filesystem + brain DB 兩條 I1 路徑同步：
        - filesystem：``entities/topics/<topic_slug>/iro/<iro_slug>.md``
          （``generate_materiality_matrix`` 內建 I1 check 在掃此目錄）
        - brain DB：``iro`` entity page + ``topic_has_iro`` typed edge
          （``invariants.assert_i1_core_topic_coverage`` 在掃 ``v_core_topic_action_coverage``）

    Idempotency：``iro_slug = <topic_slug>-<iro_type>-<sha8>``；同 (topic, type, name)
    重複呼叫不複製 — 回既有 IRO 與 ``created=False``。

    Args:
        client_slug: per-client workspace 目錄名稱。
        topic_slug: 已存在的 topic slug（必須先 ingest 或先 score 過）。
        iro_type: 'impact' / 'risk' / 'opportunity'（lower-case input，內部 normalize）。
        iro_name: 人類可讀短名稱，例如「客戶健康」、「碳費」、「永續品牌差異化」。
        description: 顧問描述（可後續再 enrich）；空字串 → 留 placeholder。
        category: 分類（physical / transition / reputational / legal / operational /
            supply_chain / market / technology），對應 TCFD + CSRD 常用枚舉。
        time_horizon: 'S' / 'M' / 'L'（short / medium / long term）。
        financial_magnitude: 0-5 估值（IroFrontmatter schema 限定 float），預設 3.0。
        actor: 寫入 timeline 的 actor 欄位（"consultant" / "consultant:王" / agent id）。

    Returns:
        ``LinkedIroResult`` — 含 iro_slug、page_file、brain_page_id、edge_id、
        timeline_entry_id、created（是否新建）。

    Raises:
        FileNotFoundError: client workspace 或 topic markdown 不存在。
        LookupError: topic 沒在 brain DB 裡（需先 ingest）。
        KeyError: ``iro_type`` 不在 {'impact', 'risk', 'opportunity'}。
    """
    iro_type_title = _IRO_TYPE_MAP.get(iro_type.lower())
    if iro_type_title is None:
        raise KeyError(
            f"unknown iro_type {iro_type!r}; expected one of {sorted(_IRO_TYPE_MAP)}"
        )

    # 軟邊界（IroFrontmatter.financial_magnitude 是 free float，但這裡仍夾到 0..5）
    financial_magnitude = max(0.0, min(5.0, float(financial_magnitude)))

    client_path = find_client_workspace(client_slug)
    topic_page_md = client_path / "entities" / "topics" / f"{topic_slug}.md"
    if not topic_page_md.exists():
        raise FileNotFoundError(
            f"topic markdown not found: {topic_page_md} "
            f"(score_topic_dual_axis or ingest the topic first)"
        )

    # ── lazy import — engine import 拉 sqlite3，cold-start 維持輕量 ──
    from susr.brain.engine import BrainEngine

    db_path = client_path / ".susr" / "db.sqlite"
    engine = BrainEngine.open(str(db_path), load_sqlite_vec=False)
    try:
        topic_page, topic_brain_slug = _find_topic_brain_page(engine, topic_slug)
        if topic_page is None:
            raise LookupError(
                f"topic {topic_slug!r} not found in brain DB at {db_path}; "
                "ingest the topic page first (engine.put_page entity_type='topic')"
            )

        short_hash = _iro_short_hash(topic_slug, iro_type_title, iro_name)
        iro_slug = f"{topic_slug}-{iro_type.lower()}-{short_hash}"
        iro_brain_slug = f"iros/{iro_slug}"

        iro_md_path = client_path / "entities" / "topics" / topic_slug / "iro" / f"{iro_slug}.md"

        # Idempotency — 看 brain DB（filesystem 可能被外部刪，brain 是 ground truth）。
        existing = engine.get_page(iro_brain_slug)
        if existing is not None:
            # 已建過：不複寫、不重 link，回既有結構。
            row = engine.conn.execute(
                "SELECT id FROM links WHERE src_page_id = ? AND dst_page_id = ? "
                "AND edge_type = 'topic_has_iro'",
                [topic_page.id, existing.id],
            ).fetchone()
            existing_edge_id = int(row[0]) if row else 0
            tl_row = engine.conn.execute(
                "SELECT id FROM timeline_entries WHERE page_id = ? "
                "ORDER BY id DESC LIMIT 1",
                [existing.id],
            ).fetchone()
            existing_tl_id = int(tl_row[0]) if tl_row else 0
            return LinkedIroResult(
                iro_slug=iro_slug, page_file=str(iro_md_path),
                topic_slug=topic_slug, iro_type=iro_type_title,  # type: ignore[arg-type]
                brain_page_id=existing.id, edge_id=existing_edge_id,
                timeline_entry_id=existing_tl_id, created=False,
            )

        # ── 1. 寫 IRO markdown（filesystem source of truth）──
        iro_fm = {
            "slug": iro_slug, "topic_slug": topic_slug, "type": iro_type_title,
            "category": category or "operational",
            "time_horizon": time_horizon,
            "financial_magnitude": float(financial_magnitude),
            "iro_name": iro_name, "created_at": _now(), "created_by": actor,
        }
        body = _build_iro_body(
            iro_slug, iro_type_title, iro_name, description,
            category=category, time_horizon=time_horizon,
            financial_magnitude=float(financial_magnitude), topic_slug=topic_slug,
        )
        _write_md(iro_md_path, iro_fm, body)

        # ── 2. 寫 brain DB（iro entity page）──
        # IroFrontmatter schema：slug + topic_slug + type + category + time_horizon
        # + financial_magnitude；其他 markdown frontmatter 額外欄位 brain 不收，
        # 因為 validate_frontmatter 對 extra fields 寬鬆但會記到 entity_attributes。
        brain_fm = {
            "slug": iro_slug, "topic_slug": topic_slug, "type": iro_type_title,
            "category": category or "operational",
            "time_horizon": time_horizon,
            "financial_magnitude": float(financial_magnitude),
        }
        brain_page_id = engine.put_page(
            slug=iro_brain_slug, entity_type="iro",
            title=f"{iro_type_title}: {iro_name}",
            compiled_truth=body, file_path=str(iro_md_path),
            frontmatter=brain_fm,
        )

        # ── 3. 寫 topic_has_iro typed edge ──
        edge_id = engine.link(topic_brain_slug, "topic_has_iro", iro_brain_slug)

        # ── 4. 寫 timeline_entries（brain DB；action_type='ingest' 表第一次建立）──
        payload = {
            "topic_slug": topic_slug, "iro_slug": iro_slug,
            "iro_type": iro_type_title, "iro_name": iro_name,
            "category": category, "time_horizon": time_horizon,
            "financial_magnitude": float(financial_magnitude),
            "tool": "link_topic_to_iro",
        }
        cur = engine.conn.execute(
            """
            INSERT INTO timeline_entries
                (page_id, action_type, source_ref, actor, payload)
            VALUES (?, 'ingest', ?, ?, ?)
            """,
            [
                brain_page_id, str(iro_md_path), actor,
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
            ],
        )
        engine.conn.commit()
        tl_id = int(cur.lastrowid or 0)

        return LinkedIroResult(
            iro_slug=iro_slug, page_file=str(iro_md_path),
            topic_slug=topic_slug, iro_type=iro_type_title,  # type: ignore[arg-type]
            brain_page_id=brain_page_id, edge_id=edge_id,
            timeline_entry_id=tl_id, created=True,
        )
    finally:
        try:
            engine.close()
        except Exception:  # pragma: no cover
            pass


def register(server) -> None:  # noqa: ANN001
    """Bind ``link_topic_to_iro`` to a FastMCP server instance."""
    server.tool()(link_topic_to_iro)


__all__ = [
    "LinkedIroResult", "IroCategory",
    "link_topic_to_iro", "register",
]
