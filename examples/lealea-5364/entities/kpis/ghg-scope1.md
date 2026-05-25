---
slug: ghg-scope1
entity_type: kpi
topic_slug: E1-climate
name: GHG Scope 1（範疇一）絕對排放
unit: tCO2e
framework_refs:
  - GRI 305-1
  - GHG Protocol Corporate Standard
  - IPCC AR6 GWP
boundary: 營運控制法（含直營三館；Scenario B 含委託二館）
formula: "Σ(Activity × EF / 1000) over 燃氣鍋爐 / 廚房 / 公務車 / 發電機(備援) / HVAC 制冷劑外洩"
values_by_year: []
restatement_flag: false
xbrl_concept: null
---

# KPI: GHG Scope 1（範疇一）

## 定義

旅館營運直接排放：燃氣鍋爐熱水、廚房燃氣、公務車、發電機備援、HVAC 制冷劑外洩（補充量法）。

## 計算公式

```
tCO2e = Activity × EF / 1000
```

EF 來源：環境部 113 年版（2024）固定燃燒因子。

## 來源 / 對應 sheet

`_legacy/phase4-xlsx-skeleton.md` Sheet 5 `04_GHG_S1`。

## 旅館業特化

- 南投山區發電機備援獨立列
- 制冷劑採「補充量法」（年度補充量 × GWP）
- 委託二館 Scenario B 視可得性納入

## 對齊原版（力麗 2023）

🔴 **力麗 2023 未揭露 Scope 1** — `phase7-gap-analysis.md` 列為高嚴重度缺口。試做版示範完整 skeleton。
