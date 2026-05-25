# susr — Sustainability Brain for ESG Consultants

> 顧問的 ESG 第二大腦 — 把寫永續報告書的時間從 40-80h 壓縮到 8-15h，
> 同時讓品質更高、框架更完整、責任 100% 在顧問判斷。
>
> **Co-pilot for ESG consultants, not Replacement.**

[繁體中文](#繁體中文) · [English](#english) · [License & Acknowledgements](#license--acknowledgements)

---

## TL;DR

susr v0.1 是**本地優先（local-first）+ MCP-native + Markdown source of truth** 的 ESG 顧問 Co-pilot。
顧問 `pip install susr` 後，在 Claude Desktop 聊天介面操作 21 個 MCP tools，
跑完 Phase 3 雙重重大性評估 / Phase 6 報告書 payload 準備（含內建 docx 草稿渲染）/ Phase 7 差距分析。
資料以 Markdown + SQLite + sqlite-vec 留在顧問本機，符合「客戶資料不出機」原則。

- **MVP 已可用**：Phase 3（4 tools）/ Phase 6 payload prep（4 tools）+ render_docx_simple（1 tool 內建 docx 草稿）/ Phase 7 gap analysis（4 tools）
- **驗證基準**：力麗觀光（5364, TPEx）lealea-5364 fixture 端到端 walkthrough
- **測試**：293 passed + 2 skipped（Layer 1 lint + Layer 2 scenario + Layer 3 invariant + Layer 4 unit）
- **誠實揭露**：Phase 4 GHG 計算引擎 / Phase 5 章節自動草稿 / Phase 8 公告流程**尚未實作**

---

## 目錄

- [繁體中文](#繁體中文)
  - [這是什麼](#這是什麼)
  - [為什麼 — Co-pilot vs Replacement](#為什麼--co-pilot-vs-replacement)
  - [給誰用](#給誰用)
  - [快速開始](#快速開始)
  - [8-Phase SOP 與 MVP 涵蓋](#8-phase-sop-與-mvp-涵蓋)
  - [顧問場景示範](#顧問場景示範)
  - [架構概覽](#架構概覽)
  - [MVP 驗收成果（依 lealea-5364 真實案例）](#mvp-驗收成果依-lealea-5364-真實案例)
  - [限制（誠實揭露）](#限制誠實揭露)
  - [三條 hard rules](#三條-hard-rules)
  - [文件導覽](#文件導覽)
  - [戰略樞轉註記](#戰略樞轉註記)
- [English](#english)
- [License & Acknowledgements](#license--acknowledgements)

---

## 繁體中文

### 這是什麼

`susr`（codename，canonical name = `sustainability-report`）是一套給 ESG 顧問的 AI 第二大腦。
它把「寫永續報告書」這件每年從零做起的事，重組成**可審計、可比較、可信任**的結構化工作流：

- **Local-first**：所有資料以 Markdown 留在顧問本機；SQLite + sqlite-vec + FTS5 提供 hybrid search
- **MCP-native**：透過 Anthropic 的 MCP 協定，Claude Desktop / Claude Code / Cursor / Windsurf 都能直接讀寫
- **Markdown source of truth**：每個 entity 一個 `.md`，配 YAML frontmatter，顧問用 git 就能 diff / review
- **Co-pilot 不是 Replacement**：susr 不替顧問決定議題重大度、不替顧問寫結論——它只把 40-80h 中**重複、機械、易翻車**的部分自動化，把判斷與責任留給顧問

技術形態：[Garry Tan 的 gbrain](https://github.com/garrytan/gbrain) 是參考設計來源，但 susr 純粹學習架構模式（page_versions / hybrid search / typed edges / RRF），**code 自己重寫**，不繼承不 fork。

### 為什麼 — Co-pilot vs Replacement

| 面向 | Co-pilot ✅ | Replacement ❌ |
|---|---|---|
| 目標客戶 | ESG 顧問 / 顧問公司 | 想省顧問費的企業 |
| 商業模式 | 顧問公司訂閱 | 按報告計價 |
| 顧問反應 | 視為幫手 | 視為威脅 |
| 護城河 | 顧問專業 + AI = 混合智能 | 純 AI，易被追上 |
| 法律風險 | 低（人類最終決策） | 高（幻覺、責任歸屬） |
| 定位 | 顧問的第二大腦 | 企業的自動報告機 |

詳見三原則文件 [`docs/defeinition.md`](docs/defeinition.md) / [`docs/target.md`](docs/target.md) / [`docs/product_structure.md`](docs/product_structure.md)。

### 給誰用

- ✅ **獨立 ESG 顧問 / 小型顧問公司**（目前 design partner 鎖定）
- ✅ **顧問內 dev-friendly 成員**（Claude Code 進階操作）
- ❌ **想省顧問費的中小企業**（戰略決策上排除，避免變成 Replacement）
- ❌ **中型本土顧問 + 四大永續組**（短期不主動爭取，留待 PMF 後）

### 快速開始

> **目前狀態（v0.1 alpha）**：尚未上架 PyPI，請從 GitHub 安裝。Design partner 顧問請走方法 1（升級最方便）。

**方法 1：editable install（推薦給 design partner，可隨 git pull 升級）**

```bash
git clone https://github.com/M4ORE/m4ore-skill-susr
cd m4ore-skill-susr/packages/susr
pip install -e .
```

**方法 2：pip from git（不用 clone）**

```bash
pip install "git+https://github.com/M4ORE/m4ore-skill-susr.git#subdirectory=packages/susr"
```

**方法 3：uv tool install（隔離 venv，最乾淨）**

```bash
uv tool install "git+https://github.com/M4ORE/m4ore-skill-susr.git#subdirectory=packages/susr"
```

安裝完驗證：

```bash
susr-mcp --help    # 應該看到 entry point 跑起來
```

設定 Claude Desktop：在 `claude_desktop_config.json` 加入

```json
{
  "mcpServers": {
    "susr": {
      "command": "susr-mcp",
      "env": {
        "SUSR_WORKSPACE_ROOT": "C:\\Users\\<your-name>\\work\\susr-workspace"
      }
    }
  }
}
```

- **config 路徑**：macOS `~/Library/Application Support/Claude/`，Windows `%APPDATA%\Claude\`
- **`SUSR_WORKSPACE_ROOT`**：所有 client workspace 的 root 目錄（susr 會在裡面建 `<client-slug>/` 子資料夾）。Mac/Linux 用 `/Users/<name>/work/susr-workspace`
- PyPI 上架後將簡化為 `pip install susr`

重啟 Claude Desktop，開新對話：

```
顧問：幫我建一個叫 acme-1234 的客戶 workspace。
      紡織業上市櫃，合併報表邊界，要做 2025 永續報告書。

Claude：[呼叫 create_client_workspace ...]
        已建立 ~/work/acme-1234/，下一步建議...
```

之後零 shell 指令。完整安裝流程與健康檢查見 [`docs/user-guide/README.md`](docs/user-guide/README.md)。

> 想看 30 分鐘從零跑出 Phase 3 重大性矩陣的完整對話腳本？見 [`docs/demo/lealea-phase3-quickstart.md`](docs/demo/lealea-phase3-quickstart.md)。

### 8-Phase SOP 與 MVP 涵蓋

```
Phase 1  Scoping              ── ⚙️  intelligence + skill SOP guidance
Phase 2  Research             ── ⚙️  WebSearch + shared_kb/regulations
Phase 3  Double Materiality   ── ✅ MVP v0.1（4 MCP tools 端到端）
Phase 4  Data Engineering     ── ❌ 未實作（顧問仍用 xlsx skill 手算 GHG）
Phase 5  Content Drafting     ── ❌ 未自動草稿（章節骨架 + IRO 已有）
Phase 6  Report Assembly      ── ✅ Payload prep v0.1（4 tools）+ ✅ render_docx_simple（內建草稿，python-docx）；docx/pdf/pptx 精修走 anthropics/skills
Phase 7  Gap Analysis         ── ✅ 4 tools（compliance / GRI Index / assurance readiness / full gap）
Phase 8  Filing & Improve     ── ❌ 未實作
```

詳細工作流見 [`skills/sustainability-report/SKILL.md`](skills/sustainability-report/SKILL.md)（Claude Code 對話版）與 [`docs/research/step1-spec.md`](docs/research/step1-spec.md)（brain 架構藍圖）。

### 顧問場景示範

四個 walkthrough 場景，從顧問實際痛點出發：

- **[接到新客戶第一週](docs/user-guide/scenarios/接到新客戶第一週.md)** — 過去 12-18h 啟動成本壓到 5 分鐘建 workspace + 一句話 fork 上年資料
- **[議題池怎麼選](docs/user-guide/scenarios/議題池怎麼選.md)** — 三方合併（產業包 + 框架 + 上年）3 分鐘給 28 候選 + 雙軸評分
- **[客戶問為何用這個排放因子](docs/user-guide/scenarios/客戶問為何用這個排放因子.md)** — timeline + page_versions 30 秒拉完整證據鏈，告別翻 mailbox
- **[客戶今年要重述去年範疇 3](docs/user-guide/scenarios/客戶今年要重述去年範疇3.md)** — 自動算變動 %、超過 5% 強制揭露、反綠色洗白機制 fail-closed

完整 user-guide 入口見 [`docs/user-guide/README.md`](docs/user-guide/README.md)。

### 架構概覽

四層內部結構（對應三原則文件的「智能層」+「輸入層」+「顧問專屬功能」）：

1. **`susr.brain`** — SQLite + sqlite-vec + FTS5 引擎；17 個 entity types、19 條 typed edges、6 條連結性 invariants（含 R4 拆出的 I1a/I1b），page_versions snapshot + append-only timeline
2. **`susr.mcp.tools`** — 21 個 MCP tools 跨 Phase 3 / Phase 6 (payload prep + render_docx_simple) / Phase 7 / Workspace / IRO / Action / KPI
3. **`susr.shared_kb.data`** — pip ship 的常駐知識庫（frameworks / industry-packs / factors / glossary / regulations / checklists / prompts）
4. **`skills/sustainability-report/`** — Claude Code 用對話路徑（純 SOP guidance，與 brain 並行獨立）

完整 spec 見 [`docs/research/step1-spec.md`](docs/research/step1-spec.md)。

### MVP 驗收成果（依 lealea-5364 真實案例）

對照力麗觀光（5364, TPEx，觀光業）2025 永續報告書情境跑端到端：

| 指標 | 數字 |
|---|---|
| Entity 多樣性 | 17 types |
| Lealea pages ingested | 99（28 topics + 14 IROs + 14 actions + 5 chapters + 14 frameworks + 7 stakeholders + 9 KPIs + 6 targets + 2 governance） |
| Typed edges | 70（含 14 `topic_has_iro` + 14 `iro_addressed_by` + 19 `chapter_conforms_to` + 20 `discloses_topic` + 3 `target_measures`） |
| Layer 3 invariants | **6/6 全綠**（I1a / I1b / I2 / I3 / I4 / I5 ✅，R8-3 收尾 chapter framework 一致性） |
| 端到端測試 | 293 passed + 2 skipped |
| Phase 6 payload | chapters 5 / iros 14 / kpis 8 / targets 3 **全非空** |
| Phase 7 gap severity | critical 38 / warning 22 / info 39（fixture placeholder 含其中） |

詳細驗收見 [`docs/walkthroughs/`](docs/walkthroughs/)（R2 first cut / R3 P0 補強 / R6 Phase 6+7 收尾共 3 份）。

### 限制（誠實揭露）

> 「對使用者誠實的前提是先對自己誠實。」— CLAUDE.md §6.1

- ❌ **Phase 4 GHG 計算引擎未實作**：顧問仍用 `xlsx` sub-skill 手算 Scope 1/2/3，susr brain 只存結果不算過程
- ❌ **Phase 5 章節 LLM 自動草稿未實作**：顧問用 brain 整理素材，章節敘事仍由顧問手寫
- ⚠️ **Phase 6 雙路徑**：susr 內建 `render_docx_simple`（python-docx，適合草稿 / demo / regression）；投資人版 / 監管揭露建議走 `anthropics/skills` 精修（見 [`docs/walkthroughs/lealea-5364-docx-skill.md`](docs/walkthroughs/lealea-5364-docx-skill.md)）。pdf / pptx 仍只走 payload prep
- ❌ **Phase 8 公告 / MOPS filing 未實作**
- ⏳ **Claude Desktop stdio transport 端到端未驗證**：dev env 無 mcp SDK，目前所有 tool 驗證均繞 stdio 直呼函式
- ⏳ **I2 chapter framework 一致性 invariant 仍有 5 violations**：R8-3 backlog
- ⏳ **跨 client 「我服務過 5 家觀光業，共通議題?」匿名化合規邊界未定**：consultant-kb 單向闘已實作，反向 promotion 需手動 anonymize + reviewer

### 三條 hard rules

CLAUDE.md 主條文，違反不 commit：

1. **Subagent 派工原則（§4.5）**：可派則派 — 研究 / scaffold / 並行可行工程必派 subagent；對齊邊界 + 跑驗證
2. **Commit 紀律（§4.7）**：test pass + docs 同步 + 無 stale references → 才能 commit
3. **Content Hygiene（§4.6）**：漸進揭露 + 文件大小門檻（Markdown 軟 500 / 硬 1000；Python 軟 300 / 硬 500）

每個宣稱 feature 都必須有對應測試（§6.1）— 來自 gbrain spec-impl gap 教訓。

### 文件導覽

| 路徑 | 用途 |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | 對 Claude Code 的最高原則 instructions |
| [`docs/defeinition.md`](docs/defeinition.md), [`docs/target.md`](docs/target.md), [`docs/product_structure.md`](docs/product_structure.md) | 三原則文件（憲法級，最高優先） |
| [`docs/user-guide/`](docs/user-guide/) | 給顧問的場景、哲學、features |
| [`docs/research/`](docs/research/) | gbrain survey + Step 1 spec + websearch audit |
| [`docs/walkthroughs/`](docs/walkthroughs/) | Layer 5 acceptance tests（R2/R3/R6） |
| [`docs/standards/skill-development.md`](docs/standards/skill-development.md) | Skill 開發 SOP |
| [`dashboard.html`](dashboard.html) | 決策討論協作板（17 個 Q 全 decided） |
| [`packages/susr/`](packages/susr/) | Python package（brain + MCP server + shared_kb） |
| [`skills/sustainability-report/`](skills/sustainability-report/) | Claude Code skill |
| [`examples/lealea-5364/`](examples/lealea-5364/) | 端到端 fixture，Option C 結構（entities + projects + sourcedocs） |
| [`tests/`](tests/) | Repo-level Layer 1+2 lint / scenario；package-level Layer 3+4 在 `packages/susr/tests/` |

### 戰略樞轉註記

**2026-05-25** 由「通用 Claude Code skill」戰略樞轉為「**顧問 Co-pilot SaaS**（local-first OSS 路線）」。
17 個關鍵問題（Q1-Q17）一輪密集對話內全部 decided，含三次自我修正（Postgres → SQLite、shared-kb 獨立 repo → mono-repo、3 packages → 1 package）。完整決策軌跡見 [`CLAUDE.md` §8 Decisions Log](CLAUDE.md#8-演進註記decisions-log)。

關鍵架構決定：
- **儲存層**：SQLite + sqlite-vec + FTS5（**不**用 Postgres，顧問零 Docker）
- **Repo 結構**：mono-repo 內單一 Python package；shared-kb 透過 snapshot copy 進 client repo（**不**用 submodule）
- **入口**：`susr-mcp` console script，Claude Desktop 是預設 GUI（PMF 後再做自家 GUI + multi-agent CLI）
- **MVP 第一刀**：Phase 3 重大性評估端到端（susr 與 gbrain 差距最大、價值密度最高）

---

## English

### What is this

`susr` is a **local-first + MCP-native** AI second-brain for ESG consultants. It restructures the every-year-from-scratch labor of writing a sustainability / ESG report into an auditable, comparable, trustable workflow:

- **Local-first** — all data lives as Markdown on the consultant's laptop; SQLite + sqlite-vec + FTS5 power hybrid search
- **MCP-native** — Anthropic's MCP protocol lets Claude Desktop / Claude Code / Cursor / Windsurf read & write directly
- **Markdown source of truth** — one `.md` per entity with YAML frontmatter; consultants can diff / review with plain git
- **Co-pilot, not Replacement** — susr never decides material topics for you. It automates the 40-80h of repetitive, mechanical, error-prone steps and leaves judgment + accountability with the consultant

Architectural reference: [Garry Tan's gbrain](https://github.com/garrytan/gbrain) (we study the patterns — page_versions, hybrid search, typed edges, RRF — and **rewrite the code from scratch**; no fork, no dependency).

### Why — Co-pilot vs Replacement

| Dimension | Co-pilot (yes) | Replacement (no) |
|---|---|---|
| Target customer | ESG consultants / firms | Enterprises trying to cut consultant cost |
| Business model | Consulting-firm subscription | Per-report pricing |
| Consultant reaction | Sees it as an ally | Sees it as a threat |
| Moat | Consultant expertise + AI = hybrid intelligence | Pure AI, easily overtaken |
| Legal risk | Low (human-in-the-loop) | High (hallucination, liability) |
| Positioning | "Consultant's second brain" | "Enterprise auto-report machine" |

See the three canonical docs: [`docs/defeinition.md`](docs/defeinition.md) / [`docs/target.md`](docs/target.md) / [`docs/product_structure.md`](docs/product_structure.md).

### Quick Start

> **Current status (v0.1 alpha)**: Not yet on PyPI. Install from GitHub. Design-partner consultants should use Method 1 (easiest to upgrade).

**Method 1: editable install (recommended for design partners, upgrade via `git pull`)**

```bash
git clone https://github.com/M4ORE/m4ore-skill-susr
cd m4ore-skill-susr/packages/susr
pip install -e .
```

**Method 2: pip from git (no clone needed)**

```bash
pip install "git+https://github.com/M4ORE/m4ore-skill-susr.git#subdirectory=packages/susr"
```

**Method 3: uv tool install (isolated venv, cleanest)**

```bash
uv tool install "git+https://github.com/M4ORE/m4ore-skill-susr.git#subdirectory=packages/susr"
```

Verify:

```bash
susr-mcp --help
```

Configure Claude Desktop's `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "susr": {
      "command": "susr-mcp",
      "env": {
        "SUSR_WORKSPACE_ROOT": "/Users/<your-name>/work/susr-workspace"
      }
    }
  }
}
```

- Config path: macOS `~/Library/Application Support/Claude/`, Windows `%APPDATA%\Claude\`
- `SUSR_WORKSPACE_ROOT` is the parent dir for all client workspaces; susr creates `<client-slug>/` subdirs there
- After PyPI release this collapses to `pip install susr`

Restart Claude Desktop. In a new chat:

```
You: Create a client workspace called acme-1234. Textile industry,
     consolidated boundary, working on the 2025 sustainability report.

Claude: [calls create_client_workspace ...]
```

Zero shell commands after that. Full install path: [`docs/user-guide/README.md`](docs/user-guide/README.md).

### MVP Status

- ✅ **Phase 3 (Double Materiality)** — 4 MCP tools end-to-end (topic universe search / dual-axis scoring / matrix generation / stakeholder engagement helper)
- ✅ **Phase 6 (Payload Prep)** v0.1 — 4 tools (docx / pdf / pptx investor deck / pptx board deck) + ✅ **`render_docx_simple`** (built-in python-docx draft renderer); investor-grade / regulatory disclosure → `anthropics/skills`
- ✅ **Phase 7 (Gap Analysis)** — 4 tools (compliance checklist / GRI Content Index / assurance readiness / full gap analysis)
- ❌ Phase 4 (GHG calculation engine) — not implemented; consultants still use the `xlsx` sub-skill manually
- ❌ Phase 5 (LLM chapter drafting) — not implemented; consultants write narrative themselves on top of brain-managed material
- ❌ Phase 8 (Filing / continuous improvement) — not implemented
- ⏳ Claude Desktop stdio transport — not yet end-to-end verified (no `mcp` SDK in dev env)

### Architecture

Four internal layers:

1. **`susr.brain`** — SQLite + sqlite-vec + FTS5; 17 entity types, 19 typed edges, 6 connectivity invariants (incl. R4-split I1a / I1b), `page_versions` snapshot + append-only `timeline_entries`
2. **`susr.mcp.tools`** — 21 MCP tools across Phase 3 / Phase 6 (payload prep + render_docx_simple) / Phase 7 / Workspace / IRO / Action / KPI
3. **`susr.shared_kb.data`** — pip-shipped knowledge base (frameworks / industry-packs / emission factors / glossary / regulations / checklists / prompts)
4. **`skills/sustainability-report/`** — Claude Code conversational SOP path (runs in parallel with brain, independent)

Full spec: [`docs/research/step1-spec.md`](docs/research/step1-spec.md).

### Validation — Lealea-5364 end-to-end

Validated against **Lealea Hotels (5364, TPEx, hospitality)** 2025 sustainability report scenario:

- 95 pages ingested (28 topics + 14 IROs + 14 actions + 5 chapters + 14 frameworks + others)
- 51 typed edges (incl. 14 `topic_has_iro` + 14 `iro_addressed_by`)
- **6/6 Layer-3 invariants green** (all I1a/I1b/I2/I3/I4/I5 pass with R8-3 frameworks landed)
- Phase 6 payload all non-empty (chapters 5 / iros 14 / kpis 8 / targets 3)
- Phase 7 gap severity: critical 38 / warning 22 / info 39
- **293 tests passed + 2 skipped**

Detailed walkthroughs: [`docs/walkthroughs/`](docs/walkthroughs/) (R2 / R3 / R6).

### Strategic Pivot

**2026-05-25** — pivoted from "generic Claude Code skill" to "**consultant Co-pilot SaaS (local-first OSS path)**". 17 architectural questions decided in a single intensive session, with three self-corrections (Postgres → SQLite, separate shared-kb repo → mono-repo, 3 packages → 1 package). Full trail in [`CLAUDE.md` §8](CLAUDE.md#8-演進註記decisions-log).

---

## License & Acknowledgements

MIT License — see [`LICENSE`](LICENSE).

**Thanks to:**

- [Anthropic Claude](https://claude.com) for the MCP protocol and Python SDK that makes susr's tool surface possible
- [`anthropics/skills`](https://github.com/anthropics/skills) for the document-skills (docx / xlsx / pptx / pdf) that handle Phase 6 rendering
- [Garry Tan's gbrain](https://github.com/garrytan/gbrain) — reference architecture for a local-first AI knowledge system. susr studies the patterns (page_versions, hybrid search, typed edges, RRF) and **rewrites without inheriting code** (Plan B per CLAUDE.md §8, 2026-05-25 decision)
- First-principles ESG SOP design rooted in the SP1-004 walkthrough on Lealea Hotels (5364, TPEx)

**Project status:** susr **v0.1 MVP** — Phase 3 / Phase 6 payload prep / Phase 7 gap analysis are end-to-end usable. Phase 4 / 5 / 8 explicitly out of scope for v0.1.

See [`CLAUDE.md`](CLAUDE.md) for the canonical instructions to Claude Code working on this repo, and [`dashboard.html`](dashboard.html) for the live decisions board.
