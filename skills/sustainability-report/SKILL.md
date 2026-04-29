---
name: sustainability-report
description: |
  Sustainability / ESG Report Skill — 永續報告書專業協作大腦，依雙重重大性（Double Materiality）
  與 8-Phase SOP 引導使用者完成從重大性評估到專業檔案輸出的全流程。
  Trigger on: 永續報告書, ESG report, sustainability report, 雙重重大性, double materiality,
  Scope 1, Scope 2, Scope 3, GHG inventory, 溫室氣體盤查, TCFD, ISSB, IFRS S1, IFRS S2,
  GRI, CSRD, ESRS, SBTi, 金管會永續, TWSE 永續, MOPS 公告, 利害關係人議合, IRO, 重大性矩陣,
  排放因子, 範疇三, 轉型計劃, 氣候揭露, 永續治理, 利害關係人, 碳中和, 淨零, net-zero.
  Non-trigger: 純程式開發, 單純財報計算（無永續面向）, 非 ESG 的法遵問題, 個人理財,
  與企業永續無關的環保議題.
  Always load 8-Phase SOP and enforce double materiality as core principle.
  繁體中文優先；輸出檔案需與 docx / xlsx / pptx / pdf skill 整合。
---

# Sustainability Report Skill

**版本**：0.1 (2026-04-29)
**目標**：把「寫一份永續報告書」從每年從零開始的藝術，變成可重複、可審計、可訓練的 8-Phase SOP + 模組化能力組合。

## 核心不可違反原則（First Principles）

1. **雙重重大性（Double Materiality）優先**：所有議題識別必須同時評估
   - Impact Materiality（公司對環境/社會的影響）
   - Financial Materiality（議題對公司財務的風險與機會）
2. **價值鏈邊界明確**：上游 → 自營 → 下游，每個 KPI 都要說邊界
3. **數據可追溯（Auditable）**：每個數字必須有來源、計算公式、版本、責任人
4. **IRO 連結性（Connectivity）**：Impact / Risk / Opportunity → 治理 → 策略 → 行動 → 目標 → KPI 必須首尾貫通
5. **反綠色洗白（Anti-Greenwashing）**：不只報好消息，必須揭露挑戰、未達標、目標調整理由
6. **決策有用性（Decision-Usefulness）**：報告對象是利害關係人決策，不是行銷部

## 自動觸發行為

當對話符合 frontmatter 觸發詞時：

1. **辨識使用者所在 Phase**（若未明說，預設從 Phase 1 開始）
2. **載入對應 reference**（見每個 Phase 的 Integration 段落）
3. **以 SOP 引導推進**，不跳階段、不省略決策點
4. **強制檢查連結性**：產出任何 KPI / 目標 / 章節時，反問「對應到哪個 IRO？哪個治理機制？」

## Phase 0 — Pre-flight Dependencies（前置依賴提醒）

本 skill 在 Phase 4 與 Phase 6 會 orchestrate `document-skills:docx / xlsx / pptx / pdf` 等 sub-skill。這些 sub-skill 各自依賴外部工具，若環境缺失會在中段失敗：

| Sub-skill | 主要依賴（簡列） |
|-----------|----------------|
| docx | pandoc、LibreOffice、`npm install -g docx` |
| xlsx | LibreOffice（用於 recalc）、Python `openpyxl pandas` |
| pptx | LibreOffice、Poppler、Pillow、`npm install -g pptxgenjs` |
| pdf | Python `pypdf pdfplumber reportlab pytesseract pdf2image`、Poppler |

**行為規則**：
- 不在本 skill 維護完整安裝指令清單（容易與 sub-skill 自身文件不同步）
- 在 Phase 1 Scoping 時主動提醒使用者：「Phase 4/6 將呼叫 document-skills，請確認其依賴已安裝（詳見各 sub-skill 自身 SKILL.md）」
- 若 sub-skill 呼叫失敗，不要僅報「執行失敗」；須**檢查錯誤訊息中的工具名稱（如 `pandoc: not found`、`Cannot find module 'docx'`），向使用者明確指出缺失的依賴**並建議安裝來源
- 詳細依賴與安裝指令請參考各 sub-skill 自身 SKILL.md（authoritative source）

## 8-Phase SOP 工作流

### Phase 1 — Preparation & Scoping
- **Objective**：確定報告邊界、適用標準、報告期間、責任分工
- **Key Activities**：
  - 確認適用標準組合（GRI / ISSB / ESRS / 台灣金管會 / 產業 SASB）
  - 定義組織邊界（合併報表 vs 營運控制 vs 股權法）
  - 鎖定報告期間（通常 = 財報期間）
  - 指派各章節 owner 與簽核人
- **Output**：`scoping-decision.md`（一頁式）
- **Integration**：無外部 skill；可呼叫 `WebSearch` 查最新法規版本

### Phase 2 — Research, Benchmarking & External Intelligence
- **Objective**：用外部資訊校準內部認知，避免閉門造車
- **Key Activities**：
  - 同業 peer benchmark（3–5 家最相近公司的最新報告）
  - 法規最新動態（金管會 / TWSE / ISSB / EFRAG）
  - 排放因子最新版本（環境部、IEA、DEFRA、ecoinvent）
  - 投資人 ESG 評等問項（MSCI / Sustainalytics / CDP）
- **Output**：`research-log.md`（含來源、日期、對報告的影響）
- **Integration**：`WebSearch` + `WebFetch`，prompt 模板見 `references/phase2-research-prompts.md`

### Phase 3 — Double Materiality Assessment
- **Objective**：產出當年度的重大性議題清單與矩陣
- **Key Activities**：
  - 從 25–40 項議題池起始（見 `references/materiality-topics-universe.md`）
  - 利害關係人盤點與議合（問卷 / 訪談）
  - 雙軸評分：Impact（嚴重度 × 範圍 × 不可逆性 × 可能性）× Financial（風險規模 × 時間 × 機率）
  - 董事會 / 永續委員會 review 並核准
- **Output**：`materiality-matrix.md` + 議題排序表
- **Integration**：可用 `xlsx` skill 建立評分工作簿

### Phase 4 — Data Collection, Validation, KPI Engineering
- **Objective**：建立可審計的 ESG 數據包
- **Key Activities**：
  - GHG Scope 1/2/3 盤查（見 `references/ghg-protocol.md`）
  - 員工、安全、用水、廢棄物、董事會結構等社會與治理 KPI
  - 內部稽核 / 第三方確信（assurance）前置驗證
  - 基線重述（restatement）規則：> 5% 變動需揭露
- **Output**：`ESG_Data_Pack.xlsx`（含公式、驗證列、註腳、來源）
- **Integration**：`xlsx` skill，prompt 模板見 `references/phase4-xlsx-prompts.md`

### Phase 5 — Content Drafting & Narrative
- **Objective**：把數據與重大議題寫成連結性強的章節敘事
- **Key Activities**：
  - 依重大性議題建立章節骨架（不是抄 GRI 目錄）
  - 每個議題章節必含：IRO → 治理 → 策略 → 行動與資源 → 目標 → KPI → 展望
  - E1 Climate（含轉型計劃、scenario analysis）為強制章節
  - 反綠色洗白檢查：揭露挑戰與未達標
- **Output**：各章節 Markdown 草稿
- **Integration**：無；交由 Phase 6 組裝

### Phase 6 — Report Assembly & Professional Output
- **Objective**：把草稿與數據包組裝成專業檔案：報告書 docx/pdf + 董事會/投資人 pptx
- **Key Activities**：
  - docx：封面、目次、running header、各章節、Content Index、附錄
  - pdf：高解析度輸出，預留 iXBRL / ESEF 標記欄位
  - pptx：投資人版（10–15 頁）、董事會版（5–8 頁）
- **Output**：`Report_YYYY.docx` / `.pdf` / `Investor_Deck.pptx` / `Board_Deck.pptx`
- **Integration**：
  - `docx` skill，prompt 見 `references/phase6-docx-prompts.md`
  - `pdf` skill，prompt 見 `references/phase6-pdf-prompts.md`
  - `pptx` skill，prompt 見 `references/phase6-pptx-prompts.md`

### Phase 7 — Review, Gap Analysis, Assurance Readiness
- **Objective**：確保符合度、連結性、可確信性
- **Key Activities**：
  - 合規檢查清單逐項過（見 `references/compliance-checklist.md`）
  - GRI Content Index / ESRS datapoint mapping
  - 第三方確信前置會議（confirm 範圍、文件清單）
  - 法務 / 投關 / 永續委員會三方 review
- **Output**：`gap-analysis.md` + `assurance-readiness-checklist.md`
- **Integration**：無外部 skill

### Phase 8 — Finalization, Filing & Continuous Improvement
- **Objective**：完成報送、紀錄改進建議、銜接下一年度
- **Key Activities**：
  - MOPS / 公司網站 / 外部平台公告（時程見 `references/taiwan-fsc-sustainability-guidelines.md`）
  - 利害關係人發布（投資人說明會、員工大會、供應商溝通）
  - Year-over-year 比較紀錄
  - 開立下年度改進事項（轉成下個年度的 Phase 1 輸入）
- **Output**：`post-mortem.md` + 下年度 backlog
- **Integration**：無外部 skill

## 與其他 skill 的整合對照表

| Phase | 整合 skill | 說明 |
|-------|-----------|------|
| 2 | WebSearch / WebFetch | 法規、peer、排放因子查詢 |
| 3 | xlsx | 議題評分工作簿 |
| 4 | xlsx | ESG_Data_Pack with formulas |
| 6 | docx | 主報告書專業排版 |
| 6 | pdf | 最終 PDF + iXBRL 預留 |
| 6 | pptx | 投資人 / 董事會簡報 |
| 6 | theme-factory / brand-guidelines | 品牌一致性（如需要） |
| 7 | （無） | 仰賴 reference 內的清單 |

## 台灣上市櫃預設情境

- **適用標準**：金管會「上市上櫃公司編製與申報永續報告書作業辦法」+ GRI Universal Standards 2021 + ISSB（IFRS S1/S2）
- **發布時程**：通常於財報後一定期限內（依規模）發布於 MOPS
- **強制章節**：誠信經營、利害關係人議合、氣候相關財務揭露（TCFD/ISSB 四大構面）
- **語言**：繁體中文 zh-TW 優先；如有海外投資人版本另出 EN

## 反綠色洗白強制檢查（每章節必過）

1. 是否揭露未達標項目與原因？
2. 目標是否含基線、達成時程、驗證路徑？
3. 範疇三是否覆蓋主要類別（不止外購電力與商務旅行）？
4. 董事會 ESG 專業背景是否揭露？
5. 是否有負面事件（罰款、勞資爭議、資安事件）的透明處理？

## 漸進式深度

- **第 1 年**：聚焦合規 + 重大性矩陣 + 高品質 Scope 1/2 + Scope 3 主要類別 + E1 + S1
- **第 2–3 年**：補齊 Scope 3 全類別、轉型計劃量化、scenario analysis、目標 SBTi 認證
- **成熟期**：iXBRL 標記、第三方限定確信→合理確信、TNFD 生物多樣性、價值鏈盡職調查

## References 目錄

```
references/
  esg-glossary-zh-en.md              ← 雙語詞彙表
  compliance-checklist.md            ← 合規檢查清單（Phase 7）
  materiality-topics-universe.md     ← 議題起始池（Phase 3）
  ghg-protocol.md                    ← GHG 計算原則（Phase 4）
  taiwan-fsc-sustainability-guidelines.md ← 台灣法規（Phase 1, 8）
  websearch-pending.md               ← 待查證項目清單（Phase 2 入口）
  phase2-research-prompts.md         ← WebSearch 模板（Phase 2）
  phase4-xlsx-prompts.md             ← Data Pack 結構（Phase 4）
  phase6-docx-prompts.md             ← docx 組裝 prompt（Phase 6）
  phase6-pdf-prompts.md              ← pdf 輸出 prompt（Phase 6）
  phase6-pptx-prompts.md             ← pptx 簡報 prompt（Phase 6）
```

## 回應規範

- 引用任何法規必標註版本與日期（如 `金管會 2026-Q1 修訂版`）
- 引用任何數字必標註來源、計算邊界、單位
- 用詞遵循 `references/esg-glossary-zh-en.md`，不混用同義詞
- 預設繁體中文；專業術語首次出現時加註英文原文
- 若使用者跳階段（如 Phase 1 直接跳 Phase 6），主動提醒風險並建議補做
