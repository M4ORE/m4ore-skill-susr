"""susr.mcp.tools.workspace — Workspace lifecycle + KB MCP tools.

Per CLAUDE.md §8 decision 4, these replace `susr init / doctor / kb-update`
CLI subcommands we deliberately did not ship.

Tools (spec §6.3 + §6.4):
    create_client_workspace   — git init + DDL + frontmatter + shared/ snapshot
    health_check              — sqlite-vec / DDL / API key / embed sanity
    update_shared_kb          — snapshot copy + diff + audit
    promote_to_consultant_kb  — single-direction anonymize gate (KB信息流)
    read_consultant_kb        — open-scope read of the consultant KB
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from susr import workspace as ws_lib
from susr.shared_kb.snapshot import apply_diff, diff_against


def _consultant_kb_root(override: Optional[str] = None) -> Path:
    return Path(override).expanduser() if override else Path.home() / ".susr" / "consultant-kb"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_client_workspace(
    name: str,
    legal_name: str,
    industry: str,
    standards: list[str],
    boundary: Literal["合併", "營運控制", "股權法"],
    reporting_period: str,
    embedding_policy: Literal["local", "cloud", "twostage"] = "twostage",
    pii_classification: Literal["high", "medium", "low"] = "medium",
) -> dict:
    """Create a new client workspace under SUSR_WORKSPACE_ROOT/<name>/."""
    return ws_lib.create_client_workspace(
        ws_lib.workspace_root(),
        name=name, legal_name=legal_name, industry=industry, standards=standards,
        boundary=boundary, reporting_period=reporting_period,
        embedding_policy=embedding_policy, pii_classification=pii_classification,
    )


def health_check(client_slug: Optional[str] = None) -> dict:
    """Run env + optional client workspace checks (spec §6.3)."""
    return ws_lib.health_checks(client_slug)


def update_shared_kb(client_slug: str, accept_changes: bool = False) -> dict:
    """Diff or apply a fresh shared_kb snapshot to a client repo."""
    client_path = ws_lib.find_client_workspace(client_slug)
    diff = diff_against(client_path)
    if not accept_changes:
        return {"dry_run": True, "diff": diff, "hint": "rerun with accept_changes=True to apply"}
    applied = apply_diff(client_path)
    client_md = client_path / "_client.md"
    if client_md.exists():
        text = client_md.read_text(encoding="utf-8")
        note = (
            f"\n- [{_now()}] action=ingest actor=susr payload="
            f"{json.dumps({'shared_kb_applied': applied['applied'], 'version': applied['source_version']}, ensure_ascii=False)}\n"
        )
        if "## Timeline" not in text:
            text = text.rstrip() + "\n\n---\n\n## Timeline\n\n"
        client_md.write_text(text + note, encoding="utf-8")
    return {"dry_run": False, "applied": applied, "diff_before": diff}


# ---------- promote_to_consultant_kb (single-direction gate) ----------


_PII_PATTERNS = [
    (re.compile(r"\b09\d{2}[- ]?\d{3}[- ]?\d{3}\b"), "[REDACTED-TW-MOBILE]"),
    (re.compile(r"\b[A-Z][12]\d{8}\b"), "[REDACTED-TW-ID]"),
    (re.compile(r"\b\d{8}\b"), "[REDACTED-NUMBER]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[REDACTED-EMAIL]"),
]


def _anonymize_text(text: str, strategy: str) -> str:
    out = text
    if strategy in ("redact-pii", "both"):
        for pat, repl in _PII_PATTERNS:
            out = pat.sub(repl, out)
    if strategy in ("generalize-numbers", "both"):
        out = re.sub(r"\b\d{4,}\b", lambda m: str(int(round(int(m.group(0)), -2))) + "*", out)
    return out


def _expected_token(client_slug: str, page_slugs: list[str], strategy: str, reviewer: str) -> str:
    h = hashlib.sha256()
    for part in (client_slug, ",".join(sorted(page_slugs)), strategy, reviewer):
        h.update(part.encode("utf-8"))
        h.update(b"|")
    return h.hexdigest()[:16]


def _resolve_page(client_path: Path, slug: str) -> Optional[Path]:
    """Resolve `topics/E1` etc to client_path/entities/<slug>.md, or absolute fallback."""
    for cand in (client_path / "entities" / f"{slug}.md", client_path / f"{slug}.md"):
        if cand.exists():
            return cand
    return None


def promote_to_consultant_kb(
    client_slug: str,
    client_page_slugs: list[str],
    anonymize_strategy: Literal["redact-pii", "generalize-numbers", "both"],
    reviewer: str,
    confirm_token: str = "",
    target_kb_path: Optional[str] = None,
) -> dict:
    """Single-direction gate (CLAUDE.md §8 KB信息流): client → consultant-kb.

    Two-step confirmation (no real MCP elicitation needed for v0):
        1. confirm_token=""  → returns {needs_confirm: True, confirm_token: <hash>}
        2. consultant approves; caller re-invokes with that token to apply.
    """
    expected = _expected_token(client_slug, list(client_page_slugs), anonymize_strategy, reviewer)
    kb_root = _consultant_kb_root(target_kb_path)
    client_path = ws_lib.find_client_workspace(client_slug)

    if confirm_token != expected:
        preview = [
            {"slug": slug, "found": (p := _resolve_page(client_path, slug)) is not None,
             "path": str(p) if p else None}
            for slug in client_page_slugs
        ]
        return {
            "needs_confirm": True, "confirm_token": expected, "preview": preview,
            "anonymize_strategy": anonymize_strategy, "target_kb_root": str(kb_root),
            "message": "review the listed pages then re-invoke with the confirm_token above",
        }

    kb_root.mkdir(parents=True, exist_ok=True)
    promo_dir = kb_root / "from-clients" / client_slug
    promo_dir.mkdir(parents=True, exist_ok=True)
    audit_log = kb_root / "audit.jsonl"

    promoted: list[dict] = []
    for slug in client_page_slugs:
        src = _resolve_page(client_path, slug)
        if src is None:
            continue
        anon = _anonymize_text(src.read_text(encoding="utf-8"), anonymize_strategy)
        dst = promo_dir / f"{slug.replace('/', '_')}.md"
        dst.write_text(anon, encoding="utf-8")
        promoted.append({"slug": slug, "src": str(src), "dst": str(dst)})

    audit_entry = {
        "ts": _now(), "client_slug": client_slug, "reviewer": reviewer,
        "anonymize_strategy": anonymize_strategy, "promoted": promoted,
    }
    with audit_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")

    client_md = client_path / "_client.md"
    if client_md.exists():
        line = (
            f"\n- [{_now()}] action=comment actor={reviewer} payload="
            f"{json.dumps({'promoted_to_kb': [p['slug'] for p in promoted], 'strategy': anonymize_strategy}, ensure_ascii=False)}\n"
        )
        text = client_md.read_text(encoding="utf-8")
        if "## Timeline" not in text:
            text = text.rstrip() + "\n\n---\n\n## Timeline\n\n"
        client_md.write_text(text + line, encoding="utf-8")

    return {"ok": True, "audit_entry": audit_entry, "audit_log_path": str(audit_log)}


def read_consultant_kb(
    query: str,
    framework_filter: Optional[list[str]] = None,
    top_k: int = 10,
    target_kb_path: Optional[str] = None,
) -> list[dict]:
    """Plain substring + filename retrieval over the consultant KB.

    Per spec §6.4 this is intentionally read-only.  No embedding model
    needed at v0 — the KB is small (methodology / anonymised cases /
    framework crib sheets).  Brain-DB indexing arrives in Step 2.
    """
    root = _consultant_kb_root(target_kb_path)
    if not root.exists():
        return []
    q = query.lower()
    hits: list[tuple[int, dict]] = []
    for md in root.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:  # pragma: no cover
            continue
        score = text.lower().count(q)
        if score == 0 and q not in md.name.lower():
            continue
        idx = text.lower().find(q)
        snippet = text[max(0, idx - 80) : idx + 200] if idx >= 0 else text[:200]
        hits.append((score, {"path": str(md.relative_to(root)), "score": score, "snippet": snippet}))
    hits.sort(key=lambda kv: -kv[0])
    return [h for _, h in hits[:top_k]]


def register(server) -> None:  # noqa: ANN001
    """Bind the 5 workspace / KB tools to a FastMCP server instance."""
    server.tool()(create_client_workspace)
    server.tool()(health_check)
    server.tool()(update_shared_kb)
    server.tool()(promote_to_consultant_kb)
    server.tool()(read_consultant_kb)


__all__ = [
    "create_client_workspace", "health_check", "update_shared_kb",
    "promote_to_consultant_kb", "read_consultant_kb", "register",
]
