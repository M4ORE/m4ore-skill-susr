# SP1-004 端到端試做 — Walkthrough Notes（Lessons Learned）

**標的**：力麗觀光開發（5364, TPEx, 觀光業, 2023 年度報告書 66 頁）
**期間**：2026-04-30（單日試做）
**性質**：susr 8-Phase SOP 端到端驗證，**不是**真要寫力麗的報告書
**輸出**：`examples/lealea-5364/` 下 8 個產物（phase1–phase7 + 本檔）

---

## 1. 試做摘要

| Phase | 產出 | 形式 | 是否實際呼叫 sub-skill |
|---|---|---|---|
| 1 | `phase1-scoping.md` | 完整 | — |
| 2 | `phase2-research-log.md` | 完整 + 1 處資本額誤差已修 | WebSearch（Agent） |
| 3 | `phase3-materiality.md` | 完整（28 議題雙軸評分 + 矩陣 + IRO 對應）| — |
| 4 | `phase4-xlsx-skeleton.md` | skeleton（12 sheets 設計規格）| ❌ 未呼叫 xlsx skill |
| 5 | `phase5-chapter-skeleton.md` + `phase5-tcfd-sample.md` | 全章節骨架 + 1 個完整章節示範 | — |
| 6 | `phase6-assembly-plan.md` | prompt 套裝（5 個輸出）+ 失敗模式表 | ❌ 未呼叫 docx/pdf/pptx skill |
| 7 | `phase7-gap-analysis.md` + `phase7-pdf-extract.md`（agent 補）| 結構對照 + 強弱項 + 合規自評 | Agent 抽 PDF |

---

## 2. 關鍵 lessons learned

### 2.1 SOP 串連邏輯成立 ✅

8-Phase 之間的 prompt 鏈確實能跑通：每個 phase 的輸出格式恰好是下一 phase 的輸入。最強的連結點：
- Phase 1 邊界 → Phase 4 Scenario A/B 雙軌
- Phase 2 法規時程 → Phase 3 ISSB 適用判斷
- Phase 3 議題清單 → Phase 5 章節骨架（不是抄 GRI 目錄）
- Phase 5 TCFD 章節 §11 數據鏈接 → Phase 4 xlsx 來源
- Phase 6 prompt → Phase 7 失敗模式

### 2.2 連結性公式（IRO → 治理 → 策略 → 行動 → 目標 → KPI → 展望）強迫深度 ✅

Phase 5 TCFD 示範驗證：7 段公式有效防止「列舉式」永續報告。每段未達內容必然觸發疑問（「這個目標的基線是什麼？」「這個風險的董事會監督在哪？」），自然產生填補機制。

### 2.3 反綠色洗白機制有效 ✅

三大保護：
- **占位符規範**：`[X] [Y] [Z] [N/A]` 明確區分「未取得數據」與「填假數字」
- **未達標強制揭露**：Phase 5 TCFD §8 強制兩個未達標欄位
- **基線 / 時程 / 驗證三要素**：Phase 5 §6 7 個目標全具三要素

### 2.4 旅館業特化能跑出差異化 ✅

通用 SOP 仍能識別旅館業專屬議題：HVAC 制冷劑、廚房油煙、夜班疲勞、房務肌肉骨骼、客戶 PII、明池泰雅族文化保存、委託經營邊界、集團內紡織備品。

---

## 3. 痛點與待補強（給後續 Sprint）

### 3.1 工具依賴（Phase 0 預警生效）

**Poppler 缺失**：本機嘗試 Read 力麗 PDF 失敗（`pdftoppm not found`）。雖然 Phase 0 已預警，但 SKILL.md 沒寫純 Python fallback（pypdf）。
- **建議**：SKILL.md Phase 0 加分級：「Tier 0 Poppler 最佳；Tier 1 pypdf 純 Python 退階」

### 3.2 同業量化數據抓取（Phase 2）

4 家 peer 的 Scope 1/2/3、員工數、用水具體值多為 `N/A`，因為 ESG 報告書全是 PDF binary，WebFetch 抓不到內頁表格。
- **建議**：`references/phase2-research-prompts.md` 加 fallback prompt：「先試 ESG 平台（CSRone / SustainAI / ESG Times）摘要 → 失敗則 download PDF → pdf skill 抽表格」

### 3.3 Agent 估算誤差（Phase 2）

Agent 自行估算「力麗資本額 ~25 億」，與實際（實收 6.38 億 / 核定 45 億）不符。雖未影響結論，但暴露 prompt 沒強制要求「資本額抓 MOPS 公開資訊主檔」。
- **建議**：phase2-research-prompts.md 加硬性規則「資本額、員工數、營收等核心財務數據，必須註明 MOPS / Goodinfo / 年報來源連結，不接受估算」

### 3.4 議合方法（Phase 3）

本試做模擬 7 大利害關係人議合，但**沒有議合方法決策樹**告訴使用者「我們公司規模、預算、議題複雜度下應該選哪些議合工具」。
- **建議**：`references/materiality-topics-universe.md` 補一份決策樹

### 3.5 Phase 5 章節示範深度

僅完成 TCFD 1 個完整章節，食安、隱私、在地三個高優先章節僅骨架。
- **建議**：後續 Sprint 補 3 個示範章節，作為使用者參考模板

### 3.6 Phase 6 未實機 build

prompt 套裝完備，但 docx / pdf / pptx skill 未實際呼叫驗證。
- **建議**：另起 task（非 SP1）真實 build 一次，驗證跨平台字型 / 圖表 / 中文亂碼 / 跨 sheet 公式等實機問題

---

## 4. 試做產出容量與 commit 策略

| 檔案 | 大小 | commit ? |
|---|---|---|
| `source-2023-report.pdf` | 3.21 MB | ❌ 已 .gitignore（第三方 PDF 不 vendoring）|
| `phase1-scoping.md` | ~7 KB | ✅ |
| `phase2-research-log.md` | ~10 KB | ✅ |
| `phase3-materiality.md` | ~13 KB | ✅ |
| `phase4-xlsx-skeleton.md` | ~10 KB | ✅ |
| `phase5-chapter-skeleton.md` | ~7 KB | ✅ |
| `phase5-tcfd-sample.md` | ~12 KB | ✅ |
| `phase6-assembly-plan.md` | ~8 KB | ✅ |
| `phase7-gap-analysis.md` | ~8 KB | ✅ |
| `phase7-pdf-extract.md`（agent 補）| ~3 KB | ✅ |
| `walkthrough-notes.md`（本檔）| ~7 KB | ✅ |

**結論**：MD 檔案總計 ~85 KB，全部 commit 進 repo 作為 examples 範本。**未 build** 的 xlsx / docx / pdf / pptx 維持 .gitignore 規則（待真實 build 後依容量決定）。

---

## 5. SP1-004 收尾動作

- [ ] 等 sub-agent 完成 `phase7-pdf-extract.md` → 回填 `phase7-gap-analysis.md` §1
- [x] 試做產出 8 檔已完成
- [x] .gitignore 規則已生效（PDF / xlsx / docx 不 commit）
- [ ] 將本試做 lessons learned（§3）回填到 `references/phase2-research-prompts.md`、`materiality-topics-universe.md`、`SKILL.md` Phase 0 — **歸入下個 Sprint 或 SP1-002~003 後續迭代**
- [ ] 更新 README.md Examples 段落（從「TBD」改為實際連結 `examples/lealea-5364/`）
- [ ] 更新 SP1-004 task phase: doing → done
- [ ] 更新 SP1.md sprint phase: plan → check / act

---

## 6. SOP 評等（試做整體）

| 維度 | 評等 | 說明 |
|---|---|---|
| 結構完整性 | A | 8-Phase 串連、輸入輸出對應、失敗 fallback 都有 |
| 領域知識深度 | A- | 旅館業特化夠深；食材里程 / 制冷劑 / 原民共融都納入 |
| 反綠色洗白 | A | 三層保護機制（占位符、未達標、三要素）扎實 |
| Sub-skill 整合 | B | prompt 套裝齊但未實機驗證 |
| 工具依賴揭露 | B+ | Phase 0 預警生效；fallback 分級可加強 |
| 用戶體驗（UX） | B+ | prompt 過長章節（如 Phase 6）可拆模板 |

**整體：A- / B+** — SOP 可以推廣，但需要 1–2 個迭代補強（特別是 Phase 6 實機驗證 + Phase 5 補完 3 個示範章節）。

---

## 7. 意外重大發現：力麗 2023 是「反向示範」

Phase 7 PDF 解析後發現力麗實際版本存在全方位揭露缺口：

- 重大性方法為**單向 impact materiality**（18 議題 → 4 重大），無雙重重大性
- **TCFD 完全缺席**（全文 0 hits）
- **GHG 僅揭 Scope 2 + 強度**，無 Scope 1 / 無 Scope 3、無雙軌、無實際數值表
- GRI 版本停在 **2016 + 102 系列**（落後 2021 版 5+ 年）
- **無第三方確信**（自行編製，明確聲明）
- 環境章節「8 善待環境」**僅 p.44 半頁**

**戰略意涵：** 力麗 2023 是台灣中型 TPEx 上市公司的「典型樣本」，揭露品質遠低於金管會 2026/2027/2028 ISSB 強制標準。susr SOP 各 phase 的設計恰好對應力麗版本的具體缺口，這讓 SP1-004 的價值從「驗證 SOP 串連」升級為「直接示範 gap closing 路徑」。

對未來使用者（推測為類似力麗的中型上市公司永續團隊）而言，本 examples 不是「優秀範本」，而是「**升級指南**」— 「我家公司報告書像力麗版本，怎麼升級到 ISSB 標準？」是核心使用情境。

**Phase 7 對照表（`phase7-gap-analysis.md` §0）**已將 14 項揭露差距編成表格，可直接作為產品教學素材。
