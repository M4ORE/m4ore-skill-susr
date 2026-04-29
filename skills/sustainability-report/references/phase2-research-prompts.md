# Phase 2 Research — WebSearch / WebFetch Prompt 模板

**使用時機**：Phase 2 啟動時整批執行；reference 內容更新前；年度報告編製啟動會議後第一週。

**前置**：先讀 `websearch-pending.md` 確認本年度待查項目。本檔案提供查詢模板，輸出整合進 `research-log.md`（Phase 2 產出物）。

---

## 1. 查詢分類與優先序

| 類別 | 用途 | 頻率 |
|------|------|------|
| A. 法規與時程 | 確認當年度強制要求 | 每年必跑 |
| B. 排放因子與計算方法 | 更新 Scope 1/2/3 計算基礎 | 每年必跑 |
| C. 同業 Peer Benchmark | 校準揭露深度與目標野心 | 每年必跑 |
| D. 投資人期望與評等問項 | 補強揭露點 | 每年必跑 |
| E. 標準更新 | ISSB / ESRS / GRI / SBTi 變動 | 每半年 |
| F. 產業特定議題 | 半導體 / 金融 / 製造等 | 每年 |

**優先序**：A → B → E → C → D → F（法規與時程是 hard constraint，其餘是品質提升）

---

## 2. 查詢模板（直接複製即可）

### A. 法規與時程

#### A1. 台灣電力排碳係數最新版

```
WebSearch query: 台灣 電力 排碳 係數 2026 公告 能源署
WebSearch query: Taiwan electricity emission factor 2026 announcement
WebFetch: https://www.moeaea.gov.tw/ECW/populace/web_book/wHandWebBookFile.ashx?...
```

**抓取重點**：年度、公告值（kgCO₂e/kWh）、適用範圍（全電網 / 區域電網）、生效日

#### A2. 第四階段強制申報年度

```
WebSearch query: 上市上櫃 永續報告書 作業辦法 第四階段 資本額
WebSearch query: 金管會 永續報告書 強制 中小企業 年度
```

**抓取重點**：適用對象資本額門檻、實施年度、過渡期安排

#### A3. 第三方確信最新規定

```
WebSearch query: 永續報告書 第三方確信 強制 ISAE 3000
WebSearch query: 金管會 永續 限定確信 合理確信 適用對象
```

**抓取重點**：強制適用對象、確信類型（限定 vs 合理）、認可確信機構

#### A4. 公告時程與雙語版本要求

```
WebSearch query: 永續報告書 公告 期限 MOPS 2026
WebSearch query: 永續報告書 中英文 強制 外資
```

**抓取重點**：法定公告日期、是否需與財報同步、雙語強制對象

### B. 排放因子與計算方法

#### B1. IEA 國家電力因子最新版

```
WebSearch query: IEA Emissions Factors database 2026 update
WebFetch: https://www.iea.org/data-and-statistics/data-product/emissions-factors-2024
```

**抓取重點**：版本號、各國電網因子、Scope 2 雙重報告適用性

#### B2. GHG Protocol Scope 3 修訂

```
WebSearch query: GHG Protocol Scope 3 Standard revision 2026
WebSearch query: Land Sector and Removals Guidance final
```

**抓取重點**：是否有新版 Standard、Land Sector Guidance 進度、Cat 11 / Cat 15 修訂

#### B3. SBTi 標準變動

```
WebSearch query: SBTi Corporate Net-Zero Standard 2.0 final
WebSearch query: SBTi Scope 3 target requirement update
```

**抓取重點**：新版發布日、過渡期、Scope 3 涵蓋率要求變動

### C. 同業 Peer Benchmark（產業泛化模板）

#### C1. 通用模板：選 5 家最相近 peer

**步驟**：
1. 識別「規模 × 業務 × 地理」最相近的 3–5 家公司（含本土 1–2 家、國際 2–3 家）
2. 對每家執行查詢：

```
WebSearch query: <公司名> 永續報告書 <年度>
WebSearch query: <Company Name> sustainability report <year>
WebSearch query: <Company Name> ESG report <year> site:<公司官網>
```

3. 抓取重點（共通項，不分產業）：
   - 重大議題清單與排序
   - Scope 1/2/3 排放量與強度（強度單位需可比）
   - 目標野心（淨零年度、SBTi 認證狀態、SBTi 標的覆蓋率）
   - 揭露頁數、結構、是否取得第三方確信
   - 重大未達標項目與處理方式

4. **整理成可比表格**（強度單位需先標準化）：

| Peer | Scope 1 (tCO₂e) | Scope 2 市場 | Scope 3 涵蓋類別 | 強度（每營收/每產品） | SBTi 狀態 | 淨零年度 |
|------|-----------------|-------------|-----------------|---------------------|----------|---------|
| ...  | ...             | ...         | ...             | ...                 | ...      | ...     |

#### C2. 產業特定關注議題（補強 C1 通用模板）

不同產業的 peer benchmark 有不同重點，**先確認 SP1-004 試做產業，再對應補查**：

| 產業 | 必補查詢 | 重點議題 |
|------|---------|---------|
| 半導體 | 用水回收率、PFC 減量、RE100 進度、超純水管理 | E03 水、E07 化學品、E01 範疇三 Cat 11 |
| 金融 | 投融資組合排放（PCAF）、永續金融商品占比、TCFD 情境分析揭露 | Scope 3 Cat 15、S14 普惠金融 |
| 紡織 | 供應鏈勞動稽核、染整廢水、纖維循環 | S07/S08 勞動、E03 水、E04 廢棄物 |
| 食品 | 食安事件、生物多樣性、食物里程 | S09 產品安全、E05 生物多樣性 |
| 製造 | 職災率、危險物質、產品碳足跡 | S01 職安、E07 化學品 |
| 不動產 | 建築能效、綠建築認證、租戶 Scope 3 | E02 能源、Scope 3 Cat 13 |

**範例（半導體）**：
```
WebSearch query: <peer 名稱> water reclamation rate 2025
WebSearch query: <peer 名稱> PFC reduction roadmap
WebSearch query: <peer 名稱> RE100 progress 2025
```

**選 peer 時的選擇原則**：
- 至少 1 家本土上市櫃（規模相近）
- 至少 2 家國際領先者（揭露成熟度高）
- 至少 1 家規模略大者（學習揭露野心）
- 避免全選「best-in-class」造成不切實際的對標

### D. 投資人期望與評等問項

#### D1. MSCI ESG Ratings 最新方法論

```
WebSearch query: MSCI ESG Ratings methodology 2026 update
WebSearch query: MSCI key issue framework <industry>
```

#### D2. CDP Climate Change Questionnaire 最新題目

```
WebSearch query: CDP Climate Change questionnaire 2026 changes
WebFetch: https://www.cdp.net/en/guidance/guidance-for-companies
```

#### D3. Sustainalytics ESG Risk Rating

```
WebSearch query: Sustainalytics ESG Risk Rating methodology <industry>
```

**整理重點**：評等機構新增的問項 → 反推報告書應補揭露的點

### E. 標準更新

#### E1. ISSB 最新動態

```
WebSearch query: IFRS S1 S2 implementation guidance 2026
WebSearch query: ISSB connectivity financial reporting update
```

#### E2. ESRS 最新動態

```
WebSearch query: ESRS Set 2 sector standards adoption
WebSearch query: EFRAG ESRS implementation guidance 2026
```

#### E3. GRI 最新動態

```
WebSearch query: GRI Standards 2026 update biodiversity
WebSearch query: GRI sector standards mining oil gas
```

### F. 產業特定（範例：半導體）

```
WebSearch query: SEMI sustainability initiative 2026
WebSearch query: semiconductor PFC emission reduction roadmap
WebSearch query: semiconductor water positive commitment
```

**抓取重點**：產業協會倡議、共通指標、共同目標

---

## 3. Research Log 格式

每筆查詢後填入 `research-log.md`：

```markdown
### [日期] [類別代碼] [主題]

- **查詢字串**：（原始 query）
- **來源**：
  - 來源 1：URL（標題、發布日期）
  - 來源 2：URL（標題、發布日期）
- **關鍵發現**：
  - 發現 1
  - 發現 2
- **對報告書的影響**：
  - 章節 X 需更新：...
  - KPI Y 需重算：...
- **後續動作**：
  - [ ] 更新 reference: <檔案>
  - [ ] 通知 owner: <角色>
- **回填到 websearch-pending.md**：是 / 否
```

---

## 4. Citation 規則

報告書本文引用外部資訊時：

| 資訊類型 | 引用格式 |
|---------|---------|
| 法規 | 法規名稱、版本年度、發布單位（如「金管會 2026 修訂版」） |
| 排放因子 | 來源、版本、發布日期、適用範圍 |
| 同業數據 | 公司名稱 + 年度報告 + 頁碼 |
| 標準框架 | 標準名稱 + 版本（如「GRI 305-1 (2016)」） |
| 學術 / 產業研究 | 作者 / 機構 + 年度 + 標題 + URL |

**禁止**：引用維基百科、無作者部落格、二手轉述新聞作為唯一來源

---

## 5. 防止 Hallucination 的查證規則

1. **任何「2026 最新」「最新版」表述必須有 URL + 發布日期**
2. **數字三來源原則**：關鍵數字（peer 排放量、法規門檻）至少兩個獨立來源相符
3. **不確定就標註「需進一步確認」**，不要編
4. **截圖或保存 PDF**：法規與標準文件保存到 `assets/research-evidence/<year>/`，避免來源失效
5. **WebFetch 過大頁面要分段抓取**：直接從 PDF 章節編號定位，不要整份貼

**URL 失效處理**：本檔案中所有 WebFetch URL（能源署、IEA、CDP 等）僅為示範。若實際使用時 URL 已失效（404 / redirect / 改版），回退到 WebSearch 用對應 query 重新定位最新頁面，不要硬猜或使用快取版本。

---

## 6. 與其他 Phase 的銜接

| 銜接點 | 動作 |
|-------|------|
| → Phase 3 重大性評估 | C 類 peer benchmark 結果輸入議題池排序 |
| → Phase 4 數據工程 | A1 / B1 結果直接更新 Scope 計算 |
| → Phase 5 草稿 | C / D 結果作為「同業比較」段落素材 |
| → Phase 7 確信前 review | E 類標準更新確認對照表是否需修訂 |
| → 回填 websearch-pending.md | 完成查詢後填「最後確認日期 + URL」 |

---

## 7. 年度執行檢查表

- [ ] A 類 4 項全跑完，回填到 `websearch-pending.md`
- [ ] B 類 3 項至少 2 項有更新確認
- [ ] C 類至少選 5 家 peer 跑完
- [ ] D 類至少 1 家評等機構方法論已 review
- [ ] E 類三大標準（ISSB / ESRS / GRI）至少各 1 項
- [ ] `research-log.md` 完成度 ≥ 90%
- [ ] 重要證據已存到 `assets/research-evidence/<year>/`
