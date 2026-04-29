# WebSearch Pending — 待外部查證項目清單

**使用時機**：Phase 2 Research 啟動時的查詢入口；reference 內任何「需 WebSearch 確認」標記都必須對應到此清單。每年度報告編製前完整跑一次。

**維護規則**：
- 新增 reference 時若有時效性內容，同步更新本清單
- 完成查證後不刪除項目，改填「最後確認日期」與來源 URL（保留稽核軌跡）
- 若查證結果與原 reference 不符，回頭修正 reference 並標註 commit

---

## 待查清單（共 4 項）

### Q1. 台灣電力排碳係數最新版

- **位置**：`ghg-protocol.md:47`
- **問題**：2026 年（或最新年度）電力排碳係數公告值是多少？
- **目前已知**：原 reference 寫「2024 年公告值 0.495」，可能是舊版本（111 年度 ≈ 0.494）的混淆
- **建議來源**：
  - 經濟部能源署 https://www.moeaea.gov.tw/
  - 環境部「國家溫室氣體排放清冊報告」
- **查詢關鍵字**：「台灣 電力 排碳 係數 2026」、「能源署 電力 排碳係數 公告」
- **對報告書的影響**：直接影響所有 Scope 2 計算結果；錯誤值會造成歷年比較失真
- **最後確認日期**：2026-04-29（透過 SP1-003 Check 階段 WebSearch 實測）
- **確認來源 URL**：
  - https://www.moeaea.gov.tw/ecw/populace/content/ContentDesc.aspx?menu_id=26678（113 年度公告）
  - https://law.moea.gov.tw/LawContent.aspx?id=GL001356（114 年電力排碳係數基準）
- **確認結果**：
  - **113 年度（2024 年度）= 0.474 kgCO₂e/度**（公用售電業總銷售電量基準）
  - 2025 年目標 = 0.388 kgCO₂e/度
  - 2030 年目標 = 0.319 kgCO₂e/度
- **後續動作**：在 SP1-004 試做時依此更新 `ghg-protocol.md:47`，並用基線重述邏輯處理歷年值

### Q2. 第四階段強制申報年度

- **位置**：`taiwan-fsc-sustainability-guidelines.md:28`
- **問題**：資本額 < 20 億上市櫃公司強制編製永續報告書的具體實施年度為何？
- **目前已知**：第三階段（20–50 億）已實施；第四階段原寫「推進中」
- **建議來源**：
  - 金管會 https://www.fsc.gov.tw/
  - 證交所 https://www.twse.com.tw/
  - 櫃買中心 https://www.tpex.org.tw/
- **查詢關鍵字**：「上市上櫃 永續報告書 作業辦法 第四階段」、「資本額 20 億以下 永續報告書」
- **對報告書的影響**：影響中小型公司是否需提早佈局；範圍判定錯誤會違反法規
- **最後確認日期**：2026-04-30
- **確認來源 URL**：
  - https://www.fsc.gov.tw/ch/home.jsp?id=96&parentpath=0,2&mcustomize=news_view.jsp&dataserno=202410170001&dtable=News（金管會新聞稿）
  - https://csrone.com/news/6359（CSRone 整理）
- **確認結果**：
  - **自 114 年（2025）起，全體上市櫃公司均應編製 113 年度（2024 年度）永續報告書**
  - 換句話說：第四階段已正式實施
  - 特定產業（水泥、塑膠、鋼鐵、油電燃氣、**半導體**、電腦週邊、光電、通信網路、電子零組件、電子通路、其他電子）若資本額 ≥ 20 億，需依產業別加強揭露
- **後續動作**：在 SP1-008 同步更新 `taiwan-fsc:28`

### Q3. 第三方確信最新適用規定

- **位置**：`taiwan-fsc-sustainability-guidelines.md:92`
- **問題**：永續報告書第三方確信（限定確信 / 合理確信）的最新強制適用對象與時程？
- **目前已知**：部分大型上市櫃適用限定確信；全體適用「漸進推進中」
- **建議來源**：
  - 金管會作業辦法附表
  - 會計研究發展基金會公告
- **查詢關鍵字**：「永續報告書 第三方 確信 強制」、「ISAE 3000 永續報告 台灣」
- **對報告書的影響**：影響預算編列、確信機構選擇、文件準備時程
- **最後確認日期**：2026-04-30
- **確認來源 URL**：
  - https://dsp.tpex.org.tw/storage/csr/%E4%B8%8A%E5%B8%82%E4%B8%8A%E6%AB%83%E5%85%AC%E5%8F%B8%E6%B0%B8%E7%BA%8C%E5%A0%B1%E5%91%8A%E6%9B%B8%E7%A2%BA%E4%BF%A1%E6%A9%9F%E6%A7%8B%E7%AE%A1%E7%90%86%E8%A6%81%E9%BB%9E%E7%9B%B8%E9%97%9C%E8%A6%8F%E7%AB%A0.pdf（TPEx 確信機構管理要點）
  - https://www.tejwin.com/insight/%E6%B0%B8%E7%BA%8C%E5%A0%B1%E5%91%8A%E6%9B%B8%E5%8F%AF%E4%BF%A1%E5%BA%A6/（TEJ 確信現況分析）
- **確認結果**：
  - **ISAE 3000** 是會計師確信主流標準
  - **食品/金融業強制取得會計師確信**（食品業營收占比 > 50% 等門檻）
  - 截至 2023 年永續報告書統計：28.29% 取得會計師確信 / 34.77% 取得第三方驗證確信 / 40.13% 尚未取得任何確信
  - **金管會 2024 年計畫研議要求永續指標取得確信**，方向是漸進擴大適用對象
- **後續動作**：更新 `taiwan-fsc:92` 補上食品/金融強制 + 2024 研議計畫

### Q4. 公告時程與雙語版本最新要求

- **位置**：`taiwan-fsc-sustainability-guidelines.md` §6（公告與報送時程）
- **問題**：
  - (a) 永續報告書是否需與財報同步發布？
  - (b) 雙語版本（中英）對哪些公司強制？
  - (c) MOPS 上傳的結構化資料規格是否更新？
- **目前已知**：通常於年度結算後 6 個月內發布；雙語對外資比例高的公司「建議」但未強制
- **建議來源**：
  - 金管會作業辦法
  - 證交所「永續報告書專區」公告
- **查詢關鍵字**：「永續報告書 公告 期限」、「永續報告書 中英文 強制」
- **對報告書的影響**：時程逾期會影響公司治理評鑑；雙語要求變動會影響翻譯預算
- **最後確認日期**：2026-04-30
- **確認來源 URL**：
  - https://iso.24go.com.tw/esg2023new/（申報期限改為 8/31 整理）
  - https://www.sustaihub.com/en/blog/2025-latest-sustainability-report-operating-procedures-updated-key-points-of-latest-filing-regulations/（2025 年 5 月作業辦法更新）
  - https://twse-regulation.twse.com.tw/m/LawContent.aspx?FID=FL075209（TWSE 作業辦法原文）
- **確認結果**：
  - **(a) 申報期限改為每年 8/31**（2025 年 5 月 TWSE 更新作業辦法後正式生效）
  - **(b) 雙語版本未強制**，但實務上外資比例高、海外掛牌、金融業多自願出英文版
  - **(c) MOPS 結構化資料規格細節未取得明確結果**，建議直接洽詢 TWSE / TPEx 永續報告書專區
- **後續動作**：更新 `taiwan-fsc §6` 改為 8/31 + 註明雙語非強制

---

## 統括提醒（非獨立查詢項）

下列為 reference 檔頭 `注意` 區塊的統括提醒，不對應單一查詢，但每年度啟動 Phase 2 時應整體 review：

- `taiwan-fsc-sustainability-guidelines.md:5` — 整份文件以 2026-Q1 為基準
- `ghg-protocol.md:142` — 台灣本土因子以 2026-Q2 公告為基準

---

## 與 SP1-003 的銜接

本清單作為 `phase2-research-prompts.md`（SP1-003 待建）的核心輸入。SP1-003 將：
1. 為每個項目寫成可直接複製的 WebSearch query template
2. 補充非台灣特定的查詢（同業 peer benchmark、ISSB / ESRS 更新、SBTi 標準變動）
3. 規定 Research Log 格式
