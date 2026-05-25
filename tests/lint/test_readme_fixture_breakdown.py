"""Layer 1 lint：README §MVP 驗收成果『Lealea pages ingested』breakdown 表 vs
``examples/lealea-5364/entities/*/`` 實際 .md 數量。

設計原則
========

README 內這一行（line ~156）：

    | Lealea pages ingested | 95（28 topics + 14 IROs + 14 actions + 5 chapters
      + 14 frameworks + 7 stakeholders + 8 KPIs + 3 targets + 2 governance） |

是顧問 demo 時最會 quote 的「fixture 規模」訊號。R6/R7+ Agent C 補食安 / 隱私 /
原住民 target 後，targets 數字會從 3 變成 6，README 通常會滯後。

容差策略
========

* **±2 容差**：顧問補 demo 檔案不需要每次都同步更新 README — 比 ``test_readme_numbers``
  的 ±0 嚴格度低。
* 抓 ``XX topics`` / ``XX IROs`` / ``XX actions`` / ``XX chapters`` /
  ``XX frameworks`` / ``XX stakeholders`` / ``XX KPIs`` / ``XX targets`` /
  ``XX governance`` 9 個 token；某個 token README 沒寫就跳過該行（不算 drift）。
* drift > 2 → fail with **per-token diff**（顧問可一眼看出哪個 entity 補了 / 縮了）。
* ``examples/lealea-5364/entities/<bucket>/`` 不存在或為空 → 該 bucket 不計（不
  fail，讓 R8 之後 entity bucket 結構演化彈性）。

註：本檔不檢查 README ``Lealea pages ingested`` 總數（95）與 breakdown 加總是否
一致 — 那是 README 內部一致性，由 ``test_walkthrough_r6_numbers_consistent``
類的 source-of-truth 檢查負責。

與 ``test_readme_numbers`` 的關係
==================================

* ``test_readme_numbers.py``：結構不變量數字（entity types 17 / edges 19 /
  invariants 6 / MCP tools N）— **±0**，drift 即 bug
* ``test_readme_fixture_breakdown.py``（本檔）：fixture 案例數字 — **±2**，
  允許 demo 補檔短暫滯後

兩檔互補，不重疊。
"""

from __future__ import annotations

import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Token map — README label ↔ entities/<bucket>/ 目錄名（單複數對應）
# ---------------------------------------------------------------------------

# (README_token_regex_chunk, entities_bucket_dir_name)
# regex_chunk 是「N (?:中英文 token)」的單側，會由 _scan_readme 拼進完整 pattern。
_BREAKDOWN_TOKENS: list[tuple[str, str]] = [
    (r"topics?", "topics"),
    (r"IROs?", "iros"),
    (r"actions?", "actions"),
    (r"chapters?", "chapters"),
    (r"frameworks?", "frameworks"),
    (r"stakeholders?", "stakeholders"),
    (r"KPIs?", "kpis"),
    (r"targets?", "targets"),
    (r"governance", "governance"),
]

# README breakdown 容差：顧問 demo 補 1-2 個檔不需要馬上同步 README。
TOLERANCE = 2


def _scan_readme(readme_text: str) -> dict[str, int]:
    """從 README 內抓 ``N topics`` / ``N IROs`` / ... 等 token → bucket count。

    對每個 token 抓**第一個** match（README 在 §架構概覽 / §MVP 驗收 / line 156
    可能各出現一次，line 156 是 source-of-truth；我們抓第一個 match 跟它對齊）。

    若 README 沒寫某 token，該 bucket 不在 dict 內 → caller 跳過（不算 drift）。
    """
    out: dict[str, int] = {}
    # 集中在 line 156 區段：抓 "Lealea pages ingested" 同一表格列
    # 但 regex 不限定 — 找全文第一個 match 就回，避免「Phase 6 payload chapters 5」
    # 這種其他段落的干擾
    # 策略：找「Lealea pages ingested」行，截取它後面的內容到下一個 `|`，只在這
    # 片段內 scan。
    line_match = re.search(
        r"Lealea\s+pages\s+ingested[^|]*\|([^|]+)\|",
        readme_text,
        flags=re.IGNORECASE,
    )
    if not line_match:
        return out
    snippet = line_match.group(1)

    for token_re, bucket in _BREAKDOWN_TOKENS:
        # "28 topics" / "14 IROs" / "2 governance"
        m = re.search(rf"(\d+)\s+{token_re}\b", snippet)
        if m:
            out[bucket] = int(m.group(1))
    return out


def _count_entity_files(entities_root: Path) -> dict[str, int]:
    """掃 ``examples/lealea-5364/entities/<bucket>/*.md`` 數量。

    *.md 過濾掉 ``__pycache__`` / dot files / ``README.md`` / ``_skeleton.md``
    （SP1-004 skeleton placeholder，非真實 chapter）。

    特例：``chapters`` 不在 ``entities/`` 而在 ``projects/<year>-sr/chapters/``
    — Option C 結構把 chapter 視為 project 交付，不是 client 常駐 entity。
    我們在 caller 端對這個 bucket 特殊處理。
    """
    out: dict[str, int] = {}
    if not entities_root.exists():
        return out
    for sub in sorted(entities_root.iterdir()):
        if not sub.is_dir():
            continue
        bucket = sub.name
        files = [
            p for p in sub.glob("*.md")
            if not p.name.startswith(".")
            and not p.name.startswith("_")
            and p.name.lower() != "readme.md"
        ]
        out[bucket] = len(files)
    return out


def _count_project_chapters(projects_root: Path) -> int:
    """掃 ``projects/<year>-sr/chapters/*.md`` 數量（Option C 結構特例）。

    chapters 是 project 交付，不是常駐 entity，跨所有 project 加總。
    過濾 ``_skeleton.md`` / ``_*.md`` placeholder。
    """
    if not projects_root.exists():
        return 0
    total = 0
    for project_dir in projects_root.iterdir():
        if not project_dir.is_dir():
            continue
        chapters_dir = project_dir / "chapters"
        if not chapters_dir.exists():
            continue
        for p in chapters_dir.glob("*.md"):
            if p.name.startswith(".") or p.name.startswith("_"):
                continue
            if p.name.lower() == "readme.md":
                continue
            total += 1
    return total


def test_readme_lealea_fixture_breakdown(REPO_ROOT):
    """README 內 ``Lealea pages ingested`` breakdown 數字應對齊
    ``examples/lealea-5364/entities/<bucket>/`` .md 檔案數（容差 ±2）。

    Lint 抓「README 宣稱 N entity 但實際 ≠ N ± 2」這類顧問 demo drift。
    """
    readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    if readme_text.startswith("﻿"):
        readme_text = readme_text.lstrip("﻿")
    readme_text = readme_text.replace("\r\n", "\n").replace("\r", "\n")

    readme_counts = _scan_readme(readme_text)
    assert readme_counts, (
        "README 未抓到任何 'Lealea pages ingested' breakdown token；"
        "regex 可能要調整，或該行已被刪 / 改成不同 label。"
    )

    entities_root = REPO_ROOT / "examples" / "lealea-5364" / "entities"
    actual_counts = _count_entity_files(entities_root)
    assert actual_counts, (
        f"沒掃到 entities buckets at {entities_root}；"
        "fixture 可能未建好或路徑改變。"
    )

    # 特例：chapters 在 projects/<year>-sr/chapters/，不在 entities/
    projects_root = REPO_ROOT / "examples" / "lealea-5364" / "projects"
    actual_counts["chapters"] = _count_project_chapters(projects_root)

    drifts: list[str] = []
    for bucket, claimed in readme_counts.items():
        actual = actual_counts.get(bucket, 0)
        if actual == 0:
            # bucket 在 README 有提到但 entities/<bucket>/ 不存在或空 — 視為
            # 結構性問題（非 demo drift），但我們仍 fail 以提醒
            drifts.append(
                f"  - {bucket}: README claims {claimed} but entities/{bucket}/ "
                f"is missing or empty (actual=0)"
            )
            continue
        if abs(claimed - actual) > TOLERANCE:
            drifts.append(
                f"  - {bucket}: README claims {claimed}, actual {actual} "
                f"(drift={actual - claimed:+d}, tolerance ±{TOLERANCE})"
            )

    assert not drifts, (
        "README 內 `Lealea pages ingested` breakdown 與實際 fixture 數量 drift "
        f"超過 ±{TOLERANCE}（顧問補檔不該超過此容差就忘了同步 README）:\n"
        + "\n".join(drifts)
        + "\n\n請更新 README §MVP 驗收成果『Lealea pages ingested』行。"
    )


def test_readme_lealea_breakdown_total_consistent(REPO_ROOT):
    """README 宣稱的 total（如 ``95``） 應約等於 breakdown 各 token 加總（容差 ±2）。

    這是 README 內部一致性檢查（不依賴 fixture）— 抓「文字 paraphrase 時忘了
    重算總和」這類人為打錯。
    """
    readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    if readme_text.startswith("﻿"):
        readme_text = readme_text.lstrip("﻿")
    readme_text = readme_text.replace("\r\n", "\n").replace("\r", "\n")

    # 抓「Lealea pages ingested | N（M1 topics + M2 IROs + ...）」
    line_match = re.search(
        r"Lealea\s+pages\s+ingested\s*\|\s*(\d+)\s*[（(]([^)）|]+)[)）]",
        readme_text,
        flags=re.IGNORECASE,
    )
    if not line_match:
        # 若 README 改寫成不含 total 格式（如「N pages」純文字），略過此 test
        return

    claimed_total = int(line_match.group(1))
    breakdown_text = line_match.group(2)

    # 從 breakdown 內抓所有 "N <token>" 加總
    parts = re.findall(r"(\d+)\s+\S+", breakdown_text)
    computed = sum(int(n) for n in parts)

    assert abs(claimed_total - computed) <= TOLERANCE, (
        f"README 宣稱 total {claimed_total} 與 breakdown 加總 {computed} 不一致 "
        f"（差 {computed - claimed_total:+d}，容差 ±{TOLERANCE}）。"
        f"breakdown={breakdown_text!r}。請檢查 README 是否漏算或重複算某 bucket。"
    )
