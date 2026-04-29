# Phase 6 — Report Assembly & Professional Output（組裝計畫）

**用途**：彙整 Phase 5 章節草稿與 Phase 4 數據包，呼叫 `document-skills:docx / pdf / pptx` 產出最終專業檔案。
**狀態**：本試做 **不實際 build** 真實 docx / pdf / pptx — 因為（1）試做未取得力麗真實內部數據，build 出的會是 placeholder；（2）SP1-004 的核心驗證目標是 SOP prompt 鏈串連，sub-skill 呼叫已在 SP1-003 reference 內驗證；（3）sub-skill 底層依賴（pandoc / LibreOffice / Node / Python）需確認使用者環境。本檔提供**可直接複製的 prompt 套裝**，待真實環境就緒即可執行。

---

## 1. 三個輸出的依賴與 Phase 0 檢查

| 輸出 | Sub-skill | 底層依賴 | 預估執行時間 |
|---|---|---|---|
| `Report_2023.docx`（主報告書） | `document-skills:docx` | pandoc + LibreOffice + `npm install -g docx` | 5–10 分鐘（多章節組裝） |
| `Report_2023.pdf`（最終 PDF） | `document-skills:pdf` | Poppler + Python `pypdf pdfplumber reportlab` | 1–3 分鐘（自 docx 轉換） |
| `Investor_Deck_2023.pptx` | `document-skills:pptx` | LibreOffice + Poppler + Pillow + `npm install -g pptxgenjs` | 3–5 分鐘 |
| `Board_Deck_2023.pptx` | `document-skills:pptx` | 同上 | 3–5 分鐘 |
| `ESG_Data_Pack_2023.xlsx` | `document-skills:xlsx`（Phase 4 既有） | LibreOffice + Python `openpyxl pandas` | 5–10 分鐘 |

**執行前 Pre-flight**：
1. `pandoc --version` / `soffice --version` / `node --version` / `python --version`
2. 缺哪個就裝哪個（依各 sub-skill 自身 SKILL.md authoritative source）
3. **不要硬撐**：失敗就停下查錯誤訊息，不要嘗試手寫 docx XML

---

## 2. 主報告書 docx — 完整 prompt（可直接複製）

```
請使用 document-skills:docx 為力麗觀光（5364）2023 永續報告書建立主檔，需求：

【輸入來源】
- 章節骨架：examples/lealea-5364/phase5-chapter-skeleton.md
- 完整章節示範：examples/lealea-5364/phase5-tcfd-sample.md（第 3.1 章）
- 數據附錄：examples/lealea-5364/phase4-data-pack.xlsx（待 Phase 4 build 後）
- 重大性：examples/lealea-5364/phase3-materiality.md（矩陣與議題）

【文件規格】
- 紙張：A4，邊界 2.5cm
- 字體：標楷體（標題）+ 微軟正黑體（內文）；英文 Times New Roman
- 行距：1.5
- 主標 18pt 粗、副標 14pt、內文 11pt
- 頁碼：頁腳置中
- 章首頁：每章新頁開始
- Running header：「力麗觀光 2023 企業永續報告書」+ 章節名

【結構】
- 封面（手動稿，不在自動化範圍 — 留白）
- 目次（自動產生）
- 7 大篇章（依 phase5-chapter-skeleton §篇 1–7）
- 附錄 A1–A6（含 GRI / SASB / TCFD Index）

【表格與圖】
- 數據表全部用 Word 表格樣式（不嵌圖）
- 重大性矩陣以表格 + 註腳呈現（pptx 才用視覺化）
- 章節 IRO / 目標 / KPI 全用 6×N 表格

【強制連結性】
每個重大議題章節必含 7 段：IRO → 治理 → 策略 → 行動與資源 → 目標 → KPI → 展望（依 phase5-tcfd-sample 結構）

【限制】
- 占位符 [X] [Y] [Z] [N/A] 全部保留，不要填假數字
- 不要美化未達標欄位；保留原樣

【輸出】
- examples/lealea-5364/phase6-output/Report_2023.docx
- 處理時間預期 5–10 分鐘
```

---

## 3. PDF 輸出 — 完整 prompt

```
請使用 document-skills:pdf 將前述 docx 轉為 PDF：

【輸入】
- examples/lealea-5364/phase6-output/Report_2023.docx

【規格】
- A4，與 docx 完全一致
- 嵌入字型（避免跨平台亂碼）
- 書籤（依目次自動）
- 文件中繼資料：
  - Title: 力麗觀光 2023 企業永續報告書（試做版）
  - Author: susr Skill 試做（非力麗官方）
  - Subject: SP1-004 端到端 SOP 驗證
  - Keywords: ESG, GRI, TCFD, ISSB, 永續, 旅館業
- 預留 iXBRL / ESEF 標記欄位（金管會未強制旅館業，但保留結構）

【輸出】
- examples/lealea-5364/phase6-output/Report_2023.pdf
```

---

## 4. 投資人版簡報 — 完整 prompt

```
請使用 document-skills:pptx 為力麗觀光建立投資人版永續簡報：

【目的】法說會 / 投資人說明會用，10–12 頁
【受眾】機構投資人、ESG 評等機構（CDP/MSCI/Sustainalytics）

【骨架】
1. 封面 — 標題 + 邊界 + 報告期間
2. 力麗觀光永續定位 — 在集團與旅館業的位置
3. 永續治理結構 — 董事會 → 永續委員會 → 副總 → 辦公室組織圖
4. 雙重重大性矩陣 — Phase 3 矩陣圖 + 議題排序
5. 氣候 TCFD 4 構面摘要 — 治理 / 策略 / 風險 / 指標目標
6. 排放軌跡與目標 — Scope 1+2 三年趨勢 + 2030 目標 + SBTi 路徑
7. 重大議題進度 — 食安、隱私、員工、在地（4 議題各一句）
8. 未達標誠實揭露 — 反綠色洗白章節
9. 2024 重點計畫 + 資源投入
10. Q&A 與聯絡

【視覺】
- 主色：力麗品牌綠（試做用 #2E7D32 占位）+ 中性灰
- 圖表：條圖（排放）+ 矩陣（重大性）+ 流程圖（治理）
- 每頁 < 50 字，重圖表輕文字
- 字體：思源黑體（中）+ Roboto（英）

【輸出】
- examples/lealea-5364/phase6-output/Investor_Deck_2023.pptx
```

---

## 5. 董事會版簡報 — 完整 prompt

```
請使用 document-skills:pptx 為力麗觀光建立董事會版永續簡報：

【目的】董事會永續委員會議程用，5–7 頁，深度 > 廣度
【受眾】董事與獨董，含 ESG 專業背景與非專業背景

【骨架】
1. 重大決策一覽 — 本年度需董事會決議的永續事項清單
2. 風險地圖 — 氣候 + 食安 + 隱私三大議題財務影響量化
3. 目標達成率紅綠燈 — 三年目標進度 traffic light
4. 法規遵循狀態 — 金管會 ISSB 路徑圖 + 公司準備度
5. 內控與確信狀態 — 第三方確信進度
6. 資源請求 — 2024 永續預算與人力
7. 結論與決議事項

【視覺】
- 風險量化（NTD 影響）必有
- 紅綠燈圖示
- 字體稍大（董事年齡層考量）：標題 24pt、內文 16pt

【輸出】
- examples/lealea-5364/phase6-output/Board_Deck_2023.pptx
```

---

## 6. 預期失敗模式與回退（Failure Modes & Fallback）

| 失敗 | 訊息 | 處理 |
|---|---|---|
| docx skill 找不到 | `skill not found: document-skills:docx` | 安裝 anthropics/skills 插件後重試 |
| pandoc 缺失 | `pandoc: command not found` | `brew install pandoc` / `winget install pandoc` / `apt install pandoc` |
| LibreOffice 缺失 | `soffice: command not found` | 安裝 LibreOffice |
| 中文字型亂碼 | docx 開啟字型替換 | 安裝思源黑體 / 標楷體；docx skill 重 build |
| pptx 圖表生成失敗 | `pptxgenjs: cannot create chart` | 改用表格或外部圖片 |

---

## 7. Phase 6 試做結論（SOP 驗證重點）

✅ **prompt 鏈完整**：5 個輸出皆有可複製 prompt，依賴明確
✅ **連結性可追**：docx / pdf 引用 Phase 4 / 5；pptx 引用 Phase 3 矩陣
✅ **失敗模式有 fallback**：每個 sub-skill 失敗訊息都有對應安裝 / 替代方案
⚠️ **未實際 build**：試做版以驗證 SOP 串連為主；真實 build 留待使用者環境就緒後執行
⚠️ **占位符（[X][Y][Z][N/A]）大量存在**：試做未取得力麗真實內部數據，prompt 已要求保留占位不填假值

下一步：Phase 7 對照原版 PDF 找差異。
