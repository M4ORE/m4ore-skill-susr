# Contributing to susr / 貢獻指南

> susr is the project codename for the `sustainability-report` Claude Code skill.
> See [README.md](README.md) for context.

[繁體中文](#繁體中文) | [English](#english)

---

## English

### How to file an issue

1. Search existing issues first to avoid duplicates
2. Provide:
   - Which **Phase** (1–8) you were in
   - Which **sub-skill** failed (`docx` / `xlsx` / `pptx` / `pdf` / `WebSearch`)
   - Full error message and reproduction steps
   - Your environment (OS, Claude Code version, sub-skill versions if known)

### How to propose changes

This project uses a **PDCA workflow** — see
[`docs/standards/skill-development.md`](docs/standards/skill-development.md)
for the full development standard.

For any non-trivial contribution:

1. Open an issue first to align on the **Plan**
2. Reference `docs/sprints/` and `docs/tasks/` for project structure
3. Submit a PR including:
   - Updated `references/` (if knowledge content changes)
   - Updated `SKILL.md` (if SOP / workflow changes)
   - A new task file under `docs/tasks/` describing the change
4. Each PR should map to one PDCA Task (small) or one Sprint (large)

### Code style

- User-facing text: **Traditional Chinese (zh-TW)** primary, English secondary
- Code identifiers: English (snake_case for Python, kebab-case for skill names)
- Markdown headings: bilingual in `README.md` / `CONTRIBUTING.md`; monolingual elsewhere
- Skill development conventions: see
  [`docs/standards/skill-development.md`](docs/standards/skill-development.md) §1–9

### Sub-skill compatibility

This skill orchestrates `document-skills:docx / xlsx / pptx / pdf` from
[anthropics/skills](https://github.com/anthropics/skills). When their internal
APIs change, integration prompts in `references/phase*-prompts.md` may need
updating.

See [`docs/standards/skill-development.md`](docs/standards/skill-development.md)
**§9 (Orchestrator Skill 開發流程)** for maintenance principles.

### Updating time-sensitive references

Regulations, emission factors, and standards versions evolve. When updating:

1. Add / update an entry in `skills/sustainability-report/references/websearch-pending.md`
2. Run a `WebSearch` to verify the latest source
3. Update the affected reference file
4. Record the verification date and source URL in `websearch-pending.md` (audit trail)

---

## 繁體中文

### 提交 Issue

1. 先搜尋既有 issue 避免重複
2. 提供：
   - 卡在哪個 **Phase**（1–8）
   - 哪個 **sub-skill** 失敗（`docx` / `xlsx` / `pptx` / `pdf` / `WebSearch`）
   - 完整錯誤訊息與重現步驟
   - 你的環境（OS、Claude Code 版本、若知道則附 sub-skill 版本）

### 提交變更

本專案採 **PDCA 工作流程** — 詳見
[`docs/standards/skill-development.md`](docs/standards/skill-development.md)。

任何非簡單變更：

1. 先開 issue 對齊 **Plan**
2. 參考 `docs/sprints/` 與 `docs/tasks/` 的專案結構
3. 提交 PR 並附：
   - 更新 `references/`（若是知識內容變動）
   - 更新 `SKILL.md`（若是 SOP / 流程變動）
   - 新增 `docs/tasks/` 下 task 文件描述變更
4. 每個 PR 對應一個 Task（小）或一個 Sprint（大）

### 程式碼風格

- 使用者面向文字：**繁體中文 zh-TW** 為主，英文為輔
- 程式碼識別字：英文（Python 用 snake_case、skill 名用 kebab-case）
- Markdown 標題：`README.md` / `CONTRIBUTING.md` 採雙語，其他單語
- Skill 開發慣例：詳見
  [`docs/standards/skill-development.md`](docs/standards/skill-development.md) §1–9

### Sub-skill 相容性

本 skill 整合 [anthropics/skills](https://github.com/anthropics/skills) 的
`document-skills:docx / xlsx / pptx / pdf`。當其內部 API 變動，
`references/phase*-prompts.md` 整合 prompt 可能需要更新。

維護原則見
[`docs/standards/skill-development.md`](docs/standards/skill-development.md) **§9（Orchestrator Skill 開發流程）**。

### 更新時效性 reference

法規、排放因子、標準版本會變動。更新時：

1. 在 `skills/sustainability-report/references/websearch-pending.md` 新增 / 更新項目
2. 跑 `WebSearch` 驗證最新來源
3. 更新對應 reference 檔案
4. 在 `websearch-pending.md` 記錄確認日期與來源 URL（保留稽核軌跡）
