# susr — Sustainability Report Skill

> A Claude Code skill that orchestrates the entire ESG / 永續報告書 SOP using first-principles design.
>
> - **Codename:** `susr`（短代號，repo / 工作目錄使用）
> - **Canonical name:** `sustainability-report`（skill frontmatter 識別字）

[繁體中文](#繁體中文) ・ [English](#english) ・ [License](#license--acknowledgements)

---

## 繁體中文

### 這是什麼

`susr` 是一個 Claude Code skill，把「寫一份永續報告書」從 **「每年從零開始的藝術」** 變成 **「可重複、可審計、可訓練的 8-Phase SOP + 模組化能力組合」**。

整合範圍：

- **領域知識** — GRI / ISSB / TCFD / ESRS / 台灣金管會作業辦法
- **數據工程** — GHG Protocol Scope 1/2/3、雙重重大性評估、KPI 公式
- **檔案產出** — 透過 [`anthropics/skills`](https://github.com/anthropics/skills) 的 `document-skills:docx / xlsx / pptx / pdf` 產出專業檔案
- **外部研究** — WebSearch 整合，自動同步最新法規、排放因子、同業 benchmark

### 為什麼

核心第一性原理：

1. **雙重重大性（Double Materiality）優先** — 同時評估 Impact + Financial
2. **價值鏈邊界明確** — 上游 → 自營 → 下游
3. **數據可追溯** — 每個數字必有來源、公式、版本、責任人
4. **IRO 連結性** — Impact / Risk / Opportunity → 治理 → 策略 → 行動 → 目標 → KPI 首尾貫通
5. **反綠色洗白** — 不只報好消息，必須揭露挑戰、未達標、目標調整理由
6. **決策有用性** — 報告對象是利害關係人決策，不是行銷部

### 8-Phase SOP

```
Phase 0  Pre-flight Dependencies      ── 確認 sub-skill 環境
Phase 1  Preparation & Scoping        ── 確定邊界、標準、責任分工
Phase 2  Research & Benchmarking      ── WebSearch 同步法規 / peer / 因子
Phase 3  Double Materiality           ── 雙軸評估 → 重大性矩陣
Phase 4  Data Engineering             ── ESG_Data_Pack.xlsx（公式 + 驗證）
Phase 5  Content Drafting             ── 章節草稿（IRO → KPI 連結）
Phase 6  Report Assembly              ── docx + pdf + pptx 專業輸出
Phase 7  Review & Assurance Readiness ── 合規檢查 + 確信前置
Phase 8  Filing & Continuous Improve  ── MOPS 公告 + 衍生改進
```

詳細工作流見 [`skills/sustainability-report/SKILL.md`](skills/sustainability-report/SKILL.md)。

### Quick Start

```bash
# 1. Clone 本專案
git clone https://github.com/M4ORE/m4ore-skill-susr.git susr
cd susr

# 2. 複製 skill 到 Claude Code skills 目錄
# macOS / Linux:
cp -r skills/sustainability-report ~/.claude/skills/

# Windows (PowerShell):
Copy-Item -Recurse skills\sustainability-report $env:USERPROFILE\.claude\skills\

# Windows (cmd):
xcopy /E /I skills\sustainability-report %USERPROFILE%\.claude\skills\sustainability-report
```

**3. 在 Claude Code 中觸發**

```
為 X 公司製作 2025 永續報告書
ESG 雙重重大性評估
Scope 3 範疇三盤查指引
```

> **更新 skill：** 本 repo 採 *複製式部署*（不是 symlink），每次 repo 更新後需重跑 step 2 才會在 Claude 環境生效。

### 依賴等級（Graceful Degradation）

susr 採 **漸進式降級** 設計：缺少高 tier 不會破壞低 tier 的使用。

| Tier | 內容 | 不滿足時的影響 |
|---|---|---|
| **0 必要** | Claude Code + skill 已複製到 `~/.claude/skills/` | susr 無法啟動 |
| **1 建議** | 啟用 [`anthropics/skills`](https://github.com/anthropics/skills) document-skills 插件 | Phase 1–5 完整可用；Phase 4 / 6 呼叫 sub-skill 時 fail with `skill not found` |
| **2 完整** | 底層工具（LibreOffice、Node、Python 套件） | sub-skill 啟動但中段失敗（例如 `soffice: command not found`）；Phase 0 會引導 AI 解析錯誤 |

**Tier 2 底層工具**（各 sub-skill 各自需要）：

| Sub-skill | 底層依賴 |
|---|---|
| `docx` | pandoc、LibreOffice、`npm install -g docx` |
| `xlsx` | LibreOffice、Python `openpyxl pandas` |
| `pptx` | LibreOffice、Poppler、Pillow、`npm install -g pptxgenjs` |
| `pdf`  | Poppler、Python `pypdf pdfplumber reportlab pytesseract pdf2image` |

> 完整安裝指令請見各 sub-skill 自身 `SKILL.md`（避免本 repo 與 sub-skill 不同步）。

**80% 使用價值不依賴 Tier 2** — 即使沒有底層工具，使用者仍能取得 SOP 指引、知識庫、prompt 模板，自行用 Word / Excel / PowerPoint 收尾。

### References 目錄導覽

```
skills/sustainability-report/
├── SKILL.md                                    主入口（Phase 0 + 8-Phase SOP）
└── references/
    ├── esg-glossary-zh-en.md                   雙語詞彙表
    ├── compliance-checklist.md                 60+ 項合規檢查（Phase 7）
    ├── materiality-topics-universe.md          40 項議題池 + 評分範本（Phase 3）
    ├── ghg-protocol.md                         GHG Scope 1/2/3 計算（Phase 4）
    ├── taiwan-fsc-sustainability-guidelines.md 台灣金管會（Phase 1, 8）
    ├── websearch-pending.md                    待查證項目清單（Phase 2 入口）
    ├── phase2-research-prompts.md              WebSearch 模板（Phase 2）
    ├── phase4-xlsx-prompts.md                  Data Pack 結構（Phase 4）
    ├── phase6-docx-prompts.md                  docx 組裝（Phase 6）
    ├── phase6-pdf-prompts.md                   pdf 輸出（Phase 6）
    └── phase6-pptx-prompts.md                  pptx 簡報 + 視覺 QA（Phase 6）
```

### Examples

端到端試做案例：[`examples/lealea-5364/`](examples/lealea-5364/) — 以力麗觀光開發（5364, TPEx, 觀光業）2023 永續報告書為對照標的，完整跑完 8-Phase SOP。

| 檔案 | Phase | 內容 |
|---|---|---|
| `phase1-scoping.md` | 1 | 公司邊界、適用標準、責任分工、9 大假設與限制 |
| `phase2-research-log.md` | 2 | 4 家旅館業同業 peer benchmark + 法規最新版 + 113 年度排放因子 |
| `phase3-materiality.md` | 3 | 28 議題池、雙軸評分、矩陣、IRO 對應、利害關係人議合 |
| `phase4-xlsx-skeleton.md` | 4 | 12 sheets 設計（Scenario A/B 雙軌、HVAC 制冷劑、Scope 3 取捨）|
| `phase5-chapter-skeleton.md` | 5 | 7 大篇 + 附錄章節骨架 |
| `phase5-tcfd-sample.md` | 5 | 完整 TCFD 章節示範（IRO → 治理 → 策略 → 行動 → 目標 → KPI → 展望）|
| `phase6-assembly-plan.md` | 6 | 5 個 sub-skill prompt 套裝 + 失敗模式表 |
| `phase7-gap-analysis.md` | 7 | **力麗實際 vs SOP 試做 14 項揭露差距總表** |
| `phase7-pdf-extract.md` | 7 | 力麗 2023 PDF 章節結構抽取（66 頁逐章）|
| `walkthrough-notes.md` | — | Lessons learned + SOP 評等 + 反向示範意涵 |

**重要發現**：力麗 2023 為台灣中型 TPEx 上市公司的「**反向示範**」典型樣本 — 無雙重重大性、TCFD 完全缺席、GHG 僅 Scope 2 殘缺、GRI 用 2016 舊版、無第三方確信。本案例可直接作為「**升級指南**」教材：「我家公司報告書像力麗，怎麼升級到金管會 ISSB 強制標準？」

### 開發歷程（PDCA 透明化）

本專案採 PDCA 工作流，所有設計決策都有可追溯紀錄：

- [`docs/sprints/`](docs/sprints/) — Sprint 規劃
- [`docs/tasks/`](docs/tasks/) — 任務追蹤
- [`docs/standards/skill-development.md`](docs/standards/skill-development.md) — 開發標準（§9 涵蓋 Orchestrator Skill 開發流程，適用於任何呼叫 sub-skill 的 skill）

### Contributing

詳見 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

### 為何 codename 是 susr

工作目錄與 repo 採短代號 `susr` 方便輸入；skill frontmatter 的 `name` 保留描述性的 `sustainability-report`，以利 Claude 與其他使用者識別。詳見 [`docs/tasks/SP1-006.md`](docs/tasks/SP1-006.md)。

---

## English

### What is this

`susr` is a Claude Code skill that turns "writing a sustainability / ESG report" from **a yearly from-scratch art** into **a repeatable, auditable, trainable 8-Phase SOP + modular capabilities**.

It integrates:

- **Domain knowledge** — GRI / ISSB / TCFD / ESRS / Taiwan FSC reporting rules
- **Data engineering** — GHG Protocol Scope 1/2/3, double materiality assessment, KPI formulas
- **File production** — via Anthropic's [`document-skills`](https://github.com/anthropics/skills) (`docx / xlsx / pptx / pdf`)
- **External research** — WebSearch integration to sync latest regulations, emission factors, peer benchmarks

### Why

Core first principles:

1. **Double Materiality first** — Impact + Financial
2. **Value chain boundary explicit** — upstream → operations → downstream
3. **Auditable data** — every number has source, formula, version, owner
4. **IRO connectivity** — Impact / Risk / Opportunity → governance → strategy → actions → targets → KPIs end-to-end
5. **Anti-greenwashing** — disclose challenges, missed targets, target revisions
6. **Decision-usefulness** — the report serves stakeholder decisions, not marketing

### 8-Phase SOP

```
Phase 0  Pre-flight Dependencies
Phase 1  Preparation & Scoping
Phase 2  Research & Benchmarking         (WebSearch)
Phase 3  Double Materiality
Phase 4  Data Engineering                (xlsx)
Phase 5  Content Drafting
Phase 6  Report Assembly                 (docx + pdf + pptx)
Phase 7  Review & Assurance Readiness
Phase 8  Filing & Continuous Improvement
```

Full workflow in [`skills/sustainability-report/SKILL.md`](skills/sustainability-report/SKILL.md).

### Quick Start

```bash
# 1. Clone
git clone https://github.com/M4ORE/m4ore-skill-susr.git susr
cd susr

# 2. Copy the skill to Claude Code's skills directory
# macOS / Linux:
cp -r skills/sustainability-report ~/.claude/skills/

# Windows (PowerShell):
Copy-Item -Recurse skills\sustainability-report $env:USERPROFILE\.claude\skills\

# Windows (cmd):
xcopy /E /I skills\sustainability-report %USERPROFILE%\.claude\skills\sustainability-report
```

**3. Trigger in Claude Code**

```
Create a 2025 sustainability report for Company X
ESG double materiality assessment
Scope 3 emissions inventory guidance
```

> **Updating the skill:** this repo uses *copy-based deployment* (not symlink), so any repo update requires re-running step 2 to take effect in Claude.

### Dependency Tiers (Graceful Degradation)

susr is designed for **progressive degradation** — missing a higher tier does not break the lower tiers.

| Tier | Requirement | Impact if missing |
|---|---|---|
| **0 Required** | Claude Code + skill copied to `~/.claude/skills/` | susr cannot launch |
| **1 Recommended** | Enable [`anthropics/skills`](https://github.com/anthropics/skills) document-skills plugin | Phases 1–5 fully usable; Phase 4 / 6 fail with `skill not found` when invoking sub-skills |
| **2 Full** | Underlying tools (LibreOffice, Node, Python packages) | Sub-skill loads but fails mid-flow (e.g., `soffice: command not found`); Phase 0 teaches the AI how to parse such errors |

**Tier 2 underlying tools** (per sub-skill):

| Sub-skill | Dependencies |
|---|---|
| `docx` | pandoc, LibreOffice, `npm install -g docx` |
| `xlsx` | LibreOffice, Python `openpyxl pandas` |
| `pptx` | LibreOffice, Poppler, Pillow, `npm install -g pptxgenjs` |
| `pdf`  | Poppler, Python `pypdf pdfplumber reportlab pytesseract pdf2image` |

> For full install commands, refer to each sub-skill's own `SKILL.md` (we don't mirror them here to avoid drift).

**80% of the value does not depend on Tier 2** — even without the underlying tools, users still get SOP guidance, the knowledge base, and prompt templates, and can finalize outputs manually in Word / Excel / PowerPoint.

### References Layout

See the directory tree in the [繁體中文 section](#references-目錄導覽) above.

### Examples

End-to-end walkthrough: [`examples/lealea-5364/`](examples/lealea-5364/) — uses **Lealea Hotels (5364, TPEx, hospitality)** 2023 sustainability report as the benchmark target, running the full 8-Phase SOP.

10 deliverables covering Phase 1 scoping → Phase 2 peer benchmark → Phase 3 double materiality → Phase 4 xlsx skeleton → Phase 5 TCFD sample chapter → Phase 6 assembly plan → Phase 7 gap analysis → walkthrough notes.

**Key finding**: Lealea 2023 turned out to be a **reverse-example** typical of mid-cap TPEx-listed companies — no double materiality, TCFD entirely absent, GHG only Scope 2 (incomplete), GRI stuck on 2016, no third-party assurance. The case study works as an **upgrade-path guide**: "my company's report looks like Lealea's — how do I upgrade to FSC ISSB-mandatory standards?"

### Development History (PDCA Transparency)

This project follows a PDCA workflow with full traceability:

- [`docs/sprints/`](docs/sprints/) — sprint planning
- [`docs/tasks/`](docs/tasks/) — task tracking
- [`docs/standards/skill-development.md`](docs/standards/skill-development.md) — development standards (§9 covers orchestrator skill principles, applicable to any skill that calls sub-skills)

### Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

### Why the codename `susr`

The working directory and repo use the short codename `susr` for easy typing; the skill's frontmatter `name` keeps the descriptive `sustainability-report` so Claude and other users can identify its purpose. See [`docs/tasks/SP1-006.md`](docs/tasks/SP1-006.md) for the rationale.

---

## License & Acknowledgements

MIT License — see [`LICENSE`](LICENSE).

**Thanks to:**

- [Anthropic Claude](https://claude.com) and
  [`anthropics/skills`](https://github.com/anthropics/skills) for the
  document-skills foundation that this orchestrator builds upon
- First-principles discussion sparked by Grok 4 (private draft `plan.md`)

**Project status:** under active development. See `docs/sprints/SP1.md` for
current Sprint progress.
