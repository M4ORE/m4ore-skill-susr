---
slug: sasb-hl
entity_type: framework
version: "2018-10"
disclosures:
  - SV-HL-130a.1 Energy management — energy consumed
  - SV-HL-140a.1 Water management — total water withdrawn
  - SV-HL-260a.1 Customer health and safety — food safety violations
  - SV-HL-310a.1 Labor practices — average wages and turnover
  - SV-HL-310a.2 Labor practices — diversity
  - SV-HL-410a.1 Climate change adaptation — properties in 100-year flood zones
is_mandatory_in:
  - US
  - Global
---

# SASB — Hotels & Lodging (SV-HL)

**發行機構**：Sustainability Accounting Standards Board（現為 IFRS Foundation 旗下 ISSB）
**領域**：行業特定（觀光旅館業）
**首次發布**：2018 年。

## 範圍

SASB Hotels & Lodging Industry Standard 提供旅館業財務重大性指標清單，含環境、客戶健康安全、勞動實務、氣候適應四大議題，每項指標含具體 metric code 與計算方法。

## 主要指標

- **SV-HL-130a.1**：年度能源消耗（拆 grid electricity vs renewable）。
- **SV-HL-260a.1**：食品安全違規事件數、警告函、罰款。
- **SV-HL-310a.1 / a.2**：勞動條件（薪資、流動率）、多元（性別 / 種族）。
- **SV-HL-410a.1**：氣候風險（位於 100 年洪泛區之物業比例）。

## 與本 demo 對應

- `tcfd-2025.md` (130a.1 能源)、`food-safety-2025.md` (260a.1 食安)、`local-indigenous-2025.md` (310a.1 在地勞動)。
- 本 demo 不細分子 metric code，統一以 `sasb-hl` 一個 framework slug 對應，避免 entity 過度碎裂。
