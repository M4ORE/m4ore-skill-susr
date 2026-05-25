# tests/ — susr 測試基礎建設

> susr 對自己誠實的 forcing function。所有對外宣稱的 feature 必須有測試證明它真的可用。

---

## 為什麼有這個目錄

`CLAUDE.md §6.1` 訂下 hard rule：

> **任何在 `CLAUDE.md` / `SKILL.md` / `README.md` / `dashboard` 宣稱的 feature，必須至少有一個對應的測試證明它真的可用。沒測試的「招牌功能」不能寫進對外文案。**

這條規則的存在來自 2026-05-25 的 gbrain survey 教訓：penfieldlabs 查證發現 gbrain 多個招牌功能（compiled-truth rewriting / dream cycle / entity detection）只存在於 markdown 指令裡、原始碼根本沒實作。susr 選擇 Plan B 自己重寫，價值之一就是**對自己誠實**——而測試正是把這份誠實制度化的工具。

---

## 五層測試結構

對應 `CLAUDE.md §6.2`：

| Layer | 名稱 | 範圍 | 狀態（2026-05-25） |
|-------|------|------|-------------------|
| 1 | 靜態 / Lint | `references/` 結構、詞彙一致性、frontmatter 必備欄位 | **已 bootstrap** |
| 2 | SOP / Scenario | `examples/lealea-5364/` 各 phase expected outcomes | **已 bootstrap** |
| 3 | 領域 invariants | survey §4.3 五條連結性、KB 單向闘、client 隔離 hard rule | 待（隨 susr-brain Step 1 開工） |
| 4 | 引擎單元 | BrainEngine / RRF 數學 / page_versions / MCP handler | 待（隨 susr-brain Step 1 開工） |
| 5 | 合規回歸 | GRI Content Index 完整性 / ISSB datapoint 覆蓋 / 反綠檢查 | 待（真實顧問案件後補） |

---

## 目錄結構

```
tests/
├── README.md                   ← 本檔
├── requirements.txt            ← pytest + pyyaml
├── conftest.py                 ← shared fixtures & helpers
├── lint/                       ← Layer 1（待填）
│   ├── test_references.py      ← 使用時機段落 / frontmatter
│   └── test_terminology.py     ← 反查錯誤用詞應為零
└── scenarios/                  ← Layer 2（待填）
    ├── expectations/
    │   └── lealea-5364.yaml    ← 各 phase 預期內容斷言
    └── test_lealea_5364.py
```

---

## 如何本機跑

```bash
# 一次性安裝測試依賴
pip install -r tests/requirements.txt

# 跑所有測試
python -m pytest tests/ -v

# 只跑 Layer 1（靜態 / lint）
python -m pytest tests/lint/ -v

# 只跑 Layer 2（SOP / scenario）
python -m pytest tests/scenarios/ -v

# 跑單一檔
python -m pytest tests/lint/test_references.py -v

# 跑單一 test function
python -m pytest tests/lint/test_references.py::test_frontmatter_required_fields -v
```

跨平台提示：Windows 上請用 `python -m pytest` 而非裸 `pytest`，可避免 PATH / venv 落差。

---

## CI

`.github/workflows/test.yml` 會於 `push` / `pull_request` 觸發，跑整個 `tests/`。Pull request 必須綠燈才允許 merge。

---

## 加新測試的 checklist

新增測試前自問：

- [ ] **檔名規範**：`test_<scope>.py`（pytest auto-discovery 依賴此前綴）；測試函式 `test_<behaviour>()`
- [ ] **歸位正確的 Layer**：Lint / Scenario / Invariant / Engine / Compliance？放錯資料夾會被誤跑或漏跑
- [ ] **需要更新 fixture？** 若新增的 expected outcome 屬於 lealea-5364 phase，更新 `tests/scenarios/expectations/lealea-5364.yaml`，**不要**把斷言寫死進 `.py`
- [ ] **需要更新本 README？** 若加了新 Layer 或大幅改動結構，務必同步上方表格與目錄樹
- [ ] **CLAUDE.md / SKILL.md / README 有對外宣稱的 feature 嗎？** 若有，依 §6.1 hard rule，這個 PR 必須帶相應測試才能 merge

---

## 不適用情境（§6.5）

- 純文案修訂、typo 修復：不需要測試
- 三原則文件（`docs/defeinition.md` / `target.md` / `product_structure.md`）：由使用者親自更新，測試只負責確認檔案存在
- `docs/research/` 的研究報告：snapshot 性質，不需 regression test
