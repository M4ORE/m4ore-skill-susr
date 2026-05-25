# 可審計的信任

## 30 秒先看這段

永續報告書最終要過第三方確信（assurance）。確信師會問你：「這個 KPI 的值是怎麼算的？source document 在哪？誰填的？什麼時候填的？跨年是否重述？」過去你翻 mailbox、翻共享資料夾、翻 git history、翻 Slack——平均一個質詢吃掉 30 分鐘。

susr 把每個數字的時間戳、來源檔、填寫者、信心度、後續修改全部寫進 `timeline_entries` 與 `page_versions`，append-only、不可改。確信時拉一次查詢就齊。

---

## 每個數字必有來源

susr 的鐵則：**任何量化 datapoint 必須至少有一條 `datapoint_derived_from` 指向 source_doc**。

這條由 I4 invariant 強制：

```
I4: 任一量化 datapoint 必須 ≥ 1 個 datapoint_derived_from → source_doc
```

如果你 ingest 一個碳排數字卻沒指明來源檔，commit 會 fail-closed。你不能繞過——除非你顯式跑 `health_check` 看 violation 並用顧問身份決定是否豁免（並留 timeline）。

對應排放類數字還有更嚴的 I5：

```
I5: 排放類 datapoint 必須關聯一個 effective_from ≤ year ≤ effective_to 的 emission_factor
```

過期的排放因子（例如環境部 2023 因子用在 2025 年數據）會被擋。

---

## timeline + page_versions 怎麼幫你應付確信

susr 的證據鏈設計來自一個簡單事實：**確信師不接受「我記得」，他們要看 audit trail**。

### timeline_entries：append-only 行動紀錄

每個 page（議題、KPI、datapoint、章節）有自己的 timeline，每筆紀錄不可改、不可刪，只能 append 新紀錄。

| action_type | 用在哪 |
|---|---|
| `ingest` | 第一次寫入或重新匯入 |
| `verify` | 顧問複核確認（含原始評分） |
| `restate` | 數值重述（> 5% 自動觸發） |
| `assure` | 第三方確信通過 |
| `comment` | 顧問附註 |
| `iro_link` | IRO 對應建立 |
| `gap_flag` | gap analysis 標記 |

確信師問「這個範疇 2 的值是 2025-08 之後被改過嗎」——你回：「`SELECT * FROM timeline_entries WHERE page_id=X ORDER BY ts`」，列出來給他看。

`actor` 欄位區分 `consultant:zhang` 與 `agent:claude-opus-4-7`，確信師可以反查哪些動作是顧問本人簽核、哪些是 AI 建議後顧問批准。

### page_versions：snapshot 鎖版

四個時刻 susr 會自動建 snapshot：

1. **`phase_complete`**：phase 收尾時（例如 Phase 3 materiality matrix 產出）
2. **`year_freeze`**：跨年 fork 前對上年所有 entity 鎖版
3. **`restate`**：值變動 > 5% 自動觸發
4. **`assurance`**：第三方確信通過時鎖版

每個 snapshot 存 `compiled_truth_snap`（page 內容全文）+ `frontmatter_snap`（所有結構化欄位），parent_version_id 串成 lineage。

確信師要看「Q3 揭露的這個值，跟正式報告書送出時是否一致」——你回：「我給你看 `snapshot_reason='assurance'` 的版本，跟現在 live 的 diff 給你。」

---

## 為什麼這比 git history 更有用

你可能會想：「我把 client repo 開 git，不就有 history 了嗎？」

git 給你的是 **文件層級**的 history（誰改了哪行）。但確信師問的問題是**語意層級**的：

- 「這個 KPI 重述了嗎？」→ 要查 `action_type='restate'`，不是查 commit log
- 「核心議題誰評的、什麼時候評的、原始分數多少？」→ 要查 timeline payload 的 raw_scores
- 「IRO 是哪次議合提出來的？」→ 要走 edge `engagement_raised_topic`

git 答不出來，timeline + page_versions + edges 答得出來。

兩者不衝突——susr 的 markdown source of truth 本來就在 git 裡，你同時擁有 git history 與 brain 內的語意 audit trail。

---

## 對應三原則

- **Definition**：「Assurance & Trust」是四個原子元件之一，susr 是直接服務這個元件的
- **Target**：顧問痛點之一是「確信攻防」，susr 把這段從「翻 mailbox」變「跑一次 query」
- **Product Structure**：輸出層的「版本管理 + 審核軌跡」直接由 page_versions + timeline 實作

---

## 一個實戰提示

確信開始前，跑一次 `health_check(client_slug='your-client')`。它會把所有 invariant violation 列給你看。**先在內部把 violations 處理掉再讓確信師進場**，比起被確信師當場抓出來，省下的時間是天文數字。
