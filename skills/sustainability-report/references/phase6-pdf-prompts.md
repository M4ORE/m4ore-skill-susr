# Phase 6 — pdf Skill 整合 Prompt 模板

**使用時機**：Phase 6 最終 PDF 輸出（用於 MOPS 公告 + 公司網站）、Phase 7 review 階段產生比對版、Phase 8 多語版本合併。

**子 skill**：`document-skills:pdf`（authoritative docs：`https://raw.githubusercontent.com/anthropics/skills/main/skills/pdf/SKILL.md`）

---

## 1. pdf Skill 的關鍵約束

| 約束 | 規則 |
|------|------|
| 輸入格式 | 自然語言 + **絕對檔案路徑**（單一或多檔） |
| 工具矩陣 | 不同任務用不同 lib，**prompt 中要明確指名** |
| Unicode 上下標陷阱 | **reportlab 不支援 unicode 上下標字元**（如 ₂ ₃ ²），**必須用 `<sub>` / `<super>` XML tag** |
| 環境依賴 | Python: `pypdf pdfplumber reportlab pytesseract pdf2image`、Poppler、`qpdf`、`pdftotext` |

## 2. 工具矩陣（任務 → 最佳工具）

| 任務 | 工具 | 命令範例 |
|------|------|---------|
| docx → PDF 轉檔 | LibreOffice headless | `soffice --convert-to pdf` |
| 多份 PDF 合併 | `pypdf` | `from pypdf import PdfWriter` |
| 提取文字 | `pdfplumber` | 表格抓取首選 |
| OCR 掃描檔 | `pytesseract` + `pdf2image` | 中文需裝 `tesseract-ocr-chi-tra` |
| 加密 / 解密 | `pypdf` 或 `qpdf` | qpdf 較快 |
| 拆頁 / 旋轉 | `pypdf` | |
| 從零產生 PDF（少用） | `reportlab` | 內建 Paragraph 處理上下標 |

## 3. 永續報告書 PDF 輸出規範

| 項目 | 規範 |
|------|------|
| 來源 | docx → PDF（不直接從 reportlab 生成主報告） |
| 解析度 | 300 dpi（含內嵌圖表） |
| 字型嵌入 | 必須嵌入（avoid「字型替換」造成排版位移） |
| 書籤 | 章節層級書籤自動產生（PDF 導覽用） |
| 元資料 | Title、Author、Subject、Keywords 完整填寫 |
| iXBRL 預留 | 對 ESRS / 未來金管會 iXBRL 要求預留結構化標記欄位（不在本 phase 完成，記錄為 follow-up） |
| 大小 | 主報告書建議 < 30 MB，> 50 MB 必須壓縮重出 |

---

## 4. 標準 Prompt 範本

### 4.1 docx → PDF（最常用）

```
請呼叫 document-skills:pdf skill，將 Report_2025.docx 轉為 PDF。

【工具選擇】
LibreOffice headless（soffice --convert-to pdf）

【輸入絕對路徑】
/abs/path/to/.../Report_2025.docx

【輸出絕對路徑】
/abs/path/to/.../Report_2025.pdf

【關鍵約束】
1. 解析度 300 dpi
2. 字型必須嵌入（檢查 PDF 屬性的「字型」分頁，無「無法嵌入」警告）
3. 自動生成章節書籤（依 docx 中的 H1/H2 結構）
4. 元資料填寫：
   - Title: <公司名> 2025 永續報告書
   - Author: <公司名>
   - Subject: ESG / Sustainability Report
   - Keywords: 永續, ESG, GRI, ISSB, TCFD, 金管會

【完成後輸出】
- 檔案絕對路徑
- 檔案大小（MB）
- 字型嵌入檢查結果
- 書籤層級數
```

### 4.2 多份 PDF 合併（主報告 + 確信報告 + 附錄）

```
請呼叫 document-skills:pdf skill，合併最終公告版 PDF。

【工具選擇】
pypdf

【輸入檔絕對路徑（合併順序）】
1. /abs/path/to/.../Report_2025_main.pdf
2. /abs/path/to/.../Assurance_Report.pdf
3. /abs/path/to/.../Appendix_GRI_Index.pdf

【輸出絕對路徑】
/abs/path/to/.../Report_2025_final.pdf

【關鍵約束】
1. 保留各原檔的書籤，合併後重新編組
2. 新增頂層書籤對應每段（主報告 / 確信 / 附錄）
3. 頁碼連續編號（不重置）
4. 合併後檔案 < 50 MB；若超過呼叫 qpdf 壓縮（保留圖片解析度 300 dpi）
```

### 4.3 從掃描檔做 OCR（如歷史合約備查）

```
請呼叫 document-skills:pdf skill，OCR 掃描版採購合約取得文字。

【工具選擇】
pytesseract + pdf2image（中文需安裝 tesseract-ocr-chi-tra 語言包）

【輸入絕對路徑】
/abs/path/to/scan/Supplier_Contract_2024.pdf

【輸出絕對路徑】
/abs/path/to/extracted/Supplier_Contract_2024_ocr.txt

【OCR 設定】
- 語言：chi_tra+eng
- DPI：300
- 預處理：去歪斜、去雜訊（pdf2image 內建選項）

【完成後輸出】
- 文字檔絕對路徑
- 信心分數平均
- 標註低信心區段（< 70%）以利人工 review
```

### 4.4 從 reportlab 產生表格密集附錄（少用）

```
請呼叫 document-skills:pdf skill，從 ESG_Data_Pack_2025.xlsx 產生附錄 F「完整 KPI 表」。

【工具選擇】
reportlab（含 Paragraph 處理上下標）

【輸入絕對路徑】
/abs/path/to/.../ESG_Data_Pack_2025.xlsx

【輸出絕對路徑】
/abs/path/to/.../Appendix_F_KPI_Table.pdf

【關鍵約束（reportlab 陷阱）】
1. 不得使用 unicode 上下標字元（CO₂ ₃ ² 等）
2. 必須改用 XML tag：
   - 下標：CO<sub>2</sub>e、Scope <sub>3</sub>
   - 上標：m<super>3</super>、3°C 用 3°C 即可（°符號可用）
3. 違反會導致 reportlab 渲染為亂碼或預設替代字符

【表格處理】
- pandas 讀 xlsx → reportlab Table
- 表頭粗體 + 公司主色底
- 數字右對齊、文字左對齊
- 跨頁時表頭自動重複
```

---

## 5. 防呆檢查清單

- [ ] PDF 字型已嵌入（無「無法嵌入」警告）
- [ ] 解析度 ≥ 300 dpi
- [ ] 章節書籤完整
- [ ] 元資料 4 欄已填
- [ ] 檔案大小 < 30 MB（主報告）/ < 50 MB（合併版）
- [ ] 若用 reportlab：無 unicode 上下標字元
- [ ] OCR 結果若有 < 70% 信心區段，已人工 review
- [ ] 加密設定（若公司要求）已套用且密碼已書面交付

---

## 6. iXBRL / ESEF 預留設計

CSRD（歐盟）已要求 iXBRL 標記；台灣金管會未來可能跟進。**現階段不執行**，但設計時預留：

- 各 KPI 在 docx 階段加 hidden bookmark（如 `kpi_scope1_2025`）
- 轉 PDF 時保留 bookmark
- 未來補上 iXBRL 標記時，bookmark 可作為 anchor

**現階段動作**：在 `assets/<example>/ixbrl-bookmark-list.md` 記錄已加 bookmark 的 KPI 清單，作為下年度升級基礎。

---

## 7. 與下游 Phase 的銜接

| 銜接點 | 動作 |
|-------|------|
| → Phase 7 review | PDF 是 reviewer 拿到的最終版 |
| → Phase 8 公告 | 最終 PDF 上 MOPS（檔案大小 + 元資料必須符合 MOPS 規範） |
| → 對外網站 | 同一份 PDF，加 OG 預覽用元資料即可 |
| → 投資人 / 客戶詢答 | 加密版（如有保密需求）+ 浮水印（公司內部留存） |

---

## 8. 失敗時的依賴提示

| 錯誤訊息片段 | 缺失依賴 | 處理 |
|-------------|---------|------|
| `pdftoppm: command not found` | Poppler 未安裝 | 提示安裝 Poppler |
| `No module named 'pdfplumber'` | Python 套件未安裝 | 提示 `pip install pdfplumber` |
| `tesseract: command not found` | Tesseract 未安裝 | 提示安裝 + 中文語言包 |
| `qpdf: command not found` | qpdf 未安裝 | 提示安裝 qpdf 或改用 pypdf 替代 |

詳細指令見 pdf skill 自身 SKILL.md（authoritative）。
