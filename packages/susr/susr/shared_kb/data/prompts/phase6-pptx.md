---
slug: phase6-pptx-prompts
category: prompt
source: skills/sustainability-report/references/phase6-pptx-prompts.md
version: "2025-05-25"
language: zh-Hant
last_reviewed: 2025-05-25
phase: 6
sub_skill: document-skills:pptx
---

# Phase 6 — pptx Skill 整合 Prompt 模板

**使用時機**：Phase 6 投資人簡報 / 董事會簡報組裝、Phase 8 對外發表會材料。

**子 skill**：`document-skills:pptx`（authoritative docs：`https://raw.githubusercontent.com/anthropics/skills/main/skills/pptx/SKILL.md`）

---

## 1. pptx Skill 的關鍵約束（**特別注意視覺 QA loop**）

| 約束 | 規則 |
|------|------|
| 輸入格式 | 自然語言 + **絕對檔案路徑** |
| Workflow 分流 | **編輯範本** → unpack/edit/pack；**從零建立** → pptxgenjs（Node） |
| **視覺 QA Loop（強制）** | render → PDF → JPGs → 子 agent 視覺檢查 → fix → re-verify。**必須至少跑完一輪 fix-and-verify** 才能宣告完成 |
| 設計準則 | 配色用 brand palette、不在標題下加裝飾線、每張投影片必須有視覺元素 |
| 環境依賴 | LibreOffice、Poppler（pdftoppm）、Pillow、`npm install -g pptxgenjs`、markitdown |

**為什麼視覺 QA loop 強制**：pptxgenjs 與 unpack/pack 的 XML 操作容易產生「程式上正確但視覺上崩潰」的 bug（文字超框、圖表蓋字、配色不對比）。LLM 看不到視覺，必須走 render → 圖片 → 視覺檢查的回饋路徑。

---

## 2. 投資人版 vs 董事會版的差異

| 維度 | 投資人版 | 董事會版 |
|------|---------|---------|
| 頁數 | 10–15 | 5–8 |
| 受眾 | 法人、外資、ESG 評等機構 | 董事會成員（部分非執行） |
| 重點 | 績效 + 目標 + ESG 評等 + 財務連動 | 重大議題決策點 + 風險 + 資源請求 |
| 數字密度 | 高（KPI 重點圖表） | 中（聚焦戰略選擇） |
| 同業比較 | 必有 | 可選 |
| 措辭 | 投資語言（風險 / 機會 / 估值） | 治理語言（監督 / 核准 / 決議） |
| 結論頁 | 「我們做了什麼 + 接下來做什麼」 | 「請董事會核准的事項」 |

---

## 3. 標準結構

### 投資人版（13 頁範本）

```
1. 封面
2. CEO 訊息（1 段）
3. 雙重重大性矩陣
4. ESG 治理架構
5. 氣候戰略 + 轉型計劃
6. Scope 1/2/3 績效（YoY + 同業）
7. 水 / 廢棄物（產業適用）
8. 社會議題重點（人才 / 供應鏈）
9. 治理 + 誠信
10. ESG 評等與 ESG 連結薪酬
11. 目標進度 + SBTi
12. 風險與機會（TCFD 對照）
13. 結論：未來 12 個月優先事項
```

### 董事會版（7 頁範本）

```
1. 封面
2. 永續委員會本季 update（1 頁濃縮）
3. 重大議題與待決策點
4. 氣候風險與資源請求
5. 法規動態與合規狀態
6. 危機 / 重大事件揭露（如有）
7. 請董事會核准的事項
```

---

## 4. 樣式規範

| 元素 | 規範 |
|------|------|
| 配色 | 公司 brand 主色 + 1 次色 + 2 中性色（不超過 4 色） |
| 字型 | 中文 Noto Sans TC、英文 Inter / Calibri；標題粗體 |
| 投影片大小 | 16:9（除非客戶要求） |
| 標題 | 28–32 pt，**不加裝飾下劃線** |
| 內文 | 16–18 pt（董事會版可大到 20 pt） |
| 圖表 | SVG 或 ≥ 300 dpi PNG，圖表配色與簡報一致 |
| 視覺元素 | 每張投影片必有圖、icon、或表（純文字頁禁止） |
| 留白 | 邊距 ≥ 1 inch（讓投影機投影不切邊） |

---

## 5. 標準 Prompt 範本

### 5.1 投資人版（從零建立）

```
請呼叫 document-skills:pptx skill，建立投資人版永續簡報。

【Workflow 路徑】
從零建立 → pptxgenjs（Node）

【輸出絕對路徑】
/abs/path/to/.../assets/example-<industry>-2025/Investor_Deck_2025.pptx

【建立前確認】
- ESG_Data_Pack_2025.xlsx 已 finalize
- 圖表 PNG 已導出（解析度 ≥ 300 dpi，路徑：/abs/path/to/charts/）
- 公司 brand palette 已知（主色 hex / 次色 hex）

【投影片結構】
依 prompts/phase6-pptx.md §3「投資人版（13 頁範本）」建立。

【設計約束】
1. 配色：主色 #XXXXXX、次色 #YYYYYY、中性色 #F5F5F5、深灰 #333333（不超過 4 色）
2. 標題下不加裝飾線
3. 每張投影片必有視覺元素（圖 / icon / 表 / chart）
4. 字型：中文 Noto Sans TC、英文 Inter
5. 留白邊距 ≥ 1 inch

【內容組裝規則】
- 第 6 頁 Scope 數字直接從 ESG_Data_Pack_2025.xlsx 的 Scope 工作表讀取
- 第 11 頁目標進度用堆疊長條圖（基線 / 當年 / 目標）
- 第 12 頁 TCFD 對照用四象限圖（治理 / 策略 / 風險管理 / 指標目標）

【視覺 QA Loop（強制）】
完成 .pptx 後：
1. 用 LibreOffice headless 轉 PDF
2. 用 pdftoppm 把 PDF 每頁轉 JPG（300 dpi）
3. 對 JPG 序列 spawn 一個視覺檢查 subagent，使用以下 prompt：

   ---
   你是視覺設計品質檢查員。對下列 JPG 序列（投影片 1 至 N）逐張檢查：
   - 文字是否超出投影片邊界？
   - 標題與內文是否重疊？
   - 圖表配色是否與品牌一致？
   - 數字是否清晰可讀（投影距離 5 公尺仍可辨識）？
   - 視覺元素是否平衡？
   - 任何頁是否純文字無圖？

   逐張回報：
   - 頁碼
   - 問題描述
   - 修復建議（具體到「把 X 移到 Y 位置」）
   ---

4. 依檢查結果修正 .pptx
5. **重複 1–4 直到視覺檢查 0 問題**
6. **未完成至少一輪 fix-and-verify 不得宣告完成**

【完成後輸出】
- 檔案絕對路徑
- 投影片數
- 視覺 QA loop 跑了幾輪
- 最後一輪 subagent 回報
```

### 5.2 董事會版（從投資人版精簡）

```
請呼叫 document-skills:pptx skill，從 Investor_Deck_2025.pptx 精簡為董事會版。

【Workflow 路徑】
編輯範本 → unpack → 大量刪除 + 重組 → pack

【來源檔絕對路徑】
/abs/path/to/.../Investor_Deck_2025.pptx

【目標檔絕對路徑】
/abs/path/to/.../Board_Deck_2025.pptx

【精簡規則】
1. 從 13 頁減至 7 頁，依 §3「董事會版（7 頁範本）」結構
2. 措辭從「投資語言」改為「治理語言」（如「風險暴露」→「待決策點」）
3. 加上「請董事會核准的事項」明確列點
4. 移除 ESG 評等頁（董事會不關心）
5. 補上「永續委員會本季 update」（從 perm 紀錄）

【視覺 QA Loop（強制）】
同 §5.1 第 4 步，跑完整一輪 fix-and-verify。
```

### 5.3 範本基礎建構（適用首次建立公司範本）

```
請呼叫 document-skills:pptx skill，建立公司專屬永續簡報範本。

【Workflow 路徑】
從零建立 → pptxgenjs

【輸出絕對路徑】
/abs/path/to/.../assets/templates/sustainability_template.pptx

【範本內容】
- 母片：公司 logo（左上）、頁碼（右下）、頁眉品牌色帶
- 預設樣式：標題 / 內文 / 引用 / 圖表標題 4 種文字樣式
- 預設配色：4 色 palette
- 預設圖表類型：長條 / 堆疊長條 / 圓餅 / 折線（4 種，依公司 brand 上色）
- 占位符：標題、內文、圖表、表格

【完成後輸出】
- 範本檔絕對路徑
- 後續使用方式：呼叫此範本作為新建簡報的 base
```

---

## 6. 視覺 QA Loop 子 Prompt（完整版）

```
你是視覺設計品質檢查員。對下列 JPG 序列（投影片 1 至 N）逐張檢查並回報。

【輸入】
- JPG 序列路徑：/abs/path/to/render/slide_001.jpg ~ slide_NNN.jpg
- 設計約束：（從上層 prompt §5 複製）
  - 主色 #XXXXXX
  - 字型 Noto Sans TC + Inter
  - 標題下不加裝飾線
  - 每張投影片必有視覺元素
  - 留白邊距 ≥ 1 inch

【檢查項目】
1. 文字是否超出投影片邊界？（截斷或溢出）
2. 標題與內文是否重疊？
3. 圖表 / 表格是否與背景或文字重疊？
4. 配色是否符合 4 色 palette（不超過 4 色）？
5. 數字是否清晰可讀（5 公尺距離可辨識，視為 ≥ 16 pt）？
6. 純文字頁面（無圖、icon、chart、表）？
7. 視覺重心是否平衡（不偏左 / 偏右 / 頭重腳輕）？
8. 標題下是否誤加了裝飾線（明令禁止）？
9. 留白是否 ≥ 1 inch？
10. 圖表配色是否與簡報一致？

【回報格式】
針對每張投影片：

頁 N：
- 狀態：通過 / 待修正
- 問題（若有）：
  1. 具體問題描述
  2. 具體修復建議：「將 X 元素從 (x1, y1) 移到 (x2, y2)」/「將文字大小從 14pt 改為 18pt」/「移除標題下的橫線」
- 評分：1–5（5 = 完美，3 = 可用但有改進空間，1 = 嚴重問題）

【總結】
- 通過頁數 / 總頁數
- 高優先級修正項（評分 ≤ 2）
- 中優先級修正項（評分 = 3）
- 是否需要再跑一輪？（若任一頁 < 4 → 是）
```

---

## 7. 防呆檢查清單

- [ ] 視覺 QA loop 至少跑完一輪 fix-and-verify
- [ ] 配色 ≤ 4 色
- [ ] 標題下無裝飾線
- [ ] 每張投影片有視覺元素
- [ ] 字型嵌入（投放他人電腦不變預設）
- [ ] 16:9 比例
- [ ] 圖表來源（xlsx / 數據包）已標註
- [ ] 投資人版 / 董事會版用詞分別到位
- [ ] 不超過 15 頁（投資人）/ 8 頁（董事會）
- [ ] 中英版本（如需要）字數差異合理

---

## 8. 與下游 Phase 的銜接

| 銜接點 | 動作 |
|-------|------|
| → Phase 7 review | 投資人版供 IR 部門 review，董事會版供永續委員會 review |
| → Phase 8 對外發表 | 投資人版用於法說會 / IR 路演 |
| → 內部使用 | 董事會版進入年度報告佐證資料 |
| → 範本沿用 | §5.3 的範本可作為下年度起點 |

---

## 9. 失敗時的依賴提示

| 錯誤訊息片段 | 缺失依賴 | 處理 |
|-------------|---------|------|
| `Cannot find module 'pptxgenjs'` | npm package 未安裝 | 提示 `npm install -g pptxgenjs` |
| `pdftoppm: command not found` | Poppler 未安裝 | 提示安裝 Poppler |
| `markitdown: command not found` | markitdown 未安裝 | 提示 `pip install markitdown` |
| `Pillow / PIL not found` | Python 套件未安裝 | 提示 `pip install Pillow` |
| `soffice: command not found` | LibreOffice 未安裝 | 提示安裝 LibreOffice |

詳細指令見 pptx skill 自身 SKILL.md（authoritative）。
