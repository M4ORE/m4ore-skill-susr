# 雙重重大性

## 30 秒先看這段

雙重重大性（Double Materiality）是 CSRD 與台灣 2026 後 ISSB 強化的核心：你不能只評估「氣候風險如何影響公司財務」，也必須評估「公司營運如何影響環境與社會」。susr 把雙軸評分（影響重大性 + 財務重大性）做成 first-class capability，每一個議題的兩個分數、評分者、評分時間、評分理由全部結構化，不靠 Excel 手動拼貼。

過去你用 Excel 矩陣手動算分、拉散點圖、跟客戶來回對焦，每個議題大約吃 30 到 45 分鐘。susr 把這段壓到 5 分鐘，但**評分本身仍由你做**。

---

## 雙重重大性是什麼

簡單講，一個議題重不重大要從兩個方向看：

| 影響重大性（Impact Materiality） | 財務重大性（Financial Materiality） |
|---|---|
| 公司對外面世界的衝擊 | 外面世界對公司的衝擊 |
| 嚴重度 + 範圍 + 不可逆性 + 可能性 | 規模 + 時間維度 + 機率 |
| 對利害關係人 / 環境 / 社會 | 對公司現金流 / 估值 / 資本成本 |
| GRI 強調 | ISSB / SASB 強調 |
| CSRD / ESRS 強制 | ISSB / SEC Climate Rule 強制 |

CSRD 把這兩個方向**都**列為強制。台灣金管會在 2026 路徑圖中也明確指出 ISSB 採用後仍會保留 GRI 的影響重大性要求。

如果你只做單向（只看財務或只看影響），等於沒做雙重重大性。

---

## susr 怎麼幫你做

**1. 雙軸獨立評分**

`score_topic_dual_axis` MCP tool 同時收兩組分數：

- **影響面**：severity（嚴重度）、scope（範圍）、irreversibility（不可逆性）、likelihood（可能性）
- **財務面**：magnitude（規模）、time_horizon（時間維度 S/M/L）、probability（機率）

每組 normalize 後給 1 到 5 的 axis score，再依規則（兩軸都 ≥ 4 = 核心；任一 ≥ 3.5 = 重大；其他 = 邊界）決定議題分級。

**2. 評分透明留底**

每次評分自動寫 `timeline_entries(action_type='verify', payload={raw_scores})`。半年後客戶問「為什麼 E1 是核心」，你 30 秒內拉出當時的 7 個原始分數 + rationale。

**3. 矩陣自動產出**

`generate_materiality_matrix` 讀所有評分過的 topic，產出 markdown 矩陣 + SVG 5x5 grid，**並同步跑 I1 invariant**——核心議題如果還沒有 action chain，commit 會被擋下來。

**4. 上年資料 fork**

新年度啟動時，從 `projects/YYYY-sr/materiality-YYYY.md` fork 過來，已評分的議題保留分數，只需重評變動的部分。

---

## 為什麼不能只看單向

過去顧問常被誘惑只做財務面（因為財務語言比較容易跟董事會溝通）。但這樣會踩到三個雷：

**雷 1：被確信單位打回**

CSRD 明文要求雙向；ISSB 雖以財務為主軸但要求說明「為什麼某些 GRI 強調的影響項目不重大」。只給單向，確信報告會註記 limitation。

**雷 2：被投資人質疑漂綠**

只挑對公司財務影響大的議題（碳定價、轉型風險）寫，避開對社會衝擊大的議題（供應鏈勞動、原住民同意），會被 ESG 投資人標為「selective materiality」。

**雷 3：跨年無法比較**

只做單向，下一年若補做雙向，會與上年不可比；客戶會問「為什麼今年議題多了」。susr 從第一天就雙軸結構，沒有後補麻煩。

---

## 對應三原則

- **Definition**：「Narrative + Judgment」這個原子元件特別點名雙重重大性是「需要人類脈絡理解的判斷」——susr 提供結構，判斷仍是你
- **Target**：雙軸評分 + 議合 + 矩陣是顧問「40-80h 變 8-15h」最有感的痛點
- **Product Structure**：智能層的「雙重重大性評估輔助」直接對應 MVP v0.1 第一刀

---

## 一個現實提醒

雙重重大性不是計算題，是判斷題。susr 給你的是**評分骨架 + 證據鏈**，不是「正確答案」。同一個議題，你可能評 4.5，另一位顧問可能評 3.8——這是正常的，因為兩位看到的脈絡不同。susr 的價值不是讓答案統一，是讓**你的判斷可以被你自己跟客戶辯護**。
