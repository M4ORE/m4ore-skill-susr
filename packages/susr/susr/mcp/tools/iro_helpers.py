"""susr.mcp.tools.iro_helpers — file-IO / slug / md helpers for iro.py.

R4d + R4e refactor: extracted from ``iro.py`` so the main tool file stays
below CLAUDE.md §4.6.1 軟門檻（500 行）. Three concerns:

    1. Markdown frontmatter read/write (yaml-roundtrip).
    2. IRO slug generation — R4e idempotency 鍵改用 slug 自身（不再用
       ``(topic, type, name)`` hash 當 primary key），但仍保留 deterministic
       生成 helper 供 default 路徑使用。
    3. IRO entity body 排版（compiled_truth 區段）。

不引 brain engine — 純 IO + 字串 helper，方便單元測試與 reuse。
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Markdown IO
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def read_md(path: Path) -> tuple[dict, str]:
    """讀 markdown，回 (frontmatter dict, body)。檔案不存在 → ``({}, "")``."""
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


def write_md(path: Path, frontmatter: dict, body: str) -> None:
    """寫 markdown 並附 YAML frontmatter；父目錄不存在會自動建。"""
    import yaml  # type: ignore

    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
    path.write_text(f"---\n{serialized}---\n\n{body.lstrip()}", encoding="utf-8")


def now_iso() -> str:
    """Current UTC ISO-8601 timestamp (seconds resolution)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Slug generation (R4e — slug is the idempotency primary key)
# ---------------------------------------------------------------------------

# Reserve ascii-only kebab-case for the leading segment so the slug is URL safe
# and predictable in filesystem layout.  CJK / 標點 / 空白都會被去除或映射。
_SLUG_KEEP = re.compile(r"[^A-Za-z0-9]+")
_SLUG_TRIM = re.compile(r"^-+|-+$")
_SLUG_MAX_LEN = 40  # 控制總長 — 後續還有 8-char hash 後綴


def iro_short_hash(topic_slug: str, iro_type_title: str, iro_name: str) -> str:
    """deterministic 8-char sha256 hash — 純粹用來「補強 slug 唯一性」，
    不再做 idempotency primary key（R4e）。

    保留 ``(topic, type, name)`` 三因子是因為實務上同 IRO 名稱（如「碳費」）
    可能跨多個 topic / type 出現，加上前綴可避 slug 碰撞。
    """
    h = hashlib.sha256(
        f"{topic_slug}|{iro_type_title}|{iro_name}".encode("utf-8")
    )
    return h.hexdigest()[:8]


def _kebab_token(text: str) -> str:
    """中英混合字串 → ascii kebab-case token；中文先 ascii-fold 不到的部分剝除。

    1. NFKD 拆 + drop combining marks
    2. 非 ASCII 字元變空白
    3. 連續非英數變 hyphen
    4. 去頭尾 hyphen / lower / 截長
    """
    nfkd = unicodedata.normalize("NFKD", text or "")
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    ascii_only = ascii_only.encode("ascii", errors="ignore").decode("ascii")
    kebab = _SLUG_KEEP.sub("-", ascii_only).lower()
    kebab = _SLUG_TRIM.sub("", kebab)
    return kebab[:_SLUG_MAX_LEN]


def generate_iro_slug(
    topic_slug: str,
    iro_type: str,
    iro_name: str,
    *,
    explicit_slug: Optional[str] = None,
) -> str:
    """產生 IRO 自身的 slug（per-client unique）。

    R4e idempotency primary key 即此 slug — caller 同 slug 重複呼叫 ``link_topic_to_iro``
    一律 idempotent return existing；caller 不給 slug 才走自動生成。

    生成規則（``explicit_slug`` 為 None 時）：

        ``<topic_slug>-<iro_type_lower>-<sha8(topic|type|name)>``

    為何保留 topic_slug 前綴：
        - filesystem 結構 ``entities/topics/<topic>/iro/<slug>.md`` 直接看得出歸屬
        - 同 (topic, type, name) 三因子永遠映射到同 slug → 沿用 R3 idempotency 契約
        - 不同 topic 下同名 IRO（如「碳費」）不會碰撞 slug

    若 caller 給 ``explicit_slug``，先做 ascii-fold + sanitise 確保 URL safe；
    結果為空字串時 fallback 到自動生成路徑。
    """
    if explicit_slug:
        cleaned = _kebab_token(explicit_slug)
        if cleaned:
            return cleaned
    short_hash = iro_short_hash(topic_slug, iro_type.title(), iro_name)
    return f"{topic_slug}-{iro_type.lower()}-{short_hash}"


# ---------------------------------------------------------------------------
# Body builder
# ---------------------------------------------------------------------------


def build_iro_body(
    iro_slug: str,
    iro_type_title: str,
    iro_name: str,
    description: str,
    *,
    category: Optional[str],
    time_horizon: str,
    financial_magnitude: Optional[float],
    topic_slug: str,
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


__all__ = [
    "read_md",
    "write_md",
    "now_iso",
    "iro_short_hash",
    "generate_iro_slug",
    "build_iro_body",
]
