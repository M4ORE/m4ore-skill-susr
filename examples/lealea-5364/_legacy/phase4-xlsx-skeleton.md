# Phase 4 — ESG_Data_Pack.xlsx 結構規格（力麗觀光 5364）

**用途**：作為 `document-skills:xlsx` 的 build prompt 輸入，產出 Phase 4 數據母檔。
**標的**：力麗觀光（254 員工、5 旅館：日潭/月潭/木棉道/明池/棲蘭）。
**標準**：GRI 2021 + GHG Protocol（Corporate + Scope 3）+ SASB Hotels & Lodging（SV-HL）。
**邊界處理（重要）**：所有 sheet 設一欄 `Scenario`（A=直營三館 / B=直營+委託全 5 館），以營運控制法雙軌呈現。

---

## Sheet 清單（共 12 sheets）

| # | Sheet | 用途 | GRI / SASB 對應 |
|---|---|---|---|
| 1 | `00_README` | 使用說明、邊界、版本、單位、縮寫 | GRI 2-1~2-4 |
| 2 | `01_Versions` | 版本紀錄、排放因子版本切換、re-statement log | GRI 2-4 |
| 3 | `02_Sites` | 5 據點 master：地理、樓地板、客房數、營運型態 | GRI 2-1 |
| 4 | `03_Energy` | 電、燃氣、柴油、太陽能（如有） | GRI 302、SV-HL-130a.1 |
| 5 | `04_GHG_S1` | Scope 1：燃氣鍋爐/車輛/廚房/制冷劑/發電機 | GRI 305-1 |
| 6 | `05_GHG_S2` | Scope 2 雙軌（地點 / 市場） | GRI 305-2 |
| 7 | `06_GHG_S3` | Scope 3：C1/C3/C4/C5/C6/C7（C11 註腳處理） | GRI 305-3 |
| 8 | `07_Water` | 取水（自/山泉/井）、排水、再生水、水風險 | GRI 303、SV-HL-140a.1 |
| 9 | `08_Waste` | 一般/廚餘/回收/有害 | GRI 306 |
| 10 | `09_HR` | 員工結構、流動、訓練、薪酬比、外包/派遣 | GRI 2-7、401、404、405 |
| 11 | `10_OHS_Food` | 職安（FR/SR/千人率）+ 食安（HACCP/事件） | GRI 403、416 |
| 12 | `11_Customer_Local` | 客滿意度/客訴/隱私/在地僱用採購 | GRI 204、413、418、SV-HL-230a |

**通用約定**：
- 所有數據 sheet 包含欄：`Year`(數字), `Site_ID`(FK→02_Sites), `Scenario`(A/B), `Value`, `Unit`, `Source_System`, `Owner_Dept`, `Confidence`(H/M/L), `Note`
- 底列固定 SUM 行（公式 `=SUM(...)`），合計與細項不一致時條件格式標紅
- 跨年比對欄 `YoY_%` = `(本年-去年)/去年`；`|YoY_%|>5%` 觸發 `Restatement_Flag` = TRUE，於 `01_Versions` 補註

---

## Sheet 1 — `00_README`

| 欄 | 中文 | 型別 | 說明 |
|---|---|---|---|
| A | 項目 | 文字 | 報告期間 / 邊界方法 / 標準組合 / 單位定義 / Scenario 定義 |
| B | 內容 | 文字 | 對應內容 |
| C | 備註 | 文字 | 限制 / 假設 |

**必填區塊**：報告期間 2023-01-01~12-31；邊界＝營運控制法；Scenario A vs B 差異說明；GWP 採 IPCC AR6；單位（kWh, MJ, m³, tCO2e, tonne, person, hour, NTD）。

---

## Sheet 2 — `01_Versions`

| 欄 | 中文（英） | 型別 | 說明 |
|---|---|---|---|
| A | 版本號 (Version) | 文字 | v0.1, v0.2... |
| B | 日期 (Date) | 日期 | YYYY-MM-DD |
| C | 修改人 (Editor) | 文字 | 部門 + 姓名 |
| D | 修改範圍 (Scope) | 文字 | 哪個 sheet / 欄位 |
| E | 變動原因 (Reason) | 文字 | 含 restatement 理由 |
| F | 排放因子版本 (EF_Version) | 文字 | 例：環境部 113 年版 / IPCC AR6 / DEFRA 2023 |
| G | YoY 變動率 (YoY_%) | 公式 | 引用對應 sheet |
| H | Restatement 旗標 | 公式 | `=IF(ABS(G)>0.05,TRUE,FALSE)` |

---

## Sheet 3 — `02_Sites`（據點 master）

| 欄 | 中文（英） | 型別 | 範例 |
|---|---|---|---|
| A | Site_ID | 文字 PK | S01~S05 |
| B | 據點名 (Name) | 文字 | 力麗哲園日潭館 / 月潭館 / 木棉道 / 明池山莊 / 棲蘭山莊 |
| C | 區域 (Region) | 文字 | 南投/台南/宜蘭 |
| D | 營運型態 (Operation) | 文字 | 直營 / 委託經營 |
| E | Scenario_Inclusion | 文字 | A / A+B |
| F | 客房數 (Rooms) | 數字 | — |
| G | 樓地板面積 (GFA m²) | 數字 | — |
| H | 海拔 / 水資源風險區 | 文字 | 例：日月潭流域、棲蘭山區 |
| I | 員工數 (Headcount) | 數字 | 連動 09_HR 合計 |

---

## Sheet 4 — `03_Energy`

| 欄 | 中文（英） | 型別 | 公式 / 說明 |
|---|---|---|---|
| A | Year | 數字 | |
| B | Site_ID | FK | |
| C | 能源類別 (Type) | 文字 | 外購電 / 天然氣 / 桶裝瓦斯 / 柴油（發電機+公務車） / 汽油 / 太陽能自發自用 / 綠電憑證 |
| D | 活動數據 (Activity) | 數字 | 原始用量 |
| E | 單位 (Unit) | 文字 | kWh / m³ / L |
| F | 換算 MJ (Energy_MJ) | 公式 | `=D*F_factor` 對 04_GHG 因子表 |
| G | 自發自用比例 (%) | 公式 | 太陽能 / 總用電 |
| H | 綠電憑證 (T-REC kWh) | 數字 | |
| I | Scope 對應 | 文字 | S1 / S2 |
| J | Source_System | 文字 | 台電帳單 / 欣中燃氣帳單 / 加油憑證 |
| K | Owner_Dept | 文字 | 工程部 |

**底部驗證列**：總用電 SUM、總燃氣 SUM、能耗強度 = 總 MJ / 住房數（連動 11_Customer）。

---

## Sheet 5 — `04_GHG_S1`

| 欄 | 中文（英） | 型別 | 公式 |
|---|---|---|---|
| A-C | Year / Site_ID / Scenario | — | |
| D | 排放源 (Source) | 文字 | 燃氣鍋爐(熱水) / 廚房燃氣 / 公務車 / 發電機(備援) / 制冷劑外洩(HVAC) |
| E | 活動數據 | 數字 | 用量 |
| F | 單位 | 文字 | m³ / L / kg |
| G | 排放因子 EF | 數字 | 從因子表抓（命名範圍 `EF_Table`） |
| H | EF 來源 | 文字 | 環境部 113 年版 / IPCC AR6 / GWP 值 |
| I | 排放量 tCO2e | 公式 | `=E*G/1000` |
| J | GWP 版本 | 文字 | AR6（制冷劑 R410A=2256 等） |
| K | Source_System | 文字 | 帳單 / 加油憑證 / 維修紀錄 |

**南投山區特化**：發電機備援應獨立列；制冷劑採「補充量法」（年度補充量 × GWP）。
**底部 SUM**：`Total_S1 = SUM(I:I)`；強度 `tCO2e/員工`、`tCO2e/百萬營收`。

---

## Sheet 6 — `05_GHG_S2`

| 欄 | 中文（英） | 型別 | 公式 |
|---|---|---|---|
| A-C | Year / Site_ID / Scenario | — | |
| D | 外購電量 kWh | 數字 | 連動 03_Energy |
| E | 地點基礎 EF (kgCO2e/kWh) | 數字 | 經濟部能源署最新公告（2023=0.494） |
| F | 地點基礎排放 tCO2e | 公式 | `=D*E/1000` |
| G | 市場基礎 EF | 數字 | 扣除已採購之 T-REC |
| H | 已採購 T-REC kWh | 數字 | 連動 03_Energy |
| I | 市場基礎排放 tCO2e | 公式 | `=(D-H)*E/1000`（無自選合約時 fallback） |
| J | EF 版本 | 文字 | 公告年度 |

**雙軌呈現**：location-based 與 market-based 分開列示，附對照註腳。

---

## Sheet 7 — `06_GHG_S3`（旅館業重點 6+1 categories）

| 欄 | 中文（英） | 型別 | 說明 |
|---|---|---|---|
| A | Category | 文字 | C1/C3/C4/C5/C6/C7/C11 |
| B | Sub_Item | 文字 | 見下表 |
| C | Year | 數字 | |
| D | Scenario | 文字 | |
| E | 活動數據 | 數字 | |
| F | 單位 | 文字 | |
| G | EF | 數字 | |
| H | EF 來源 / 方法 | 文字 | 支出法 / 平均法 / hybrid |
| I | 排放 tCO2e | 公式 | `=E*G` |
| J | 資料品質 | 文字 | H/M/L（一級資料 vs 推估） |
| K | 是否揭露 | 文字 | Y/N + 理由 |

**Sub_Item 對照（旅館業特化）**：
- **C1 採購商品**：食材（生鮮/乾貨/飲料）、布巾與紡織備品（**集團內力麗1444/力鵬1447供應比例獨立標注**）、清潔備品、客房備品（一次性盥洗）。
- **C3 燃料與能源相關活動**：電力 T&D 損失、上游燃料萃取。
- **C4 上游運輸**：食材冷鏈物流、布巾配送（集團內車輛）。
- **C5 廢棄物**：廚餘委外處理、客房垃圾、回收物。
- **C6 商務旅行**：員工出差（高鐵/航空/租車）。
- **C7 員工通勤**：**南投山區據點獨立**（自駕比例高、單程公里長），用問卷推估法。
- **C11 使用階段排放（取捨說明欄位）**：
  - 旅館業 vs 製造業差異：客戶住房用電屬「自營範疇」（已計入 S2，不重複算 C11）；
  - 客戶從家裡到旅館的「住客交通」屬下游但**通常不納入**（GHG Protocol 旅館業實務）；
  - 本表設 `C11` 但 `Disclosure=N` + 理由欄記載「旅館營運控制法下，客戶用電已計於 S2；客戶交通排放不可控且資料不可得，故不納入」。

**底部驗證**：每 category SUM；Total_S3 SUM；S1+S2+S3 強度（每員工 / 每百萬營收 / 每住房數）。

---

## Sheet 8 — `07_Water`

| 欄 | 中文（英） | 型別 | 說明 |
|---|---|---|---|
| A-C | Year / Site_ID / Scenario | — | |
| D | 取水來源 (Source) | 文字 | 自來水 / 山泉水 / 地下井水 / 回收水 |
| E | 取水量 (Withdrawal m³) | 數字 | |
| F | 排水量 (Discharge m³) | 數字 | |
| G | 耗水量 (Consumption) | 公式 | `=E-F` |
| H | 再生水使用 (Recycled m³) | 數字 | |
| I | 再生水比例 | 公式 | `=H/E` |
| J | 水資源風險區 (WRI Aqueduct) | 文字 | 日月潭流域中度 / 棲蘭低度（外部 reference） |
| K | Source_System | 文字 | 自來水帳單 / 流量計 / 估算 |

**強度**：m³ / 住房數、m³ / 員工。
**驗證**：`Discharge ≤ Withdrawal`；山泉/井水須附主管機關取水核准文件編號欄。

---

## Sheet 9 — `08_Waste`

| 欄 | 中文（英） | 型別 | 說明 |
|---|---|---|---|
| A-C | Year / Site_ID / Scenario | — | |
| D | 廢棄物類別 | 文字 | 一般事業 / 廚餘 / 資源回收（紙/塑/鐵鋁/玻璃）/ 有害（廢電池/廢燈管/醫療急救品）|
| E | 處理方式 | 文字 | 焚化 / 掩埋 / 堆肥 / 回收 / 委外有害處理 |
| F | 重量 (tonne) | 數字 | |
| G | 處理廠商 (Vendor) | 文字 | 須附許可證號 |
| H | 廠商許可證號 | 文字 | 環保署核發 |

**驗證**：總廢棄量 = 各類別合計；廚餘比 = 廚餘 / 總；有害類獨立 SUM 並對應職安欄位。

---

## Sheet 10 — `09_HR`（員工結構）

**Block A — 人數結構**

| 欄 | 中文（英） | 型別 | 說明 |
|---|---|---|---|
| A | Site_ID | FK | |
| B | 性別 | 文字 | M/F/Other |
| C | 年齡層 | 文字 | <30 / 30-50 / >50 |
| D | 職等 | 文字 | 主管 / 專業 / 一般 / 派遣 / 兼職 / **房務外包** |
| E | 僱用型態 | 文字 | 正職 / 約聘 / 派遣 / 兼職 |
| F | 國籍 | 文字 | 本國 / 移工（旅館業常見） |
| G | 在地僱用 (Y/N) | 文字 | 戶籍同縣市 |
| H | 人數 | 數字 | |

**Block B — 流動 / 訓練 / 薪酬**

| 欄位 | 公式 |
|---|---|
| 新進 | 數字 |
| 離職 | 數字 |
| 流動率 | `=離職/期初人數` |
| 訓練時數 | 數字（依職等分組） |
| 平均訓練時數 | `=訓練時數/人數` |
| 平均薪資 | 數字（依性別×職等） |
| 男女薪酬比 | `=女平均/男平均` |
| 最高薪 / 中位數薪比 | 公式 |

**跨 sheet 驗證**：`SUM(人數) = 02_Sites!I合計 = 254`；性別合計 = 年齡合計 = 職等合計（條件格式不等時標紅）。

---

## Sheet 11 — `10_OHS_Food`

**職安**

| 欄 | 中文（英） | 公式 |
|---|---|---|
| 工時 (Hours_Worked) | 數字 | |
| 失能傷害次數 | 數字 | |
| 失能傷害日數 | 數字 | |
| FR | `=次數*1e6/工時` |
| SR | `=日數*1e6/工時` |
| 千人率 | `=次數*1000/人數` |
| 職業病案例 | 數字 | 餐飲燙傷 / 房務肌肉骨骼 / 夜班疲勞 分類 |
| 夜班人數 | 數字 | |

**食品安全**

| 欄 | 內容 |
|---|---|
| HACCP 認證範圍 | 餐廳清單 + 證書編號 + 有效期 |
| 食安事件數 | 數字 + 嚴重度 |
| 食材在地溯源比例 | 公式 = 在地採購 / 總採購（連動 11） |
| 食材檢驗次數 | 數字 |

---

## Sheet 12 — `11_Customer_Local`

| 欄 | 中文（英） | 型別 | 說明 |
|---|---|---|---|
| Site_ID | FK | | |
| 住房數 (Room_Nights) | 數字 | 強度分母來源 |
| 住房率 (Occupancy %) | 公式 | |
| 滿意度分數 | 數字 | 5 分制平均 |
| 客訴件數 | 數字 | |
| 客訴回應時數中位數 | 數字 | |
| 隱私事件 | 數字 | GRI 418-1 |
| 會員資料筆數 | 數字 | |
| 在地採購金額 | 數字 NTD | |
| 總採購金額 | 數字 NTD | |
| 在地採購比例 | 公式 = 在地/總 | 按據點 |
| 在地僱用比例 | 公式 引 09_HR | |

**SASB 對應**：SV-HL-230a.1（資料外洩）、SV-HL-310a（員工流動率）、SV-HL-440a（生態敏感區營運）。

---

## 公式與驗證匯總

| 類型 | 範例 |
|---|---|
| 排放計算 | `tCO2e = Activity × EF / 1000`（EF 引用 named range `EF_v2023`） |
| 強度（員工） | `=Total_GHG / Headcount` |
| 強度（營收） | `=Total_GHG / Revenue_M_NTD` |
| 強度（住房） | `=Total_GHG / Room_Nights`（旅館業 SASB 主指標） |
| 跨年變動 | `=(Y-Y_prev)/Y_prev`；`|>5%|` 觸發 restatement |
| 跨 sheet check | `=09_HR!Total = 02_Sites!Headcount_Total`，不等則紅 |
| Scenario 切換 | 用 `Data Validation` 下拉 A/B；公式 `SUMIF(Scenario=$A$1, ...)` |

---

## 給 `document-skills:xlsx` 的 prompt 範本（可直接複製）

```
請依下列規格 build 一份 ESG_Data_Pack_LeaLea_5364_v0.1.xlsx：

[基本]
- 12 sheets，名稱固定：00_README, 01_Versions, 02_Sites, 03_Energy,
  04_GHG_S1, 05_GHG_S2, 06_GHG_S3, 07_Water, 08_Waste, 09_HR,
  10_OHS_Food, 11_Customer_Local
- 報告期間 2023-01-01~12-31；單位以中文標註，公式以 SI 單位計算
- 全表配色：表頭深綠 #1F6F3D 白字、Sub-header 淺綠 #D9E8DC、SUM 列粗體底線

[共通欄]
每個數據 sheet 前置欄：Year, Site_ID, Scenario(A/B), Value, Unit,
Source_System, Owner_Dept, Confidence(H/M/L), Note。
所有 Site_ID 設 Data Validation 下拉，引用 02_Sites 的 A 欄。
所有 Scenario 設下拉 A/B。

[02_Sites]
建立 5 列：S01 力麗哲園日潭館(南投/直營/A+B)、S02 月潭館(南投/直營/A+B)、
S03 木棉道(台南/直營/A+B)、S04 明池山莊(宜蘭/委託/B)、S05 棲蘭山莊(宜蘭/委託/B)。

[公式 / 驗證]
- 04_GHG_S1 / 05_GHG_S2 / 06_GHG_S3 設 named range `EF_v2023` 對應因子表
- 03_Energy 計算 MJ 與強度
- 09_HR 設條件格式：性別/年齡/職等合計與 Site 員工數總計不等時填紅
- 每個 sheet 底部設 SUM 列；右側加 YoY_% 欄與 Restatement_Flag(>5%)
- 05_GHG_S2 同時呈現 Location-based 與 Market-based 兩列

[填值規則]
- 數字欄留空但設好格式（千分位、2 位小數、tCO2e 顯示 0.00）
- 註腳欄留模板文字 "[來源：___；計算法：___；責任人：___]"
- 委託經營據點 (S04/S05) 在 Scenario=A 時 SUMIF 排除

[輸出]
存於 examples/lealea-5364/phase4-data-pack/ESG_Data_Pack_LeaLea_5364_v0.1.xlsx，
凍結首列+Site_ID 欄；新增工作表保護（公式欄鎖定，數據欄可編輯）。
```

---

## 邊界處理註解（給 Phase 5 章節撰寫引用）

- **Scenario A（直營三館）**：日潭/月潭/木棉道。最保守、最可控。
- **Scenario B（直營+委託 5 館）**：含明池/棲蘭，符合營運控制法廣義解。
- **建議主揭露 = B，附錄揭露 = A 對照**，並於 `00_README` 與報告書「報告邊界」章明示。
- 委託經營據點若無法取得獨立水/電帳單，於 `Confidence=L` + Note 註明「估算法：依客房數比例分攤」。
