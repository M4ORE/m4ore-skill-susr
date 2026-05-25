# 反綠色洗白

## 30 秒先看這段

綠色洗白（Greenwashing）的最常見形態不是「寫假數字」，是「**選擇性揭露**」：只寫達標的目標、隱藏未達標的、悄悄調整基準年讓對比看起來變好、把挑戰段落寫成空話。susr 用 schema-level 強制機制讓這些手段做不到——目標必須有 baseline + target_year + verification_path，未達標必須留 timeline，調基準年必須觸發 restate snapshot。

你不會被迫揭露公司的爛事，但你也不會在客戶不自覺的情況下幫他寫出綠漂的報告。

---

## susr 強制揭露的三類內容

### 1. 目標的完整性（I3 invariant）

每個 `target` entity 必須在 frontmatter 同時有：

- `baseline_year`（基準年）
- `baseline_value`（基準值）
- `target_year`（目標年）
- `verification_path`（驗證路徑——誰來驗、用什麼方法驗）

少一個 commit 就 fail-closed。

為什麼這四個欄位是綠漂的剎車？因為綠漂目標的共通樣貌是「我們承諾 2050 淨零」——沒有 baseline、沒有中期 milestone、沒有驗證機制。susr 不讓你寫出這種目標。

### 2. 核心議題必須有行動（I1 invariant）

任一被你評為「核心」的議題，必須有 `topic_has_iro → iro_addressed_by → action` 的完整鏈路。

也就是：你說這個議題很重要，那你公司做了什麼？沒做 action commit 會 fail。

這條杜絕了一個常見綠漂手法：「材料性矩陣放滿好看的核心議題，但實際章節只寫了三個」。

### 3. 重述自動留痕（restate threshold）

`DataPoint.value` 變動 > 5% 自動觸發：

1. `page_versions` 寫 `snapshot_reason='restate'` 的 snapshot（保留變動前的值）
2. `timeline_entries` 寫 `action_type='restate'`，payload 含 old_value / new_value / delta_pct

換句話說：你不能悄悄把去年的範疇 1 從 12,500 噸改成 11,800 噸假裝今年表現變好。susr 會記下變動，並且要求你在 timeline 補 rationale。

---

## 顧問如何用 susr 對抗客戶的綠漂壓力

實話：很多時候綠漂壓力來自客戶（客戶的董事會、客戶的投資人關係部）。客戶會說「這個寫得太尖銳，能不能軟化」、「未達標的目標可不可以不揭露」、「基準年能不能調」。

susr 給你三個工具回應：

**工具 1：用 invariant 當「外部標準」**

「我也想幫你軟化，但 susr 的 I3 invariant 是寫死的，沒有 baseline + verification_path 我這邊 commit 不過。」客戶不會跟工具吵架，他會跟你一起想怎麼補齊。

**工具 2：用 timeline 當「不可改的歷史」**

「我可以幫你重述今年的值，但 page_versions 會留前一版的 snapshot，確信師會看到 delta。如果重述合理，我們在 timeline 寫清楚 rationale，確信師通常接受。」

**工具 3：用 page_versions 當「對比工具」**

「上年 Q3 報告書揭露的這個目標是 30%，現在我們改成 20%——page_versions 留著舊值，我們需要在報告書內主動說明調整理由，不能默默改。」

---

## susr 不會做什麼

公平起見也要說清楚 susr 的邊界：

- **它不替你判斷什麼是綠漂**。決定「這個段落是不是空話」仍然是你的工作
- **它不替你回應客戶**。客戶若堅持要綠漂，最終決定權在你
- **它不審核 narrative 的「軟性綠漂」**。例如「我們致力於 ESG」這種空話，susr schema 不管
- **它不阻止你硬要忽略 invariant**。技術上你可以用 `health_check` 看 violation 然後決定發報告，但 timeline 會記下這個決定，責任跟著你

susr 提供的是**結構性的反綠漂防線**，最終專業判斷仍 100% 在你。這也呼應 Co-pilot vs Replacement 的設計原則。

---

## 對應三原則

- **Definition**：「可驗證、可比較、可信任」中的「可比較」直接被 restate / snapshot 機制保障
- **Target**：顧問接案的長期信譽就建立在「我輔導的客戶沒被抓綠漂」上，susr 是你的保險
- **Product Structure**：智能層的差距分析 + 輸出層的版本管理 + 顧問專屬功能的審核流程，三層協同

---

## 最後一個提醒

反綠漂機制最大的價值不是在「客戶想綠漂時你擋下」，是在「**客戶不自覺地綠漂時你提前發現**」。很多客戶並非惡意，只是不知道揭露不完整。susr 的 I1/I3 fail-closed 在你 commit 前就把這些 case 標出來——你在 client 還沒看到報告之前就能補齊，沒人會難堪。
