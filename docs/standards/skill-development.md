# Skill 開發標準

**版本**：1.0 (2026-04-29)
**來源**：SP1-001 Lessons Learned
**適用範圍**：本專案內所有 Claude Code skill 開發

## 1. Frontmatter 慣例

最小可行 frontmatter，不使用 `allowed-tools`：

```yaml
---
name: <hyphen-case-name>
description: |
  <一句話定位> — <核心能力>。
  Trigger on: <關鍵詞 1>, <關鍵詞 2>, ...（中英並列）
  Non-trigger: <避免的情境 1>, <避免的情境 2>, ...
  Always <強制行為>.
  <輸出語言 / 整合需求>.
---
```

**為什麼不用 `allowed-tools`**：本專案環境（`design-first-development`、`production-mgmt`、`shenggengtw`、`workspace-flow`）皆無此欄位，加上反而與既有慣例衝突。

## 2. Trigger / Non-trigger 雙列法

**規則**：description 內必須同時列出觸發詞與不觸發情境。

**為什麼**：單列觸發詞容易過度觸發。實測「幫我寫 README.md」在無 Non-trigger 情況下會誤觸發 sustainability-report skill；加上「純程式開發」作為 Non-trigger 後正確不觸發。

**實作要點**：
- Trigger：中英雙語列出，至少涵蓋核心領域 + 主要標準名 + 常用同義詞
- Non-trigger：列出 3–5 個邊界情境，特別是與本 skill 領域「看起來相關但實際不該觸發」的問題

## 3. SOP-Style Skill 的 8×4 結構

當 skill 內容是流程性 SOP（如 sustainability-report 的 8 Phase），SKILL.md 主文採此結構：

```markdown
### Phase N — <名稱>
- **Objective**：<這個 phase 要達成什麼>
- **Key Activities**：<3–5 條主要動作>
- **Output**：<具體產出物名稱>
- **Integration**：<外部 skill / 工具呼叫，指向 references/ 對應檔案>
```

**規模指引**：
- SKILL.md 主文 ≤ 200 行
- 細節（詞彙表、檢查清單、prompt 模板）一律進 `references/`
- references/ 每個檔案開頭寫「使用時機」段落

## 4. Skill 建構位置與部署

**規則**：先在專案目錄 `./skills/<name>/` 建構與迭代，驗證後才部署到 `~/.claude/skills/`。

**為什麼**：
- 直接寫到全域目錄會跳過版本控制、難追溯
- 專案目錄成果可與 PDCA 文件、commit 歷史一起追蹤
- 部署是最後一步，通常獨立成一個 Task

## 5. 命名策略（skill name vs folder vs repo）

當有公開分享需求時，三層命名可分離：

| 層級 | 策略 |
|------|------|
| GitHub repo / 工作目錄 | 短代號（`susr`） |
| Skill folder | 與 repo 對齊（`susr`） |
| Skill `name` frontmatter | 描述性全名（`sustainability-report`） |

**為什麼**：repo URL 短好記、skill 識別字串對 Claude 與其他使用者具描述性，各取所需。

## 6. 結構驗證

新 skill 完成後驗證項目：

- [ ] frontmatter `name` 與 folder 名一致
- [ ] description 含 Trigger / Non-trigger 雙列
- [ ] SKILL.md ≤ 200 行
- [ ] 至少 3 個正面觸發測試 + 1 個負面（Non-trigger）測試通過
- [ ] 對照既有 skill（如 `production-mgmt`）做格式 cross-check

## 7. 不適用情境

本標準針對「SOP-style」或「領域知識型」skill。下列情境可不完全套用：

- 純 slash command skill（短小、無領域知識）
- 工具型 skill（如 statusline-setup，純設定操作）
- 一次性實驗 skill

## 8. Reference 撰寫慣例

當 skill 有 `references/` 子目錄時，每份 reference 檔案遵循：

### 8.1 固定位置的「使用時機」段落

每份檔案第 3 行放：

```markdown
# <檔名標題>

**使用時機**：<在哪個 Phase 用 / 何時 confirm / 何時最終裁決>
```

**為什麼**：固定位置（line 3）便於用 Grep 一次驗證所有 reference 都有此段落，不需逐檔開啟。實測指令：
```
Grep pattern="^\*\*使用時機\*\*" path="references/" -n
```

### 8.2 雙語 / 術語一致性的反查驗證

不要逐字對讀，改用「反查錯誤用詞零出現」：
- 規定統一用「範疇 1/2/3」→ Grep `範圍 1/2/3` 應為零
- 規定統一用「利害關係人」→ Grep `持份者` 應為零（或僅在 glossary 規則段落出現）

**為什麼**：對長文檔逐字校對成本高，反查錯誤用詞快又精確。

### 8.3 時效性內容的標記原則

法規 / 公告 / 排放因子等會隨時間更新的內容，必須：
1. 在檔頭加「**注意**：本文件以 YYYY-Qn 已知資訊為準」
2. 在每個過時風險段落加「（具體年度需 WebSearch 確認最新）」或同類標記
3. 將所有 WebSearch 標記彙整成清單，便於下次更新時一次處理

**為什麼**：reference 一旦寫入就會被信任引用，沒有時效性標記會造成過期資訊滲透到正式報告。

**彙整檔案命名建議**：`websearch-pending.md`（或 `external-verification-pending.md`），放在同一個 `references/` 目錄下，每項記錄：
- 來源檔案位置（含行號）
- 待確認問題
- 建議查詢來源
- 對下游產出的影響
- 最後確認日期 + 來源 URL（查證後填，保留稽核軌跡）

### 8.3.1 External Verification Workflow（時效性 reference 的批次驗證）

當 `websearch-pending.md` 累積多個待查項時，採批次處理：

1. **並行跑 WebSearch**：可一次發 3+ 個 query，Claude 並行處理沒問題，比逐筆跑省 3–4 倍時間
2. **記錄副產品**：WebSearch 常會回傳超出原問題的資訊（例如查「強制申報年度」順便拿到產業清單；查「確信標準」順便拿到實況統計）。所有附帶發現都要寫進 reference，不只答原問題 — 否則下次又要重查
3. **不容忍模糊敘述**：若原 reference 寫「通常於 6 個月內」、「漸進推進中」這類模糊話，視為品質紅旗。WebSearch 的價值就是把模糊精確化（如「8/31 為法定期限」）
4. **`需直接洽詢` escape hatch**：不是所有問題都能在網路查到答案（如非公開的內部規格），明確標註「建議直接洽詢 X 機構」並指出窗口，比編造看似精確的答案誠實也安全

## 9. Orchestrator Skill 開發流程

當 skill 是「呼叫其他 sub-skill 完成工作」的 orchestrator（例如 sustainability-report 呼叫 docx / xlsx / pptx / pdf），遵循此順序：

### 9.1 先研究 sub-skill 內部 API

在寫整合 prompt 前，先派研究 agent 看 sub-skill 的 SKILL.md（如 `https://raw.githubusercontent.com/anthropics/skills/main/skills/<name>/SKILL.md`），抓取：
- 輸入約定（natural language vs JSON）
- workflow 分流（建立新 / 編輯既有 / 從範本）
- 隱性 gotchas（如 reportlab unicode 上下標陷阱、xlsx 必須跑 recalc.py、pptx 必須視覺 QA）
- 環境依賴

**為什麼**：寫完再回頭改成本高；猜想出來的 prompt 命中率低。

### 9.2 Prompt 通用約定

整合 prompt 一律：
- 用「自然語言 + 絕對路徑」，**不用 JSON 結構化輸入**
- 要求呼叫前先 `mkdir -p` 輸出目錄
- 明確告訴 sub-skill 走哪條 workflow（跳過它自己的 router）

### 9.3 視覺類產出強制 QA Loop

任何輸出可視覺檢查的格式（pptx、html、PNG），prompt 必須：
1. render 為 image（pdftoppm / soffice 等）
2. spawn 視覺檢查 sub-agent，給定具體檢查項
3. 依回報修正後 re-verify
4. **至少跑完一輪 fix-and-verify** 才能宣告完成

**為什麼**：LLM 看不到視覺，純程式正確不等於視覺可用。

### 9.4 主 SKILL.md 加 Pre-flight Dependencies 段落

在 8-Phase SOP 之前加一段「Phase 0 — Pre-flight Dependencies」：
- 列出所有 sub-skill 各自的依賴（簡列即可，不複製安裝指令）
- 加行為規則：「sub-skill 呼叫失敗時，解析錯誤訊息中的工具名稱，明確指出缺失依賴，指向 sub-skill 自身文件」
- 不維護完整安裝步驟（會與 sub-skill 文件不同步）

### 9.5 各 phase prompt 末尾加「失敗時的依賴提示」對照表

每份整合 prompt 的最後一節：

```markdown
## N. 失敗時的依賴提示

| 錯誤訊息片段 | 缺失依賴 | 處理 |
|-------------|---------|------|
| `<工具>: command not found` | <工具名> | 提示安裝 + 指向 sub-skill SKILL.md |
| `No module named '<pkg>'` | <Python 套件> | 提示 `pip install <pkg>` |
```

**為什麼**：搭配 9.4 的 SKILL.md Phase 0 形成兩層保護。錯誤訊息是 sub-skill 失敗的 first-class signal，與其讓 agent 報「執行失敗」，不如解析訊息給出具體缺失。

## 10. 公開分享 Skill 的設計原則

當 skill 預計公開到 GitHub / 內部 share 給其他人使用時，遵循以下原則：

### 10.1 Graceful Degradation（漸進式降級）

設計成「未滿足高 tier 不會破壞低 tier 的使用」，分等級揭露依賴：

| Tier | 內容 | 不滿足時 |
|------|------|---------|
| **0 必要** | skill 本身（複製到 `~/.claude/skills/`） | 完全無法啟動 |
| **1 建議** | sub-skill 插件啟用（如 anthropics/skills 的 document-skills） | 部分 phase 仍可用，需要 sub-skill 的 phase 才 fail |
| **2 完整** | sub-skill 底層工具（LibreOffice、Node、Python 套件） | sub-skill 啟動但中段失敗，由錯誤訊息引導使用者 |

**為什麼**：使用者環境不一定齊全，但他們不該因為 Tier 2 缺失而完全用不到 skill。Tier 0–1 通常能覆蓋 70–80% 的使用價值（規劃、知識庫、prompt 模板）。

**實作要點**：
- README 必須清楚標示三個 tier 與不滿足時的影響
- skill 內部設計：Phase 拆分時讓「規劃 / 研究 / 知識應用」phase 不依賴 sub-skill；只有「檔案產出」phase 才依賴
- 在 Phase 0 Pre-flight（見 §9.4）解析錯誤訊息，引導使用者裝 Tier 2 工具

### 10.2 README 公開可達引用原則

任何 `README.md` 內的引用必須是：
- **repo 內可達**（git tracked 的檔案，未被 `.gitignore` 排除）
- **或外部公開連結**（穩定 URL）

**禁止**：引用 `.gitignore` 排除的私人草稿、本地路徑、需登入才能看的內部連結。

**為什麼**：讀者拿到 repo 後，README 是他第一個看的東西。引用「找不到的東西」立刻破壞信任。

**檢查方式**：
- 寫完 README 後 grep 所有相對路徑引用，與 `.gitignore` 對照
- 寫完 README 後 grep 所有絕對 URL，確認非內部連結

### 10.3 Codename vs Skill Name 的分層

當有公開分享需求時（見 §5），三層命名可分離：
- **GitHub repo / 工作目錄**：短代號（易輸入、易記）
- **Skill folder 名稱**：與 repo 對齊
- **Skill `name` frontmatter**：描述性全名（利於 Claude 識別與其他使用者理解）

在 README 開頭明確說明這個分層，避免讀者困惑。
