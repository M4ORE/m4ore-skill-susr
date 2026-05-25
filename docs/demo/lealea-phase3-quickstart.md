# Lealea 5364 — Phase 3 重大性評估 30 分鐘 Quickstart

> 本文件示範 ESG 顧問**從零開始到產出力麗觀光（5364, TPEx）2025 Phase 3
> 重大性矩陣**的完整對話過程。預期讀完 5 分鐘、動手跟做 30 分鐘。
>
> 對話腳本逐一對應 `packages/susr/susr/mcp/tools/phase3.py` 四個 Phase 3
> tools 真實 signature；驗收數字對齊 [`docs/walkthroughs/lealea-5364-phase6-r6.md`](../walkthroughs/lealea-5364-phase6-r6.md)。

---

## 0. 一次性安裝（5 分鐘）

```bash
pip install "susr[embeddings-bge]"
```

編輯 Claude Desktop config：
- macOS：`~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows：`%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "susr": { "command": "susr-mcp" }
  }
}
```

重啟 Claude Desktop，新開一個對話，右下角看到 susr 工具圖示就 OK。
（細節 + `susr-mcp doctor` 健康檢查見 [`docs/user-guide/README.md`](../user-guide/README.md)。）

---

## 1. 接新客戶（30 秒）

**你**：
> 幫我建一個叫 lealea-5364 的客戶 workspace。公司全名「力麗觀光開發股份
> 有限公司」，產業 hospitality，台灣上市櫃，採營運控制法邊界，報告期間
> 2025 全年，採用 GRI 2021 / ISSB / 金管會作業辦法。

**Claude Desktop**（呼叫 `create_client_workspace`）：
> 已為你建立 client workspace：
> - 路徑：`~/susr-clients/lealea-5364/`
> - 初始 git commit hash：`a1b2c3d`
> - shared_kb snapshot：13 個檔案複製進 `shared/`
> - brain DB：`.susr/db.sqlite` (schema_version=1)
>
> 目錄結構已備好：
> - `_client.md`（公司 profile + Timeline）
> - `entities/{topics,stakeholders,governance,kpis,targets,iros,actions}/`
> - `projects/2025-sustainability-report/`
> - `sourcedocs/`（請把客戶提供的舊報告 PDF / 訪談紀錄 / Excel 放這）
>
> 下一步建議：把 sourcedocs/ 填好之後，跟我說「拉 hospitality 議題池」。

> （幕後：`create_client_workspace(name='lealea-5364', legal_name='力麗觀光開發股份有限公司', industry='hospitality', standards=['GRI 2021','ISSB','TWSE-FSC'], boundary='營運控制', reporting_period='2025-01-01..2025-12-31')` — 建 SQLite + sqlite-vec + FTS5 + 17 entity types schema + shared_kb snapshot。）

---

## 2. 找議題候選池（1 分鐘）

**你**：
> 幫 lealea-5364 從 hospitality industry pack 抽前 40 個議題候選，框架 GRI。

**Claude Desktop**（呼叫 `search_topics_universe`）：
> 三方合併（shared_kb industry-packs + GRI 通用準則 + client entities/topics/）
> 去重後 **28 個 candidates**：
>
> **環境 (E)** — 8 項：E1 氣候 / E2 能源 / E3 水資源（日月潭流域風險）/
> E4 廢棄物 / E5 生物多樣性 / ...
>
> **社會 (S)** — 14 項：S1 員工權益 / S4 職安 / S6 食安 ⭐⭐⭐ /
> S7 顧客隱私 / S12 在地原民共榮 / ...
>
> **治理 (G)** — 6 項：G1 治理結構 / G2 誠信 / G3 法遵 / G4 資安 / ...
>
> 推薦核心優先 **9 項**：E1 / E2 / S1 / S4 / S6 / S7 / G2 / G3 / G4
> （依 hospitality 旅館業特化 + SP1-004 walkthrough 結論）

> （幕後：`search_topics_universe(industry='hospitality', framework='GRI', client_slug='lealea-5364', top_k=40)` — 讀 `shared/industry-packs/hospitality.md` + GRI 標準對應 + client 既有 topics，每個 candidate 帶 `source_kb` 欄位讓你知道來源。）

---

## 3. 雙軸評分（5-10 分鐘 — 顧問判斷時間 bulk）

**你**：
> 對 E1 氣候議題評分。Impact：嚴重度 4、範圍 4、不可逆 5、可能性 4；
> Financial：規模 4、時間 S、機率 4。理由：旅館業日月潭區點面臨颱風頻率
> 上升 + 高溫衝擊冷氣負載，碳費 2026 上路直接影響營運成本。

**Claude Desktop**（呼叫 `score_topic_dual_axis`）：
> E1 氣候 評分結果：
> - Impact = (4+4+5+4)/4 = **4.25**
> - Financial = (4+4)/2 = **4.00**
> - Auto-tier: 核心（雙軸都 ≥ 4）
> - Resolved tier: **核心**（無 frontmatter explicit override，採 auto）
> - timeline_entry_id: 1（actor: consultant，含原始 7 個分數 + rationale）
>
> 已更新 `entities/topics/E1-climate.md` frontmatter。

> （幕後：`score_topic_dual_axis(client_slug='lealea-5364', topic_slug='E1-climate', impact=ImpactScores(severity=4, scope=4, irreversibility=5, likelihood=4), financial=FinancialScores(magnitude=4, time_horizon='S', probability=4), actor='consultant', rationale='...')`。若顧問先前已 explicit 標 tier 與 auto 不一致，會 honor explicit 並 emit `tier_resolution_warning` 上 audit trail。）

剩下 8 個核心議題 + 19 個次要議題逐一評分，每個約 30-60 秒（顧問判斷時間最重）。

---

## 4. 利害關係人議合（2-3 分鐘）

**你**：
> 記一筆員工問卷議合：2025-03 員工問卷 N=200 回收 156 份（78% response），
> 訪到的議題 E1 / S1 / S6，findings：流動率高、夜班疲勞、食安 SOP 落實度
> 訴求最強。

**Claude Desktop**（呼叫 `stakeholder_engagement_helper`）：
> 已建：`entities/stakeholders/員工/engagements/2025-03-問卷.md`
> - method: 問卷
> - sample_size: 156
> - topics_raised: [E1-climate, S1-labor, S6-food-safety]
> - 3 個 `engagement_raised_topic` edges 已建
> - 3 個 topic frontmatter 自動加上 `identified_by_stakeholders: [員工]`
> - timeline 已紀錄

> （幕後：`stakeholder_engagement_helper(client_slug='lealea-5364', stakeholder_slug='員工', method='問卷', date='2025-03', sample_size=156, topics_raised=['E1-climate','S1-labor','S6-food-safety'], findings_summary='...', actor='consultant')`。）

---

## 5. 對核心議題建 IRO（5-7 分鐘 — 9 個核心議題各 1-3 個）

**你**：
> 對 E1 建 3 個 IRO：物理風險（颱風 + 高溫衝擊營運）、轉型風險（2026 碳費
> 上路）、機會（永續旅遊定位差異化）。

**Claude Desktop**（呼叫 `link_topic_to_iro` × 3）：
> 已建 3 個 IRO 並 wire 雙路：
> - `E1-climate-risk-physical-typhoon`（risk / physical / S）
> - `E1-climate-risk-transition-carbon-fee`（risk / transition / S）
> - `E1-climate-opportunity-sustainable-tourism`（opportunity / market / L）
> - 3 個 `topic_has_iro` typed edges 已建（brain DB）
> - filesystem：`entities/topics/E1-climate/iro/*.md` × 3
> - 3 條 timeline entries 已紀錄

> （重複此步對其他 8 個核心議題建 IRO，總共產出 **14 個 IRO**：risk × 7 / impact × 4 / opportunity × 3 — 對齊 R6 walkthrough。）

---

## 6. 產出矩陣（5 秒）

**你**：
> 產出 lealea-5364 2025 重大性矩陣。

**Claude Desktop**（呼叫 `generate_materiality_matrix`）：
> Materiality matrix 已產出：
> - md：`projects/2025-sustainability-report/materiality-2025.md`
> - SVG：`projects/2025-sustainability-report/materiality-2025.svg`（5×5 散布，紅色右上象限為核心區）
> - 分群：**核心 9 / 重大 4 / 邊界 15**
> - tier_overrides: 0（無顧問 explicit ≠ auto 不一致）
> - invariants_passed: **True**（I1 — 9 個核心議題皆有 IRO chain）
>
> 矩陣 .md 已含議題評分表 + 矩陣圖嵌入。

> （幕後：`generate_materiality_matrix(client_slug='lealea-5364', year=2025, include_svg=True)` — 掃 `entities/topics/*.md`，對每個 scored topic 透過 `resolve_materiality_tier` 收斂 frontmatter explicit vs auto-suggested tier，把不一致的 emit 到 `tier_overrides` 供 audit。）

---

## 7. 跑 Phase 7 連結性檢查（10 秒）

**你**：
> 對 lealea-5364 跑 2025 full gap analysis。

**Claude Desktop**（呼叫 `run_full_gap_analysis`）：
> Gap analysis 完成：`projects/2025-sustainability-report/gap-analysis-2025.md`
>
> | Severity | Count |
> |---|---:|
> | 🔴 critical | 14 |
> | 🟡 warning | 22 |
> | ℹ️ info | 39 |
>
> Invariant breakdown：
> - I1a 核心 topic 必有 IRO：✅ 0 violations（你剛把 IRO chain 建完）
> - I1b IRO 必有 Action：⚠️ 14 violations（屬 Phase 5 範疇，預期中間態）
> - I2 Chapter conformsTo Framework：⚠️ 5 violations（章節未建，預期）
> - I3 / I4 / I5：✅ 0 violations
>
> 推薦下一步：Phase 5 建章節時順便呼叫 `link_iro_to_action` 補 I1b。

> （幕後：`run_full_gap_analysis(client_slug='lealea-5364', year=2025)` — 整合 invariants + compliance checklist + GRI Content Index + assurance readiness 四路徑。）

---

## 30 分鐘總結

從 `pip install` 到 Phase 3 完整矩陣 + Phase 7 gap analysis 約 **30 分鐘**：

| 階段 | 時間 |
|---|---|
| 0 安裝 + Claude Desktop config | 5 分鐘（一次性） |
| 1 建 workspace | 30 秒 |
| 2 拉議題池 | 1 分鐘 |
| 3 雙軸評分 28 議題 | 10-15 分鐘（顧問判斷 bulk） |
| 4 議合事件 × 1-3 | 2-3 分鐘 |
| 5 建 14 個 IRO | 5-7 分鐘 |
| 6 產矩陣（md + SVG） | 5 秒 |
| 7 Phase 7 gap analysis | 10 秒 |

對比手做版（SP1-004 試做）：**4-8 小時**。
**時間節省約 90%，audit trail + I1 invariant 自動 sanity check 白賺。**

最終專業判斷與責任 100% 在顧問手上：susr 不替你定議題、不替你打分、不替你結論。

---

## 下一步推薦

- Phase 5 章節骨架 + 為每個 IRO 建 Action（讓 I1b 全綠）
- Phase 6 payload prep（docx / pdf / pptx investor / pptx board 4 個 tools）
- 客戶問「為何給 E1 4.25 分」時，timeline 30 秒拉證據鏈
- 跨年承續：明年接 lealea-5365 時，`search_topics_universe` 自動帶上年 28 個議題

→ 完整顧問場景見 [`docs/user-guide/scenarios/`](../user-guide/scenarios/)
→ 端到端驗收數字見 [`docs/walkthroughs/lealea-5364-phase6-r6.md`](../walkthroughs/lealea-5364-phase6-r6.md)
→ 三原則 + 戰略定位見 [`CLAUDE.md`](../../CLAUDE.md) §0-§1
