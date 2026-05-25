---
slug: ghg-scope2
entity_type: kpi
topic_slug: E2-energy
name: GHG Scope 2（範疇二）外購電力排放（雙軌）
unit: tCO2e
framework_refs:
  - GRI 305-2
  - GHG Protocol Scope 2 Guidance
  - SASB SV-HL-130a.1
boundary: 營運控制法
formula: |
  地點基礎：tCO2e = 外購電量 kWh × 0.474 (kg CO2e/kWh, 113 年度) / 1000
  市場基礎：tCO2e = (外購電量 - T-REC) × EF / 1000
priority: 10
values_by_year: []
restatement_flag: false
xbrl_concept: null
---

# KPI: GHG Scope 2（雙軌）

## 定義

外購電力排放，必須以「地點基礎」與「市場基礎」雙軌呈現。

## 排放因子

- **113 年度（2024）台電電力排碳係數：0.474 kg CO2e/kWh**（經濟部能源署，2025-04-14 公告）
- 較 112 年度（0.494）下降 4.0%
- 市場基礎：扣除 T-REC 採購

## 計算公式

```
地點基礎：tCO2e = 外購電量 × 0.474 / 1000
市場基礎：tCO2e = (外購電量 - T-REC) × 殘餘 EF / 1000
```

台電未公告獨立殘餘係數；無 RE 採購時雙軌差異不顯著。

## 來源

`_legacy/phase2-research-log.md` §C1 台灣電力排放係數、`_legacy/phase4-xlsx-skeleton.md` Sheet 6 `05_GHG_S2`。

## 對齊原版（力麗 2023）

🟠 **力麗 2023 GRI 305-2 列入 GRI Index**，但 8.1 章僅半頁、**無實際數值表**。試做版加雙軌設計 + T-REC 欄位。
