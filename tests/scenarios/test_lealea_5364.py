"""Layer 2 scenario 測試 — examples/lealea-5364/ 作為 golden fixture。

對應 CLAUDE.md §6.2 五層測試結構的 Layer 2：scenario regression。
本檔用 ``expectations/lealea-5364.yaml`` 作為「核心 ESG domain invariant」清單，
parametrize 一次跑完所有 phase 的 expectation。

設計選擇：
- expectation 寫在 YAML（人類可讀）而非 .py（CLAUDE.md §6.4 hard rule）
- assertion 鎖「ESG domain invariant」（必須存在的概念與結構），
  而非「特定文字長相」（日期、金額、行銷詞）
- 重做 example 時若仍合乎 invariant，本測試應通過；
  若刪掉核心概念（如 TCFD 章節、雙重重大性方法），本測試應抓出 regression

fixture 依賴（由 ``tests/conftest.py`` 提供）：
- ``examples_dir``：``examples/lealea-5364/`` 絕對路徑
- ``read_md``：讀檔並正規化 BOM / CRLF 的 helper（function 或 fixture 皆相容）
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# ``read_md`` 在現行 conftest 是 module-level function（非 fixture）。
# 本檔直接 import 該 function，避免硬綁 fixture 介面；若日後 conftest
# 將 ``read_md`` 升級為 fixture，本 import 仍能取到該 callable（function 物件
# 本身仍存在於 module namespace），test 端不需改動。
# 若 conftest 完全不存在或未匯出 ``read_md``，落到內建 fallback。
try:
    from tests.conftest import read_md as _read_md
except ImportError:  # pragma: no cover — 從 tests/ 目錄啟動 pytest 的情境
    try:
        from conftest import read_md as _read_md  # type: ignore[no-redef]
    except ImportError:
        _read_md = None


def _fallback_read(path):
    """最終保底讀檔：UTF-8 + 去 BOM + CRLF→LF。

    僅當 ``conftest.read_md`` 不可 import 時才會走到此處，
    語意刻意對齊 conftest 版本以維持正規化一致性。
    """
    text = Path(path).read_text(encoding="utf-8")
    if text.startswith("﻿"):
        text = text.lstrip("﻿")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _read(path):
    """單一入口 — 永遠回傳已正規化的 markdown 字串。"""
    if _read_md is not None:
        return _read_md(path)
    return _fallback_read(path)


EXPECTATIONS_PATH = Path(__file__).parent / "expectations" / "lealea-5364.yaml"


def _load_expectations() -> dict:
    """讀 expectations YAML，回傳 dict。

    在 module-load 時就讀進來，讓 ``pytest.mark.parametrize`` 可以拿到 key 清單。
    """
    with open(EXPECTATIONS_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or not data:
        raise RuntimeError(
            f"expectations YAML 必須是非空 dict：{EXPECTATIONS_PATH}"
        )
    return data


EXPECTATIONS = _load_expectations()


@pytest.mark.parametrize("phase_key", sorted(EXPECTATIONS.keys()))
def test_lealea_phase_expectations(phase_key, examples_dir):
    """逐 phase 驗證 ESG domain invariant。

    每個 phase 的 expectation spec 結構（見 ``expectations/lealea-5364.yaml``）：
        file: 相對於 examples_dir 的檔名
        description: 守護的 invariant 一句話說明（assertion 失敗時印出）
        must_contain: list[str]，全部必須出現
        must_contain_any: list[str]，至少一個必須出現（選用）
        must_not_contain: list[str]，全部不可出現（選用）
        min_lines: int，最少行數（選用）
    """
    spec = EXPECTATIONS[phase_key]
    file_rel = spec["file"]
    file_path = examples_dir / file_rel
    description = spec.get("description", "(no description)")

    # 1. 檔案存在性 —— example 被誤刪會在這裡爆
    assert file_path.exists(), (
        f"[{phase_key}] 預期檔案不存在：{file_path}\n"
        f"description: {description}"
    )

    content = _read(file_path)

    # 2. must_contain：domain invariant 必有
    for needle in spec.get("must_contain", []):
        assert needle in content, (
            f"[{phase_key}] {file_rel} 缺少必要內容: {needle!r}\n"
            f"description: {description}"
        )

    # 3. must_contain_any：等價類至少一個（避免逼一字不差）
    any_list = spec.get("must_contain_any", [])
    if any_list:
        assert any(n in content for n in any_list), (
            f"[{phase_key}] {file_rel} 至少要含一個: {any_list!r}\n"
            f"description: {description}"
        )

    # 4. must_not_contain：anti-pattern 禁止出現
    for forbidden in spec.get("must_not_contain", []):
        assert forbidden not in content, (
            f"[{phase_key}] {file_rel} 不該出現: {forbidden!r}\n"
            f"description: {description}"
        )

    # 5. min_lines：防止被抽空 / 截斷
    min_lines = spec.get("min_lines")
    if min_lines:
        actual = len(content.splitlines())
        assert actual >= min_lines, (
            f"[{phase_key}] {file_rel} 太短: {actual} < {min_lines}\n"
            f"description: {description}"
        )


def test_expectations_yaml_loadable():
    """smoke test — expectations YAML 結構自身的完整性。

    確保每個 phase entry 都至少含 ``file`` 與 ``must_contain``，
    避免不小心刪掉 expectations 內容但測試還誤判為 pass。
    """
    assert EXPECTATIONS, "expectations YAML 不能為空"
    for key, spec in EXPECTATIONS.items():
        assert isinstance(spec, dict), f"{key} spec 必須是 dict"
        assert "file" in spec, f"{key} 缺 file 欄"
        assert "must_contain" in spec and spec["must_contain"], (
            f"{key} 必須至少一個 must_contain assertion"
        )
        assert len(spec["must_contain"]) >= 3, (
            f"{key} must_contain 至少 3 條（caller 要求每份檔案至少 3 個 assertion）"
        )
