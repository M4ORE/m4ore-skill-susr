# Lealea 5364 · docx skill 端到端 walkthrough

**日期**：2026-05-25
**狀態**：⚠️ **設計文件 / 半驗證** — payload 端（susr brain）已驗，渲染端（document-skills:docx）的串接**待 design partner 顧問本機跑**。

**對照**：
- `docs/walkthroughs/lealea-5364-phase6-r6.md` — Phase 6 payload prep tools 端到端驗證（**brain 端已綠**）
- `packages/susr/susr/mcp/tools/phase6.py` — `prepare_docx_payload` 實作 + `invocation_hint`
- `skills/sustainability-report/references/phase6-docx-prompts.md` — docx skill 約束與標準結構（§1, §2）
- `examples/lealea-5364/projects/2025-sustainability-report/output/docx-payload.json` — 真實 payload 範例（46 KB / 448 行）

---

## 0. TL;DR（≤150 字）

susr 出 docx 有**兩條路徑**：

1. **草稿路徑** — `render_docx_simple`（brain 內建，python-docx 渲染）：適合內部 review / 顧問 demo / 客戶第一輪 walk-through。
2. **精修路徑**（本文件）— `prepare_docx_payload` + `document-skills:docx` skill（docx-js 渲染）：適合投資人版 / 監管揭露版 / 對外正式定稿。

精修路徑步驟：**Claude Code 載入 client workspace → 跑 `prepare_docx_payload` → 把 payload 餵給 docx skill → 出檔到 `projects/<year>-sustainability-report/output/Report_<year>.docx`**。

**30 秒讀者要看的價值**：你不必自己組 docx — brain 把 67 pages 的 entity 圖（5 章 + 14 IRO + 9 KPI + 6 target）一次拿出來，docx skill 把它變成 Word 文件，你顧問的時間花在審內容、不是排版。

---

## 目錄（TOC）

- [1. 兩條 docx 產出路徑比較](#1-兩條-docx-產出路徑比較)
- [2. 環境準備](#2-環境準備)
- [3. 步驟 A：用 brain MCP tool 出 payload](#3-步驟-a用-brain-mcp-tool-出-payload)
- [4. 步驟 B：把 payload 餵給 docx skill](#4-步驟-b把-payload-餵給-docx-skill)
- [5. 預期輸出檢查清單](#5-預期輸出檢查清單)
- [6. 驗收狀態](#6-驗收狀態)
- [7. 與其他 walkthrough 的關係](#7-與其他-walkthrough-的關係)
- [8. 已知限制 / Open questions](#8-已知限制--open-questions)

---

## 1. 兩條 docx 產出路徑比較

| 屬性 | `render_docx_simple`（內建草稿） | `document-skills:docx`（Claude Code 精修） |
|---|---|---|
| 入口 | Claude Desktop / MCP（susr-mcp）| Claude Code（CLI agent） |
| 渲染引擎 | python-docx | docx-js (Node) — `npm install -g docx` |
| 設定成本 | pip install susr 即用 | 需有 Claude Code + docx skill 環境（Node + LibreOffice + pandoc） |
| TOC 頁碼 | 需 Word 打開後 F9 手動更新 | docx-js field 寫入，開檔後 Word 自動算 |
| 表格樣式 | bordered 預設 + theme color | richer themes、column-width 細控 |
| 圖表嵌入 | 只能引用 SVG（顧問或 Word 後手嵌入） | docx-js chart object（原生） |
| 中文字型 | python-docx 設 `rPr/rFonts`（顧問本機字型決定）| skill prompt 指定 Noto Sans TC / Arial |
| 適合場景 | **草稿 / 內部 review / 顧問 demo** | **投資人版 / 監管揭露 / 對外正式** |
| 是否經本文件驗證 | 由 Agent A code 驗證 | **半驗證**（payload OK，渲染待顧問本機跑） |

**決策建議**：每個 client 第一年用草稿路徑跑通流程，第二年起對外版本走精修路徑。兩條路徑共用 `DocxPayload` schema，切換無摩擦。

---

## 2. 環境準備

### 2.1 安裝 susr（一次性）

依 `README.md`「快速開始」章節：

```bash
pip install susr
# Claude Desktop / Claude Code MCP config 加入 susr-mcp 入口
```

### 2.2 確認 Claude Code 環境有 docx skill

在 Claude Code 內：

```
/skills list
```

預期看到 `document-skills:docx`。若沒有，依 `https://raw.githubusercontent.com/anthropics/skills/main/skills/docx/SKILL.md` 安裝步驟：

```bash
npm install -g docx
# LibreOffice headless（讀取既有 docx 用）：依 OS 安裝 soffice
# pandoc：依 OS 安裝
```

### 2.3 確認 lealea fixture 已 ingest 到 brain

```
（在 Claude Code 內，已連 susr MCP server）
顧問：「載入 examples/lealea-5364/ 到 brain」

→ Claude invoke create_client_workspace + ingest_directory
→ 預期 67 pages（62 entities + 5 chapters）；同 R6 walkthrough §1
```

> ⚠️ 注意：lealea fixture 在 `examples/`，正式顧問案例會在顧問自己 workspace 的獨立 git repo（見 CLAUDE.md §8「Workspace / Repo 結構」決策）。本 walkthrough 借 fixture 示範。

---

## 3. 步驟 A：用 brain MCP tool 出 payload

### 3.1 顧問端 dialog 範例

```
顧問：「準備力麗 5364 的 2025 報告書 docx payload」

Claude（invokes `prepare_docx_payload`）：
{
  "client_slug": "lealea-5364",
  "year": 2025
}

→ Returns DocxPayload (46 KB JSON)

Claude 回覆顧問：
「Payload 已備齊：
- 5 個章節（_skeleton, customer-privacy, food-safety,
  local-indigenous, tcfd）
- 14 個 IRO entity
- 9 個 KPI（其中 8 有 latest_value）
- 6 個 target
- 重大性矩陣：9 核心議題 + 14 重大議題
- GRI Content Index 連結：待 Phase 7 產出

invocation_hint：
請呼叫 document-skills:docx skill 建立 Report_2025.docx。
輸出路徑：<workspace>/projects/2025-sustainability-report/output/Report_2025.docx
Workflow：建立新檔 → docx-js (Node)。
章節結構：依本 payload chapters[] 與 phase6-docx-prompts.md §2 標準。
樣式約束：表格 WidthType.DXA、條列 LevelFormat.BULLET（不要 unicode 圓點）；
中文 Noto Sans TC、英文 Arial。
附錄 A GRI Content Index 來源：尚未產生 — 請先跑 Phase 7

是否進入步驟 B（呼叫 docx skill）？」
```

### 3.2 Payload shape（節錄真實 fixture）

來源：`examples/lealea-5364/projects/2025-sustainability-report/output/docx-payload.json`（448 行）

```json
{
  "document_type": "sustainability_report",
  "client": {
    "slug": "lealea-5364",
    "legal_name": "力麗觀光開發股份有限公司",
    "industry": "hospitality",
    "stock_code": null
  },
  "reporting_period": "2025-01-01..2025-12-31",
  "frameworks": ["GRI 2021", "ISSB", "TWSE-FSC"],
  "chapters": [ /* 5 chapters, 每個含 title / slug / content_md / order / framework_refs / owner */ ],
  "materiality_matrix": {
    "embedded_svg": "",  // 待跑 Phase 3 tool 3 generate_materiality_matrix
    "core_topics": [ /* 9 個 slug */ ],
    "material_topics": [ /* 14 個 slug */ ],
    "tier_overrides": []
  },
  "iros": [ /* 14 個，含 iro_type / topic_slug / time_horizon / financial_magnitude */ ],
  "kpis_summary": [ /* 9 個，含 latest_value / latest_year / yoy_change_pct */ ],
  "targets_summary": [ /* 6 個，含 baseline_year / target_year / verification_path */ ],
  "gri_content_index_ref": null,
  "annex": { "project_slug": "2025-sustainability-report" },
  "invocation_hint": "..."
}
```

**關鍵設計**：`invocation_hint` 是給 caller（Claude 自己）的下一步 prompt 雛形 — 不是給顧問看的。顧問看到的應是 Claude 已經消化過的「我準備好做什麼」摘要（如 3.1）。

---

## 4. 步驟 B：把 payload 餵給 docx skill

### 4.1 顧問端 dialog 範例

```
顧問：「OK，呼叫 docx skill 出檔」

Claude（讀 payload.invocation_hint，invoke document-skills:docx）：
「我會建立新 docx。Workflow：docx-js（Node）。

執行：
1. 載入 payload.chapters[]（5 章）作為主結構
2. 套用 phase6-docx-prompts.md §2 標準章節順序
   （封面 → 目次 → 1 報告書概述 → 2 治理 → ... → 7 附錄）
3. 將 payload.iros[] 渲染為附錄 IRO 對照表
4. 將 payload.kpis_summary[] 渲染為附錄 KPI 對照表
5. 將 payload.targets_summary[] 渲染為附錄目標進度表
6. materiality_matrix.embedded_svg 為空 — 跳過矩陣圖
   （請先跑 generate_materiality_matrix 補 SVG）
7. 樣式：WidthType.DXA / LevelFormat.BULLET / Noto Sans TC + Arial
8. 輸出到 <workspace>/projects/2025-sustainability-report/output/Report_2025.docx

預估時間：30-60 秒。」

→ docx skill 跑 docx-js
→ 產出 Report_2025.docx

Claude 回覆：
「Report_2025.docx 已產出。建議顧問檢查：
- 在 Word 內開檔後按 F9 更新 TOC 頁碼
- 矩陣圖目前為空 — 請補跑 generate_materiality_matrix
- GRI Content Index 附錄為空 — 請補跑 Phase 7」
```

### 4.2 docx skill 的關鍵約束（quote from `phase6-docx-prompts.md` §1）

| 約束 | 規則 |
|---|---|
| 輸入格式 | 自然語言 + **絕對檔案路徑**，**不接受 JSON 結構化輸入** |
| Workflow 分流 | **建立新檔** → docx-js（Node）；**讀取既有** → pandoc 或 unpack.py；**編輯既有** → unpack XML → Edit → pack.py |
| 表格寬度 | **只能用 `WidthType.DXA`** |
| 條列符號 | **用 `LevelFormat.BULLET`**，不要用 unicode 圓點 |
| 環境依賴 | LibreOffice + pandoc + `npm install -g docx` |

**這意味著 Claude 必須把 payload JSON「翻譯」成自然語言指令**給 docx skill。skill 本身不會直接 parse 我們的 schema —— **這是本路徑的工程關鍵**，也是 §8 第 1 條 open question 的來源。

### 4.3 Invocation hint 原文（`packages/susr/susr/mcp/tools/phase6.py:653-662`）

```
請呼叫 document-skills:docx skill 建立 Report_{year}.docx。
輸出路徑：{client_path}/projects/{resolved_project}/output/Report_{year}.docx
Workflow：建立新檔 → docx-js（Node）。
章節結構：依本 payload chapters[] 與 phase6-docx-prompts.md §2 標準。
樣式約束：表格 WidthType.DXA、條列 LevelFormat.BULLET（不要 unicode 圓點）；
中文 Noto Sans TC、英文 Arial。
附錄 A GRI Content Index 來源：{gri_ref or '尚未產生 — 請先跑 Phase 7'}
```

---

## 5. 預期輸出檢查清單

顧問拿到 `Report_2025.docx` 後應逐項確認：

| # | 檢查項 | 預期 |
|---|---|---|
| 1 | 封面 | 含 `client.legal_name`（「力麗觀光開發股份有限公司」）+ 報告期間（「2025-01-01..2025-12-31」）+ 適用框架（GRI / ISSB / 金管會） |
| 2 | 目次 | Word 打開後 F9 / 自動更新可正確填頁碼；7 大章 + 附錄全列 |
| 3 | 章節內容 | 5 個章節皆渲染（_skeleton / customer-privacy / food-safety / local-indigenous / tcfd）— 中文無亂碼、表格未崩、條列符號正確 |
| 4 | IRO 附錄 | 14 行表格（impact / risk / opportunity 分類），含 topic_slug + time_horizon + financial_magnitude |
| 5 | KPI 附錄 | 9 行表格 + framework_refs + latest_value / latest_year / yoy_change_pct |
| 6 | Target 附錄 | 6 行表格 + baseline / target_year / verification_path |
| 7 | 字型 | 中文 Noto Sans TC（或 macOS 系統 fallback）、英文 Arial |
| 8 | 頁尾頁碼 | 自動編號 |
| 9 | 矩陣圖 | **本次為空**（待跑 Phase 3 tool 3）；docx 內留位置 / 顯示提示文字「待補」 |
| 10 | GRI Content Index | **本次為空**（待跑 Phase 7）；附錄 A 顯示 placeholder |

**最後一道顧問判斷**：開啟後通讀一次。susr brain 給的是**結構與證據鏈**，最終語氣 / 揭露策略 / 反綠檢查仍是顧問的責任（呼應 CLAUDE.md §1「Co-pilot ≠ Replacement」）。

---

## 6. 驗收狀態

⚠️ 本 walkthrough 為**設計文件 + 半驗證紀錄**。已驗 vs 待驗：

| 驗收項 | 狀態 | 證據 |
|---|---|---|
| Payload 完整性（99 pages ingest + 14 IRO + 9 KPI + 6 target） | ✅ 已驗 | `lealea-5364-phase6-r6.md` §3、`docx-payload.json` 448 行 |
| `prepare_docx_payload` tool 行為（chapters / iros / kpis / targets / matrix 載入正確） | ✅ 已驗 | Layer 4 單元測試 + R6 walkthrough |
| `invocation_hint` 文字內容（路徑 / 樣式約束 / 框架 / GRI ref 處理） | ✅ 已驗 | `phase6.py:653-662` + 對應測試 |
| document-skills:docx 可從 Claude Code `/skills list` 看到 | ⏳ **待顧問本機驗** | 取決於顧問是否依 docx skill SKILL.md 完成 Node + LibreOffice + pandoc 環境 |
| 渲染後 `.docx` 開啟可讀，無亂碼、中文字體正確 | ⏳ **待顧問本機驗** | 受顧問本機字型 + Word 版本 + skill prompt 解讀力影響 |
| TOC 按 F9 / 自動更新後頁碼正確 | ⏳ **待顧問本機驗** | docx-js field 寫入 + Word 計算 |
| `invocation_hint` 內容能讓 Claude 正確 invoke docx skill | ⏳ **待顧問本機驗** | 含**自然語言指令 vs JSON payload 翻譯**（§8 Q1） |
| 真實顧問案例端到端跑通（不是 fixture） | ⏳ **設計合作夥伴階段驗證** | CLAUDE.md §8「首批 design partner」決策 |

**本 walkthrough 對應的下一步**：找一位獨立顧問 / 小型顧問公司願意把流程跑一輪，回報實際渲染結果 + 對 `invocation_hint` 的改進建議。

---

## 7. 與其他 walkthrough 的關係

| Walkthrough | 範圍 | 與本文件關係 |
|---|---|---|
| `lealea-5364-phase3.md`（R2） | Phase 3 MVP 第一刀 | brain 端早期驗證；無 docx output |
| `lealea-5364-phase3-r3.md`（R3） | R3 P0 三項補強 | brain 端 ingest / IRO / materiality_tier 端到端；無 docx output |
| `lealea-5364-phase6-r6.md`（R6+R7） | Phase 6 payload prep + Phase 7 gap analysis | **brain 端**端到端綠燈；payload 已就緒；**沒做** docx skill 串接 |
| **本 walkthrough** | docx skill 串接（精修路徑） | 補上 R6 walkthrough 留下的「跨工具 / 跨 host」缺口 |
| `lealea-5364-phase6-builtin.md`（**Agent A 並行寫**） | `render_docx_simple` 內建草稿渲染 | 與本文件並列為**兩條路徑**；共用 payload schema |

**讀者建議**：
- 想看「susr brain 已驗證什麼」→ 讀 R6 walkthrough
- 想看「我（顧問）怎麼出檔」→ 讀本 walkthrough + Agent A 內建路徑文件
- 想看 brain 內部資料模型 → 讀 R2 / R3

---

## 8. 已知限制 / Open questions

以下為**工程上真的還沒答案的問題**（不是裝模作樣的 placeholder）：

### Q1. document-skills:docx 是否認得 `DocxPayload` schema？

**現況**：根據 `phase6-docx-prompts.md` §1，docx skill **不接受 JSON 結構化輸入**，只接受自然語言 + 絕對檔案路徑。
**含意**：步驟 B（§4）中，Claude 必須把 `DocxPayload` JSON **翻譯成自然語言指令**給 docx skill。
**未知**：翻譯品質取決於 Claude 對 payload 的理解 + invocation_hint 的引導力。**是否每次 Claude 翻出來的指令都一致 / 完整 / 符合 phase6-docx-prompts.md §2 標準結構？目前沒有測試覆蓋此翻譯層**。
**建議**：design partner 顧問本機跑時，記錄 Claude 給 docx skill 的實際 prompt，逐步精煉 `invocation_hint`。

### Q2. payload JSON 是否要做 token preprocessing？

**現況**：`docx-payload.json` 46 KB / 448 行；單一章節 `content_md` 可達 7-10 KB。
**未知**：Claude 讀完整 payload + 翻譯給 docx skill 時，是否會在大 prompt 內出現 truncation / hallucination？是否需在 brain 端先 ASCII-fold 中文標點、移除 markdown comments、壓縮 whitespace？
**衝突**：壓縮 → 渲染品質下降（中文標點 / 段落結構）；不壓縮 → token 風險。
**建議**：design partner 跑大型案例（>10 章）時觀察。

### Q3. 跨平台中文字型切換邏輯誰負責？

**現況**：`invocation_hint` 寫死「中文 Noto Sans TC、英文 Arial」。
**未知**：顧問在 Windows 機器跑時，Noto Sans TC 可能不存在 — 應該 fallback 微軟正黑體 / PMingLiU 嗎？
**選項**：
- (a) susr 在 `invocation_hint` 內加 OS 偵測（不可行，brain 不知道 caller OS）
- (b) docx skill 自行 fallback（取決於 docx-js / Word 渲染時機）
- (c) 顧問本機 docx 後處理（不理想）
**建議**：先依 (b) 由 docx skill 自負，本 walkthrough 不約束。

### Q4. 重大性矩陣 SVG 能否被 docx skill 嵌入？

**現況**：`MaterialityMatrixPayload.embedded_svg` 是 SVG 字串。docx-js 對 SVG 直接嵌入支援有限（通常需先轉 PNG）。
**未知**：
- (a) docx skill 是否內建 SVG → PNG 轉換？
- (b) 若不能，是否需要 susr brain 端就轉好（依賴 cairosvg / Pillow）？
- (c) 還是顧問人工開 Word 後手插圖？
**建議**：design partner 階段測試後決定 SVG 處理邊界。

### Q5. document-skills:docx 隨時間演進的 schema 相容性

**現況**：`invocation_hint` 引用 `phase6-docx-prompts.md` §2 標準結構，但 anthropics/skills repo 是活 repo，未來 skill 可能升級 API / workflow。
**未知**：susr `invocation_hint` 與 docx skill 之間沒有版本綁定機制。
**建議**：post-MVP 考慮在 `invocation_hint` 加上「期待的 skill version / commit sha」。

### Q6. 兩條 docx 路徑的選擇判準

**現況**：本 walkthrough §1 給了「草稿 vs 精修」的指引，但**沒有 hard rule**。
**未知**：顧問實務上，第幾輪 review 切換到精修路徑？是不是某些 client（如已上市櫃投資人關係場景）一開始就走精修？
**建議**：累積 3-5 個 design partner 案例後寫成決策樹放回本文件。

---

**End of walkthrough.**
