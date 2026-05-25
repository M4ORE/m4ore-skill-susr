# Co-pilot, 不是 Replacement

## 30 秒先看這段

susr 從第一天起就決定**不取代顧問**。它把你 40 到 80 小時的低附加價值勞動（資料蒐集、框架對應、初稿打字、引用追蹤、矩陣繪製）壓到 8 到 15 小時，留出來的時間讓你做高附加價值的事：跟客戶談重大議題的戰略含意、跟董事會解釋雙重重大性、跟確信單位攻防。

最終所有對外揭露的內容，責任歸屬永遠是你。susr 連這條都寫進了它的 schema 設計裡。

---

## 為什麼這個原則重要

市場上 AI 永續工具有兩種路線：

| Replacement 路線 | Co-pilot 路線（susr） |
|---|---|
| 賣給企業，「按一鍵自動生成報告」 | 賣給顧問，「讓你接更多案子、做更好品質」 |
| 顧問視為威脅，會抵制 | 顧問視為幫手，會推廣 |
| 法律風險高，幻覺 = 揭露錯誤 = 公司被罰 | 法律風險低，AI 不做最終判斷 |
| 護城河弱，下一家 LLM 廠商就追上 | 護城河強，顧問專業 × AI = 混合智能 |

susr 選後者。這個選擇影響了所有產品決策——包括為什麼 susr 不會自動發報告、為什麼每個 MCP tool 的輸出都需要顧問顯式 confirm、為什麼 page_versions 設計成 snapshot 而非自動 rewrite。

---

## 你的判斷如何被放大

susr 用三種方式放大你的判斷：

**1. 把記憶外部化**

你不必再記得「這個 KPI 去年是用範疇 2 的市場基準算還是地域基準算」——`entities/kpis/*.md` 的 `values_by_year[]` 跟 timeline 記得。你只需要做新判斷，不用花時間挖舊判斷。

**2. 把例行檢查自動化**

I1 invariant（核心議題必須有 action chain）會在 commit 前 fail-closed。過去你要手動核對 28 個議題對應幾條 action，現在 susr 跑一次 SQL view 就告訴你「E1、E2、S6 還缺」。你的眼睛留給判斷「這個 action 寫得夠不夠強」。

**3. 把證據鏈打包**

當客戶問「為什麼這份報告寫『流動率高』」，timeline 立刻拉出 2025-03 的員工問卷議合紀錄（N=254、findings_summary、evidence_refs）。你不用翻 mailbox 找原始檔。

---

## 責任歸屬

這條是**鐵則**：susr 產出的任何內容，在報告書送出前都必須經過顧問顯式 confirm。

具體機制：

- 所有寫入 client repo 的 MCP tool 都會留 `timeline_entries(action_type='verify', actor='consultant:xxx')`
- `actor` 欄位區分 `consultant:zhang` 與 `agent:claude-opus-4-7`——確信單位可以用這欄反查哪些內容是顧問本人簽核的
- `promote_to_consultant_kb` tool 強制要 `confirm_token`（顧問必須先 dry_run 再帶回 token 才能真寫）

換句話說：**susr 留下的審計痕跡證明「這份報告是顧問做的，AI 是輔助」**。

這對你有兩重好處：

1. 法律上你的專業判斷地位沒被稀釋
2. 確信時你拿得出「我是怎麼決定的」證據

---

## 對應三原則

- **Definition**：susr 強化「可信任」這個原子元件，因為人在迴圈是信任的最後一道閘
- **Target**：susr 對象就是顧問，把你 40-80h 變 8-15h
- **Product Structure**：智能層的所有 AI 動作都包在「輔助你決策」的封裝裡，不直接決策

---

## 你不會被取代的真實理由

不是因為 AI 不夠強，是因為**永續報告的本質是「對利害關係人的承諾」**，承諾必須由具名的人類做出。法規（金管會、CSRD、SEC Climate Rule）都明文要求最終揭露責任在董事會與專業人士身上。AI 在這個責任鏈裡的位置永遠是「輔助工具」。

susr 把這個現實內化進了產品設計，這也是它跟「自動寫報告機」最根本的差別。
