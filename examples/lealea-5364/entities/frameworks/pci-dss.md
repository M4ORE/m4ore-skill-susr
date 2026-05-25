---
slug: pci-dss
entity_type: framework
version: "v4.0"
disclosures:
  - Requirement 1 Network security controls
  - Requirement 2 Secure configurations
  - Requirement 3 Protect stored account data
  - Requirement 4 Protect cardholder data with strong cryptography during transmission
  - Requirement 5 Protect against malicious software
  - Requirement 6 Develop and maintain secure systems and software
  - Requirement 7 Restrict access by business need-to-know
  - Requirement 8 Identify users and authenticate access
  - Requirement 9 Restrict physical access to cardholder data
  - Requirement 10 Log and monitor access
  - Requirement 11 Test security regularly
  - Requirement 12 Information security policy
is_mandatory_in:
  - TW
  - EU
  - US
  - Global
---

# PCI DSS — Payment Card Industry Data Security Standard

**發行機構**：PCI Security Standards Council (Visa / Mastercard / AmEx / JCB / Discover 聯合)
**領域**：治理（支付安全）
**版本**：PCI DSS v4.0（2022 發布，2025-03 完成過渡）。

## 範圍

PCI DSS 規範**支付卡資料儲存 / 傳輸 / 處理**之資訊安全控制要求。任何接受信用卡支付的旅館業均需符合，等級依年度交易量分級（Level 1-4）。

## 12 大需求類別

涵蓋網路安全、加密、存取控制、監測、漏洞測試與資安政策。

## 與本 demo 對應

- `customer-privacy-2025.md`：訂房 / 櫃台 / 餐飲 POS 信用卡處理流程；本案優先做 Level 4 自評，明年升 Level 3 雙因子。
