# Scoping — 2025 Sustainability Report Project

> 本檔為 2025 年度報告書專案的 scoping 決策；客戶常駐資料見 `../../_client.md`，避免重複。
> 內容萃取自 SP1-004 試做 `_legacy/phase1-scoping.md`（去除已搬至 `_client.md` 的公司基本資料）。

---

## 1. 報告邊界（Reporting Boundary）

- **方法**：營運控制法（Operational Control）+ 合併報表口徑
- **2023 報告期間（2023-01-01 ~ 2023-12-31）覆蓋實體**：
  - 力麗觀光開發股份有限公司本體
  - 直營旅館：力麗哲園日潭館、月潭館（南投）、木棉道．美學商旅（台南）
  - 委託經營：明池山莊、棲蘭山莊（宜蘭）— **邊界需釐清**：委託經營是否計入營運控制法邊界，待 Phase 2 對照原版確認
- **2024 後新增**：愷森能源（儲能）— 不在 2023 邊界內
- **價值鏈邊界**：
  - **上游** — 食材、紡織備品（集團內供應可能性高）、能源（電、燃氣）、清潔備品、OTA 平台
  - **自營** — 客房、餐飲、會議
  - **下游** — 客戶體驗、客戶通勤、客戶廢棄物、廚餘

## 2. 適用標準組合（Applicable Frameworks）

| 標準 | 必選 / 選用 | 備註 |
|---|---|---|
| GRI Standards 2021（Universal + Topic） | 必選 | 力麗 2023 採 GRI Core；本試做升級為 In Accordance |
| 金管會「上市上櫃公司編製與申報永續報告書作業辦法」 | 必選 | 2026 最新修訂版（Phase 2 核對） |
| TWSE / TPEx 公司治理評鑑指標 | 必選 | 旅館業屬第二類產業 |
| ISSB IFRS S1 / S2 | 試做選用 | 比對 GRI 落差，為下年度做準備 |
| TCFD 四大構面 | 必選 | 治理 / 策略 / 風險管理 / 指標與目標 |
| SASB Hotels & Lodging | 試做選用 | 旅館業特化（用水、能耗、客戶資料） |
| ESRS / CSRD | 不採 | 無歐盟營運 |
| SBTi | 標記 | 列為長期目標路徑 |

## 3. 報告期間

- **資料期間**：2023-01-01 ~ 2023-12-31
- **對照基準發行**：2024-09（試做不重發）
- **報告日後事件**：2024 董座變更、2024-06 愷森能源併入 — 以「Subsequent Events」揭露

## 4. 強制章節（依雙重重大性原則）

1. 永續治理（董事會 ESG 專業 / 永續委員會結構）
2. 雙重重大性矩陣（含議合方法、IRO 評分）
3. **誠信經營**（金管會強制）
4. **利害關係人議合**（金管會強制）
5. **氣候相關財務揭露 TCFD/ISSB 四大構面**（金管會 2026 加嚴強制）
6. 員工 / 職安 / 多元（旅館業勞動密集）
7. 用水 / 能耗 / 廢棄物（旅館業資源密集，南投山區據點水資源敏感）
8. 客戶 / 顧客隱私 / 食品安全（住房與餐飲）
9. 在地僱用 / 在地採購（南投 / 宜蘭山區據點特色）
10. GRI Content Index + ISSB Datapoint Mapping + SASB Hotels Index

## 5. Phase 0 — Pre-flight 檢查（依賴提醒）

- [ ] Phase 4 / 6 將呼叫 `document-skills:xlsx / docx / pdf / pptx`，使用前確認底層依賴（pandoc / LibreOffice / Node / Python 套件）
- [x] 已下載對照報告書 PDF：`source-2023-report.pdf`（66 頁 / 3.21 MB）— .gitignore 不 vendor
- [x] 公司基本資料 Phase 0 research 完成（見 `_client.md`）

## 6. 試做產出對照表

| Phase | 試做產出（新位置） | 對照基準（力麗實際 2023 報告書） |
|---|---|---|
| 1 | 本檔 + `_client.md` | 報告書「關於本報告書」章節 |
| 2 | `research-log.md` | （本試做新增；力麗版未公開 research log） |
| 3 | `materiality-2025.md` + `entities/topics/` | 報告書「重大主題」章節 |
| 4 | phase4-data-pack.xlsx (未 build) + `entities/kpis/` | 報告書附錄數據表 |
| 5 | `chapters/_skeleton.md` + `chapters/tcfd-2025.md` | 報告書 main body |
| 6 | `assembly-plan.md` | 報告書本身（PDF） |
| 7 | `gap-analysis.md` + `pdf-extract.md` | （內部稽核未公開；本試做產出） |

## 7. 假設與限制（Disclosure of Assumptions）

- 試做**不接觸力麗真實內部數據**；Phase 4 數據以**報告書 PDF 揭露的數字**為錨，不足者標 `[N/A：需內部數據]`
- 委託經營邊界（明池 / 棲蘭）以營運控制法處理 — Phase 2 對照原版確認後可能調整
- 重大性議題評分為 SOP 模擬（無真實利害關係人議合），Phase 7 對照原版找差異
- 集團母公司（1444 / 1447）紡織業務不在本邊界

## 8. 下一步（併行啟動）

- **Phase 2** — peer benchmark：晶華 2707 / 雲品 2748 / 寒舍 2739 / 國賓 2704 / 老爺 2705；找出旅館業重大議題 baseline + 法規最新版 + 排放因子
- **Phase 4** — xlsx skeleton：旅館業特化欄位設計（Scope 1/2/3、用水、廢棄物、員工、職安、食安、客戶滿意）
