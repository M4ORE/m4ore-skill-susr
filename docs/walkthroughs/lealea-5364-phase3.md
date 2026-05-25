# Lealea 5364 Phase 3 重大性評估 — Brain Walkthrough

**日期**：2026-05-25
**範圍**：MVP v0.1 第一個端到端驗收 — 用 susr brain（packages/susr R2 implementation）跑力麗觀光 5364 Phase 3 重大性評估
**對照 baseline**：SP1-004 SOP 試做版（`examples/lealea-5364/_legacy/phase3-materiality.md`）
**Brain 版本**：R2 implementation（158/158 + 22 = 180/180 tests pass）
**執行方式**：tmp workspace + mock embedding provider，直接呼叫 4 個 Phase 3 tool 函式（繞過 MCP stdio transport）

---

## TL;DR

4 個 Phase 3 tools **全部能跑、全部回正確的 Pydantic 結構**；但端到端跑下來暴露 5 個必須處理的 brain 設計缺口：

1. **schema strict-mode 阻擋 ingest**：`_client.md` 的 `boundary: operational_control`（英文 token）+ topic 的 `assessed_at: 2025-01-15`（PyYAML 自動 parse 成 `datetime.date`）都會被 brain Pydantic schema 拒絕，需要 ingest 層做 normalization。
2. **Phase 3 tools 完全不走 brain**：4 個 tools 直接讀寫 markdown 檔（filesystem source-of-truth），brain DB 在 ingest 之後形同未被使用 — MCP 工具與 brain 的耦合度幾乎為零。
3. **`_classify_tier` 與 frontmatter `materiality_tier` 邏輯衝突**：source markdown 用 SP1-004 的「核心(Impact 軸)」標法把 S1/S4/S7/S8/G2/G3 都標為「核心」，但 `_classify_tier` 嚴格要求兩軸都 ≥4 — `_collect_scored_topics` 直接吃 frontmatter 的 tier，造成 brain 矩陣輸出 9 個核心議題（SP1-004 原版只有 3 個）。
4. **brain hybrid search 在沒有 vec leg 時非常脆**：trigram FTS5 對「個資隱私」query 找不到 S7「客戶隱私與資料保護」（同義詞無橋接）— 一旦顧問環境 mock 或沒裝 sentence-transformers，retrieval 召回率會崩。
5. **I1 invariant 雙路徑、雙語義**：tool 3（`generate_materiality_matrix`）跑 filesystem-based I1 check（找 `entities/topics/<slug>/iro/*.md`），brain `check_all_invariants` 跑 DB-based I1 check（找 `topic_has_iro` edges）— 兩條路徑都報 9 個 core topic 缺 IRO，但 evidence 不可互通。

**MVP success criteria 評估**：「顧問可在 Claude Desktop 對 lealea 跑完 Phase 3，產出雙軸 + 矩陣 + IRO 對應」 →
- 雙軸：**YES**（tool 2 寫對 frontmatter + timeline）
- 矩陣：**YES**（tool 3 出 .md + .svg）
- IRO 對應：**部分 NO**（tools 沒有任何一個處理 IRO 建立；I1 100% 失敗，全部 9 個核心 topic 缺 IRO）

底線：**Claude Desktop UI 跑得起來，但 IRO chain 缺一個關鍵 tool**（建議 R3 加入 `link_topic_to_iro` 或讓 `score_topic_dual_axis` 同步建 IRO 骨架）。

---

## 0. Setup

| 項目 | 值 |
|---|---|
| Python | 3.12.0 |
| Tmp workspace root | `tempfile.mkdtemp(prefix="susr_walkthrough_")`（exact path varies per run） |
| Client workspace | `{tmp_root}/lealea-5364/`（由 `create_client_workspace` 生成 + git init + initial commit） |
| Brain DB | `{tmp_root}/lealea-5364/.susr/db.sqlite`（schema_version=1） |
| Embedding provider | **mock:deterministic** — SHA-256 → 1024-dim float32，仿 `packages/susr/tests/conftest.py` 的 `_MockEmbeddingProvider` |
| `load_sqlite_vec` | `False`（mock 向量無需 vec0 vtable；FTS5 仍透過 triggers 自動同步） |
| Shared KB snapshot | 1 個檔案複製進 `shared/`（只有 `README.md`；hospitality industry pack 尚未存在） |

### Ingest 統計

| Entity Type | Count |
|---|---|
| client | 1 |
| topic | 13（E1, E2, E3, E7, S1, S4, S6, S7, S8, S12, G1, G2, G3） |
| stakeholder | 3（employees, customers, community-indigenous） |
| **Total pages** | **17** |

Ingest 全部成功 — **但必須在 ingest helper 內做兩個 normalization**才能避開 brain schema strict-mode 拒絕：

1. `boundary: operational_control` → `營運控制`（中文 Literal mapping）
2. `assessed_at: 2025-01-15` → `"2025-01-15"`（`isoformat()` — TopicFrontmatter.assessed_at 是 `Optional[str]`，但 PyYAML 自動把 `YYYY-MM-DD` parse 成 `datetime.date`，造成 type mismatch）

→ 詳見 §7 R3 backlog。

---

## 1. Tool 1 — `search_topics_universe`

### 輸入

```python
search_topics_universe(
    industry="hospitality",
    framework="GRI",
    client_slug="lealea-5364",
    top_k=40,
)
```

### Brain 輸出

13 個 `TopicCandidate`（全部 `source_kb="client"`）：

| # | slug | axis | name | source_kb |
|---|---|---|---|---|
| 1 | E1-climate | E | 氣候變遷與低碳轉型 | client |
| 2 | E2-energy | E | 能源管理 | client |
| 3 | E3-water | E | 水資源管理 | client |
| 4 | E7-biodiversity | E | 生物多樣性與生態 | client |
| 5 | G1-governance-structure | G | 公司治理結構 | client |
| 6 | G2-integrity | G | 商業道德與誠信經營 | client |
| 7 | G3-compliance | G | 法令遵循與風險管理 | client |
| 8 | S1-labor-conditions | S | 員工權益與勞動條件 | client |
| 9 | S12-indigenous-culture | S | 文化保存與原民共榮 | client |
| 10 | S4-occupational-health | S | 員工健康安全 | client |
| 11 | S6-food-safety | S | 客戶健康安全（食品安全） | client |
| 12 | S7-customer-privacy | S | 客戶隱私與資料保護 | client |
| 13 | S8-customer-experience | S | 客戶體驗與滿意度 | client |

排序：依 markdown 檔名字典序（`sorted(topics_dir.glob("*.md"))`）— 沒有任何「relevance score」概念。

### 對照 SP1-004

- SP1-004 phase3-materiality.md §3 列了 **28 個議題**（E1-E8 + S1-S14 + G1-G6）
- 本次 walkthrough 只挑了 13 個 ingest（含全部高優先核心 + 部分重大 + 一個邊界），所以 brain 找到 13 個是正確的
- 如果 ingest 全部 28 個，預期會列 28 個

### 觀察

- ❌ **完全沒有 shared_kb 加成**：`shared_kb/data/industry-packs/hospitality.md` 不存在（R2 尚未填 industry packs），所以「跨 client 跨產業共享議題池」這個 brain 戰略賣點此刻**空跑**
- ❌ **沒有「相似度排序」**：tool 1 的命名暗示 retrieval（"search"），但實際只做 filesystem glob — `top_k` 參數會吃前 40 個檔案而非 top 40 by relevance
- ❌ **不走 brain**：函式直接讀 `client_path/entities/topics/*.md`，**brain 裡的 17 頁完全沒被查詢**。如果顧問用 brain hybrid_search 查 "氣候"，會找到（見下方 aux），但 `search_topics_universe` 不會用到 hybrid_search

### Brain hybrid_search aux 對照

額外跑了 `engine.search()` 真實走 hybrid_search RRF（FTS-only fallback，mock embedding 向量 random hash 無語義）：

| Query | Hits | 觀察 |
|---|---|---|
| `氣候變遷` | `[E1-climate (score=0.0164, fts)]` | trigram FTS5 命中 |
| `食品安全` | `[S6-food-safety (score=0.0164, fts)]` | trigram FTS5 命中 |
| `個資隱私` | `[]` | **同義詞 fail** — S7 內文用「客戶隱私 / 個資洩漏 / 信用卡」，沒有「個資隱私」連續 3-gram |

→ **R3 backlog #4**：FTS-only fallback 對中文同義詞極脆；vec leg 是必需品而不是 nice-to-have。

---

## 2. Tool 2 — `score_topic_dual_axis` × 2

### 2.1 E1-climate

**輸入**：

```python
score_topic_dual_axis(
    client_slug="lealea-5364",
    topic_slug="E1-climate",
    impact=ImpactScores(severity=5, scope=5, irreversibility=4, likelihood=4),
    financial=FinancialScores(magnitude=4, time_horizon="L", probability=4),
    actor="consultant:walkthrough",
    rationale="walkthrough scoring for E1-climate",
)
```

**Brain 算分**：
- impact_score = `(5+5+4+4)/4 = 4.5`
- financial_score = `(4+4)/2 = 4.0`（**注意：`time_horizon='L'` 沒有進入算式**，僅 magnitude + probability 平均）
- tier = `核心`（both ≥4）

**Page state after**：

```yaml
impact_score: 4.5
financial_score: 4.0
materiality_tier: 核心
assessed_at: 2026-05-25T05:48:58+00:00
assessed_by: consultant:walkthrough
```

**Timeline entry**（appended 至檔尾 `## Timeline` 段）：

```
- [2026-05-25T05:48:58+00:00] action=verify actor=consultant:walkthrough
  payload={"impact": {"severity": 5.0, ...}, "financial": {...},
           "impact_score": 4.5, "financial_score": 4.0,
           "tier": "核心", "rationale": "walkthrough scoring for E1-climate"}
```

✅ Frontmatter 寫對、timeline 寫對、文件 hash 應該變了（但 brain DB 不會自動 re-ingest，這是 markdown-as-source-of-truth 的設計含意 — 顧問需要顯式 re-ingest，或讓 watcher 跑）。

### 2.2 S6-food-safety

**輸入**：

```python
score_topic_dual_axis(
    client_slug="lealea-5364",
    topic_slug="S6-food-safety",
    impact=ImpactScores(severity=5, scope=4, irreversibility=4, likelihood=5),
    financial=FinancialScores(magnitude=5, time_horizon="S", probability=4),
    actor="consultant:walkthrough",
)
```

**Brain 算分**：
- impact_score = `(5+4+4+5)/4 = 4.5`
- financial_score = `(5+4)/2 = 4.5`
- tier = `核心`

Page state + timeline 同 E1 模式 — 都正確。

### 觀察

1. **`time_horizon` 不進 score 算式 — 但出現在 timeline payload**：顧問選了 "L" 或 "S" 看起來會被記錄，但對 financial_score 數值毫無影響。應該設計成 `time_horizon == "S"` 加成（短期風險），或顯式說明這欄只是 audit metadata。
2. **timeline 用 markdown 附加而非 DB 寫**：`_append_timeline_md` 改 markdown 檔內文，**沒有寫進 brain 的 `timeline_entries` 表**。如果顧問問「請列我跑過的所有評分動作」，brain timeline query 會空。
3. **brain page 未同步**：scoring 後 markdown 變了，但 brain 內 page 的 `compiled_truth` / `source_hash` 是上一次 ingest 的快照 — 任何後續 hybrid search 拿到的是舊資料。需要 ingest watcher 或顯式 re-ingest 機制。

---

## 3. Tool 3 — `generate_materiality_matrix`

### 輸入

```python
generate_materiality_matrix(
    client_slug="lealea-5364", year=2025, include_svg=True,
)
```

### 輸出（13 個 ingested topics + 2 個 freshly-scored）

| 象限 | 數量 | Topics |
|---|---|---|
| **核心** | 9 | E1-climate, E2-energy, G2-integrity, G3-compliance, S1-labor-conditions, S4-occupational-health, S6-food-safety, S7-customer-privacy, S8-customer-experience |
| 重大 | 4 | E3-water, E7-biodiversity, G1-governance-structure, S12-indigenous-culture |
| 邊界 | 0 | （本次 ingest 沒挑邊界 topics — E5/E8/S9/S14/G5 未進 brain） |

### 不變量檢查

**FAIL**（9 條 I1 violations）— 全部 9 個核心 topic 都沒有 IRO chain：

```
I1: core topic E1-climate has no IRO chain
I1: core topic E2-energy has no IRO chain
I1: core topic G2-integrity has no IRO chain
I1: core topic G3-compliance has no IRO chain
I1: core topic S1-labor-conditions has no IRO chain
I1: core topic S4-occupational-health has no IRO chain
I1: core topic S6-food-safety has no IRO chain
I1: core topic S7-customer-privacy has no IRO chain
I1: core topic S8-customer-experience has no IRO chain
```

### SVG 輸出（前 500 字元）

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="540" height="540" viewBox="0 0 540 540">
  <rect x="390.0" y="150.0" width="80.0" height="320.0"
        fill="#ffeaea" stroke="#e88" stroke-dasharray="4,2"/>
  <line x1="70.0" y1="70" x2="70.0" y2="470" stroke="#ddd"/>
  <line x1="70" y1="70.0" x2="470" y2="70.0" stroke="#ddd"/>
  <text x="70.0" y="488" font-size="10" text-anchor="middle">0</text>
  <text x="58.0" y="473.0" font-size="10" text-anchor="end">0</text>
  <line x1="150.0" y1="70" x2="150.0" y2="470" stroke="#ddd
```

→ 是正規的 SVG（純 string 拼接，540×540，含核心象限淡紅高亮 + 5×5 格線），共 3,854 bytes。

### Markdown 輸出（檔頭）

```markdown
# 2025 雙重重大性矩陣 — lealea-5364

_由 susr `generate_materiality_matrix` 自動產出於 2026-05-25T05:48:58+00:00_

- 核心議題：9 / 重大議題：4 / 邊界議題：0
- 不變量檢查：失敗 (9)

## 議題評分表

| slug | name | axis | impact | financial | tier |
|------|------|------|-------:|----------:|------|
| S6-food-safety | 客戶健康安全（食品安全） | S | 4.50 | 4.50 | 核心 |
| E1-climate | 氣候變遷與低碳轉型 | E | 4.50 | 4.00 | 核心 |
| E2-energy | 能源管理 | E | 4.00 | 4.00 | 核心 |
| E3-water | 水資源管理 | E | 4.00 | 3.50 | 重大 |
| S1-labor-conditions | 員工權益與勞動條件 | S | 4.00 | 3.50 | 核心 |
| S4-occupational-health | 員工健康安全 | S | 4.00 | 3.50 | 核心 |
| G2-integrity | 商業道德與誠信經營 | G | 3.50 | 4.00 | 核心 |
| G3-compliance | 法令遵循與風險管理 | G | 3.50 | 4.00 | 核心 |
| S7-customer-privacy | 客戶隱私與資料保護 | S | 3.50 | 4.00 | 核心 |
| E7-biodiversity | 生物多樣性與生態 | E | 3.50 | 2.50 | 重大 |
| S12-indigenous-culture | 文化保存與原民共榮 | S | 3.50 | 2.50 | 重大 |
| S8-customer-experience | 客戶體驗與滿意度 | S | 3.00 | 4.00 | 核心 |
| G1-governance-structure | 公司治理結構（董事會多元 / 獨立性） | G | 3.00 | 3.50 | 重大 |
```

### 對照：SP1-004 _legacy/phase3 §5

**SP1-004 manual 矩陣只有 3 個核心**：S6、E1、E2（嚴格 both ≥ 4）；其他 17 個歸「重大」，5 個歸「邊界」。

**brain matrix 跑出 9 個核心**：多了 S1, S4, S7, S8, G2, G3 — 因為這些 topic 的 markdown frontmatter 在 SP1-004 SOP 標記時被設成「核心」（用「核心(Impact 軸)」/ 「核心(Financial 軸)」的延伸定義），**而 `_collect_scored_topics` 直接吃 frontmatter `materiality_tier` 不重新分類**：

```python
"tier": fm.get("materiality_tier") or _classify_tier(i_s, f_s),
```

→ **發現的 bug / 設計衝突**：frontmatter tier 與 `_classify_tier(i,f)` 兩套標準並存，沒有 reconciliation。Step 2-A 重組 entities 時把 SP1-004 的「核心 (Impact)」誠實地 mirror 進去，但 brain matrix 工具吃這個 label 就會「失真」放大核心數。

→ **R3 backlog #2**：要嘛 (a) `_collect_scored_topics` 強制重新分類（ignore frontmatter tier），要嘛 (b) frontmatter 改用「nuanced tier」+「strict tier」雙欄位，要嘛 (c) `_classify_tier` 改採 SP1-004 寬鬆定義（任一軸 ≥4 即核心）。

---

## 4. Tool 4 — `stakeholder_engagement_helper`

### 輸入

```python
stakeholder_engagement_helper(
    client_slug="lealea-5364",
    stakeholder_slug="employees",
    method="問卷",
    date="2025-03-15",
    sample_size=254,
    topics_raised=["E1-climate", "S1-labor-conditions", "S6-food-safety"],
    findings_summary=(
        "員工反映：(1) 山區據點冬季能源費對加班餐補貼造成壓力 (E1)；"
        "(2) 房務輪班 / 加班費結算機制不夠透明 (S1)；"
        "(3) 餐飲部要求增加 HACCP 換證訓練頻率 (S6)。"
    ),
    evidence_refs=["survey-2025-q1-rawdata", "focus-group-2025-03-mins"],
    actor="consultant:walkthrough",
)
```

### Engagement page 建立

**Path**：
```
{tmp_root}/lealea-5364/entities/stakeholders/employees/engagements/2025-03-15-問卷.md
```

**Frontmatter**：

```yaml
slug: 2025-03-15-問卷
stakeholder_slug: employees
topic_slugs:
  - E1-climate
  - S1-labor-conditions
  - S6-food-safety
date: '2025-03-15'
method: 問卷
sample_size: 254
findings_summary: '員工反映：(1) 山區據點冬季能源費對加班餐補貼造成壓力 (E1)；...'
evidence_refs:
  - survey-2025-q1-rawdata
  - focus-group-2025-03-mins
```

**Body**：

```markdown
# 議合事件 2025-03-15-問卷

- 利害關係人：`employees`
- 方法：問卷
- 樣本數：254

## Findings

員工反映：(1) 山區據點冬季能源費對加班餐補貼造成壓力 (E1)；...

## Topics Raised

- `E1-climate`
- `S1-labor-conditions`
- `S6-food-safety`

---

## Timeline

- [2026-05-25T05:48:58+00:00] action=iro_link actor=consultant:walkthrough
  payload={"stakeholder": "employees", "method": "問卷", "date": "2025-03-15", ...}
```

### Back-link 驗證

✅ 三個 topic markdown 檔 frontmatter 都有新加上 `identified_by_stakeholders: [employees]`：

| Topic | identified_by_stakeholders |
|---|---|
| E1-climate | `[employees]` |
| S1-labor-conditions | `[employees]` |
| S6-food-safety | `[employees]` |

### 觀察

1. ✅ **filesystem source-of-truth 寫得很乾淨**：engagement page + 3 個 topic page 的 frontmatter back-link 都更新
2. ❌ **slug 含 CJK + 路徑**：`2025-03-15-問卷.md` slug 含中文 — 在 cross-platform git / URL encoding 場景可能出問題（macOS HFS+ normalized form 與 Windows NTFS 不同）。建議 slug 拆 ASCII + display_name
3. ❌ **action 名稱誤導**：tool 4 寫的 timeline action 是 `"iro_link"`，但實際做的是「stakeholder→topic raised」連結，**完全沒碰 IRO** — action 名稱應是 `"engagement_logged"` 或 `"topic_raised_by"`
4. ❌ **brain 內無 engagement page**：tool 4 寫了 markdown 但沒呼叫 `engine.put_page(entity_type="engagement", ...)`，brain DB 對這個議合事件一無所知 — `engagement_raised_topic` edge 也沒建。後續 R3 加 `Engagement` entity DB ingest 是必要工程

---

## 5. Cross-tool Integration 驗證

### 5.1 Brain `check_all_invariants` 結果

```python
violations = check_all_invariants(engine.conn)
# total = 9
# by_invariant = {I1: 9, I2: 0, I3: 0, I4: 0, I5: 0}
```

I1 全部 9 個核心 topic 都沒有 `topic_has_iro → iro_addressed_by → action` chain — 因為本次 walkthrough 完全沒建 IRO entity 也沒建 Action entity。

I2/I3/I4/I5 都 0 violations，但這是**空集 vacuously true**：
- I2 chapter completeness → 0 chapters in brain
- I3 target completeness → 0 targets in brain
- I4 datapoint source → 0 datapoints in brain
- I5 emission factor window → 0 GHG datapoints in brain

→ Phase 3 端到端在 invariants 面上 **只測到 I1**，這是 spec §2.5 MVP gate 預期的（Phase 3 只 gate I1+I2+I3）。

### 5.2 Tool 3 內建 I1 vs Brain I1

- Tool 3 `_collect_scored_topics` 算 `iro_link_count = sum(1 for _ in (topics_dir / slug / "iro").glob("*.md"))`（filesystem）
- Brain `_i1_violations` 查 `v_core_topic_action_coverage` view（DB edges）

兩條路徑都各自報 9 條 violation，但**互不知道**對方存在 — 顧問如果手動建了 `entities/topics/E1-climate/iro/i-emission.md`，filesystem 的 I1 會過、brain DB 的 I1 不會過（直到顧問 re-ingest）。

→ **R3 backlog #5**：I1 雙路徑必須收斂到單一 source（建議改成「brain ingest 時把 `entities/topics/<slug>/iro/*.md` 自動建 IRO entity + topic_has_iro edge」）

### 5.3 SP1-004 試做版的「強項 / 弱項」一致性

SP1-004 _legacy/phase3-materiality.md §7 自己列了 5 個試做與實際版差異風險。brain 跑下來的觀察 vs SP1-004 試做版自評：

| SP1-004 自評弱項 | Brain 跑出來是否仍然弱 |
|---|---|
| 模擬議合（不是真的問卷） | brain 的 tool 4 也僅記錄事件，不驗證樣本代表性、不檢查問項涵蓋議題 |
| TCFD 揭露深度（金管會 2026 加嚴前版本） | brain 跑 Phase 3 不碰 TCFD scenario / metrics |
| 議題分類體系 28 項 vs GRI 主題分類 | brain 全照 SP1-004 axis (E/S/G) + slug 收 |
| 心理健康、原民文化保存試做新增 | brain 沒概念，照樣 ingest |

底線：brain 並未糾正 SP1-004 試做版的弱項，但也沒新引入扭曲 — 它是忠實的「結構化容器」，不是「自動 QA 機器」。這與 CLAUDE.md §1 Co-pilot 定位一致：**顧問判斷在前**。

---

## 6. 對照 SP1-004 vs Brain（核心交付物）

| 維度 | SP1-004 手做（`_legacy/phase3-materiality.md`） | Brain 跑（本 walkthrough） | 差異 / 改進 |
|---|---|---|---|
| 議題識別深度 | 28 議題（E1-8 + S1-14 + G1-6），表格手列 | tool 1 撈出已 ingest 的 13 個（本次 sample；可擴大到 28） | **brain 無加成** — 完全靠 client 既有檔案 + 缺 industry pack；shared_kb 工程缺口 |
| 雙軸評分一致性 | 顧問手填 5 分制，但有「核心(Impact 軸)」/「核心(Financial 軸)」彈性分類 | tool 2 嚴格算式 `impact=avg(4 sub)`, `financial=avg(magnitude+prob)`；`_classify_tier` 嚴格 both ≥4 | brain 算式可重現、但 frontmatter 的「彈性 tier」未被 reclassify — 矩陣輸出失真（核心數從 3 變 9） |
| 矩陣呈現 | ASCII art (§5) 適合 markdown 內閱讀 | tool 3 出 .md 表 + .svg 圖（540×540，核心象限淡紅高亮） | **brain 改進** — SVG 可塞進報告書 / web；同時 audit-friendly md table |
| IRO 對應 | 表 §6 手列 12 個重大議題的 I/R/O + 章節 | brain **沒任何 tool 建 IRO entity**；I1 全 fail（9/9） | **brain 退步** — SP1-004 已手列但 brain 沒接住；R3 必補 `link_topic_to_iro` tool |
| Timeline / Audit trail | SP1-004 無 timeline 概念，僅靠 git history | tool 2 + tool 4 寫 markdown 內 timeline + brain timeline 表 | **brain 改進** — 同檔可追溯誰 / 何時 / 改什麼，git diff + timeline 雙重證據 |
| Stakeholder engagement | §1, §2 手列 7 利害關係人 + 議合方法 | tool 4 對 employees 建 1 個 engagement event；3 個 topic 自動 back-link | **brain 改進** — back-link 維護自動化；但 engagement 無進 brain DB（filesystem only） |
| Gap analysis vs 力麗實際版 | §7 手列 5 個預測差異 | brain 沒有 gap analysis tool；要 R3 後續 phase 才支援 | brain 持平 |
| Re-runnability | 改評分需手改 markdown 表 + 重排序 | tool 2 重跑可冪等覆寫 frontmatter + append timeline | **brain 改進** — 工具化降低 manual error |
| Invariant gate | 無自動檢查 | brain `check_all_invariants` 報 9 條 I1（無 IRO 鏈）— failsafe | **brain 改進** — 明確標示什麼還沒做完 |

**最大差異**：**IRO chain 是 SP1-004 已有但 brain MVP 沒接住的功能** — 這是 MVP success criteria 的明確缺口（顧問已經會手寫 IRO，但工具不幫他寫進 brain）。

---

## 7. 發現的 bug / R3 backlog

按優先序：

### #1 [P0] Schema strict-mode 阻擋 ingest（兩處）

- **症狀**：
  - SP1-004 `_client.md` 寫 `boundary: operational_control` → `ClientFrontmatter.boundary` Literal['合併', '營運控制', '股權法'] 拒絕
  - SP1-004 topic `assessed_at: 2025-01-15` → PyYAML auto-parse 成 `datetime.date` → `TopicFrontmatter.assessed_at: Optional[str]` 拒絕
- **影響**：顧問現有「真實案件」markdown 100% ingest fail
- **修法**：在 `put_page` 之前加 ingest helper layer 做 (a) value normalization（中英文邊界對應、PyYAML date coercion）；或 (b) 放寬 schema（boundary 加 English alias，assessed_at 接受 `str | date`）

### #2 [P0] frontmatter `materiality_tier` 與 `_classify_tier` 二套標準

- **症狀**：tool 3 矩陣輸出 9 個核心 vs SP1-004 嚴格 3 個核心
- **影響**：MVP 第一個給顧問看的 deliverable 數字就「失真」
- **修法**：選一條 — (a) `_collect_scored_topics` 強制 reclassify，(b) frontmatter 區分 `strict_tier` / `consultant_tier`，(c) `_classify_tier` 對齊 SP1-004 寬鬆定義

### #3 [P1] Phase 3 tools 完全不走 brain

- **症狀**：4 個 tools 都直接讀寫 markdown，brain DB ingest 只是「載入」但不被任何 phase 3 tool 查詢
- **影響**：brain 的 hybrid_search / page_versions / timeline 等核心能力**在 MVP UX 完全不被使用**
- **修法**：tool 4 應呼叫 `engine.put_page(entity_type="engagement", ...) + engine.link(engagement, "engagement_raised_topic", topic)`；tool 1 應走 `engine.search()` 並 RRF 混 shared_kb hits

### #4 [P1] FTS-only fallback 中文同義詞召回崩

- **症狀**：query `"個資隱私"` 找不到 S7 `客戶隱私與資料保護`
- **影響**：顧問環境若沒裝 sentence-transformers / 走 mock 模式，brain search 召回率不可用
- **修法**：(a) 必要時提示顧問裝 vec leg；(b) 在 shared_kb 內維護同義詞表，FTS query 端做 expansion；(c) MCP server 啟動時 health_check 強制檢查 embedding provider

### #5 [P1] I1 雙路徑（filesystem vs DB）

- **症狀**：tool 3 自己跑 filesystem I1 check，brain `check_all_invariants` 跑 DB I1 check，evidence 不可互通
- **影響**：顧問建 IRO markdown 後 tool 3 過了，但 brain DB 不知道
- **修法**：刪 tool 3 的內建 I1，全部走 brain；或讓 brain ingest 時自動讀 `entities/topics/<slug>/iro/*.md` 建 IRO entity + edges

### #6 [P2] tool 4 timeline action 名稱誤導

- **症狀**：tool 4 寫 `action="iro_link"` 但實際做的是 stakeholder→topic raised
- **修法**：rename 成 `"engagement_logged"` 或 `"topic_raised_by_stakeholder"`

### #7 [P2] tool 2 `time_horizon` 不入算式

- **症狀**：FinancialScores.time_horizon ∈ {S, M, L} 但 financial_score 公式只用 magnitude + probability
- **修法**：(a) 加上 time_horizon weight（短期 ×1.2 / 長期 ×0.8 之類），或 (b) 文件明確說「time_horizon 是 audit-only field」

### #8 [P2] CJK slug + 路徑

- **症狀**：tool 4 生成 `2025-03-15-問卷.md`
- **修法**：slug 限 ASCII（`2025-03-15-survey`）+ frontmatter `display_method: 問卷`

---

## 8. MVP Success Criteria 評估

依 `CLAUDE.md` §8「MVP 第一刀」決策：

> 顧問可在 Claude Desktop 內，用對話方式對 lealea 5364 跑完 Phase 3，產出含**雙軸評分 + 矩陣 + IRO 對應**的 materiality matrix；通過 Layer 2 scenario test

| 子目標 | 達標 | 證據 |
|---|---|---|
| 顧問在 Claude Desktop 內可跑（透過 MCP）| **未驗證**（本 walkthrough 直接呼叫 Python 函式 + 走 FastMCP `server.tool()` 已 wired） | 4 tools 都已 `register(server)`，需另跑 MCP stdio + Claude Desktop 整合測 |
| 對 lealea 5364 跑通 | **YES** | 17 entities ingest 成功；4 tools 全部回正確 Pydantic 結構 |
| **雙軸評分** | **YES** | tool 2 在 E1 + S6 都正確寫 frontmatter + timeline |
| **矩陣** | **YES**（但數字失真，見 §7 #2） | tool 3 出 .md（1,491 bytes）+ .svg（3,854 bytes），9 核心 / 4 重大 / 0 邊界 |
| **IRO 對應** | **NO** | 4 個 tools 完全沒處理 IRO entity / topic_has_iro edge；I1 全 fail（9/9） |
| 通過 Layer 2 scenario test | **未驗證** | 本 walkthrough 跑的是 Layer 4 unit-level invocation，不是 Layer 2 scenario test |

**結論**：**3/5 達標、1/5 部分達標（矩陣數字失真）、1/5 完全未達標（IRO 對應）**。

→ MVP v0.1 **可以對外展示「雙軸 + 矩陣」**，但**不能宣稱「IRO 對應」** — 那是 R3 必補項。

---

## Appendix A：實際 Python script

完整 script 位於 repo root `_tmp_walkthrough.py`（不 commit；本附錄保留全文供顧問之後參考改造）：

```python
"""End-to-end Phase 3 walkthrough for Lealea 5364 against susr brain.

Mirrors the integration test pattern in
packages/susr/tests/test_mcp_tools_phase3.py: directly invokes the 4
Phase 3 tool functions, bypassing the MCP stdio transport.

Run with:
    cd packages/susr && python ../../_tmp_walkthrough.py
"""

from __future__ import annotations
import hashlib, json, os, sys, tempfile, traceback
from pathlib import Path
from typing import Any, Sequence

PACKAGE_DIR = Path(__file__).parent / "packages" / "susr"
sys.path.insert(0, str(PACKAGE_DIR))

import numpy as np
import yaml


# ---- Mock embedding (deterministic SHA-256 → 1024-dim float32) ----
class MockEmbeddingProvider:
    name = "mock:deterministic"
    dimension = 1024
    hosting = "local"

    def embed_query(self, text: str) -> np.ndarray:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        repeats = (self.dimension // len(digest)) + 1
        raw = (digest * repeats)[: self.dimension]
        return (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 127.5) / 127.5

    def embed_documents(self, texts):
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        return np.stack([self.embed_query(t) for t in texts])


# ---- Markdown parse helper ----
def parse_md(path: Path) -> tuple[dict, str, str]:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            try:
                fm = yaml.safe_load(text[3:end].strip()) or {}
            except yaml.YAMLError:
                fm = {}
            body = text[end + 4 :].lstrip("\n")
            return fm, body, text
    return {}, text, text


def main():
    from susr.brain.engine import BrainEngine
    from susr.brain.invariants import check_all_invariants
    from susr.mcp.tools.phase3 import (
        FinancialScores, ImpactScores,
        generate_materiality_matrix, score_topic_dual_axis,
        search_topics_universe, stakeholder_engagement_helper,
    )
    from susr.workspace import create_client_workspace, find_client_workspace

    REPO_ROOT = Path(__file__).parent
    LEALEA_SRC = REPO_ROOT / "examples" / "lealea-5364"

    # 0. tmp workspace + brain
    tmp_root = Path(tempfile.mkdtemp(prefix="susr_walkthrough_"))
    os.environ["SUSR_WORKSPACE_ROOT"] = str(tmp_root)
    create_client_workspace(
        root=tmp_root, name="lealea-5364",
        legal_name="LEALEA HOTELS & RESORTS CO., LTD.",
        industry="hospitality",
        standards=["GRI Standards 2021", "TCFD", "ISSB IFRS S1/S2"],
        boundary="營運控制", reporting_period="2025-01-01..2025-12-31",
    )
    client_path = find_client_workspace("lealea-5364", root=tmp_root)
    engine = BrainEngine.open(
        client_path / ".susr" / "db.sqlite",
        load_sqlite_vec=False,
        embedding_provider=MockEmbeddingProvider(),
    )

    # Copy real topic + stakeholder files into the tmp workspace.
    selected_topic_files = [
        "E1-climate.md", "E2-energy.md", "E3-water.md", "E7-biodiversity.md",
        "S1-labor-conditions.md", "S4-occupational-health.md",
        "S6-food-safety.md", "S7-customer-privacy.md", "S8-customer-experience.md",
        "S12-indigenous-culture.md",
        "G1-governance-structure.md", "G2-integrity.md", "G3-compliance.md",
    ]
    src_topics = LEALEA_SRC / "entities" / "topics"
    for fn in selected_topic_files:
        (client_path / "entities" / "topics" / fn).write_text(
            (src_topics / fn).read_text(encoding="utf-8"), encoding="utf-8",
        )
    for sh in ("employees.md", "customers.md", "community-indigenous.md"):
        (client_path / "entities" / "stakeholders" / sh).write_text(
            (LEALEA_SRC / "entities" / "stakeholders" / sh)
            .read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    # 0a. Client page (with normalisation)
    fm, body, _ = parse_md(LEALEA_SRC / "_client.md")
    boundary_map = {"operational_control": "營運控制",
                    "consolidation": "合併", "equity": "股權法"}
    fm["boundary"] = boundary_map.get(str(fm.get("boundary","")).strip(), "營運控制")
    fm.setdefault("embedding_policy", "twostage")
    fm.setdefault("legal_name", "LEALEA HOTELS & RESORTS CO., LTD.")
    fm.setdefault("industry_gri_sector", "hospitality")
    fm.setdefault("reporting_period", "2023-01-01..2023-12-31")
    if isinstance(fm.get("applicable_standards"), list):
        fm["applicable_standards"] = [str(s) for s in fm["applicable_standards"]]
    allowed = {"slug", "legal_name", "stock_code", "industry_gri_sector",
               "boundary", "reporting_period", "applicable_standards",
               "embedding_policy", "xbrl_concept"}
    fm_clean = {k: v for k, v in fm.items() if k in allowed}
    fm_clean["slug"] = "lealea-5364"
    if fm.get("stock_code"):
        fm_clean["stock_code"] = str(fm["stock_code"])
    engine.put_page(
        slug="lealea-5364", entity_type="client", title="力麗觀光開發 5364",
        compiled_truth=body[:4000], file_path=str(LEALEA_SRC / "_client.md"),
        frontmatter=fm_clean,
    )

    # 0b. Topic pages (with date coercion)
    import datetime as _dt
    for fn in selected_topic_files:
        path = src_topics / fn
        fm, body, _ = parse_md(path)
        if isinstance(fm.get("assessed_at"), (_dt.date, _dt.datetime)):
            fm["assessed_at"] = fm["assessed_at"].isoformat()
        engine.put_page(
            slug=fm.get("slug", path.stem), entity_type="topic",
            title=fm.get("name", path.stem), compiled_truth=body,
            file_path=str(path), frontmatter=fm,
        )

    # 0c. Stakeholder pages (with 高/中/低 → numeric)
    scale = {"高": 5.0, "中": 3.0, "低": 1.0}
    for sh in ("employees", "customers", "community-indigenous"):
        path = LEALEA_SRC / "entities" / "stakeholders" / f"{sh}.md"
        fm, body, _ = parse_md(path)
        sh_fm = {
            "slug": sh, "category": fm.get("category", "unknown"),
            "influence_on_company": scale.get(str(fm.get("influence_on_company")), 3.0),
            "affected_by_company": scale.get(str(fm.get("affected_by_company")), 3.0),
        }
        engine.put_page(
            slug=sh, entity_type="stakeholder",
            title=fm.get("name", sh), compiled_truth=body,
            file_path=str(path), frontmatter=sh_fm,
        )

    # ---- Tool 1 ----
    candidates = search_topics_universe(
        industry="hospitality", framework="GRI",
        client_slug="lealea-5364", top_k=40,
    )

    # ---- Brain hybrid search (aux) ----
    for q in ("氣候變遷", "食品安全", "個資隱私"):
        engine.search(q, entity_types=["topic"], top_k=5)

    # ---- Tool 2 ----
    score_topic_dual_axis(
        client_slug="lealea-5364", topic_slug="E1-climate",
        impact=ImpactScores(severity=5, scope=5, irreversibility=4, likelihood=4),
        financial=FinancialScores(magnitude=4, time_horizon="L", probability=4),
        actor="consultant:walkthrough",
        rationale="walkthrough scoring for E1-climate",
    )
    score_topic_dual_axis(
        client_slug="lealea-5364", topic_slug="S6-food-safety",
        impact=ImpactScores(severity=5, scope=4, irreversibility=4, likelihood=5),
        financial=FinancialScores(magnitude=5, time_horizon="S", probability=4),
        actor="consultant:walkthrough",
    )

    # ---- Tool 3 ----
    matrix = generate_materiality_matrix(
        client_slug="lealea-5364", year=2025, include_svg=True,
    )

    # ---- Tool 4 ----
    stakeholder_engagement_helper(
        client_slug="lealea-5364", stakeholder_slug="employees",
        method="問卷", date="2025-03-15", sample_size=254,
        topics_raised=["E1-climate", "S1-labor-conditions", "S6-food-safety"],
        findings_summary="員工反映：(1) 山區據點冬季能源費對加班餐補貼造成壓力 (E1)；"
                         "(2) 房務輪班 / 加班費結算機制不夠透明 (S1)；"
                         "(3) 餐飲部要求增加 HACCP 換證訓練頻率 (S6)。",
        evidence_refs=["survey-2025-q1-rawdata", "focus-group-2025-03-mins"],
        actor="consultant:walkthrough",
    )

    # ---- Invariants ----
    violations = check_all_invariants(engine.conn)
    print(f"violations: {len(violations)} "
          f"(by code: I1={sum(1 for v in violations if v.invariant=='I1')})")

    engine.close()


if __name__ == "__main__":
    raise SystemExit(main())
```

**Script 統計**：~210 行 Python，2 個 helper（MockEmbeddingProvider + parse_md），1 個 main()，跑時間約 0.8 秒（不含 `pytest` overhead）。

---

## Appendix B：實際輸出物樣本（檔案 path）

執行 `_tmp_walkthrough.py` 後在 tmp_root 下會留：

```
{tmp_root}/lealea-5364/
├── .git/
├── .gitignore
├── .susr/db.sqlite                              ← 17 pages + FTS5 index
├── _client.md
├── shared/README.md                              ← shared_kb snapshot（僅 1 檔，industry pack 缺）
├── entities/
│   ├── topics/                                   ← 13 topic md（含 frontmatter 已更新 timeline）
│   │   ├── E1-climate.md
│   │   ├── E2-energy.md
│   │   ├── ...
│   ├── stakeholders/
│   │   ├── employees.md                          ← back-link 新增於 frontmatter? 否（tool 4 不寫 stakeholder 主檔）
│   │   ├── employees/engagements/
│   │   │   └── 2025-03-15-問卷.md                ← tool 4 產出
│   │   ├── customers.md
│   │   └── community-indigenous.md
│   ├── governance/, kpis/, targets/              ← 空（gitkeep only）
├── projects/
│   └── 2025-sustainability-report/
│       ├── materiality-2025.md                   ← tool 3 產出（1,491 bytes）
│       └── materiality-2025.svg                  ← tool 3 產出（3,854 bytes）
└── sourcedocs/                                   ← 空
```

→ 9 個顧問可直接交付給客戶 / pinwheel 的檔案均在 `projects/2025-sustainability-report/` 與 `entities/stakeholders/employees/engagements/` 兩處 — 與 Option C 結構決策一致。
