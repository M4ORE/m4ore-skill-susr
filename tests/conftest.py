"""susr 測試共用 fixtures 與 helpers。

本檔提供五層測試（CLAUDE.md §6.2）所需的共用路徑常數與小工具。
所有 fixture 採 session scope —— 因為 susr 是 markdown-first，
讀檔與路徑常數於整個 test session 內不變，重複初始化沒意義。

設計選擇：
- 路徑一律走 ``pathlib.Path``，避免 Windows 反斜線 / POSIX 斜線分歧
- ``REPO_ROOT`` 透過 ``__file__`` 解析，不依賴 cwd —— pytest 可從任意目錄啟動
- ``read_md`` 統一吃 BOM / CRLF —— Windows 編輯器（VSCode / Notepad）
  與 Linux CI 之間最常見的 ``\\ufeff`` / ``\\r\\n`` 差異一次處理掉
- frontmatter 解析用 PyYAML，不自捲，避免 multi-line 值的 edge case
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml


# ---------------------------------------------------------------------------
# 路徑 fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def REPO_ROOT() -> Path:
    """susr repo 的絕對根目錄。

    從本檔位置往上推導，與 cwd / pytest 啟動目錄無關。
    """
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def examples_dir(REPO_ROOT: Path) -> Path:
    """端到端試做案例目錄，目前主要為 ``examples/lealea-5364/``。

    Layer 2 scenario 測試會把此目錄當 fixture 來源。
    """
    return REPO_ROOT / "examples" / "lealea-5364"


@pytest.fixture(scope="session")
def skill_dir(REPO_ROOT: Path) -> Path:
    """智能層原型 skill 目錄（``skills/sustainability-report/``）。

    內含 ``SKILL.md``（8-Phase SOP）與 ``references/`` 領域知識庫。
    """
    return REPO_ROOT / "skills" / "sustainability-report"


@pytest.fixture(scope="session")
def references_dir(skill_dir: Path) -> Path:
    """Skill 的 references 知識庫目錄。

    Layer 1 lint 測試會在這裡跑 frontmatter / 詞彙 / 結構檢查。
    """
    return skill_dir / "references"


# ---------------------------------------------------------------------------
# Helpers（非 fixture，給測試直接 import 用）
# ---------------------------------------------------------------------------


def read_md(path: Path | str) -> str:
    """讀 markdown 檔，回傳乾淨字串。

    - 自動以 UTF-8 解碼
    - 去掉 BOM（``\\ufeff``）—— Windows 編輯器很愛偷加
    - 將 CRLF 統一為 LF —— 讓正則 / 字串斷言不會被換行差異咬到

    Args:
        path: 檔案絕對路徑（``Path`` 或 ``str`` 皆可）。

    Returns:
        正規化後的檔案內容字串。

    Raises:
        FileNotFoundError: 路徑不存在時 raise，由呼叫端決定要 skip 還是 fail。
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if text.startswith("﻿"):
        text = text.lstrip("﻿")
    return text.replace("\r\n", "\n").replace("\r", "\n")


_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<body>.*?)\n---\s*(?:\n|\Z)",
    re.DOTALL,
)


def parse_frontmatter(text: str) -> dict:
    """從 markdown 內容抽出 YAML frontmatter，回 dict。

    - 接受 ``read_md`` 已正規化過的字串（LF 結尾）
    - 沒有 frontmatter 區塊回 ``{}``（不 raise，讓 lint 測試可決定怎麼判定）
    - frontmatter 解析失敗（不合法 YAML）會讓 ``yaml.safe_load`` raise，由呼叫端處理

    Args:
        text: markdown 全文字串。

    Returns:
        Frontmatter 鍵值對；非 dict（如純 list / scalar）會被包成 ``{}`` 視為沒有 frontmatter。
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    body = match.group("body")
    parsed = yaml.safe_load(body)
    if not isinstance(parsed, dict):
        return {}
    return parsed


# ---------------------------------------------------------------------------
# Fixture wrappers（讓 helpers 也能以 pytest fixture 風格注入）
# ---------------------------------------------------------------------------
# 兩種使用方式都支援：
#   from conftest import read_md            # module function 風格
#   def test_x(read_md): ...                # fixture 注入風格
# 內容是同一個 callable，session-scoped 避免重複包裝開銷。


@pytest.fixture(scope="session", name="read_md")
def _read_md_fixture():
    """以 fixture 形式暴露 ``read_md`` 函式，供 pytest 參數注入使用。"""
    return read_md


@pytest.fixture(scope="session", name="parse_frontmatter")
def _parse_frontmatter_fixture():
    """以 fixture 形式暴露 ``parse_frontmatter`` 函式。"""
    return parse_frontmatter
