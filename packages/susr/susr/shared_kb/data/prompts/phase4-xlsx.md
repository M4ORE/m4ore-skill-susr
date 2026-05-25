---
slug: phase4-xlsx-prompts
category: prompt
source: skills/sustainability-report/references/phase4-xlsx-prompts.md
version: "2025-05-25"
language: zh-Hant
last_reviewed: 2025-05-25
phase: 4
sub_skill: document-skills:xlsx
---

# Phase 4 — xlsx Skill 整合 Prompt 模板

**使用時機**：Phase 4 數據工程啟動時、需要建立或更新 ESG_Data_Pack 時、Phase 7 確信前 review 時。

**子 skill**：`document-skills:xlsx`（authoritative docs：`https://raw.githubusercontent.com/anthropics/skills/main/skills/xlsx/SKILL.md`）

---

## 1. xlsx Skill 的關鍵約束（必須在 prompt 中遵守）

| 約束 | 規則 |
|------|------|
| 輸入格式 | 自然語言 + **絕對檔案路徑**，**不接受 JSON 結構化輸入** |
| 計算方式 | **強制使用 Excel 公式**，**禁止用 Python 預先算好寫死數值** |
| 驗證循環 | 寫完後**必須**呼叫 `scripts/recalc.py`，直到回傳 `errors_found = 0` |
| 數據存活 | 用 `data_only=True` 開檔再存 = 公式永久失效（嚴禁） |
| 環境依賴 | LibreOffice（recalc 用）+ Python `openpyxl pandas` |

---

## 2. ESG_Data_Pack 標準結構

每年度產出一份 `ESG_Data_Pack_<year>.xlsx`，含下列工作表：

| Sheet | 內容 | 公式重點 |
|-------|------|---------|
| `0_Coversheet` | 編製單位、版本、邊界、責任人、最後修訂 | 無公式 |
| `1_Boundary` | 合併報表 / 控制 / 股權法的實體清單與權重 | 加總驗證 |
| `2_Scope1` | 自有源、移動源、製程、逸散排放（活動量 × 因子 = tCO₂e） | 乘法 + 小計 |
| `3_Scope2_Location` | 各場址外購電力（地點基礎） | 用電 × 電網因子 |
| `3_Scope2_Market` | 各場址外購電力（市場基礎，含 PPA / RE100） | 用電 × 合約因子 |
| `4_Scope3` | 15 類分頁 sub-tabs，至少前 5 大重大類別 | 各類獨立公式 |
| `5_Intensity` | 強度指標（每營收 / 每員工 / 每產品） | Scope 1+2 / 分母 |
| `6_Energy` | 能源使用（用電、燃料、再生能源比例） | 加總、比例 |
| `7_Water` | 取水、排水、回收 | 平衡式驗證 |
| `8_Waste` | 一般、有害、回收率 | 加總、比例 |
| `9_Social_HR` | 員工結構、訓練、職災 | 比例 |
| `10_Governance` | 董事會結構、薪酬連結 | 比例 |
| `11_Restatement_Log` | 基線重述紀錄（>5% 觸發） | 對照欄 |
| `12_Assurance_Trail` | 每個 KPI 的來源、邊界、公式、責任人 | 索引 |
| `13_Validation` | 全自動檢查（合計一致性、單位、邊界） | 條件公式 + 紅綠燈 |

---

## 3. 樣式規範（xlsx skill 的內建慣例）

| 元素 | 樣式 |
|------|------|
| Input 儲存格（手動輸入活動量） | 淺藍色填充（#D9E1F2） |
| Formula 儲存格（公式計算） | 淺灰色填充（#F2F2F2）+ 鎖定 |
| 不該動的常數（如排放因子） | 淺黃色填充（#FFF2CC）+ 註解標來源 |
| 標題列 | 深底白字 + 粗體 |
| 警告（>5% 變動、紅旗） | 紅字 / 紅底 |
| 數字格式 | tCO₂e 取整數、百分比 1 位、貨幣依公司本位 |

---

## 4. 標準 Prompt 範本（直接複製）

### 4.1 建立全新 Data Pack

```
請呼叫 document-skills:xlsx skill，建立 ESG_Data_Pack_2025.xlsx。

【輸出絕對路徑】
/abs/path/to/project/assets/example-<industry>-2025/ESG_Data_Pack_2025.xlsx

【建立前確認】
- 輸出目錄已建立（若無請先 mkdir -p）
- 公司基本資訊已從 Phase 1 scoping-decision.md 讀取

【Sheet 結構】
依 prompts/phase4-xlsx.md §2 的 14 個工作表清單建立。

【關鍵約束（必須遵守）】
1. 所有計算欄位必須使用 Excel 公式（如 =B2*C2），不得用 Python 預算後寫死數值
2. Input 欄位淺藍 (#D9E1F2)、Formula 欄位淺灰 (#F2F2F2)、常數欄位淺黃 (#FFF2CC)
3. 排放因子欄位必須在儲存格註解標註：來源、版本年度、發布單位
4. 每個 Scope 工作表底部需有「合計」欄位 + 對 0_Coversheet 的反查驗證公式
5. 13_Validation 工作表內含 IFERROR / IF 條件公式，單位不一致 / 加總不對自動標紅

【完成驗證（強制）】
- 寫檔完成後立即呼叫 xlsx skill 內附的 scripts/recalc.py
- 若回傳 status: errors_found，將 #REF! / #DIV/0! / #VALUE! 錯誤位置逐一修復
- 重複 recalc 直到 errors_found = 0 才視為完成
- 不允許在仍有錯誤的狀態下交付

【完成後輸出】
- 檔案絕對路徑
- recalc.py 最終回傳的 JSON
- 13_Validation 工作表的紅旗清單（若有）
```

### 4.2 更新既有 Data Pack（年度滾動）

```
請呼叫 document-skills:xlsx skill，更新既有 ESG_Data_Pack_<year>.xlsx 至下一年度。

【既有檔絕對路徑】
/abs/path/to/.../ESG_Data_Pack_2024.xlsx

【目標檔絕對路徑】
/abs/path/to/.../ESG_Data_Pack_2025.xlsx

【更新規則】
1. 複製為新檔，不得直接覆寫舊檔（保留稽核軌跡）
2. 0_Coversheet 版本欄遞增、最後修訂日填 today
3. 各 Scope 工作表：保留歷史欄、新增當年欄
4. 11_Restatement_Log：若任一歷史值因方法論修訂或邊界變更導致 >5% 變動，必須記錄
5. 排放因子若有更新（依 checklists/websearch-pending.md 查證結果），更新常數欄並在註解加上「YYYY-MM-DD 因子版本更新」

【關鍵約束】
- 公式結構必須沿用，不得改寫成硬編碼數值
- data_only=True 開檔嚴禁（會永久失去公式）
- 跑 scripts/recalc.py 直到 errors_found = 0

【完成後輸出】
- 新舊檔差異摘要（哪些 Sheet 有變動）
- 11_Restatement_Log 的新增列
```

### 4.3 個別工作表精修（如 Scope 3 Cat 11）

```
請呼叫 document-skills:xlsx skill，更新 ESG_Data_Pack_2025.xlsx 中 4_Scope3 工作表的 Cat 11（售出產品的使用）。

【檔案絕對路徑】
/abs/path/to/.../ESG_Data_Pack_2025.xlsx

【更新內容】
- 產品清單從 source.csv 匯入(路徑：/abs/path/to/source.csv)
- 對每項產品：年銷量 × 單品生命週期排放係數 = 排放量
- 生命週期排放係數來源於 LCA 報告（路徑：/abs/path/to/lca-report.pdf）

【關鍵約束】
- 每個 SKU 一列，公式不得寫死合計
- 係數欄加註解：LCA 報告章節編號 + 計算邊界（製造 only / cradle-to-gate / cradle-to-grave）
- 邊界揭露欄位若不一致，13_Validation 必須標紅

【完成驗證】
跑 scripts/recalc.py 直到 errors_found = 0
```

---

## 5. 防呆檢查清單（agent 完成 xlsx 任務前 self-check）

- [ ] 所有 KPI 欄位是公式而非硬編碼
- [ ] 排放因子欄位有來源、版本、發布單位的註解
- [ ] 13_Validation 工作表的紅旗 = 0
- [ ] `scripts/recalc.py` 最後一次回傳 `errors_found: 0`
- [ ] 檔案大小 < 50 MB（過大表示嵌入了不必要的物件）
- [ ] 沒有任何 sheet 隱藏（影響稽核透明度）
- [ ] 0_Coversheet 的最後修訂日已更新

---

## 6. 與下游 Phase 的銜接

| 銜接點 | 動作 |
|-------|------|
| → Phase 5 草稿撰寫 | 從 5_Intensity / 各 Scope sheet 取數字寫入章節 |
| → Phase 6 docx 組裝 | 圖表來源欄位需可導出為 PNG（用 pptx skill 轉檔，見 prompts/phase6-pptx.md） |
| → Phase 7 確信前 review | 12_Assurance_Trail 是 audit trail 的核心，提供確信機構 |
| → 次年滾動 | 用 §4.2 模板，不從零開始 |

---

## 7. 常見錯誤與對策

| 錯誤 | 原因 | 對策 |
|------|------|------|
| `#REF!` 在 Scope 3 sheet | 跨 sheet 連結斷掉 | 修復後重跑 recalc.py |
| 公式變硬編碼數字 | agent 偷懶用 Python 算後填值 | 在 prompt 強調「禁止 Python 預算」並 review 公式列 |
| 排放因子無註解 | agent 忽略註解要求 | prompt 明列「每個常數欄必須有來源註解」 |
| 跨年度單位不一致 | 沒看舊版本就改 | §4.2 強制讀舊檔複製 |
| 確信機構抓不到計算邏輯 | 12_Assurance_Trail 缺漏 | self-check 必看此 sheet |

---

## 8. 失敗時的依賴提示

若 xlsx skill 呼叫失敗，依錯誤訊息檢查：

| 錯誤訊息片段 | 缺失依賴 | 處理 |
|-------------|---------|------|
| `LibreOffice not found` 或 `soffice: command not found` | LibreOffice 未安裝 | 提示使用者安裝 LibreOffice，並指向 xlsx skill 自身 SKILL.md |
| `No module named 'openpyxl'` | Python 套件未安裝 | 提示 `pip install openpyxl pandas` |
| `recalc.py: ...` | 跑 recalc 環境問題 | 詳見 xlsx skill 自身的 troubleshooting |

不提供完整安裝指令，指向 sub-skill 自己的文件（避免不同步）。
