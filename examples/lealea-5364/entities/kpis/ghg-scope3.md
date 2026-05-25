---
slug: ghg-scope3
entity_type: kpi
topic_slug: E1-climate
name: GHG Scope 3（範疇三）價值鏈排放
unit: tCO2e
framework_refs:
  - GRI 305-3
  - GHG Protocol Scope 3 Standard
boundary: 營運控制法 + 上下游價值鏈
formula: "Σ(Activity × EF) over C1, C3, C4, C5, C6, C7（C11 排除）"
values_by_year: []
restatement_flag: false
xbrl_concept: null
---

# KPI: GHG Scope 3（旅館業重點 6+1 categories）

## 涵蓋 categories

- **C1 採購商品**：食材、布巾與紡織備品（**集團內力麗 1444/力鵬 1447 供應比例獨立標注**）、清潔備品
- **C3 燃料與能源相關活動**：電力 T&D 損失、上游燃料萃取
- **C4 上游運輸**：食材冷鏈物流、布巾配送（集團內車輛）
- **C5 廢棄物**：廚餘委外處理、客房垃圾、回收物
- **C6 商務旅行**：員工出差（高鐵 / 航空 / 租車）
- **C7 員工通勤**：**南投山區據點獨立**（自駕比例高、單程公里長）
- **C11 使用階段排放（取捨）**：客戶住房用電屬「自營範疇」（已計入 S2），客戶交通排放不可控且資料不可得，故 `Disclosure=N`

## 計算方法

支出法 / 平均法 / hybrid，每筆獨立標註資料品質（H/M/L）。

## 來源

`_legacy/phase4-xlsx-skeleton.md` Sheet 7 `06_GHG_S3`、`_legacy/phase2-research-log.md` §C4 國際因子庫。

## 對齊原版（力麗 2023）

🔴 **力麗 2023 未揭露 Scope 3** — `phase7-gap-analysis.md` 列為高嚴重度缺口。試做版示範完整 6+1 categories skeleton。
