---
slug: phase6-docx-prompts
category: prompt
source: skills/sustainability-report/references/phase6-docx-prompts.md
version: "2025-05-25"
language: zh-Hant
last_reviewed: 2025-05-25
phase: 6
sub_skill: document-skills:docx
---

# Phase 6 — docx Skill 整合 Prompt 模板

**使用時機**：Phase 6 報告書組裝、Phase 7 review 後的修訂、Phase 8 中英版本同步。

**子 skill**：`document-skills:docx`（authoritative docs：`https://raw.githubusercontent.com/anthropics/skills/main/skills/docx/SKILL.md`）

---

## 1. docx Skill 的關鍵約束（必須在 prompt 中遵守）

| 約束 | 規則 |
|------|------|
| 輸入格式 | 自然語言 + **絕對檔案路徑**（建立輸出路徑或編輯既有檔），**不接受 JSON 結構化輸入** |
| Workflow 分流 | **建立新檔** → 用 docx-js（Node，呼叫前 `npm install -g docx`）；**讀取既有** → pandoc 或 unpack.py；**編輯既有** → unpack XML → Edit tool → pack.py |
| 表格寬度 | **只能用 `WidthType.DXA`**，不得用其他 unit |
| 條列符號 | **用 `LevelFormat.BULLET`**，**不要用 unicode 圓點字元**（會壞渲染） |
| 環境依賴 | LibreOffice + pandoc + `npm install -g docx` |

**為什麼這些約束**：docx-js 與 OOXML 規範對 width unit 與 list level 的處理嚴苛，違反會導致 Word 開檔錯誤或表格渲染失敗。

---

## 2. 永續報告書 docx 標準結構

```
封面（Cover）
├── 公司 logo + 報告年度
├── 報告書標題 + 副標
├── 編製單位 + 公告日期

目次（Table of Contents）— 自動產生

第 1 章 報告書概述
├── 1.1 編製依據（GRI / ISSB / 金管會...）
├── 1.2 報告期間與邊界
├── 1.3 重大性鑑別過程
├── 1.4 第三方確信
├── 1.5 聯絡資訊

第 2 章 公司治理
├── 2.1 公司概況
├── 2.2 董事會與委員會
├── 2.3 誠信經營（強制）
├── 2.4 風險管理
├── 2.5 法遵

第 3 章 利害關係人議合（強制）
├── 七大類利害關係人
├── 議合方法、頻率、回應

第 4 章 環境永續
├── 4.1 氣候變遷與溫室氣體（強制 TCFD/ISSB 四構面）
├── 4.2 能源管理
├── 4.3 水資源
├── 4.4 廢棄物與循環經濟
├── 4.5 生物多樣性（適用時）

第 5 章 社會共融
├── 5.1 員工
├── 5.2 供應鏈
├── 5.3 客戶與產品責任
├── 5.4 社會公益

第 6 章 永續創新與經濟價值

附錄 A — GRI Content Index
附錄 B — ISSB / TCFD 對照表
附錄 C — SASB 產業指標對照
附錄 D — 第三方確信報告
附錄 E — 名詞對照表（zh / en）
```

---

## 3. 樣式規範

| 元素 | 樣式 |
|------|------|
| 字型 | 中文「思源黑體 Noto Sans TC」、英文 Arial / Calibri |
| 章節標題（H1） | 18 pt 粗體 + 公司主色底色 + 白字 |
| 子節標題（H2） | 14 pt 粗體 + 公司次色 |
| 內文 | 11 pt、行距 1.5 |
| 表格 | `WidthType.DXA` 統一、表頭粗體深底白字 |
| 條列 | `LevelFormat.BULLET`，最多 3 層 |
| 引用框 | 淺灰底、左側 4 pt 公司主色直線 |
| 頁眉 | 公司名 + 報告年度（左）/ 章節名（右） |
| 頁腳 | 頁碼置中 + 「Sustainability Report YYYY」 |

---

## 4. 標準 Prompt 範本

### 4.1 建立全新報告書

```
請呼叫 document-skills:docx skill，建立永續報告書主檔。

【Workflow 路徑】
建立新檔 → 使用 docx-js（Node）

【輸出絕對路徑】
/abs/path/to/.../assets/example-<industry>-2025/Report_2025.docx

【建立前確認】
- 輸出目錄已建立（mkdir -p 完成）
- 草稿章節 Markdown 已備齊（路徑：/abs/path/to/drafts/）
- ESG_Data_Pack_2025.xlsx 數據已 finalize
- 圖表 PNG 已導出（路徑：/abs/path/to/charts/）

【章節結構】
依 prompts/phase6-docx.md §2 完整結構建立。

【樣式約束（必須遵守）】
1. 表格寬度只能用 WidthType.DXA；任何其他 unit 必須拒絕
2. 條列只用 LevelFormat.BULLET；嚴禁 unicode 圓點字元（•、●、◦ 等）
3. 字型：中文 Noto Sans TC、英文 Arial（fallback Calibri）
4. 章節標題用 H1 樣式（粗體 + 公司主色），子節 H2，依此類推
5. 圖表以 image embed，不嵌入連結圖

【內容組裝規則】
- 從 drafts/ 對應 .md 讀取章節文字
- 從 ESG_Data_Pack_2025.xlsx 取得各 KPI 數字（Sheet 與 Cell 由 Phase 5 草稿標註）
- 圖表從 charts/ 目錄按章節插入
- 附錄 A GRI Content Index 從 checklists/compliance-phase7.md 對應產生

【完成後輸出】
- 檔案絕對路徑
- 章節數、表格數、圖表數
- 已知警告（缺漏的 KPI 欄、未對應的 GRI 項）
```

### 4.2 編輯既有報告書（review 後修訂）

```
請呼叫 document-skills:docx skill，編輯既有 Report_2025.docx。

【Workflow 路徑】
編輯既有 → unpack XML → Edit tool → pack.py

【既有檔絕對路徑】
/abs/path/to/.../Report_2025.docx

【修訂清單】
- 第 4.1 節氣候情境分析：補上 1.5°C 情境的財務影響表（取自 ESG_Data_Pack_2025.xlsx 的 5_Intensity）
- 第 5.2 節供應鏈：將「99% 供應商已通過評估」改為實際比例（從 source 確認後填）
- 附錄 A：補上 GRI 305-3 對應頁碼

【關鍵約束】
- 編輯後重新 pack.py，不得手動編輯產出 .docx
- 修訂處用 track changes 標記（呼叫 scripts/comment.py 加修訂註解）
- 不改動其他章節格式
```

### 4.3 中英雙版同步

```
請呼叫 document-skills:docx skill，依繁中版產生英文版報告。

【來源檔絕對路徑】
/abs/path/to/.../Report_2025_zh-TW.docx

【目標檔絕對路徑】
/abs/path/to/.../Report_2025_en.docx

【翻譯規則】
- 專業術語強制查 glossary/esg-zh-en.md，譯名必須一致
- 數字、公式、表格結構保持相同
- GRI 編號、ISSB 標準引用維持英文原文（不翻）
- 公司專有名詞（部門、職稱）依公司網站英文版

【樣式調整】
- 中文字型替換為英文（Arial / Calibri）
- 標題 H1 行高調整以適應英文（避免單字斷行）
- 頁眉「永續報告書 2025」改為「Sustainability Report 2025」
```

---

## 5. 防呆檢查清單（完成 docx 任務前 self-check）

- [ ] 表格寬度全部用 `WidthType.DXA`
- [ ] 條列符號全部用 `LevelFormat.BULLET`，無 unicode 字元
- [ ] 字型已正確設定（中文 + 英文 fallback）
- [ ] 圖表全部嵌入（image embed），無連結圖
- [ ] 目次（TOC）已重新生成
- [ ] 頁眉頁腳所有頁面正確
- [ ] 開檔測試（用 LibreOffice / Word 開啟無錯誤）
- [ ] 附錄 GRI Content Index 與正文章節對應正確
- [ ] 中英版本字數差異合理（中文約為英文 0.6 倍）

---

## 6. 與下游 Phase 的銜接

| 銜接點 | 動作 |
|-------|------|
| → Phase 6 pdf 輸出 | docx 完稿後，pdf skill 轉檔（見 prompts/phase6-pdf.md） |
| → Phase 6 pptx | 章節重點整理進 board / investor deck |
| → Phase 7 review | 用 scripts/comment.py 收集 reviewer 意見 |
| → Phase 8 公告 | 最終 PDF 上 MOPS（不上傳 docx） |

---

## 7. 常見錯誤與對策

| 錯誤 | 原因 | 對策 |
|------|------|------|
| Word 開檔錯誤「文件已損毀」 | width unit 違反 OOXML | 全面檢查 WidthType.DXA |
| 條列項變成方框 □ | 用了 unicode 圓點 | 改 LevelFormat.BULLET |
| 中文字型在 Word 變預設 | 字型未嵌入 / fallback 不對 | 確認字型可用，加 fallback chain |
| 目次頁碼錯亂 | 編輯後沒重新產生 | 呼叫 docx skill 的 update TOC 功能 |
| 圖表變模糊 | 用了過低解析度 PNG | charts/ 內 PNG 必須 ≥ 300 dpi |

---

## 8. 失敗時的依賴提示

| 錯誤訊息片段 | 缺失依賴 | 處理 |
|-------------|---------|------|
| `pandoc: not found` | pandoc 未安裝 | 提示安裝 pandoc，指向 docx skill SKILL.md |
| `Cannot find module 'docx'` | npm package 未安裝 | 提示 `npm install -g docx` |
| `soffice: command not found` | LibreOffice 未安裝 | 提示安裝 LibreOffice |

不在本檔案維護完整安裝指令，指向 sub-skill 自身文件。
