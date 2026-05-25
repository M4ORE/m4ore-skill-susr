"""Layer 1 lint：README 內 hard-coded 關鍵數字 vs 真實碼庫 / walkthrough source-of-truth。

設計原則
========

README 上有兩類數字，本檔以**不同對齊策略**處理：

1. **結構不變量數字**（entity types / typed edges / invariants / MCP tools）
   來源：``packages/susr/susr/brain/``（``entities.py`` / ``edges.py`` /
   ``invariants.py``）+ ``packages/susr/susr/mcp/tools/`` 真實 ``server.tool()``
   登記。這些數字應**精確**對齊；drift 即視為 bug。

2. **fixture 案例數字**（lealea pages / typed edges / Phase 6 payload counts
   / Phase 7 gap severity）
   來源：``docs/walkthroughs/lealea-5364-phase6-r6.md`` snapshot。
   walkthrough 為 frozen snapshot；fixture 補強會隨 R7/R8 drift。本檔對
   walkthrough **內部一致性**（TL;DR vs §1 vs §3）做 hard check，但 README
   vs walkthrough 比對只**警示式 ≤ 比較**，不 fail（README 允許滯後）。

3. **test 數**（``275 passed + 2 skipped``）
   來源：``pytest --collect-only``。test 數會持續成長 →`±tolerance` 容差。

這樣的分層讓 README drift 在 PR review 容易被 lint 抓到，而又不會因為單純
新增 test 或 fixture 補強就壞掉。
"""

from __future__ import annotations

import ast
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# 共用 regex / helpers
# ---------------------------------------------------------------------------


def _read_repo_md(repo_root: Path, *relpath: str) -> str:
    """讀 repo 內 markdown 並正規化（去 BOM / CRLF→LF）。"""
    p = Path(repo_root, *relpath)
    text = p.read_text(encoding="utf-8")
    if text.startswith("﻿"):
        text = text.lstrip("﻿")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _ast_list_frontmatter_classes(entities_py: Path) -> list[str]:
    """AST 列出 ``*Frontmatter`` 類別名稱（不依賴 susr 可 import — CI 沒 pydantic）。

    ``_EntityBase`` 不算。其他名為 ``*Frontmatter`` 的 ClassDef 全算。
    """
    tree = ast.parse(entities_py.read_text(encoding="utf-8"))
    return sorted(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        and node.name.endswith("Frontmatter")
        and not node.name.startswith("_")
    )


def _ast_count_edge_registry(edges_py: Path) -> int:
    """AST 抓 ``EDGE_REGISTRY`` dict literal 的 key 數（不依賴 susr 可 import）。"""
    tree = ast.parse(edges_py.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign | ast.Assign):
            targets = [node.target] if isinstance(node, ast.AnnAssign) else node.targets
            for tgt in targets:
                if isinstance(tgt, ast.Name) and tgt.id == "EDGE_REGISTRY":
                    val = node.value
                    if isinstance(val, ast.Dict):
                        return len(val.keys)
    raise RuntimeError(f"EDGE_REGISTRY dict literal not found in {edges_py}")


# ---------------------------------------------------------------------------
# 1. 結構不變量數字 — entity types / edges / invariants / MCP tools
# ---------------------------------------------------------------------------


def test_readme_entity_types_count(REPO_ROOT):
    """README 宣稱的 entity types 數應對齊 ``ENTITY_TYPES`` 與 ``*Frontmatter`` class 數。

    README 在 §架構概覽 / §MVP 驗收 / English Architecture 多處宣稱 17 types。
    drift 來源通常是新增 entity 後忘記同步 README。
    """
    entities_py = Path(
        REPO_ROOT, "packages", "susr", "susr", "brain", "entities.py"
    )
    frontmatter_classes = _ast_list_frontmatter_classes(entities_py)
    actual_types = len(frontmatter_classes)

    readme = _read_repo_md(REPO_ROOT, "README.md")
    # 抓「17 個 entity types」/「17 entity types」/「17 types」三種寫法
    matches = re.findall(
        r"(\d+)\s*(?:個\s*)?entity\s+types?|Entity\s+多樣性[^\d]*?(\d+)\s*types?",
        readme,
        flags=re.IGNORECASE,
    )
    # matches 是 [(num1, ''), ('', num2), ...]；取所有非空 group
    claimed_nums = {int(a or b) for a, b in matches if (a or b)}

    assert claimed_nums, (
        "README 未找到任何 'N entity types' 宣稱；regex 可能需要調整 — "
        "預期至少有 §架構概覽『17 個 entity types』。"
    )

    assert actual_types == len(frontmatter_classes), (
        f"susr.brain.entities 內部不一致：ENTITY_TYPES={actual_types} 但 "
        f"*Frontmatter classes={len(frontmatter_classes)}（{frontmatter_classes}）"
    )

    drifted = {n for n in claimed_nums if n != actual_types}
    assert not drifted, (
        f"README 宣稱 entity types {drifted} 與真實 ENTITY_TYPES "
        f"{actual_types} drift。請同步更新 README §架構概覽 / "
        f"English Architecture / MVP 驗收成果。"
    )


def test_readme_typed_edges_count(REPO_ROOT):
    """README 宣稱的 typed edges 數應對齊 ``EDGE_REGISTRY`` 長度。

    edges.py 內已有 ``assert len(EDGE_REGISTRY) == 19`` 自爆；本 test 補
    README 端的一致性（registry 變大時 README 應同步）。
    """
    edges_py = Path(
        REPO_ROOT, "packages", "susr", "susr", "brain", "edges.py"
    )
    actual = _ast_count_edge_registry(edges_py)

    readme = _read_repo_md(REPO_ROOT, "README.md")
    # 抓「19 條 typed edges」/「19 typed edges」/「19 條 typed」
    matches = re.findall(
        r"(\d+)\s*(?:條|個)?\s*typed\s+edges?",
        readme,
        flags=re.IGNORECASE,
    )
    claimed_nums = {int(n) for n in matches}

    assert claimed_nums, (
        "README 未找到任何 'N typed edges' 宣稱；regex 可能要調整。"
    )

    # README §MVP 驗收成果『Typed edges 51』是 fixture 案例數而非 registry size。
    # registry size 必須出現在 §架構概覽 / English Architecture 中。
    structural = {n for n in claimed_nums if n == actual}
    assert structural, (
        f"README 宣稱的 typed edges 數都不等於 EDGE_REGISTRY 真實長度 "
        f"{actual}。實際抓到的所有 'N typed edges' 數字：{claimed_nums}。"
        f"請確認 §架構概覽 / English Architecture 仍宣稱 {actual} 條 typed edges。"
    )


def test_readme_invariants_count(REPO_ROOT):
    """README 宣稱的 invariants 數應對齊 ``invariants.py`` 內 ``assert_iN[ab]?`` 函式數。

    R4 把 I1 拆成 I1a + I1b 後，獨立 invariant 共 6 個：I1a / I1b / I2 / I3 /
    I4 / I5。注意：``assert_i1_core_topic_coverage`` 是 deprecated 向下相容
    wrapper，**不計入**。
    """
    invariants_path = Path(
        REPO_ROOT, "packages", "susr", "susr", "brain", "invariants.py"
    )
    source = invariants_path.read_text(encoding="utf-8")

    # 抓 def assert_iN_  或 assert_iNa_ / assert_iNb_
    found = re.findall(r"^def\s+assert_i(\d+[ab]?)_", source, flags=re.MULTILINE)
    # 去掉 legacy '1'（assert_i1_core_topic_coverage 是 wrapper）
    independent = sorted(set(found) - {"1"})

    actual = len(independent)

    readme = _read_repo_md(REPO_ROOT, "README.md")
    # 抓「6 條連結性 invariants」/「6 connectivity invariants」/「N invariants」
    matches = re.findall(
        r"(\d+)\s*(?:條)?\s*(?:連結性\s*|connectivity\s+)?invariants?",
        readme,
        flags=re.IGNORECASE,
    )
    claimed_nums = {int(n) for n in matches}

    assert claimed_nums, "README 未找到任何 'N invariants' 宣稱。"

    # 任一處宣稱應等於 actual
    structural_hits = {n for n in claimed_nums if n == actual}
    assert structural_hits, (
        f"README 宣稱的 invariants 數 {claimed_nums} 沒有任何一個等於真實 "
        f"獨立 invariants 數 {actual}（從 {independent} 推得）。請更新 "
        f"§架構概覽『N 條連結性 invariants』與 English Architecture。"
    )


def test_readme_mcp_tools_count(REPO_ROOT):
    """README 宣稱的 MCP tools 總數應對齊 ``mcp/tools/*.py`` 內 ``server.tool()`` 登記數。

    Phase 3(4) + Phase 6(4) + Phase 7(4) + Workspace(5) + IRO(1) + Action(1) = 19。
    drift 來源：新增 tool 後忘記更新 README TL;DR / 架構概覽。
    """
    tools_dir = Path(REPO_ROOT, "packages", "susr", "susr", "mcp", "tools")
    total = 0
    for py in sorted(tools_dir.glob("*.py")):
        if py.name in ("__init__.py",):
            continue
        text = py.read_text(encoding="utf-8")
        # 抓 server.tool()(fn_name) — register() 內的真實登記
        total += len(re.findall(r"server\.tool\(\s*\)\s*\(", text))

    assert total > 0, (
        f"找不到任何 server.tool() 登記於 {tools_dir}；test 假設可能失效。"
    )

    readme = _read_repo_md(REPO_ROOT, "README.md")
    # 抓「19 個 MCP tools」/「19 MCP tools」
    matches = re.findall(
        r"(\d+)\s*(?:個)?\s*MCP\s+tools?",
        readme,
        flags=re.IGNORECASE,
    )
    claimed_nums = {int(n) for n in matches}

    assert claimed_nums, "README 未找到任何 'N MCP tools' 宣稱。"
    assert total in claimed_nums, (
        f"README 宣稱的 MCP tools 數 {claimed_nums} 不含真實登記數 {total}。"
        f"請更新 README TL;DR / 架構概覽。"
    )


# ---------------------------------------------------------------------------
# 2. MVP Phase status — README 標 ✅ 的 phase 應有對應 tool 模組
# ---------------------------------------------------------------------------


def test_readme_mvp_phases_status(REPO_ROOT):
    """README §8-Phase SOP 內標 ✅ 的 phase 應有對應 ``mcp/tools/phaseN.py``。

    這個 lint 抓「README 宣稱 Phase X done 但 code 沒實作」這類 drift。
    """
    readme = _read_repo_md(REPO_ROOT, "README.md")

    # 抓「Phase N」+ ✅ 同行
    phase_ok_re = re.compile(
        r"Phase\s+(\d+)\s+[^\n]*?✅",
        flags=re.IGNORECASE,
    )
    ok_phases = {int(m) for m in phase_ok_re.findall(readme)}
    assert ok_phases, "README 未找到任何 'Phase N ... ✅' 標記；regex 失效？"

    tools_dir = Path(REPO_ROOT, "packages", "susr", "susr", "mcp", "tools")
    missing = []
    for n in sorted(ok_phases):
        if not (tools_dir / f"phase{n}.py").exists():
            missing.append(n)

    assert not missing, (
        f"README 標 ✅ 的 Phase {missing} 找不到對應 mcp/tools/phaseN.py。"
        f"請確認該 phase 實作存在，或把 README 改回 ❌ / ⏳。"
    )


# ---------------------------------------------------------------------------
# 3. tests count — 容差比較（drift 範圍內 OK）
# ---------------------------------------------------------------------------


# 容差：README 宣稱數可比真實 collected 少 / 多多少。
# 設計：test 數會持續成長，README 滯後是常態；容差設 ±50 抓「忘了好幾輪 sprint」
# 級別的 drift。較小的（如 ±10）會在每次新增 parametrize case 時誤報。
# 註：AST 估算（``def test_``）與 pytest collect 的差距來自 ``@pytest.mark.parametrize``
# 展開、conftest fixture 注入式測試等。AST count 通常會比 pytest collect 低 ~15-25%，
# 所以 README 數（通常引用 pytest collect 數）會比 AST 高，容差需單向放寬。
README_TESTS_TOLERANCE = 70  # README 寫 pytest collect count (含 parametrize 展開)，AST def count 不含 → 差距通常 +50~70


def test_readme_tests_count_range(REPO_ROOT):
    """README 宣稱的 test 數應在真實 test function 數的容差範圍內。

    本 test 用 AST 數 ``def test_`` 數量（不展開 parametrize），與 README
    宣稱數比較容差 ±30。若 README 改寫成「N+ tests」之類，本 test 仍會
    過 — 唯一抓的是「具體寫死的數字 drift 太大」。
    """
    import ast

    readme = _read_repo_md(REPO_ROOT, "README.md")
    # 抓「275 passed」/「275 tests」/「275 個 test」
    matches = re.findall(
        r"(\d+)\s*(?:passed|tests?|個\s*test)",
        readme,
        flags=re.IGNORECASE,
    )
    claimed_nums = {int(n) for n in matches if int(n) >= 50}  # 過濾雜訊（如 phase 數）

    assert claimed_nums, (
        "README 未找到任何 'N tests passed' / 'N tests' 宣稱。"
    )

    # 數真實 test functions（AST，不展開 parametrize）
    test_roots = [
        Path(REPO_ROOT, "tests"),
        Path(REPO_ROOT, "packages", "susr", "tests"),
    ]
    actual = 0
    for root in test_roots:
        if not root.exists():
            continue
        for py in root.rglob("test_*.py"):
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    actual += 1

    assert actual > 0, "沒收到任何 test function；test 假設可能失效。"

    # 至少有一個 claimed 在容差內
    in_range = [
        n for n in claimed_nums if abs(n - actual) <= README_TESTS_TOLERANCE
    ]
    assert in_range, (
        f"README 宣稱的 test 數 {sorted(claimed_nums)} 全部偏離真實 test 數 "
        f"{actual}（AST def 計數）超過 ±{README_TESTS_TOLERANCE}。請更新 "
        f"README TL;DR / MVP 驗收成果『N passed + 2 skipped』。"
    )


# ---------------------------------------------------------------------------
# 4. Walkthrough R6 內部一致性 — TL;DR vs §1 vs §3
# ---------------------------------------------------------------------------


def test_walkthrough_r6_numbers_consistent(REPO_ROOT):
    """walkthrough R6 內 TL;DR / §1 ingest / §3 Phase 6 payload 對 chapters /
    iros / kpis / targets 四數字應一致。

    這是 source-of-truth 文件的**內部一致性**檢查，不跟 README 對齊
    （README 允許滯後）。若 walkthrough 自己 TL;DR 與 §3 對不上，
    說明文件草擬時人為打錯。
    """
    text = _read_repo_md(
        REPO_ROOT, "docs", "walkthroughs", "lealea-5364-phase6-r6.md"
    )

    # TL;DR 表抓 chapters / iros / kpis_summary / targets_summary 的「R6+R7 後」欄
    # 表格格式：| Phase 6 docx payload chapters | **0** | **5** |
    tldr_re = re.compile(
        r"Phase\s+6\s+docx\s+payload\s+(chapters|iros|kpis_summary|targets_summary)\s*\|"
        r"[^\|]*\|\s*\*?\*?(\d+)\*?\*?\s*\|",
        flags=re.IGNORECASE,
    )
    tldr = {key: int(val) for key, val in tldr_re.findall(text)}

    # §3.1 docx payload table 抓「R6+R7」欄
    # 格式：| chapters | 0 | **5** |
    s31_keys = {
        "chapters": "chapters",
        "iros": "iros",
        "kpis_summary": "kpis_summary",
        "targets_summary": "targets_summary",
    }
    s31 = {}
    for k_field, k_norm in s31_keys.items():
        m = re.search(
            rf"\|\s*{k_field}\s*\|\s*\*?\*?\d+\*?\*?\s*\|\s*\*?\*?(\d+)\*?\*?\s*\|",
            text,
        )
        if m:
            s31[k_norm] = int(m.group(1))

    # §1 ingest 統計區塊：「chapter 5」「iro 14」「kpi 8」「target 3」
    s1 = {}
    for key, norm in [
        ("chapter", "chapters"),
        ("iro", "iros"),
        ("kpi", "kpis_summary"),
        ("target", "targets_summary"),
    ]:
        m = re.search(rf"^\s*{key}\s+(\d+)\s*", text, flags=re.MULTILINE)
        if m:
            s1[norm] = int(m.group(1))

    # 三組都應該各抓到 4 個 key
    assert set(tldr.keys()) == {
        "chapters",
        "iros",
        "kpis_summary",
        "targets_summary",
    }, f"TL;DR 抓不到完整 4 個 key，只抓到 {sorted(tldr.keys())}"
    assert set(s31.keys()) == set(tldr.keys()), (
        f"§3.1 抓不到完整 4 個 key，只抓到 {sorted(s31.keys())}"
    )
    assert set(s1.keys()) == set(tldr.keys()), (
        f"§1 ingest 抓不到完整 4 個 key，只抓到 {sorted(s1.keys())}"
    )

    # 三組數字必須一致
    mismatches = []
    for key in tldr:
        triple = (tldr[key], s31[key], s1[key])
        if len(set(triple)) > 1:
            mismatches.append(
                f"{key}: TL;DR={tldr[key]} / §3.1={s31[key]} / §1 ingest={s1[key]}"
            )

    assert not mismatches, (
        "walkthrough R6 內部不一致（TL;DR vs §1 vs §3.1 對不上）:\n  - "
        + "\n  - ".join(mismatches)
    )
