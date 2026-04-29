---
id: SP1
title: 永續報告書 SKILL 在 Claude 環境的建構與優化
phase: check
created: 2026-04-29
updated: 2026-04-30
tasks:
  - SP1-001
  - SP1-002
  - SP1-003
  - SP1-004
  - SP1-005
  - SP1-006
  - SP1-007
  - SP1-008
---

## Plan

- **目標**：依據 `plan.md` 第一性原理設計，建構一套可重複、可審計、可整合的永續報告書 SKILL，覆蓋 8-Phase SOP 工作流。**先在專案目錄 `./skills/sustainability-report/` 建構與迭代**，驗證後才部署到 `~/.claude/skills/`。

- **為什麼**：
  - `plan.md` 提到的成果在 Grok 環境（`/root/.grok/skills/`），不存在於 Claude 環境。
  - 永續報告書（ESG / 雙重重大性）在 2026 年是台灣上市櫃公司強制要求，且需與 ISSB / ESRS 對應。
  - 通用模型缺乏程序性知識（GHG Protocol Scope 3、台灣金管會時程、IRO 連結性、反綠色洗白）。

- **範圍**：
  - 在 Claude 環境建立 `sustainability-report` skill（SKILL.md + references/ + assets/）
  - 整合 Claude 既有 document-skills（docx / xlsx / pptx / pdf）
  - 補上 Claude 環境的搜尋能力（WebSearch / WebFetch）作為 Phase 2 引擎
  - 預設情境：台灣上市櫃公司，遵循金管會實務守則 + GRI + ISSB

- **不在本 Sprint 範圍**：
  - 產業專屬 sub-skill（半導體 / 金融 / 製造）— 視試做結果決定是否獨立 Sprint
  - `scripts/` 自動化工具（KPI 驗證 Python）— 列為 follow-up

- **驗收標準**：
  - [ ] `./skills/sustainability-report/SKILL.md` 存在，含完整 frontmatter 與 8-Phase SOP
  - [ ] `references/` 至少含 5 份核心知識文件（詞彙表 / 合規清單 / 議題池 / GHG / 台灣指引）
  - [ ] 8-Phase 中每個整合點（docx / xlsx / pptx / pdf / search）皆有可直接複製的 prompt 範本
  - [ ] 透過模擬輸入「為半導體公司製作 2025 永續報告書」可順利觸發並引導到 Phase 1
  - [ ] 通過 skill-creator 的結構驗證
  - [ ] 完成部署到 `~/.claude/skills/sustainability-report/`（SP1-005）

## Do

（執行中的工作摘要會在每個 Task 進入 Do phase 時更新）

## Check

- [x] 所有 Task（SP1-001 ~ SP1-008）達到 done
- [x] SKILL.md 觸發詞測試通過（部署到 ~/.claude/skills/，自動載入驗證 OK）
- [⚠️] 與 document-skills 整合 prompt 經**規格驗證**（SP1-003）但**未實機 build**（SP1-004 walkthrough §3.6）— 轉 SP2 backlog
- [x] References 內容無互相矛盾、SP1-008 跑完最新法規 / 排放因子已回填

## Act

**SP1 收尾結論**：8 個 task 全 done；susr v0.1 已部署、已 GitHub 公開、已端到端驗證。

**SP1-004 端到端試做意外發現**：力麗 2023 為中型 TPEx 上市公司「反向示範」典型 — SOP 試做版本相對實際版本是全方位升級（雙重重大性 / TCFD / Scope 1/2/3 / GRI 2021 / 確信前置）。這讓 examples 變成 gap closing 教材，而不是優秀範本。

**SP2 候選 backlog**（依 SP1-004 walkthrough §3）：
1. SKILL.md Phase 0 工具依賴分級補強
2. phase2 PDF binary fallback + 資本額 MOPS 硬規則
3. materiality 議合方法決策樹
4. Phase 5 補食安 / 隱私 / 在地三個示範章節
5. Phase 6 真實環境實機 build 驗證（跨平台字型 / 圖表 / 中文）
6. 加碼 2 家不同產業（金融 / 食品）驗證 SOP 泛化性

**Sprint 滿意度**：A- — 八卡全收，端到端跑通，意外得到反向示範教材作為產品差異化素材。
