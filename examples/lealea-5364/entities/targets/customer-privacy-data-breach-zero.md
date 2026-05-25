---
slug: customer-privacy-data-breach-zero
entity_type: target
kpi_slug: privacy-incidents
baseline_year: 2023
baseline_value: 0
target_value: 0
target_year: 2030
verification_path: ISO 27001 認證稽核 + 個資法主管機關通報紀錄
sbti_alignment: false
is_quantitative: true
scope: 訂房系統 / POS / 會員資料庫
owner: 資訊安全長 / 資安委員會
topic_slug: S7-customer-privacy
priority: 20
---

# 目標: 客戶資料零外洩維持（2030）

## 三要素

- **基線**：2023 零起重大資料外洩事件（金管會 / 個資法定義 > 1,000 筆）
- **時程**：2030 持續零起 + 2027 達 ISO 27001 全據點認證
- **驗證路徑**：ISO 27001 第三方認證稽核 + 個資法主管機關通報紀錄

## 對應 KPI

- `entities/kpis/privacy-incidents.md`（事件數 + 受影響筆數）

## 對應議題

- `entities/topics/S7-customer-privacy.md`（**核心**象限：Impact 3.5 + Financial 4.0）

## 旅館業特化

訂房 PII、會員卡、信用卡屬高風險敏感資料；peer（晶華、國賓）皆已導入 ISO 27001。
PCI-DSS 對信用卡資料另有強制要求。

## 對應 IRO

- **I**：個資洩漏（個人受害）
- **R**：個資法罰款 / 信任崩潰 / GDPR 跨境影響
- **O**：資安認證行銷差異化（ISO 27001 / PCI-DSS）

## 對應 Action

- `entities/actions/S7-customer-privacy-action-iso27001-pilot.md`（2025 試點 → 2027 全據點）

## 階段里程碑

- 2025：旗艦館 ISO 27001 試點認證
- 2026：訂房 + POS 系統滲透測試 + 員工資安訓練全員導入
- 2027：全據點 ISO 27001 認證
- 2030：維持零起重大事件 + PCI-DSS 完整合規

## 來源

`_legacy/phase3-materiality.md` S7、`_legacy/phase7-gap-analysis.md` §1 顧客隱私 gap、`examples/lealea-5364/entities/topics/S7-customer-privacy.md`。
