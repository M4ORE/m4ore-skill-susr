# Phase 7 — Review, Gap Analysis & Assurance Readiness

**用途**：對照本試做產出（Phase 1–6）vs 力麗觀光 2023 實際報告書（66 頁 PDF），找出 SOP 強項、弱項與後續迭代方向。
**輸入**：
- 試做產出：`phase1-scoping.md`、`phase2-research-log.md`、`phase3-materiality.md`、`phase4-xlsx-skeleton.md`、`phase5-chapter-skeleton.md`、`phase5-tcfd-sample.md`、`phase6-assembly-plan.md`
- 對照基準：`source-2023-report.pdf`（PDF 章節結構摘要見 `phase7-pdf-extract.md`，由 sub-agent 抽取）
**性質**：本試做未取得真實內部數據，Gap analysis 聚焦於**結構性 / 程序性差異**，不糾結於具體數字。

---

## 0. 重大發現（Critical Findings）— 力麗 2023 實際 vs susr SOP 試做差距

> 本試做意外發現：力麗觀光 2023 報告書（中型 TPEx 觀光業，第 3 本）存在**全方位揭露缺口**，遠低於金管會 2026/2027/2028 ISSB 強制適用的標準。
> 這讓 SP1-004 的價值從「驗證 SOP 串連」升級為「直接點出中型上市公司的 gap closing 路徑」。

### 全面差距總表

| 揭露項 | 力麗 2023 實際（PDF 抽取結果） | susr SOP 試做版本 | Gap 嚴重度 |
|---|---|---|---|
| **重大性方法** | 單向 impact materiality（18 議題池→4 重大）| 雙重重大性（28 議題池，Impact × Financial）| 🔴 高 |
| **重大議題清單** | 供應商管理 / 經營績效 / 產品與服務 / 風險管理 | 食安 / 氣候 / 能源 / 隱私 / 在地 / 員工健康等 12+ 項 | 🔴 高 — 缺核心 ESG 議題 |
| **TCFD / 氣候揭露** | **完全缺席**（"TCFD"/"氣候相關" 0 hits）| 完整 4 構面 11 揭露 + 1.5/2/4°C 情境分析 | 🔴 高 — 金管會 2026 加嚴強制 |
| **Scope 1（範疇一）** | 未揭露 | xlsx skeleton 含燃氣 / 公務車 / 廚房 / HVAC 制冷劑 / 發電機 | 🔴 高 |
| **Scope 2（範疇二）** | GRI 305-2 + 305-4 強度，但 8.1 章僅半頁、**無實際數值表** | 雙軌（地點 + 市場）+ T-REC 欄位 | 🟠 中 — 有名無實 |
| **Scope 3（範疇三）** | 未揭露 | C1/C3/C4/C5/C6/C7 + C11 取捨理由 | 🔴 高 |
| **GRI 版本** | 2016 + 102 系列（舊版架構） | GRI Standards 2021 In Accordance（GRI 1/2/3）| 🟠 中 — 落後 5+ 年 |
| **第三方確信** | 明確聲明「本報告書未經外部第三方機構保證或確信」 | Phase 7 §5 確信前置清單已備 | 🟠 中 — 自評為主 |
| **環境章節深度** | 「8 善待環境」**僅 p.44 半頁**（與第 9 章員工同頁） | 篇 3 共 6 子章節（氣候 / 能源 / 水 / 廢棄物 / 食材 / 生物多樣性）| 🔴 高 |
| **連結性公式（IRO → KPI）** | 無此結構；章節敘事為列舉式 | 7 段強制公式（IRO → 治理 → 策略 → 行動 → 目標 → KPI → 展望）| 🟠 中 |
| **未達標誠實揭露** | 無此章節 | Phase 5 TCFD §8 強制揭露未達標 + 原因 + 調整 | 🟠 中 |
| **TWSE / TPEx 公司治理評鑑強化** | p.30–34 治理章節有處理 | Phase 5 篇 7 三章節 | 🟢 低 — 力麗版尚可 |
| **利害關係人議合** | p.7–10，6 類利害關係人，章節合併粗略 | Phase 3 §1–§2 七大類，含議合次數 / 樣本數 | 🟢 低 — 力麗版有做 |
| **GRI Content Index** | p.62–66 完整 | 附錄 A1 規劃中 | 🟢 低 — 力麗版完整 |

### 結論：力麗 2023 是「反向示範」教材

對 susr SOP 開發而言，力麗 2023 是**完美的對照案例**：
- 在 ISSB 強制前的「過渡期典型樣本」，揭露品質代表大量中型 TPEx 上市公司現況
- 能直接作為**教學素材**（什麼不該做、缺什麼）
- 對 SOP 試做：印證 SOP 各 phase 的設計都直接對應力麗版本的具體缺口
  - Phase 3 雙重重大性 → 力麗只做單向 impact
  - Phase 4 Scope 1/2/3 → 力麗只做 Scope 2 殘缺
  - Phase 5 TCFD 完整章節 → 力麗 0 hits
  - Phase 5 IRO 7 段公式 → 力麗列舉式敘事
  - Phase 7 第三方確信前置 → 力麗自評
- 對未來使用者：可作為 sample input 演練「我家公司報告書類似力麗，請幫我升級到 ISSB 標準」

---

## 1. 結構對照（Phase 1–5 試做骨架 vs 力麗 2023 實際章節）

| 試做章節 | 力麗 2023 對應 | 頁碼 | 差異 / 觀察 |
|---|---|---|---|
| 篇 1 關於本報告書 | 第 1 章 | p.3–4 | 力麗版精簡（揭露範疇 / 數據資訊 / 發行時間 / 聯絡資訊）；試做版加 Scenario A/B 邊界揭露、確信狀態欄 |
| 篇 1.2 董事長的話 | 第 2 章 董事長的話 | p.5 | 對等 |
| 篇 2.1 永續治理結構 | 第 4.1 永續發展執行委員會 | p.8 | 力麗版有 4 個工作小組；試做版加董事 ESG 專業 + 高管 KPI 連動 |
| 篇 2.2 利害關係人議合 | 第 4 章 4.1–4.3 | p.7–10 | 力麗版 6 類利害關係人；試做版 7 類加議合次數 / 樣本數 |
| 篇 2.3 雙重重大性矩陣 | 第 5 章 重大議題鑑別 | p.10–13 | **核心差距**：力麗單向 impact / 18→4；試做雙軸 / 28→12+ |
| 篇 3.1 TCFD 氣候揭露 ⭐ | **無對應章節** | — | **完全缺席** — 力麗版 0 hits；試做版完整 4 構面 11 揭露 |
| 篇 3.2 能源管理 | 第 8.1 章（部分）| p.44 | 力麗版半頁無數值；試做版含 GRI 302 + SASB SV-HL-130a.1 |
| 篇 3.3 水資源 | GRI 303 在 Index | — | 力麗版僅列入 GRI Index；試做版含日月潭流域風險 |
| 篇 3.4 廢棄物 | GRI 306 在 Index | — | 同上 |
| 篇 5.1 食安 | 第 7.4 供應鏈 / 食安 | p.41–43 | 力麗版有處理（旅館業核心）；試做版加 HACCP 證書追蹤 |
| 篇 5.2 顧客隱私 | GRI 418 在 Index | — | 力麗版僅 GRI Index 列入；試做版含 ISO 27001 + 資安事件揭露 |
| 篇 5.3 客戶體驗 | 第 7 章 精緻服務 | p.35–40 | 對等 |
| 篇 6.1 在地共融 | 第 10 章 社會關懷 | p.58–61 | 力麗版含棲蘭越野賽 / 公益；試做版加明池泰雅族原民共榮 |
| 篇 7.1 公司治理 | 第 6.3 公司治理 | p.30 | 對等 |
| 篇 7.2 誠信經營 | 第 6.4 誠信經營 | p.30–34 | 對等 |
| 篇 7.3 法令遵循 | 第 6.5 / 6.6 | p.30–34 | 對等 |
| 附錄 A1 GRI Index | GRI 準則內容索引 | p.62–66 | **版本差距**：力麗 2016 / 102 系列；試做 2021 In Accordance |
| 附錄 A3 TCFD Index | **無對應** | — | 力麗版完全沒有 |
| 附錄 A5 確信意見書 | **明確聲明無確信** | p.3, p.62 | 力麗版自行編製；試做版列入 Phase 7 確信前置 |

---

## 2. SOP 強項（Phase 1–6 試做驗證）

### 2.1 結構性連結性（Connectivity）

✅ **每章節 IRO 7 段公式**（Phase 5 TCFD 示範完整）— 強迫敘事從衝擊 → 治理 → 策略 → 行動 → 目標 → KPI → 展望全程連結，無斷鏈。

✅ **跨 phase 數據追蹤**（Phase 5 §11）— TCFD 章節每個數字都標註 xlsx sheet 來源，符合 SOP「數據可追溯」原則。

✅ **雙重重大性嚴格分軌**（Phase 3 §4）— Impact × Financial 各自獨立評分，未混淆。28 議題每個都有兩軸分數。

### 2.2 旅館業特化能力

✅ **委託經營邊界處理**（Phase 1 §2 + Phase 4 Scenario A/B）— 直營三館 vs 含委託全 5 館雙軌設計，解決常見旅館業集團報告書邊界爭議。

✅ **南投山區特殊風險納入**（Phase 5 §1.2）— 物理風險聚焦明池 / 月潭，不只是泛論氣候變遷。

✅ **集團母公司紡織背景處理**（Phase 3 S13 + Phase 4 C1 標注）— 集團內紡織備品（1444/1447）獨立揭露，避免「假在地採購」綠色洗白。

✅ **明池泰雅族原民共榮**（Phase 5 §6.1）— 旅館業常忽略的文化保存議題，本 SOP 主動納入。

### 2.3 反綠色洗白機制

✅ **未達標欄位強制要求**（Phase 5 TCFD §8）— LED 進度落後、Scope 3 缺口都明確列出原因與調整。

✅ **占位符 `[X] [Y] [Z]` 而非假數字**（Phase 5 + Phase 6 prompt）— 試做版未取得真實數據，明確要求保留占位不填，避免誤導。

✅ **基線 / 時程 / 驗證三要素強制**（Phase 5 §6 目標表）— 7 項目標皆具三要素，無「我們要更好」式空泛承諾。

---

## 3. SOP 弱項（待迭代）

### 3.1 內容深度

⚠️ **Phase 5 僅完成 1 個完整章節示範（TCFD）**：食安、隱私、在地三篇高優先章節僅有骨架。Sprint 後續迭代應補完 4 個完整示範章節。

⚠️ **Phase 4 未實際 build xlsx**：依賴 sub-skill 環境，本試做僅產出 skeleton md。真實使用時需驗證 xlsx skill 可正確處理跨 sheet 公式與條件格式。

⚠️ **Phase 6 未實際 build docx / pdf / pptx**：同上，prompt 套裝完備但實機驗證待補。

### 3.2 程序性

⚠️ **Phase 2 同業量化數據抓取困難**：4 家 peer 的 Scope 1/2/3、員工數、用水具體值多為 N/A，因 PDF binary。
- **改善方向**：phase2-research-prompts.md 應加 fallback：「PDF binary 不可解時，改用 ESG 平台（CSRone / SustainAI / ESG Times）摘要 + 自行下載 PDF + pdf skill 抽表格」

⚠️ **Phase 2 資本額誤差**：Agent 寫「~25 億」與實收 6.38 億 / 核定 45 億 不符。已修正。
- **改善方向**：phase2-research-prompts.md 應強制要求「資本額抓 MOPS 公開資訊主檔，不接受估算」

⚠️ **Phase 3 利害關係人議合為模擬**：本試做無真實議合。改善方向：references/materiality-topics-universe.md 應補一份「議合方法決策樹」（公司規模、預算、議題複雜度 → 建議方法組合）。

### 3.3 工具依賴

⚠️ **PDF 讀取依賴 Poppler**：本試做嘗試讀力麗 PDF 失敗（pdftoppm not found）。Phase 0 依賴提醒已預警，但 fallback 機制（純 Python pypdf）未在 SKILL.md 主流程提及。
- **改善方向**：SKILL.md Phase 0 補「PDF 讀取最低依賴」分級（Poppler 最佳；pypdf 純 Python 退而求其次）

---

## 4. 合規檢查（依 references/compliance-checklist.md）

逐項過 60+ 項：本試做先做 high-level 自評，深度檢查待 Phase 6 實機 build 後執行。

| 領域 | 自評 | 備註 |
|---|---|---|
| 雙重重大性方法揭露 | ✅ | Phase 3 §2 議合 + §4 評分公式 |
| 邊界揭露（含營運控制法說明） | ✅ | Phase 1 §2 |
| GHG Protocol Scope 1/2/3 完整性 | ⚠️ | 試做為 skeleton，C11 已有取捨理由（旅館業合理） |
| Scope 2 雙軌（地點 + 市場） | ✅ | Phase 4 sheet `05_GHG_S2` |
| 排放因子版本標示 | ✅ | Phase 4 `01_Versions` 表 + Phase 2 113 年版 0.474 |
| TCFD 4 構面 11 建議揭露 | ✅ | Phase 5 TCFD 章節 §2–§7 |
| 情境分析（1.5°C / 2°C / 4°C） | ✅ | Phase 5 §3.1 |
| 金管會誠信經營強制章節 | ⏳ | Phase 5 篇 7.2 骨架，待補完整內容 |
| 利害關係人議合（金管會強制） | ✅ | Phase 5 篇 2.2 + Phase 3 §1–§2 |
| GRI Content Index | ⏳ | 附錄 A1 規劃中，待 Phase 6 實機 build |
| ISSB datapoint mapping | ⏳ | Phase 1 §3 列為試做選用，附錄 A3 規劃中 |
| 第三方確信狀態 | ⚠️ | 本試做為「自評」，力麗 2023 實際版確信狀態待 Phase 7 PDF 對照 |

---

## 5. 確信前置（Assurance Readiness）

若力麗觀光擬於 2025/2026 啟動第三方確信，依本試做 SOP 應準備：

| 文件 | 狀態 | 對應 |
|---|---|---|
| ESG_Data_Pack.xlsx（含公式 / 來源） | ⏳ skeleton 已備 | Phase 4 |
| 邊界決策紀錄 | ✅ | Phase 1 §2 + §9 假設 |
| 重大性議合方法說明 | ✅ | Phase 3 §1–§2 |
| 排放因子版本控制 | ✅ | Phase 4 `01_Versions` + Phase 2 排放因子段 |
| Restatement log（基線重述紀錄） | ✅ skeleton | Phase 4 `01_Versions` Restatement_Flag |
| Scope 3 取捨理由 | ✅ | Phase 4 C11 註腳 |
| 內部控制與權責分工 | ✅ | Phase 1 §6 + Phase 5 章節主責 |
| 第三方契約預備（範圍書）| ⏳ | 待真實啟動時撰寫 |

---

## 6. SP1-004 結論：SOP 試做驗證

| 驗證項 | 結論 |
|---|---|
| 8-Phase 串連完整性 | ✅ Phase 1–7 prompt 鏈打通；Phase 8 為持續改進，已歸入 walkthrough |
| 連結性公式（IRO → KPI 7 段） | ✅ Phase 5 TCFD 完整示範，可規模化 |
| 反綠色洗白機制 | ✅ 占位符規範 + 未達標強制揭露 + 基線時程驗證三要素 |
| 旅館業特化 | ✅ 委託經營邊界 / HVAC / 食安 / 山區據點風險 / 原民共融 |
| Sub-skill 整合（Phase 4/6） | ⚠️ prompt 套裝完備；實機 build 待真實環境 |
| 對照原版（力麗 2023） | ⏳ 待 `phase7-pdf-extract.md` 完成後逐項填回本檔 §1 |

---

## 7. 對 SP1-001~003 的迭代建議（feedback to SOP）

| 來源 phase | 建議 | 影響檔案 |
|---|---|---|
| 試做 P2 經驗 | peer benchmark 加 PDF binary fallback；資本額抓 MOPS 主檔 | `references/phase2-research-prompts.md` |
| 試做 P3 經驗 | 議合方法決策樹（公司規模 → 建議組合）| `references/materiality-topics-universe.md` |
| 試做 P4 經驗 | xlsx skeleton 中 Scenario A/B 雙軌設計可推廣到其他多據點服務業 | `references/phase4-xlsx-prompts.md` |
| 試做 P5 經驗 | 7 段公式（IRO → KPI）成功，建議在 SKILL.md 主檔加粗強調 | `SKILL.md` |
| 試做 P6 經驗 | sub-skill 失敗模式表（§6）可提升使用者體驗 | `references/phase6-*-prompts.md` 各檔 |
| Phase 0 經驗 | PDF 讀取依賴分級（Poppler 最佳 / pypdf 退階） | `SKILL.md` Phase 0 |

---

待 sub-agent 完成 `phase7-pdf-extract.md` 後，回填本檔 §1 結構對照表的具體章節與頁碼。
