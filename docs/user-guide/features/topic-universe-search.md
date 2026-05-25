# Feature：議題池檢索（topic universe search）

## 30 秒先看這段

過去要決定議題池你要翻 GRI Sector Standard、找 3-5 家同業最新報告書、查監管要求，湊出 30+ 候選議題，平均吃掉 6 小時。`search_topics_universe` 從產業包 + 框架標準庫 + 客戶上年議題三方合併，30 秒給你去重後的候選 list，每個議題標 source 讓你知道來自哪一邊。剩下的時間留給跟客戶 CSO 對焦哪些議題在他們董事會層級真正有討論過。

這是 Phase 3 重大性評估的第一步，也是 MVP v0.1 的入口工具之一。

---

## 什麼時候用 / 解什麼痛點

### 場景 1：接到新客戶要做第一份永續報告書

- **觸發**：客戶簽約後 kickoff 前，你要準備議題池草案
- **過去**：翻 GRI Sector Standard PDF 抄通用議題（2 小時）+ 找 3-5 家同業最新報告書翻他們的核心議題（3-4 小時）+ 看金管會公告補要求（1 小時）
- **現在**：一句話拉出 28 個候選 list，按 axis 分類（環境 / 社會 / 治理），每項標 source（shared_kb 產業包 / 框架標準 / 客戶上年）；剩下時間直接跟客戶 CSO 對焦

對應場景：[`scenarios/接到新客戶第一週.md`](../scenarios/接到新客戶第一週.md)

### 場景 2：跨年延續客戶的議題池更新

- **觸發**：客戶已做 2024 報告，2025 要更新議題重評
- **過去**：手動翻上年議題表，對照新一年的監管變動（CSRD 新法 / 金管會新公告）逐項判斷增刪
- **現在**：`search_topics_universe` 自動把客戶 `entities/topics/*` 帶入；若 shared_kb 產業包有更新（新 emerging issue），會顯示為新 candidate

### 場景 3：跨產業客戶（如金控集團涵蓋銀行 + 保險 + 投信）

- **觸發**：客戶業務跨多個 GRI Sector
- **過去**：要分別讀多本 Sector Standard，自己手動 merge 議題
- **現在**：可以多次呼叫不同 industry，再讓 susr 幫你 merge 並 dedup

### 場景 4：你想嘗試切換框架對齊（如從 GRI 主導切到 ISSB 主導）

- **觸發**：客戶被投資人要求轉用 ISSB
- **過去**：把 GRI 議題 list 拿來逐項對應 ISSB topical disclosures，吃半天
- **現在**：framework 參數從 `GRI` 切到 `ISSB`，候選 list 自動切到 ISSB 主軸；對照差異可以 diff

---

## 怎麼用（在 Claude Desktop）

最簡形式：

```
顧問：幫 lealea-5364 拉旅館業議題池，框架 GRI。

Claude：[呼叫 search_topics_universe(industry='hotel', framework='GRI', client_slug='lealea-5364')]
       共 28 個 candidates（環境 8 / 社會 14 / 治理 6）：
       E1 氣候變遷（產業包 + GRI 305，industry_specificity='hotel'）
       E2 能源管理（產業包 + GRI 302）
       E3 用水（產業包 + GRI 303，industry_specificity='hotel'）
       ...
       S6 顧客健康安全（產業包 only，industry_specificity='hotel'，2024 客戶評為核心）
       ...
       G1 公司治理結構（GRI 2 + 客戶 2024）
       ...
       要先做利害關係人議合，還是直接對所有 topic 預評分？
```

進階參數：

| 參數 | 預設 | 用途 |
|---|---|---|
| `industry` | 必填 | 對應 `shared_kb/industry-packs/<industry>.md`（hotel / textile / semiconductor / banking ...） |
| `framework` | `GRI` | 可選 `GRI` / `ISSB` / `ESRS` / `TW_FSC` / `SASB` |
| `client_slug` | 選填 | 帶上會把該 client 的 `entities/topics/*` 也合併進來 |
| `top_k` | 40 | 候選議題數量上限 |

每個 candidate 回傳：

- `slug`：穩定 ID（例如 `E1` / `S6` / `G3`）
- `name`：人類可讀名稱
- `axis`：E / S / G
- `industry_specificity`：標註是否為產業特有議題
- `source_kb`：`shared` 或 `client`（幫你判斷這議題是 susr 推薦還是你過去評過）

---

## 為什麼這樣設計

### 三方合併不是 union，是有意義的去重

susr 用 slug 去重，但保留所有 source 資訊。例如同一個「氣候變遷」議題：

- shared_kb 產業包稱為 `E1`
- GRI 標準稱為 `GRI 305`
- 客戶 2024 稱為 `E1`（你過去採用 shared_kb 命名）

合併後 candidate 是 `E1`，但 source_kb 顯示「shared + client」，讓你知道這議題既被產業普遍認可、客戶過去也評過——表示應重點關注。

對應 [`philosophy/double-materiality.md`](../philosophy/double-materiality.md)：候選議題湊齊是雙重重大性的起點，但**判斷仍由你**。

### 不替你判斷重大度

`search_topics_universe` 只回 candidates，不給 score、不給 tier、不替你刪除任何議題。

對應 [`philosophy/co-pilot-not-replacement.md`](../philosophy/co-pilot-not-replacement.md)：susr 把資訊外部化，最終判斷仍 100% 在你。

**刻意不做**：susr 不會根據 LLM 主觀判斷自動把某議題標為「核心」。所有評分必須走 `score_topic_dual_axis` 並由 actor=consultant 簽核留 timeline。這是反綠漂的結構性防線（[`philosophy/anti-greenwashing.md`](../philosophy/anti-greenwashing.md)）。

### 產業包是 susr 維護者持續更新的

`shared_kb/industry-packs/` 隨 susr package 升級（pip install --upgrade），但**進 client repo 是 snapshot copy**，不會自動覆蓋。要更新某個客戶的 shared/ 用 `update_shared_kb` tool，顧問掌控升級節奏（環境部出新版排放因子時不會自動套，避免回溯影響）。

對應 [`philosophy/auditable-trust.md`](../philosophy/auditable-trust.md)：snapshot 機制讓 reproducibility 成立——確信師問「當時你用的議題池版本是什麼」，answer 是 client repo 的 shared/ 內容，不是現在的 susr 版本。

---

## 邊界與已知限制

- **MVP v0.1 只有少量 industry-packs**：旅館（hotel）已就緒，其他陸續補。如果你的客戶產業不在內，可以用 `framework='GRI'` 純靠 GRI 標準議題庫，再手動補產業特有議題到 `entities/topics/`
- **不支援 OR / NOT 邏輯**：例如「旅館業議題但排除 G 系列」目前要顧問自己過濾
- **跨產業 merge 要多次呼叫**：例如金控涵蓋銀行 + 保險，要呼叫兩次再人工 merge（後續版本會加 `industries=[...]` 多選支援）

---

## 對應原則速查

| 原則 | 這個 feature 怎麼對齊 |
|---|---|
| Co-pilot | 只給 candidates，不替判斷 |
| Double Materiality | 議題池是雙軸評分的起點 |
| Auditable Trust | shared snapshot + source_kb 標註 |
| Anti-Greenwashing | 不自動判定 tier，所有評分必經顧問 |

---

## 後續工具

選好候選後典型 next step：

1. `stakeholder_engagement_helper` — 把議合事件結構化，建 topic_identified_by edge
2. `score_topic_dual_axis` — 對每個議題雙軸評分
3. `generate_materiality_matrix` — 產出矩陣 + 跑 I1/I2 invariant check

完整工作流見 [`scenarios/議題池怎麼選.md`](../scenarios/議題池怎麼選.md)。
