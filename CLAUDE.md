# CLAUDE.md — susr 專案最高原則

> 本檔為本 repo 對 Claude Code 的常駐 instructions。
> 任何設計、實作、文案、商業決策若與本檔牴觸，**以本檔為準**。
> 本檔本身若與下述三份原則文件牴觸，**以三份原則文件為準**。

---

## 0. 三份最高原則文件（Canonical）

以下三份文件是本專案的**北極星**，任何工作開始前都必須先載入並對齊：

| 文件 | 角色 | 一句話總結 |
|------|------|-----------|
| [`docs/defeinition.md`](docs/defeinition.md) | **What** — 永續報告書的本質 | 把 ESG 表現以可驗證、可比較、可信任的方式結構化呈現給利害關係人。**Co-pilot ≠ Replacement**。 |
| [`docs/target.md`](docs/target.md) | **Who & Why** — 我們要 build 什麼 | AI 輔助生成永續報告書，**對象是顧問**，把 40-80h 壓縮到 8-15h，保留 100% 專業判斷與最終責任。 |
| [`docs/product_structure.md`](docs/product_structure.md) | **How** — 產品架構 MVP | 三層架構（輸入 / 智能 / 輸出）+ 顧問專屬功能（KB、多客戶儀表板、團隊協作）。 |

**操作規則**：
- 啟動任何新任務前先 Read 這三份檔案
- 若使用者指令與三份原則出現方向性衝突，**先指出衝突再執行**，不要默默繞過
- 三份檔案若需修訂，必須是使用者明示，不能由 AI 主動 paraphrase 或「優化」

---

## 1. 戰略定位（不可漂移）

### 1.1 我們是什麼

**「顧問的第二大腦」/ AI 超能力放大器**
（Co-pilot for ESG consultants, not Replacement for them）

### 1.2 我們不是什麼

- ❌ 不是「自動寫報告的機器」
- ❌ 不是賣給企業（尤其不是賣給想省顧問費的中小企業）的 SaaS
- ❌ 不是純 AI 黑箱（純 AI 容易被其他 LLM 追上 → 無護城河）

### 1.3 商業模式對齊

| 面向 | 對齊原則 |
|------|---------|
| 目標客戶 | ESG 輔導顧問 / 顧問公司 |
| 商業模式 | SaaS 訂閱（顧問公司月費） |
| 顧問關係 | 視為**幫手**，不是威脅 |
| 護城河 | 顧問專業知識 + AI = **混合智能** |
| 法律風險 | 低（最終決策永遠在顧問手上） |

### 1.4 核心價值主張（一句話）

> 「用我們工具的顧問，能在同樣時間內產出**品質更高、框架更完整、故事更動人**的永續報告書，同時保留 100% 專業判斷與最終責任。」

---

## 2. 產品架構心智模型

任何新功能/模組必須能放入下列其中一層，否則先質疑它是否屬於本產品：

```
┌─────────────────────────────────────────────────┐
│ 輸入層 (顧問最痛苦)                              │
│  Excel / PDF / ERP / 供應鏈問卷 / 舊報告         │
│  → 結構化 + RAG，自動抽取關鍵指標                 │
├─────────────────────────────────────────────────┤
│ 智能層 (AI 核心)                                 │
│  多框架即時對應 (GRI/ISSB/台灣指引/CSRD)         │
│  自動章節初稿 / 差距分析 / 雙重重大性輔助         │
│  TCFD 風險機會自動連結                           │
├─────────────────────────────────────────────────┤
│ 輸出層 (顧問最有價值)                            │
│  可編輯 Word/GDocs（保留來源引用）               │
│  視覺化圖表建議 / 版本管理 / 審核軌跡             │
│  「一鍵注入專業觀點與案例」按鈕                   │
├─────────────────────────────────────────────────┤
│ 顧問專屬功能                                     │
│  顧問公司 KB（學會「我們顧問的語氣」）           │
│  多客戶儀表板 / 團隊協作 / 審核流程               │
└─────────────────────────────────────────────────┘
```

---

## 3. 現有資產與新定位的關係

本 repo 既有的 `skills/sustainability-report/` skill 與 `examples/lealea-5364/` 試做案例，是新產品的**核心智能層原型**。理解方式：

- `SKILL.md` 的 8-Phase SOP → 智能層的**流程骨架**
- `references/*` → 智能層的**領域知識庫**
- `examples/lealea-5364/` → 「**升級指南教材**」，給顧問用來向客戶展示 gap-closing 路徑
- 8-Phase 每個 phase 都對應顧問實際工作的**時間黑洞**，正是 Co-pilot 要切入的著力點

**注意**：README.md 目前的 framing 是「通用 skill」，後續若需公開行銷文案，應改寫成「顧問工具集的開源核心」定位。但 README 既有內容**不直接刪改**——保留作為歷史 baseline，新文案另起檔案。

---

## 4. 開發協作慣例

### 4.1 文件路徑

| 路徑 | 用途 |
|------|------|
| `docs/defeinition.md`, `docs/target.md`, `docs/product_structure.md` | **三原則文件**（最高、唯讀） |
| `docs/sprints/` | Sprint 規劃（PDCA） |
| `docs/tasks/` | Task 追蹤（PDCA） |
| `docs/standards/` | 開發標準（如 skill-development.md） |
| `docs/research/` | Subagent 研究報告（如 gbrain-survey.md、step1-spec.md） |
| `dashboard.html` + `dashboard-data.js` | **決策討論協作板**（單檔靜態，給人類檢視） |
| `skills/sustainability-report/` | 智能層原型（Claude Code skill 形式） |
| `packages/susr/` | 核心 Python package（brain + mcp + shared_kb，post Step 1 spike 建立） |
| `examples/` | 端到端試做案例 |
| `tests/` | Repo-level Layer 1+2 測試（Layer 3+4 在 packages/susr/tests/） |

### 4.2 修改三原則的規則

- 三原則文件視同**憲法**，不能在一般 task 中被順手改寫
- 若有修訂需要，必須使用者明確指示，並在 commit message 標註 `docs(principles): ...`
- AI 在 review 時若覺得三原則需要更新，要**提出疑問**，不直接動手

### 4.3 Dashboard 更新規則

`dashboard.html` 是靜態檢視板，內容由 `docs/` 與 `dashboard-data.js` 驅動。修改順序：

1. 改 `docs/` 或 `dashboard-data.js`
2. 重新檢視 `dashboard.html` 是否還對齊
3. 必要時更新 `dashboard.html` 的渲染邏輯

不要在 dashboard.html 內 hardcode 內容；除非是版面結構。

### 4.4 任何新功能/任務的 sanity check

開工前自問三題：

1. **這個動作服務的是「顧問」嗎？** 若答案是「企業」、「終端讀者」、「行銷部」，先停下來。
2. **這個動作是 Co-pilot 還是 Replacement？** 若是 Replacement（把顧問拿掉），先停下來。
3. **這個動作能放入三層架構嗎？** 若不能，質疑它是否屬於本產品。

任一題答不出來就先 ask user，不要硬做。

### 4.5 Subagent 派工原則（hard rule）

> **可以 subagent 派工就盡量用 — 特別是研究 / 多檔案非交集寫作 / 並行可行的工程任務。**

- **何時派**：研究類（讀外部 docs / web search）、scaffold 類（建多個非交集檔）、可平行的 spec / implementation 切片
- **不派的時機**：需要連貫推理的設計討論、需要與使用者來回對齊的決策、檔案邊界會交集的任務
- **派之前**：明確劃分檔案邊界，prompt 內告訴每個 agent「你動哪些檔，其他 agent 動什麼」
- **派完之後**：必驗證 — `pytest` 跑、grep 檢查整合 bug（agents 對 fixture / interface 假設可能不一致）
- **整合 bug 是 first-class concern**：subagent 並行寫的東西經常假設不一致（例：tests scaffold agent 寫 helper function、Layer 1 agent 把它當 fixture 用 → 失敗）。**永遠跑驗證**

### 4.6 Content Hygiene — 漸進揭露原則（hard rule）

> **每個檔案 / 模組 / subagent prompt 必須「TL;DR + index」在前、「細節」在後。讀者（人或 AI）能在前 100 行決定要不要繼續讀。**

呼應 gbrain `compiled_truth` 在橫線上、`timeline` 在橫線下的 aha — 同一個 pattern 用在所有層級。

#### 4.6.1 文件大小門檻

| 類型 | 軟門檻（建議拆） | 硬門檻（必須拆 OR 必須有 TL;DR+TOC）|
|---|---|---|
| Markdown 文件 | 500 行 | **1000 行 或 ~30KB** |
| Python source | 300 行 | **500 行**（含 docstring）|
| YAML / JSON 資料 | 不限 | 不限（純機器消費可大）|
| Test fixture | 不限 | 不限 |

超過硬門檻必須**至少符合一條**：
- (a) **拆成多檔**，主檔當 index（如 `references/` 模式）
- (b) **檔頭加 TL;DR (≤150 字) + TOC (錨點清單)**
- (c) **標記為 `data fixture`**（不期待人讀）

#### 4.6.2 讀檔規則（給 AI 自己）

- **永遠先** `grep` / `ToolSearch` / `Read offset+limit` 取結構，再決定要不要 Read 全檔
- 超過硬門檻的檔，**禁止無條件 Read 全檔**；必須先 grep 確認需求
- Subagent prompt 內**不複製大段內容**，給 path + line range 引用

#### 4.6.3 寫檔規則（給 AI 自己）

- 寫新檔前自問：「這檔會超過 500 行嗎？」會的話從一開始就**設計成 index + 子檔**
- 既有檔接近硬門檻時，**主動建議拆分**而非繼續往裡塞

#### 4.6.4 程式碼模組原則

- 一個 `.py` = 一個 cohesive concept
- 超過 300 行考慮拆 sub-module
- `__init__.py` 永遠當 module index（re-export + docstring 說明模組責任）
- 不准 god class / god module

#### 4.6.5 顧問面文件特殊規則（user-guide）

- 每份 `docs/user-guide/features/*.md` 的前 100 字必須回答「**這個功能在 30 秒內怎麼幫到我**」
- 細節（API / 邊界條件 / 哲學）在後段
- 顧問可以只讀 TL;DR 不被罰

#### 4.6.6 三種「大內容」情境的對應

| 情境 | 例子 | 解法 |
|---|---|---|
| 開發產物 | CLAUDE.md / step1-spec.md / 未來 brain code | 本節（4.6）規則 |
| 顧問面文件 | docs/user-guide/ | 4.6.5 + user-guide 系列 |
| 客戶原始資料 | ESG 報告 PDF / ERP 匯出 / 問卷 | **brain 本來就是這的解** — chunk + embed + retrieve + synthesize，**不適用本節規則** |

### 4.7 Commit 紀律（hard rule）

> **每個階段 commit 必須包含：(1) 測試跑過 pass，(2) 文件已更新。**

每個自然的工作階段邊界（任務完成 / spike 回報 / 對話收斂 / 工作 session 切換），commit 之前**必跑**：

1. **`pytest tests/ -q`** — 所有 Layer 1+2 測試 pass
2. **dashboard-data.js / CLAUDE.md / 相關 docs 已對齊本次變動**
3. **無 stale references**（grep 檢查已 supersede 的詞如 Postgres / submodule 等是否仍然出現）
4. **commit message** 標明階段（如 `feat(brain): step1 spike spec`、`docs(decisions): Q11-Q16 工程選型`）

任一項未過 → **不 commit**。fix 完再來。

對應 §6.1 hard rule（任何宣稱 feature 必有對應測試），這條保證測試與文件**同步進入版本史**。

---

## 5. 既有開發標準（仍適用）

- 詳見 [`docs/standards/skill-development.md`](docs/standards/skill-development.md)（Skill 開發 SOP，§9 涵蓋 Orchestrator）
- 詳見 [`CONTRIBUTING.md`](CONTRIBUTING.md)（貢獻流程）

---

## 6. 測試紀律（Testing Discipline）

### 6.1 核心 hard rule

> **任何在 `CLAUDE.md` / `SKILL.md` / `README.md` / `dashboard` 宣稱的 feature，必須至少有一個對應的測試證明它真的可用。**
>
> **沒測試的「招牌功能」不能寫進對外文案。**

這條規則的存在來自 2026-05-25 gbrain survey 的教訓：penfieldlabs 查證發現 gbrain 多個招牌功能（compiled-truth rewriting / dream cycle / entity detection）只存在於 markdown 指令裡、原始碼沒實作。susr 採 Plan B 自己重寫的價值之一，就是**對自己誠實** — 測試是 forcing function。

### 6.2 五層測試結構

```
Layer 5  合規回歸        GRI Content Index 完整性 / ISSB datapoint 覆蓋 / 反綠檢查
Layer 4  引擎單元        BrainEngine / RRF 數學 / page_versions / MCP handler
Layer 3  領域 invariants  survey §4.3 五條連結性 / KB 單向闘 / client 隔離 hard rule
Layer 2  SOP / Scenario  lealea-5364 fixture 各 phase expected outcomes
Layer 1  靜態 / Lint     references/ 結構 / 詞彙一致性 / frontmatter 必備欄位
```

**現階段（2026-05-25）已 bootstrap**：Layer 1 + Layer 2。Layer 3 / 4 隨 susr-brain Step 1 同步開工；Layer 5 等真實顧問案件後補。

### 6.3 測試檔案結構

```
tests/
├── README.md                    ← 五層說明 + 如何跑
├── requirements.txt             ← pytest + pyyaml
├── conftest.py                  ← shared fixtures
├── lint/                        ← Layer 1
│   ├── test_references.py       ← 使用時機段落 / frontmatter
│   └── test_terminology.py      ← 反查錯誤用詞應為零
└── scenarios/                   ← Layer 2
    ├── expectations/
    │   └── lealea-5364.yaml     ← 各 phase 預期內容斷言
    └── test_lealea_5364.py
```

### 6.4 執行方式

```bash
# 本機
python -m pytest tests/ -v

# CI（GitHub Actions）
.github/workflows/test.yml 自動於 push / PR 觸發
```

### 6.5 不適用情境

- 純文案修訂、typo 修復：不需要測試
- 三原則文件（`docs/defeinition.md` / `target.md` / `product_structure.md`）的修訂：因為這是「憲法」級內容，由使用者親自更新即可，測試只負責確認檔案存在
- `docs/research/` 的研究報告：屬於 snapshot 性質，不需 regression test

---

## 7. 版本

- **建立**：2026-05-25
- **觸發事件**：使用者以 `docs/{defeinition,target,product_structure}.md` 三檔重新定錨專案戰略，要求所有後續工作以此為最高原則
- **下次審視時機**：SP2 啟動時 / 三原則文件被修訂時 / 商業模式重大調整時

---

## 8. 演進註記（Decisions Log）

本節記錄三原則文件**未明寫但已在對話中收斂**的決策，按時序累積。
若這些決策最終穩定，應由使用者親自反向更新 `docs/` 原則文件，再清理本節。

### 2026-05-25 · 形態決策：local-first + MCP，不先做 web SaaS

- **背景**：dashboard `openQuestions.Q2` 原列三選項（skill / Web SaaS / 雙軌）
- **決策**：參考 **gbrain**（`github.com/garrytan/gbrain`，Garry Tan/YC CEO 的個人 AI 知識系統）的路線
  - Local-first：Markdown files 存 Git repo，Postgres 作 backing store
  - MCP-native：tools 透過 MCP 暴露，Claude Code / Cursor / Windsurf 直接讀寫
  - Self-wiring knowledge graph：entity refs + typed edges 自動抽取（零 LLM 呼叫）
  - Synthesis + Gap Analysis 作為 first-class capability
  - OSS / MIT 授權
- **為何選這條路**：
  1. 顧問處理 client 機密 ESG 資料 → local-first 直接消除信任門檻
  2. Markdown + Git → 顧問本來就熟版本控制；天然可審計（呼應 Definition §4 信任與驗證）
  3. ESG 議題網絡（議題 → IRO → 治理 → 行動 → 目標 → KPI）與 knowledge graph 天然契合
  4. SP1-004 力麗試做核心發現 = gap analysis，gbrain 已把這做成 first-class capability
  5. 同時消除 Q4 multi-tenant 隔離問題
- **與 `docs/defeinition.md` 的牴觸**：原表格寫「商業模式：SaaS 訂閱（顧問公司月費）」。
  - **暫不擅自改動原則文件**
  - 解讀：local-first OSS 仍可商業化（open core / cloud sync 進階版 / 支援合約 / 顧問公司付費部署服務），與「SaaS 訂閱」精神可相容
  - 待商業模式具體成型後，由使用者親自更新 `docs/defeinition.md`
- **與三原則的對齊檢查**：
  - Definition：✅ 仍是 Co-pilot；信任與驗證更強
  - Target：✅ 對象仍是顧問，40-80h → 8-15h 目標不變
  - Product Structure：✅ 三層架構不變，只是承載介質從 web SaaS 改為 local-first + MCP
- **下一步**：dashboard `openQuestions.Q6`（深入研究 gbrain → 產出 susr ESG entity 圖）

### 2026-05-25 · 首批 design partner：獨立顧問 + 小型顧問公司

- **決策**：鎖定獨立顧問 / 小型顧問公司，**排除** 中型本土 + 四大永續組
- **理由**：決策快、痛點具體、與 local-first 形態相容（不需多人協作 infra 即可起步）
- **隱含的取捨**：放棄四大背書的短期信號，換取迭代速度與真實 PMF 訊號

### 2026-05-25 · Obsidian 相容性：受概念影響，不承諾相容（Claude Desktop 是真 GUI 入口）

- **決策**：採 Obsidian 的「**vault 概念 / Markdown source of truth / YAML frontmatter / per-vault config 資料夾**」設計慣例，但 syntax 以 gbrain 為準（不保證 Obsidian app 能直接開啟）
- **關鍵 reasoning（使用者補強，2026-05-25）**：**保持設計自由度高，因為 Claude Desktop 已經是現成的 GUI 入口**
  - 透過 MCP server，顧問可直接在 Claude Desktop 的聊天介面操作 susr brain（查、寫、合成、跑 SOP）
  - 不需犧牲 schema 自由度去遷就 Obsidian 的 wikilink/plugin 慣例
  - 不需自己花心力建 GUI（短期）
  - 這個觀察反向強化 Q5（AI 模型策略）→ 綁定 Claude 變得更合理
- **取捨**：放棄「Obsidian 直接開啟」的甜頭，換取與 gbrain 對齊不妥協 + Claude 生態深度整合
- **GUI 路徑優先級**：
  1. **Claude Desktop + MCP**（現成，零開發成本，顧問已熟）
  2. **Claude Code**（顧問內 dev-friendly 成員 / 進階操作）
  3. CLI（susr 命令列）
  4. （後續評估）Lightweight web / Tauri — 僅當 Claude Desktop 無法覆蓋的場景才考慮
- **與三原則對齊**：仍符合 Definition「可驗證、可比較、可信任」（Markdown + git diff 仍然成立），不影響 Co-pilot 定位

### 2026-05-25 · gbrain 路線確定：Plan B（純參考設計，自己重寫）

- **背景**：Q6 subagent 完成 gbrain 深研，報告於 `docs/research/gbrain-survey.md`（4,800 字 + Mermaid + 8 risks）。Agent 原推薦 Plan C（import as dependency），使用者選擇 **Plan B 純參考、自己重寫**
- **決策**：**學習 gbrain 已驗證可行的架構模式（pgvector + hybrid search + RRF + page_versions + MCP），自己重寫**。不 fork、不 import 為依賴
- **使用者的 reasoning**：「**沒有要繼承什麼，學習好的部分，學習人家已經大量驗證可行的架構**」— gbrain 的 spec-impl gap 是工程風險（招牌功能僅存在 markdown 指令未實作）；但它驗證可行的架構模式才是真值錢的東西。Plan B 讓我們吸收後者、規避前者
- **代價**：多寫一層工程（hybrid search / RRF / page_versions / MCP server），但這些技術選型都有現成開源組件（pgvector / Postgres FTS / RRF 數學十行可寫 / MCP 官方 SDK），重寫成本可控且換來純淨的 codebase
- **戰術級 aha 仍適用**：gbrain 的 `compiled_truth` 在橫線上、`timeline` 在橫線下 = **ESG「結論 + 證據鏈」揭露結構的完美對應**。Restatement > 5% 揭露變成 timeline 多一行。**我們要 mirror 這個資料形狀，不需要 mirror gbrain 的實作**
- **執行三步驟**（取代 survey §7 原方案；**⚠️ 儲存層與 repo 結構已於同日後續對話修正，見「工程選型」決策**）：
  1. 設計 brain 核心：自寫 BrainEngine + Markdown source of truth + page_versions  ← ~~Postgres + pgvector~~ **改 SQLite + sqlite-vec + FTS5（見決策 2）**
  2. 從 **Phase 3 重大性評估**開始試做（susr 差異化最深的地方），沿用力麗 5364 example 當 test fixture
  3. 把現有 `references/*.md` 轉成 `shared_kb/` 知識庫的 markdown pages  ← ~~獨立 git repo，submodule 進 client repo~~ **改放 mono-repo 內 packages/susr/susr/shared_kb/，pip ship + snapshot copy（見決策 3）**
- **8 個未決風險**（survey §8）：embedding 模型對中文 ESG 表現？個資/embedding 送 OpenAI 的合約風險？iXBRL 標記預留？...詳見 survey 原文（PGLite scale 限制已 moot，因 SQLite 決策取代）
- **與 Q4 決策的補強**：survey §6 confirm 我們 per-client repo 方向（gbrain 方案 A）  ← ~~`shared/` 用 git submodule 同步~~ **改用 snapshot copy（見決策 3）**

### 2026-05-25 · Client 內部架構：entities + projects 混合（Option C）

- **背景**：永續報告書是**年度循環**，client 是「持續關係」而非「單次交付」。需要支援同一 client 多年度報告 + 非報告書案（盤查 / CDP / SBTi）
- **決策**：採 **Option C** — client repo 內分「常駐 entities + 年度 projects + 跨年 sourcedocs」三層
- **結構**：
  ```
  clients/<client-slug>/
  ├── _client.md                              ← 公司 profile / 邊界 / 聯絡人
  ├── entities/                                ← 常駐實體（跨年共享，gbrain entity-as-page）
  │   ├── topics/        ← 議題池常駐
  │   ├── stakeholders/  ← 利害關係人常駐
  │   ├── governance/    ← 治理結構（迭代）
  │   ├── kpis/          ← KPI 定義常駐 + values_by_year[]
  │   └── targets/       ← 目標常駐 + progress_by_year[]
  ├── projects/                                ← 年度交付（每個 = 一個 deliverable）
  │   ├── YYYY-sustainability-report/
  │   │   ├── _project.md   ← scope / period / framework_version
  │   │   ├── scoping.md
  │   │   ├── materiality-YYYY.md
  │   │   ├── datapoints/
  │   │   ├── chapters/
  │   │   ├── research-log.md
  │   │   ├── gap-analysis.md
  │   │   └── output/       ← Word/PDF/PPTX 交付物
  │   ├── YYYY-scope3-baseline/   ← 非報告書案 OK
  │   └── YYYY-cdp-filing/        ← 非報告書案 OK
  └── sourcedocs/                              ← 原始文件按年歸檔（跨 project reuse）
      └── YYYY/
  ```
- **核心原理**：
  - `entities/` = client 的「**腦**」，跨年常駐
  - `projects/` = client 的「**交付**」，每次一個 deliverable
  - `sourcedocs/` = client 的「**原料**」，按時間歸檔可跨 project reuse
- **「新年度報告書」工作流**：
  1. `cp -r projects/YYYY-sr/ projects/YYYY+1-sr/` ← fork baseline
  2. `_project.md` 改 framework_version（如 ISSB 升級）
  3. 議題重評：`entities/topics/*.md` 加上新年度 assessment
  4. KPI：`entities/kpis/*.md` 加上新年度 values
  5. Restatement：`entities/kpis/<x>.md` 標 `restated_from` edge
  6. `chapters/` 從上年 fork 後改 deltas
- **與三原則對齊**：呼應 Definition §4「信任與驗證」（每個 entity 都有 timeline 證據鏈）、Product Structure 智能層（entity graph 是智能層的資料骨架）
- **與已有資產對齊**：力麗 5364 example（`examples/lealea-5364/`）作為 Phase 3 試做的 test fixture 時，應用此結構重新組織

### 2026-05-25 · AI 模型策略（Q5）：階段式 — 現以 Claude Desktop 為主，未來自家 GUI + multi-agent CLI

- **決策（階段式）**：
  - **Phase A（現在 → MVP / PMF）**：基於 **Claude Desktop + MCP**，讓不擅長 agent CLI 操作的顧問也能用聊天介面操作 susr brain。GTM 戰術上**短期綁定 Claude 生態**，以加速 PMF 驗證
  - **Phase B（PMF 後）**：發展**自家 GUI**（lightweight web / Tauri）+ 支援**多種 agent CLI**（Claude Code / Cursor / Windsurf / 其他 IDE agent）。模型不可知化
- **使用者原話**：「q5 先基於 claude desktop 方便不擅長 agent cli 操作的顧問們學習和使用。未來我們發展自己的 gui 以及支援多種 agent cli」
- **架構含意**：
  - 短期：MCP server 是 GUI 入口（透過 Claude Desktop 渲染聊天 + tool use）
  - 中長期：susr 內部需建立**模型抽象層**（避免把 Claude prompt 寫死進 domain logic）；MCP 暴露面要保持與 agent host 解耦
  - Embedding 模型獨立決策（見 Q7 / Q8）— 不必跟 LLM 綁同一家
- **與三原則對齊**：
  - Target「顧問用」→ Claude Desktop 的低門檻是 PMF 加速器
  - Co-pilot 定位 → multi-agent CLI 反而是 Co-pilot 路線一致的長期表達（顧問用什麼 agent 都能放大）
- **隱含的工程紀律**：所有 LLM 呼叫從 day 1 就走抽象層（即使初期只接 Anthropic）；prompt 模板與 model-specific syntax 隔離

### 2026-05-25 · Workspace / Repo 結構：per-client repo + 單向 KB 闘

- **背景**：Q4「資料邊界與隱私」在 local-first 形態下重新定義為「顧問本機如何隔離多 client」
- **決策 1（Git 邊界）**：採 **per-client 獨立 git repo**
  - 每個 client 是獨立 git repo，可推到不同 remote（包含 client 自有 git）
  - 顧問 workspace root 包含：`consultant-kb/`（獨立 repo）+ `clients/<name>/`（每個是獨立 repo）+ `.susr/`（local index DB）
  - 跨 client 查詢透過 `.susr/` index DB 聯邦，不靠單一 git tree
- **決策 2（KB 信息流）**：**單向闘 — consultant-kb → client，反向需手動 anonymize + review**
  - Client project 可讀 consultant-kb（方法論/框架/匿名案例）
  - Client 資料不能自動流入 consultant-kb；要「提煉某 client 經驗為方法論」必須：手動匿名化 → reviewer 審核 → 顯式 commit to consultant-kb
  - 工具層強制：MCP tools 層分開暴露 `read_consultant_kb` 與 `promote_to_kb`（後者必須 confirm + 留 audit trail）
  - Client 之間絕不互通（hard rule）
- **與三原則的對齊**：
  - Definition §4「信任與驗證」：git repo 邊界 + audit trail 提供物理層信任
  - Target「保留 100% 專業判斷與責任」：闘的存在防止 AI 自動「跨用」客戶資料造成顧問責任風險
  - Product Structure §顧問專屬功能「顧問公司 KB」：consultant-kb 就是這層的具體實現
- **survey 後的補強**（2026-05-25 同日 gbrain survey §6 回報；**⚠️ 後續對話再次修正，詳見「工程選型」決策**）：
  - ~~`shared/` 獨立於 client repo，用 git submodule 同步進每個 client repo~~ → **改 snapshot copy（決策 3）**
  - 顧問的「腦」三部分組成：**客戶私有（per-client repo）+ 顧問公司共用（consultant-kb）+ shared snapshot（pip ship）**
  - ~~Postgres backing 採 Per-client PGLite~~ → **改 SQLite + sqlite-vec（決策 2）**；資料模型仍保留 `tenant_id` 欄位作未來團隊版退路
- **仍未決**：
  - `.susr/db.sqlite` 的細部 schema
  - 跨 client 「我服務過 5 家觀光業，共通議題?」查詢的合規邊界（哪些匿名化後可 reuse？）
- **下一步**：見 dashboard pivot backlog

### 2026-05-25 · 測試紀律 bootstrap（Layer 1 + Layer 2）

- **背景**：使用者問「能否加入單元測試或場景測試」。回答：**現在這個時間點加最划算**，因為 gbrain spec-impl gap 教訓直接適用
- **決策**：
  - 採 pytest 作為測試框架（cross-platform、不綁定 susr-brain 實作語言）
  - 五層測試結構（見 §6.2）
  - **Hard rule（§6.1）寫進 CLAUDE.md 主條文**：任何宣稱 feature 必有對應測試
  - Layer 1 + Layer 2 today bootstrap；Layer 3 / 4 隨 susr-brain Step 1；Layer 5 後期
  - 用 GitHub Actions 跑 ubuntu-latest + Python 3.11
- **執行方式**：4 個 subagent 並行 dispatch（tests/ scaffold / Layer 1 lint / Layer 2 scenario / CI workflow），非交集檔案邊界
- **三原則對齊**：直接服務 Definition §4「信任與驗證」— 對使用者誠實的前提是先對自己誠實

### 2026-05-25 · MVP 第一刀（Q1）：Phase 3 重大性評估

- **背景**：所有架構決策收斂後（Plan B susr-brain / Option C client 結構 / Claude Desktop 入口 / lealea 5364 fixture），需定義 MVP 第一刀切點
- **決策**：MVP v0.1 = **Phase 3 重大性評估（Materiality Assessment）端到端**
  - 用 Option C 結構重組 `examples/lealea-5364/`（entities/topics/ + projects/2025-sr/materiality-2025.md）
  - 自寫 brain 最小核心（**SQLite + sqlite-vec + FTS5 + hybrid search RRF + 基本 page_versions**，見工程選型決策 2）
  - MCP server 暴露 Phase 3 相關 tools（議題池檢索 / 雙軸評分 / 矩陣產生 / 利害關係人議合輔助）
  - 入口為 Claude Desktop，顧問可用聊天介面跑完 Phase 3
- **為何選 Phase 3 為第一刀**（survey §7 觀察）：
  1. susr 與 gbrain 差距最大、價值密度最高
  2. 顧問痛點集中（雙軸評分 + 利害關係人議合常吃掉 40-80h 的 30%+）
  3. Output 是 deliverable（materiality matrix），客戶端可見、易驗證
  4. 不依賴 Phase 4 GHG 計算引擎（最複雜）或 Phase 6 文件組裝（最多 sub-skill 依賴）
  5. 力麗 5364 example phase3-materiality.md 已是 13KB 完整 fixture
- **不在 v0.1 範圍**：
  - Phase 1/2（用既有 SKILL.md SOP guidance 即可，不需 brain）
  - Phase 4 GHG 計算引擎（複雜度極高，獨立 milestone）
  - Phase 6 文件組裝（依賴 docx/xlsx/pptx sub-skills，獨立 milestone）
  - 顧問 KB 跨年 reuse（先單 client 單年）
- **成功指標**：顧問可在 Claude Desktop 內，用對話方式對 lealea 5364 跑完 Phase 3，產出含雙軸評分 + 矩陣 + IRO 對應的 materiality matrix；通過 Layer 2 scenario test

### 2026-05-25 · 工程選型：Python + 單 package + SQLite + Skill/Brain 並行

本節記錄一輪密集對話收斂的多項工程決策。**多次自我修正**（Postgres → SQLite、shared-kb 獨立 repo → mono-repo 內、3 packages → 1 package、加 CLI → 不加 CLI）— 都是使用者戳到我預設假設的弱點後改進。

#### 決策 1 — 語言：Python

- 主因：ESG 領域 80% 硬骨頭在 pandas / openpyxl / PDF / 排放因子計算 / scientific computing — Python 生態無可取代
- 次因：與既有 pytest 測試 + Phase 4 GHG 計算 + Phase 6 xlsx 整合自然連貫
- 放棄：與 gbrain TypeScript 1:1 對應的便利（Plan B 本來就不需要）
- 代價：MCP server DX 比 TS 略差（可接受，Python SDK 完整）

#### 決策 2 — 儲存引擎：SQLite + sqlite-vec（不是 Postgres）

- **使用者原話**：「得考慮 zero postgres，他們沒辦法搞 docker」
- **改動**：原本默認 Postgres + pgvector（因為 gbrain 用 Postgres）— 但 Plan B 不需要綁定引擎
- **新選擇**：SQLite + sqlite-vec + FTS5
- **理由**：
  - 顧問 `pip install susr` 後零安裝（sqlite3 是 Python stdlib，sqlite-vec 是 pip extension）
  - 完全不碰 Docker / Postgres / PGLite — 「PGLite Python binding eval」變 moot
  - 單檔 portable：`.susr/db.sqlite` 在 client repo 內，可 backup / 加密 / 移動
  - SQLite 內建 FTS5 → hybrid search 中的 BM25 拿來就用
  - susr 場景負載估算（幾千到幾萬 pages per 顧問）遠低於 SQLite/sqlite-vec 上限
- **未來退路**：brain 介面層保持抽象，未來團隊版需共用 DB 時可換 Postgres（不影響上層）

#### 決策 3 — Repo 結構：全 mono-repo + 單一 Python package

- **使用者問**：「repo 我們選擇 hybrid 那 data 的部分為啥獨立 repo？」
- **承認原 reasoning 錯誤**：我先前以為 shared-kb「必須」獨立 repo（理由是 git submodule）— 但「shared-kb 內容進 client repo」是真實需求，**不必透過 submodule** 達成
- **新方案**：shared-kb 留在主 mono-repo 內，透過 snapshot copy 機制進 client repo
  ```
  m4ore-skill-susr/                       ← 唯一 mono-repo
  ├── skills/sustainability-report/       ← Claude Code skill（並行獨立）
  ├── packages/
  │   └── susr/                           ← 唯一 Python package
  │       ├── susr/
  │       │   ├── brain/                  ← core engine (SQLite + sqlite-vec + RRF + page_versions)
  │       │   ├── mcp/                    ← MCP server (Phase 3 tools)
  │       │   ├── shared_kb/              ← bundled KB data，ships with pip
  │       │   └── workspace.py            ← create_client_workspace 等共用邏輯
  │       ├── pyproject.toml              ← entry point: susr-mcp
  │       └── tests/                      ← package 內部 Layer 3-4 單元測試
  ├── examples/lealea-5364/
  ├── tests/                              ← 已 bootstrap 的 repo-level Layer 1+2 lint/scenario
  ├── docs/
  └── dashboard.html

  per-client repo (顧問各自位置)：
  ~/work/lealea-5364/                     ← 獨立 git repo
  ├── _client.md
  ├── entities/ projects/ sourcedocs/
  └── shared/                             ← snapshot copy from susr package（不是 submodule）
  ```
- **shared-kb snapshot 機制**：
  - `susr init <client>` 時自動 copy susr package 內最新 shared_kb 進 client repo `shared/`
  - 顧問可用 `susr kb-update <client>`（未來 CLI 命令；MVP 走 MCP tool）主動觸發升級
  - Client repo 內 `shared/` 是 frozen snapshot，可審計、可離線重算（reproducibility）
  - 顧問掌控升級節奏（環境部出新版排放因子時不會自動套，避免回溯影響）

#### 決策 4 — packages 結構：單一 package（不拆 cli）

- **使用者問**：「susr-cli 是什麼？感覺有點意思？但應該不是現在做的吧」
- **使用者直覺正確**：原本提案的 3-package 結構（brain + mcp + cli）對 MVP 過頭
- **新方案**：唯一 `packages/susr/` package，內部模組化但對外是單一 pip install 標的
- **唯一需要的命令列入口**：`susr-mcp`（讓 Claude Desktop 能 spawn）
- **其他 CLI 命令延後**：原本想做的 `susr init` / `susr doctor` / `susr kb-update` **MCP tools 都能取代**（`create_client_workspace` / `health_check` / `update_shared_kb`）— 與「Claude Desktop 是 GUI 入口」決策一致，顧問零 shell 操作
- **CLI 何時補**：post-MVP power user 場景（scripting / batch ingest / migration）— YAGNI 到那時再說

#### 決策 5 — Skill 與 Brain 並行獨立（B 方案）

- Skill（`skills/sustainability-report/`）繼續服務 Claude Code 對話 — 純 SOP guidance
- Brain（`packages/susr/`）服務 Claude Desktop / Cursor / Windsurf — MCP tools
- 兩條路徑獨立、不互引用
- MVP 簡單；既有 skill 不動；brain 專心做好 Phase 3
- 未來 PMF 後再評估整合（讓 skill 在 Claude Code 內 detect 本機 brain MCP server）

#### 顧問 install UX（最終形態）

```bash
pip install susr                # 一次性
# 設定 Claude Desktop MCP config 指向 susr-mcp（一次性）
# 之後全部對話操作，零 shell 指令
```

#### 工具鏈

- Package manager: **uv**（最新最快，pyproject.toml 標準）
- Python: **3.11**（已是 CI 版本）
- DB: **SQLite + sqlite-vec + FTS5**（零安裝）
- MCP SDK: `mcp` 官方 Python package
- Test: pytest（已 bootstrap）

#### 與三原則對齊

- Definition「可驗證、可比較、可信任」→ Python pandas 對量化資料可審計性最強；SQLite 單檔可備份
- Target「顧問用」→ pip install + zero-Postgres + 零 CLI = UX 門檻最低
- Product Structure 三層架構 → 全 Python，無跨語言邊界
- Co-pilot 定位 → MCP-only 操作 = Claude Desktop 自然語言為主，符合 Q5

### 2026-05-25 · iXBRL / ESEF schema 預留（Q16）

- **背景**：survey §8 風險 #6 — 金管會 2028 強制 ISSB 後可能要求結構化標記（iXBRL / ESEF）。schema migration 影響歷史資料，建議 Step 1 就預留
- **決策**：**預留空欄位，後續再做實作**
  - Step 1 spike 在 `DataPoint` 與 `KPI` schema 上加 `xbrl_concept` nullable 欄位
  - 不寫值、不驗證、不 lint 強制
  - 純粹「未來不必動 schema 即可填值」的容量預留
- **延後到何時實作**：金管會 2028 ISSB 時程明朗後（具體強制範圍 / 標記細則 / 驗證機制公告後）再做：
  - 實際填值機制（從 GRI/ISSB code → xbrl_concept 對應）
  - iXBRL 渲染（Phase 6 文件組裝）
  - ESEF 驗證（Phase 7 gap analysis）
- **與三原則對齊**：Definition「可比較」未來能精準對應 ISSB 結構；不影響當下 Co-pilot 定位
