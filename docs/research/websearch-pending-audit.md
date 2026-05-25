# websearch-pending.md Audit 報告

**Audit 日期**：2026-05-25
**對象**：`skills/sustainability-report/references/websearch-pending.md`（SP1 階段建立）
**目的**：戰略樞轉為 Plan B Co-pilot（local-first + MCP + SQLite brain）後，檢視哪些項目仍 pending / 已 obsolete / 已解決
**Auditor**：susr 文件 audit subagent

---

## 1. 摘要

- **原檔項目數**：4 項主查 + 2 條統括提醒（檔尾「統括提醒」段落）
- **仍 pending**：0 項（所有 4 項主查均已在 2026-04-29 ~ 04-30 透過 WebSearch 完成首輪查證並回填來源 URL 與結果）
- **已 obsolete**（pivot 後機制不再適用）：0 項內容性 obsolete，但**機制本身**（websearch-pending.md 作為待辦中樞）面對 brain 化後的角色重新定義（見 §3）
- **已解決或被 superseded**：4 項主查均屬「已解決但需後續維護」狀態 — 內容已 verified，但每個都標有「後續動作」尚未真正寫回對應 reference（Q1 寫回 `ghg-protocol.md:47`、Q2/Q3/Q4 寫回 `taiwan-fsc:28/92/§6`）
- **未完成的後續動作**：4 項全部仍待寫回 reference

簡言之：**內容層全綠、執行層全黃** — 查證已完成但「結果回填 references」這一步未閉環。

---

## 2. 逐項分析

### Q1. 台灣電力排碳係數最新版（line 14–32）

- **目前狀態**：resolved（內容）/ pending（回填）
- **理由**：
  - line 24 明示「最後確認日期 2026-04-29（透過 SP1-003 Check 階段 WebSearch 實測）」
  - line 29–31 已給出 113 年度 = 0.474 kgCO₂e/度、2025 / 2030 目標值
  - line 32「後續動作：在 SP1-004 試做時依此更新 `ghg-protocol.md:47`」— 根據 SP1.md line 51–54 Check 階段勾選「SP1-008 跑完最新法規 / 排放因子已回填」，**回填這件事在 SP1 收尾應已完成**，但本 audit 不修改 references 故未交叉驗證；建議下一步用 grep 確認 `ghg-protocol.md:47` 是否仍寫 0.495 還是已更新到 0.474
- **對 Plan B 的相關性**：高 — 排放因子是 brain 層 `EmissionFactor` entity 的核心欄位（見 gbrain-survey §4.1），且帶 `effective_from` / `superseded_by`（§3 時效性資料缺口）；Q1 的查證結果直接是 v0.1 brain 的 seed data
- **建議下一步**：
  - 在 brain Step 1 spike 時，把 0.474（113 年度）連同 2025/2030 目標值寫成 `shared_kb/emission_factors/tw_grid_electricity.md` 的 frontmatter
  - websearch-pending.md 機制本身在 brain 化後應由 `EmissionFactor.superseded_by` 自動偵測過期，不再靠 markdown 待辦清單維護

### Q2. 第四階段強制申報年度（line 34–53）

- **目前狀態**：resolved（內容）/ pending（回填）
- **理由**：
  - line 45「最後確認日期 2026-04-30」
  - line 50「自 114 年（2025）起，全體上市櫃公司均應編製 113 年度（2024 年度）永續報告書」結論明確
  - line 53「後續動作：在 SP1-008 同步更新 `taiwan-fsc:28`」— 同上未交叉驗證
- **對 Plan B 的相關性**：中 — 對應 `Regulation` entity（gbrain-survey §4.1）與 SOP Phase 1 Scoping 的「適用標準判定」決策樹；資料本身穩定（已正式實施），不會頻繁變動
- **建議下一步**：
  - Phase 3 重大性評估 MVP（CLAUDE.md §8「MVP 第一刀」決策）暫不涉及「強制申報年度」判定，但 Phase 1 Scoping 的 brain 化會用到 — 列入 post-MVP backlog
  - 同 Q1，websearch 機制應由 `Regulation.effective_from / effective_to` schema 欄位取代

### Q3. 第三方確信最新適用規定（line 56–74）

- **目前狀態**：resolved（內容）/ pending（回填）
- **理由**：
  - line 65「最後確認日期 2026-04-30」
  - line 69–73 給出 ISAE 3000 主流、食品/金融強制、2023 統計分佈、金管會 2024 研議擴大適用 — 4 項子結論清楚
  - line 74「後續動作：更新 `taiwan-fsc:92` 補上食品/金融強制 + 2024 研議計畫」未交叉驗證
- **對 Plan B 的相關性**：中 — 對應 `Report.assurance_level`、`DataPoint.assurance_status`（gbrain-survey §4.1）；確信狀態是「可確信性」invariant 的核心（survey §3「Assurance Readiness」缺口）
- **建議下一步**：
  - 由於 2024 研議計畫**至 2026-05-25 仍是「漸進擴大」狀態**，這是少數可能持續變動的項目；brain 化後應在 `Regulation` entity 補 `status: draft/proposed/effective` 欄位
  - 短期照舊回填 `taiwan-fsc:92`

### Q4. 公告時程與雙語版本最新要求（line 76–98）

- **目前狀態**：partially resolved（內容） / pending（回填 + (c) 未解）
- **理由**：
  - line 89「最後確認日期 2026-04-30」
  - 子問題 (a) 申報期限 8/31、(b) 雙語非強制 — 已解決
  - **子問題 (c) MOPS 結構化資料規格 — line 97 明示「未取得明確結果，建議直接洽詢 TWSE / TPEx 永續報告書專區」 — 仍 pending**
  - line 98「後續動作：更新 `taiwan-fsc §6` 改為 8/31 + 註明雙語非強制」未交叉驗證
- **對 Plan B 的相關性**：(c) 子問題直接對應 gbrain-survey §8 風險 #6（iXBRL / ESEF 標記）— 已在 CLAUDE.md §8「iXBRL / ESEF schema 預留」決策中處理：Step 1 spike 在 `DataPoint` / `KPI` schema 加 `xbrl_concept` nullable 欄位，**實際填值機制延後到金管會 2028 ISSB 時程明朗**
- **建議下一步**：
  - (a)(b) 比照 Q1–Q3 回填即可
  - (c) **已被 CLAUDE.md §8 「iXBRL 預留」決策正式 supersede**，不應再放在 websearch-pending 追，改由 Step 1 spike spec 與「2028 ISSB 時程 watch list」承接

### 統括提醒（line 102–107）

- `taiwan-fsc-sustainability-guidelines.md:5` 以 2026-Q1 為基準
- `ghg-protocol.md:142` 以 2026-Q2 公告為基準
- **狀態**：仍適用，屬時效性元資料而非待辦
- **brain 化後應改為**：每份 reference markdown 的 frontmatter `valid_as_of` + `next_review` 欄位，由 brain `find_anomalies` 主動掃出過期項目

---

## 3. 建議行動

### 3.1 可直接判定「機制 obsolete，但內容仍有價值」

websearch-pending.md 作為**「外部查證待辦中樞」的 markdown 清單機制**，在 Plan B brain 架構下定位錯位：

- gbrain-survey §3「時效性資料」缺口明確指出：susr brain 必須有 `effective_from / effective_to / superseded_by` 原語
- gbrain-survey §5「SOP 8-Phase → gbrain capability 對照」Phase 2 Research 已規劃用 `Regulation` + `EmissionFactor` ingest + `find_anomalies`（gbrain 既有 tool）取代手動 markdown 清單
- CLAUDE.md §8「MVP 第一刀」明示 v0.1 = Phase 3 重大性，**但 Phase 2 Research 的 brain 化是 post-MVP 範圍**

→ websearch-pending.md 在 brain MVP 上線前仍是**過渡期唯一的時效性追蹤工具**，不應刪；但**SP2 結束後應正式 deprecate**，並轉移為 brain 內 `Regulation` / `EmissionFactor` entity 的 lint 規則。

### 3.2 仍需處理（短期）

| 項目 | 動作 | 負責階段 |
|---|---|---|
| Q1 回填 `ghg-protocol.md:47` | grep 確認是否已寫 0.474 | SP2 開工前 |
| Q2 回填 `taiwan-fsc:28` | 同上 | SP2 開工前 |
| Q3 回填 `taiwan-fsc:92` | 同上 + 註明 2024 研議「進行中」狀態 | SP2 開工前 |
| Q4 (a)(b) 回填 `taiwan-fsc §6` | 申報期限改 8/31 + 雙語非強制 | SP2 開工前 |
| Q4 (c) | **不在 websearch 追**，轉 brain Step 1 spike `xbrl_concept` 欄位設計 | susr-brain Step 1 |

### 3.3 升級為 dashboard openQuestions

無 — 4 個項目都屬「具體法規 / 排放因子查詢」層級，**不是架構未決問題**，不需升級至 dashboard Q。但下列**機制級**問題應確認 dashboard 是否已涵蓋：

- 「brain 化後如何取代 websearch-pending 的時效性偵測」— 屬 Plan B 工程選型問題，dashboard 應已隱含於「Regulation entity schema」討論；如未明列建議補一條
- 「SP1 階段建立的 reference 待辦機制如何過渡到 SP2+」— 屬 SP2 規劃問題

### 3.4 整體建議：保留 OR 棄用 websearch-pending.md 機制？

**建議：保留至 SP2 結束，之後 deprecate；過渡期內補 1 條使用紀律。**

- **保留理由**：MVP Phase 3 不會用到 Phase 2 Research 的 brain 化能力（CLAUDE.md §8「MVP 第一刀」line 463–467 明示 Phase 2 不在 v0.1 範圍）；在 brain Phase 2 工具上線前，markdown 清單仍是顧問**手動**啟動 WebSearch 的最低成本入口
- **過渡期紀律**：新查證項目進入 websearch-pending 時，**必須同時在 dashboard 標註 brain entity 對應**（例如「此項對應未來 `Regulation` entity」），確保 brain 化時可以一次性 migrate
- **deprecate 時機**：當 brain MCP server 暴露 `find_outdated_regulations` / `find_outdated_emission_factors` 兩個 tool 後，websearch-pending.md 改為 `archive/` 唯讀 snapshot

---

## 4. 我的判斷依據與不確定處

### 4.1 主要判斷依據

- CLAUDE.md §8 七條 Decisions Log（特別是 Plan B / SQLite / MVP=Phase 3 / iXBRL 預留）
- gbrain-survey §3（不適用點）、§4（entity 模型）、§5（SOP 對應）、§8 風險 #6（iXBRL）
- SP1.md line 51–54 Check 階段勾選「SP1-008 跑完最新法規 / 排放因子已回填」

### 4.2 不確定處

1. **最大不確定**：本 audit 任務嚴格限制「不修改其他任何檔」與「只讀」，所以**未實際 grep `ghg-protocol.md:47` 與 `taiwan-fsc-sustainability-guidelines.md:28/92/§6` 確認回填狀態**。SP1.md Check 勾選宣稱已回填，但 websearch-pending.md 自身保留「後續動作」字樣未刪 — 這兩處資訊不一致。**真正執行回填驗證需另一個 task**（建議 SP2 開工 P0）

2. **Q3 2024 研議計畫的時效性**：報告日期 2026-05-25，距 2026-04-30 確認日才 25 天，但「金管會 2024 研議計畫」距今已 2 年；研議是否已產出具體強制規定？未額外查證 — 這超出 audit 範圍但會影響「Q3 是否真已 resolved」的判斷

3. **websearch-pending.md 與 dashboard openQuestions 的職責分界線**：CLAUDE.md 未明寫，本報告 §3.3 的「機制級 vs 內容級」二分是我的推論，可能與使用者實際心智模型不符

4. **Q4 (c) 是否真的可以丟給 iXBRL schema 預留**：CLAUDE.md §8「iXBRL 預留」決策只說 schema 欄位空殼，**沒明說「MOPS 結構化資料規格查證」是否屬同一範疇** — 我做了合理推論（兩者都是金管會 2028 ISSB 後可能要求的結構化標記體系），但這個對應未經使用者確認

### 4.3 是否漏看背景文件

- 未讀 `dashboard.html` / `dashboard-data.js` — 可能 openQuestions 已有「Phase 2 brain 化時程」相關 Q，未交叉驗證
- 未讀 SP1-003 / SP1-008 task 個別文件（只看了 SP1.md sprint 主檔），可能漏掉「websearch-pending 維護週期」的設計細節
- 未讀 `docs/standards/skill-development.md §8.3.1` — 任務 prompt 引用了這節，但我未實際翻閱

以上漏看在 audit 結論層面不致命（因 4 個項目內容已 resolved），但若使用者要進一步討論「機制 deprecate 時機」，建議先補讀。

---

**字數**：約 1,450 字（不含 frontmatter 與標題）
