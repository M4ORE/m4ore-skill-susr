---
slug: water-intensity
entity_type: kpi
topic_slug: E3-water
name: 用水強度（m³ / 住房數）
unit: m³ / room-night
framework_refs:
  - GRI 303-1
  - GRI 303-2
  - SASB SV-HL-140a.1
boundary: 各據點，含自來水 / 山泉水 / 地下井水 / 回收水
formula: "Σ取水量 / Σ住房數"
values_by_year: []
restatement_flag: false
xbrl_concept: null
---

# KPI: 用水強度

## 定義

每客房入住人天用水量，旅館業 SASB SV-HL-140a.1 核心指標。

## 計算公式

```
m³ / room-night = Σ取水量(m³) / Σ住房數
```

## 旅館業特化

- 取水來源獨立追蹤：自來水 / 山泉水 / 地下井水 / 回收水
- 水資源風險區（WRI Aqueduct）：日月潭流域中度 / 棲蘭低度
- 山泉 / 井水須附主管機關取水核准文件編號

## 來源

`_legacy/phase4-xlsx-skeleton.md` Sheet 8 `07_Water`。
