"""susr.mcp.tools.action — Phase 5 Action linkage tool（為 I1b 鋪路）。

R4 拆 I1 invariant 為 I1a + I1b 後，Phase 5 完成的契約是「每個 IRO 必有
Action」（v_i1b_iro_has_action）。本模組補上 ``link_iro_to_action`` — 對既有
IRO 建立 Action entity + ``iro_addressed_by`` typed edge + timeline_entry，
讓顧問可以在 Phase 5 把行動方案鏈到先前建好的 IRO。

仿 ``packages/susr/susr/mcp/tools/iro.py`` 結構（R3-B pattern）。雙寫到：
    (a) per-client markdown filesystem（``projects/<project_slug>/actions/<slug>.md``）
    (b) brain SQLite（Action entity page + iro_addressed_by edge + timeline_entry）

Idempotency：``action_slug = <iro_slug>-action-<sha8(name)>``。重複呼叫不複製。
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional  # noqa: F401 — kept for explicit type hints below

from pydantic import BaseModel

from susr.brain.timeline import append_dual
from susr.workspace import find_client_workspace

def _write_md(path: Path, frontmatter: dict, body: str) -> None:
    """寫 markdown + YAML frontmatter；父目錄不存在會自動建。"""
    import yaml  # type: ignore

    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
    path.write_text(f"---\n{serialized}---\n\n{body.lstrip()}", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _action_short_hash(iro_slug: str, action_name: str) -> str:
    """deterministic 8-char hash — 同 (iro, name) 永遠同 slug。"""
    h = hashlib.sha256(f"{iro_slug}|{action_name}".encode("utf-8"))
    return h.hexdigest()[:8]


def _slugify(name: str) -> str:
    """中英混合 → URL-safe slug 片段（保留中文，去空白與特殊字元）。"""
    s = re.sub(r"\s+", "-", name.strip())
    # 移除明顯不安全字元；保留中文 / 英數 / 連字號 / 底線
    s = re.sub(r"[^\w一-鿿-]+", "", s)
    return s[:60] or "action"


# ---------- Pydantic models ----------


class LinkedActionResult(BaseModel):
    """``link_iro_to_action`` 回傳結構。

    Attributes:
        action_slug: deterministic 產出的 Action slug（per-client unique）。
        page_file: Action entity 的 markdown 絕對路徑（filesystem source of truth）。
        iro_slug: 鏈結到的 IRO slug。
        action_name: 顧問輸入的人類可讀短名稱。
        brain_page_id: brain SQLite ``pages.id``。
        edge_id: ``links`` 表的 row id（``iro_addressed_by`` typed edge）。
        timeline_entry_id: brain ``timeline_entries`` 表的 row id。
        created: 此次呼叫是否真的新建（False → idempotent no-op）。
    """

    action_slug: str
    page_file: str
    iro_slug: str
    action_name: str
    brain_page_id: int
    edge_id: int
    timeline_entry_id: int
    created: bool


# ---------- helpers ----------


def _find_iro_brain_page(engine, iro_slug: str):
    """brain 內 IRO page 的 slug 可能是 ``<slug>`` 或 ``iros/<slug>``（兩種慣例並存）。

    回 ``(Page, brain_slug)`` 或 ``(None, None)``，供後續 ``engine.link()`` 用。
    """
    page = engine.get_page(iro_slug)
    if page is not None:
        return page, iro_slug
    prefixed = f"iros/{iro_slug}"
    page = engine.get_page(prefixed)
    if page is not None:
        return page, prefixed
    return None, None


def _build_action_body(
    action_slug: str,
    action_name: str,
    description: str,
    *,
    iro_slug: str,
    budget: Optional[float],
    progress_pct: Optional[float],
    owner_department: Optional[str],
    period: Optional[str],
) -> str:
    """組 Action entity markdown body（compiled_truth）。"""
    return (
        f"# Action: {action_name}\n\n"
        f"- IRO：`{iro_slug}`\n"
        f"- 負責部門：{owner_department or '—'}\n"
        f"- 期間：{period or '—'}\n"
        f"- 預算：{budget if budget is not None else '—'}\n"
        f"- 進度：{f'{progress_pct:.0%}' if progress_pct is not None else '—'}\n\n"
        f"## 描述\n\n{description.strip() or '_<待顧問補充>_'}\n"
    )


# ---------- main tool ----------


def link_iro_to_action(
    iro_slug: str,
    action_name: str,
    description: str,
    *,
    client_slug: str,
    project_slug: Optional[str] = None,
    budget: Optional[float] = None,
    progress_pct: Optional[float] = None,
    owner_department: Optional[str] = None,
    period: Optional[str] = None,
    actor: str = "consultant",
) -> LinkedActionResult:
    """Phase 5 工具 — 對既有 IRO 建立 Action entity + ``iro_addressed_by`` edge。

    R4 拆 I1 invariant 為 I1a + I1b 後，本工具負責關閉 I1b（IRO → Action）。

    雙寫保證 filesystem + brain DB 同步：
        - filesystem：``projects/<project_slug>/actions/<action_slug>.md``
          （若 ``project_slug`` 為 None，預設用 current year ``YYYY-sr``）
        - brain DB：``action`` entity page + ``iro_addressed_by`` typed edge
          + timeline_entry（action_type='ingest'）

    Idempotency：``action_slug = <iro_slug>-action-<sha8(name)>``；同 (iro, name)
    重複呼叫不複製 — 回既有 Action 與 ``created=False``。

    Args:
        iro_slug: 已存在的 IRO slug（必須先 ingest 或先 ``link_topic_to_iro``）。
        action_name: 人類可讀短名稱，例如「2025 能耗減量計畫」、「採購流程升級」。
        description: 顧問描述（可後續再 enrich）；空字串 → 留 placeholder。
        client_slug: per-client workspace 目錄名稱（keyword-only）。
        project_slug: 寫入的 project 目錄（None → ``YYYY-sr`` 預設）。
        budget: 預算（單位由顧問語境決定）。
        progress_pct: 進度比例 [0..1]。
        owner_department: 主責部門（例如 'ESG' / '採購' / 'IT'）。
        period: 期間（例如 '2025' / '2025Q3-2026Q2'）。
        actor: 寫入 timeline 的 actor 欄位。

    Returns:
        ``LinkedActionResult`` — 含 action_slug、page_file、brain_page_id、
        edge_id、timeline_entry_id、created。

    Raises:
        FileNotFoundError: client workspace 不存在。
        LookupError: IRO 沒在 brain DB 裡（需先 ``link_topic_to_iro`` 或 ingest）。
    """
    # 預設 project_slug = <current_year>-sr
    if not project_slug:
        project_slug = f"{datetime.now().year}-sr"

    client_path = find_client_workspace(client_slug)

    # ── lazy import — engine import 拉 sqlite3，cold-start 維持輕量 ──
    from susr.brain.engine import BrainEngine

    db_path = client_path / ".susr" / "db.sqlite"
    engine = BrainEngine.open(str(db_path), load_sqlite_vec=False)
    try:
        iro_page, iro_brain_slug = _find_iro_brain_page(engine, iro_slug)
        if iro_page is None:
            raise LookupError(
                f"iro {iro_slug!r} not found in brain DB at {db_path}; "
                "create it first via link_topic_to_iro (or ingest the IRO page)"
            )

        # 用 iro 的「實際 slug 後綴」(去掉 'iros/' prefix) 算 hash — 讓兩種 slug
        # 慣例（'iros/<x>' vs '<x>'）得到同樣 deterministic hash。
        iro_slug_short = iro_slug.removeprefix("iros/")
        short_hash = _action_short_hash(iro_slug_short, action_name)
        action_slug = f"{iro_slug_short}-action-{_slugify(action_name)[:20]}-{short_hash}"
        action_brain_slug = f"actions/{action_slug}"
        action_md_path = (
            client_path / "projects" / project_slug / "actions" / f"{action_slug}.md"
        )

        # Idempotency check — brain DB 是 ground truth。
        existing = engine.get_page(action_brain_slug)
        if existing is not None:
            row = engine.conn.execute(
                "SELECT id FROM links WHERE src_page_id = ? AND dst_page_id = ? "
                "AND edge_type = 'iro_addressed_by'",
                [iro_page.id, existing.id],
            ).fetchone()
            existing_edge_id = int(row[0]) if row else 0
            tl_row = engine.conn.execute(
                "SELECT id FROM timeline_entries WHERE page_id = ? "
                "ORDER BY id DESC LIMIT 1",
                [existing.id],
            ).fetchone()
            existing_tl_id = int(tl_row[0]) if tl_row else 0
            return LinkedActionResult(
                action_slug=action_slug,
                page_file=str(action_md_path),
                iro_slug=iro_slug_short,
                action_name=action_name,
                brain_page_id=existing.id,
                edge_id=existing_edge_id,
                timeline_entry_id=existing_tl_id,
                created=False,
            )

        # ── 1. 組 Action markdown body（filesystem source of truth） ──
        # ActionFrontmatter 需要：chapter_slug / iro_addressed / budget / progress_pct
        # / owner_department / period（全 required）— 給 fallback 預設值避 schema fail。
        # chapter_slug 為強制欄位，Phase 5 規劃通常 chapter 已存在；
        # 沒指定時用 'ch-pending'，後續 Phase 6 顧問會 reassign。
        chapter_slug_default = "ch-pending"
        action_fm = {
            "slug": action_slug,
            "chapter_slug": chapter_slug_default,
            "iro_addressed": [iro_slug_short],
            "budget": float(budget) if budget is not None else 0.0,
            "progress_pct": float(progress_pct) if progress_pct is not None else 0.0,
            "owner_department": owner_department or "TBD",
            "period": period or f"{datetime.now().year}",
            "action_name": action_name,
            "project_slug": project_slug,
            "created_at": _now(),
            "created_by": actor,
        }
        body = _build_action_body(
            action_slug, action_name, description,
            iro_slug=iro_slug_short, budget=budget, progress_pct=progress_pct,
            owner_department=owner_department, period=period,
        )

        # ── 2. 寫 brain DB（action entity page）— 須在 timeline append_dual 之前
        # 否則 page_slug lookup 拿不到 page.id。──
        brain_fm = {
            "slug": action_slug,
            "chapter_slug": chapter_slug_default,
            "iro_addressed": [iro_slug_short],
            "budget": float(budget) if budget is not None else 0.0,
            "progress_pct": float(progress_pct) if progress_pct is not None else 0.0,
            "owner_department": owner_department or "TBD",
            "period": period or f"{datetime.now().year}",
        }
        brain_page_id = engine.put_page(
            slug=action_brain_slug,
            entity_type="action",
            title=f"Action: {action_name}",
            compiled_truth=body,
            file_path=str(action_md_path),
            project_slug=project_slug,
            frontmatter=brain_fm,
        )

        # ── 3. 寫 iro_addressed_by typed edge ──
        edge_id = engine.link(iro_brain_slug, "iro_addressed_by", action_brain_slug)

        # ── 4. 統一寫 timeline（R4d append_dual — DB + MD body 同 ts/actor/payload） ──
        payload = {
            "iro_slug": iro_slug_short,
            "action_slug": action_slug,
            "action_name": action_name,
            "project_slug": project_slug,
            "budget": budget,
            "progress_pct": progress_pct,
            "owner_department": owner_department,
            "period": period,
            "tool": "link_iro_to_action",
        }
        tl_id, body = append_dual(
            engine, action_brain_slug, "ingest", payload, actor,
            body=body, source_ref=str(action_md_path),
        )

        # ── 5. 落地 markdown（body 已含 timeline 行）──
        _write_md(action_md_path, action_fm, body)

        return LinkedActionResult(
            action_slug=action_slug,
            page_file=str(action_md_path),
            iro_slug=iro_slug_short,
            action_name=action_name,
            brain_page_id=brain_page_id,
            edge_id=edge_id,
            timeline_entry_id=tl_id,
            created=True,
        )
    finally:
        try:
            engine.close()
        except Exception:  # pragma: no cover
            pass


def register(server) -> None:  # noqa: ANN001
    """Bind ``link_iro_to_action`` to a FastMCP server instance."""
    server.tool()(link_iro_to_action)


__all__ = [
    "LinkedActionResult",
    "link_iro_to_action",
    "register",
]
