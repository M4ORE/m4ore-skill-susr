# Step 1 Spike: packages/susr v0 Spec

**Spike 日期**：2026-05-25
**範圍**：MVP v0.1 — Phase 3 重大性評估端到端的 brain core spec
**作者**：susr 首席工程師（Claude Opus 4.7）
**所有工程決策已在 `CLAUDE.md §8` 鎖定，本 spec 只實現不重新評估**
**對齊憲法**：`docs/defeinition.md` / `target.md` / `product_structure.md` 三原則

---

## TL;DR

susr-brain v0 是 local-first ESG/永續報告 Co-pilot 的大腦：以 SQLite + sqlite-vec + FTS5 為單檔引擎，落地 17 個 ESG entity、19 條 typed edges 與 5 條連結性 invariants（fail-closed）；檢索走 vector KNN + FTS5 BM25 經 RRF（k=60）融合；以 `page_versions` snapshot + append-only `timeline_entries` 提供反綠色洗白證據鏈。MVP 第一刀只切 Phase 3 重大性評估，唯一 entry point 為 `susr-mcp` console script，顧問在 Claude Desktop 聊天操作。Embedding 採 Provider Protocol，預設本地 BGE-M3（解個資合約風險）並 ship OpenAI/Voyage 三組做 Layer 4 benchmark；LLMProvider 同樣 day-1 抽象。測試骨架覆蓋 Layer 3 invariants 與 Layer 4 引擎單元。

## 目錄（TOC）

- [0. Spec 性質與不在範圍](#0-spec-性質與不在範圍)
- [1. Package 結構與 pyproject.toml](#1-package-結構與-pyprojecttoml)
- [2. SQLite + sqlite-vec + FTS5 Schema](#2-sqlite--sqlite-vec--fts5-schema)
  - [2.1 PRAGMA 與初始化](#21-pragma-與初始化)
  - [2.2 核心表 DDL（`susr/brain/ddl/v001_init.sql`）](#22-核心表-ddlsusrbraindddlv001_initsql)
  - [2.3 17 個 ESG entity 類型](#23-17-個-esg-entity-類型)
  - [2.4 19 條 typed edges 註冊](#24-19-條-typed-edges-註冊)
  - [2.5 5 條連結性 invariants（fail-closed 實現）](#25-5-條連結性-invariantsfail-closed-實現)
- [3. Hybrid Search 引擎](#3-hybrid-search-引擎)
- [4. page_versions + timeline 設計](#4-page_versions--timeline-設計)
- [5. Embedding 抽象層 + Q7/Q8 收斂建議](#5-embedding-抽象層--q7q8-收斂建議)
- [6. MCP Server (susr-mcp)](#6-mcp-server-susr-mcp)
- [7. 力麗 5364 → Option C 結構移轉草案](#7-力麗-5364--option-c-結構移轉草案)
- [8. 測試骨架（Layer 3 + Layer 4）](#8-測試骨架layer-3--layer-4)
- [9. 顧問安裝 happy path](#9-顧問安裝-happy-path)
- [10. 風險與未解](#10-風險與未解)
- [Appendix A — 所用外部資源](#appendix-a--所用外部資源)

---

## 0. Spec 性質與不在範圍

### 0.1 本檔是什麼

本檔是 **spec spike**，不是 implementation。目的是讓後續 implementation 可以照 spec 直接落地，避免再次出現像 gbrain spec-impl gap 那樣的「招牌功能存在於 markdown、實作沒寫」風險（`CLAUDE.md §6.1` 鐵則）。

### 0.2 涵蓋

- `packages/susr/` 目錄結構與 `pyproject.toml`
- SQLite + sqlite-vec + FTS5 完整 DDL（可直接 `sqlite3` 執行）
- 17 個 ESG entity 與 19 條 typed edges schema 落地
- 5 條連結性 invariants 的 schema-level / app-level 實現方案
- Hybrid Search（RRF）演算法 pseudocode
- `page_versions` snapshot + `timeline_entries` 機制
- Embedding & LLM 抽象層 Protocol signature
- MCP server tools 完整 signature
- 力麗 5364 → Option C 結構對照表
- 測試骨架（Layer 3 + Layer 4）
- 顧問安裝 happy path

### 0.3 不在範圍

- Phase 1 / 2 / 4 / 5 / 6 / 7 / 8（MVP 第一刀只切 Phase 3，`CLAUDE.md §8 MVP 決策`）
- CLI 子命令（唯一 entry point 是 `susr-mcp` console script，`CLAUDE.md §8 決策 4`）
- GUI（Claude Desktop 已是 GUI 入口）
- 商業模式 / 訂閱 / billing
- iXBRL 實際填值機制（只預留 nullable 欄位，`CLAUDE.md §8 Q16`）
- 跨 client 學習 / KB 跨年 reuse（先單 client 單年）

### 0.4 對齊 check

| 三原則 | 對齊狀態 |
|--------|---------|
| Definition：可驗證、可比較、可信任 | ✅ Markdown source of truth + git diff + page_versions snapshot + timeline append-only |
| Target：對象是顧問、40-80h → 8-15h | ✅ `pip install susr` 零 Postgres、零 Docker、Claude Desktop 聊天介面操作 |
| Product Structure：三層架構 | ✅ MCP tools 對應智能層 Phase 3；輸入層由顧問貼資料；輸出層 Phase 3 產 markdown matrix |
| Co-pilot 定位 | ✅ 所有 MCP tool 都是「輔助顧問做決策」，不替顧問決定議題重大度 |

---

## 1. Package 結構與 pyproject.toml

### 1.1 Mono-repo 目錄樹

```
m4ore-skill-susr/                          ← repo root，git
├── pyproject.toml                          ← uv workspace root (見 §1.4)
├── uv.lock
├── .python-version                         ← "3.11"
├── CLAUDE.md
├── README.md
├── dashboard.html
├── dashboard-data.json
├── skills/sustainability-report/           ← 並行獨立（決策 5），不動
├── examples/lealea-5364/                   ← 試做案例，第 7 節給對照表，本 spec 不動
├── docs/
│   ├── defeinition.md / target.md / product_structure.md
│   ├── research/
│   │   ├── gbrain-survey.md
│   │   └── step1-spec.md                   ← 本檔
│   ├── sprints/ / tasks/ / standards/
├── tests/                                  ← repo-level Layer 1 + Layer 2（已 bootstrap）
└── packages/
    └── susr/                               ← 唯一 Python package（決策 3+4）
        ├── pyproject.toml                  ← entry point: susr-mcp（見 §1.3）
        ├── README.md
        ├── susr/
        │   ├── __init__.py                 ← __version__
        │   ├── brain/
        │   │   ├── __init__.py
        │   │   ├── engine.py               ← BrainEngine（DB 連線、CRUD、search）
        │   │   ├── schema.py               ← DDL 載入 + migration version
        │   │   ├── search.py               ← RRF hybrid search
        │   │   ├── entities.py             ← 17 entity types 註冊 + frontmatter schema
        │   │   ├── edges.py                ← 19 typed edges 註冊 + invariant lint
        │   │   ├── versions.py             ← page_versions snapshot
        │   │   ├── timeline.py             ← timeline_entries append-only
        │   │   └── ddl/
        │   │       └── v001_init.sql       ← 完整 DDL（見 §2）
        │   ├── embeddings/
        │   │   ├── __init__.py
        │   │   ├── base.py                 ← EmbeddingProvider Protocol
        │   │   ├── openai_provider.py
        │   │   ├── voyage_provider.py
        │   │   └── bge_m3_provider.py
        │   ├── llm/
        │   │   ├── __init__.py
        │   │   ├── base.py                 ← LLMProvider Protocol
        │   │   └── anthropic_provider.py
        │   ├── mcp/
        │   │   ├── __init__.py
        │   │   ├── server.py               ← FastMCP server，stdio
        │   │   ├── tools_phase3.py         ← Phase 3 四件套 tools（見 §6.2）
        │   │   ├── tools_workspace.py      ← create / health / kb update（§6.3）
        │   │   └── tools_kb.py             ← read / promote consultant kb（§6.4）
        │   ├── shared_kb/                  ← bundled KB（pip ship）
        │   │   ├── materiality-topics-universe.md
        │   │   ├── ghg-protocol.md
        │   │   ├── taiwan-fsc-sustainability-guidelines.md
        │   │   ├── esg-glossary-zh-en.md
        │   │   ├── compliance-checklist.md
        │   │   └── industry-packs/
        │   │       ├── hotel.md            ← 力麗適用：旅館業 28 項特化
        │   │       └── ...
        │   ├── workspace.py                ← create_client_workspace 等共用邏輯
        │   └── _resources/
        │       └── default_db_pragmas.sql  ← journal_mode=WAL / foreign_keys=ON …
        └── tests/
            ├── conftest.py                 ← fixtures: tmp_db / sample_pages
            ├── test_schema.py              ← DDL load + migration（Layer 4）
            ├── test_invariants.py          ← 5 條連結性（Layer 3）
            ├── test_search_rrf.py          ← RRF 數學（Layer 4）
            ├── test_versions.py            ← snapshot/restore（Layer 4）
            ├── test_timeline.py            ← append-only（Layer 4）
            ├── test_embeddings.py          ← Protocol conformance（Layer 4）
            └── test_mcp_handlers.py        ← MCP tool input validation（Layer 4）

per-client repo（顧問本機，獨立 git，CLAUDE.md §8 Q9/決策 10）:
~/work/lealea-5364/
├── .git/
├── .susr/db.sqlite                         ← brain DB（SQLite 單檔）
├── _client.md                              ← profile / 邊界 / embedding_policy
├── entities/
│   ├── topics/                             ← E1.md, E2.md, S6.md ...
│   ├── stakeholders/                       ← 客戶.md, 員工.md, 投資人.md ...
│   ├── governance/
│   ├── kpis/
│   └── targets/
├── projects/
│   └── 2025-sustainability-report/
│       ├── _project.md
│       ├── scoping.md
│       ├── materiality-2025.md             ← Phase 3 主交付（MVP 目標）
│       ├── datapoints/
│       ├── chapters/
│       └── output/
├── sourcedocs/2025/
└── shared/                                 ← snapshot copy from susr package
    └── (mirror of packages/susr/susr/shared_kb/)
```

### 1.2 mono-repo root `pyproject.toml`

```toml
[project]
name = "m4ore-skill-susr-workspace"
version = "0.0.0"
description = "susr mono-repo workspace root (not published)"
requires-python = ">=3.11"

[tool.uv.workspace]
members = ["packages/*"]

[tool.uv]
# 開發時 lock 整個 workspace
dev-dependencies = [
  "pytest>=8.0",
  "pytest-asyncio>=0.23",
  "pyyaml>=6.0",
  "ruff>=0.6",
]
```

來源：`https://docs.astral.sh/uv/concepts/projects/workspaces/` — `members` glob，每個成員必須有自己的 `pyproject.toml`。Root 本身不發 PyPI。

### 1.3 `packages/susr/pyproject.toml`（發 PyPI 的真正單一 package）

```toml
[project]
name = "susr"
version = "0.1.0"
description = "susr — Sustainability/ESG report Co-pilot brain for consultants. Local-first, MCP-native."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "m4ore", email = "service@m4ore.com" }]
classifiers = [
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "License :: OSI Approved :: MIT License",
  "Operating System :: OS Independent",
  "Topic :: Office/Business",
]

dependencies = [
  # MCP server — pip install "mcp[cli]" 取得 FastMCP + stdio_server
  # 來源：https://pypi.org/project/mcp/ v1.27.1 (2026-05-08)，requires Python >=3.10
  "mcp[cli]>=1.27,<2.0",

  # SQLite vector extension — 來源：https://pypi.org/project/sqlite-vec/ v0.1.9 (2026-03-31)
  # ⚠️ 仍是 pre-v1，鎖 minor，breaking change 可能
  "sqlite-vec>=0.1.9,<0.2",

  # 資料 schema / validation
  "pydantic>=2.6,<3.0",

  # Markdown + frontmatter
  "python-frontmatter>=1.1",
  "markdown-it-py>=3.0",

  # LLM provider（預設 Anthropic）
  "anthropic>=0.40",

  # 工具
  "httpx>=0.27",
  "typer>=0.12",    # 給 susr-mcp doctor 子命令用（極簡）
]

[project.optional-dependencies]
embeddings-openai = ["openai>=1.50"]
embeddings-voyage = ["voyageai>=0.2"]
embeddings-bge = [
  "sentence-transformers>=3.0",
  "torch>=2.2",
]
all = ["susr[embeddings-openai,embeddings-voyage,embeddings-bge]"]
dev = [
  "pytest>=8.0",
  "pytest-asyncio>=0.23",
  "pytest-cov>=5.0",
  "ruff>=0.6",
]

[project.scripts]
# 唯一 console script — 顧問安裝後設定 Claude Desktop config 指向它
# `susr-mcp` 啟動 stdio MCP server
# `susr-mcp doctor` 做健康檢查（typer 子命令）
susr-mcp = "susr.mcp.server:cli"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["susr"]

[tool.hatch.build.targets.wheel.force-include]
"susr/shared_kb" = "susr/shared_kb"
"susr/brain/ddl" = "susr/brain/ddl"
"susr/_resources" = "susr/_resources"
```

### 1.4 為何沒有 `susr` CLI 子命令

`CLAUDE.md §8 決策 4` 鎖定：唯一需要 console script 是 `susr-mcp`（讓 Claude Desktop spawn）。其他原本想做的 `init / doctor / kb-update`，都已對應到 MCP tools（`create_client_workspace` / `health_check` / `update_shared_kb`），顧問零 shell 操作。

唯一例外：`susr-mcp doctor` 作為**子命令**（用 typer 拆 subcommand），協助顧問在 Claude Desktop config 還沒設好時直接從 terminal 確認安裝狀態。這是顧問**第一次 install** 的唯一一次 shell 觸碰；之後全走聊天。

---

## 2. SQLite + sqlite-vec + FTS5 Schema

### 2.1 PRAGMA 與初始化

`susr/brain/_resources/default_db_pragmas.sql`：

```sql
-- Performance & safety baseline for susr brain
PRAGMA journal_mode = WAL;          -- 顧問同時開 Claude Desktop 與編輯器修 markdown
PRAGMA synchronous = NORMAL;        -- WAL 下安全
PRAGMA foreign_keys = ON;           -- 強制 FK
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 268435456;       -- 256MB
PRAGMA cache_size = -64000;         -- 64MB page cache
```

Python 連線初始化（pseudocode）：

```python
import sqlite3, sqlite_vec

def open_brain(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    with open(_RESOURCES / "default_db_pragmas.sql") as f:
        conn.executescript(f.read())
    return conn
```

來源：`https://alexgarcia.xyz/sqlite-vec/python.html`（`sqlite_vec.load(conn)` 用法）。

### 2.2 核心表 DDL（`susr/brain/ddl/v001_init.sql`）

> ⚠️ **macOS 內建 Python 不支援 `enable_load_extension`，會 `AttributeError`。安裝指南必須提醒顧問用 Homebrew Python 或 official python.org 3.11 installer**（見 §10 風險）。

```sql
-- =============================================
-- susr brain v001 — initial schema
-- Target: SQLite >= 3.41 (sqlite-vec requirement)
-- Extensions: sqlite-vec loaded as virtual table backend
-- =============================================

-- --- 1. Migration bookkeeping ----------------
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now')),
    description TEXT
);
INSERT OR IGNORE INTO schema_version (version, description)
VALUES (1, 'initial schema: pages + entity_attributes + links + timeline + versions + vec + fts');

-- --- 2. pages 主表 ---------------------------
-- 每個 markdown file = 一筆 page
-- frontmatter 攤平存 entity_attributes；compiled_truth = 橫線上的「結論」段；
-- timeline 在橫線下，但 application 寫入時 split 到 timeline_entries
CREATE TABLE IF NOT EXISTS pages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT    NOT NULL,                  -- e.g. 'topics/E1', 'kpis/scope1-emissions'
    entity_type     TEXT    NOT NULL,                  -- see §2.3 enum
    title           TEXT    NOT NULL,
    compiled_truth  TEXT    NOT NULL DEFAULT '',       -- markdown body above '---' separator
    file_path       TEXT    NOT NULL,                  -- relative to client repo root
    source_hash     TEXT    NOT NULL,                  -- sha256 of full file content
    tenant_id       TEXT,                              -- nullable; future team edition (Q4 退路)
    project_slug    TEXT,                              -- nullable; for projects/* pages
    xbrl_concept    TEXT,                              -- nullable; iXBRL/ESEF future (Q16 預留)
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    deleted_at      TEXT,                              -- soft delete
    UNIQUE (slug, tenant_id)
);
CREATE INDEX IF NOT EXISTS idx_pages_entity_type ON pages(entity_type);
CREATE INDEX IF NOT EXISTS idx_pages_project      ON pages(project_slug);
CREATE INDEX IF NOT EXISTS idx_pages_tenant       ON pages(tenant_id);

-- --- 3. entity_attributes：frontmatter 攤平 ---
-- 每個 entity 的 frontmatter dict 拆 (page_id, key, value, value_type)
-- 配合 §2.3 的每 entity 必備欄位 validator
CREATE TABLE IF NOT EXISTS entity_attributes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id     INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    key         TEXT    NOT NULL,
    value       TEXT,                                  -- JSON string for arrays/dicts; primitives as text
    value_type  TEXT    NOT NULL CHECK (value_type IN ('text','int','float','bool','date','json_array','json_object')),
    UNIQUE (page_id, key)
);
CREATE INDEX IF NOT EXISTS idx_attr_page ON entity_attributes(page_id);
CREATE INDEX IF NOT EXISTS idx_attr_key  ON entity_attributes(key);

-- --- 4. links：typed edges -------------------
-- 19 edge types 於 §2.4 註冊；application layer 驗 src/dst entity_type 合法
CREATE TABLE IF NOT EXISTS links (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    src_page_id   INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    dst_page_id   INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    edge_type     TEXT    NOT NULL,                    -- enum value, see §2.4
    properties    TEXT    DEFAULT '{}',                -- JSON: e.g. {confidence:0.8, year:2025}
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (src_page_id, dst_page_id, edge_type)
);
CREATE INDEX IF NOT EXISTS idx_links_src     ON links(src_page_id, edge_type);
CREATE INDEX IF NOT EXISTS idx_links_dst     ON links(dst_page_id, edge_type);
CREATE INDEX IF NOT EXISTS idx_links_type    ON links(edge_type);

-- --- 5. timeline_entries：append-only 證據鏈 -
CREATE TABLE IF NOT EXISTS timeline_entries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id       INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    ts            TEXT    NOT NULL DEFAULT (datetime('now')),
    action_type   TEXT    NOT NULL CHECK (action_type IN (
                    'ingest',      -- 第一次寫入 / 重新匯入
                    'verify',      -- 顧問複核確認
                    'restate',     -- 數值重述（> 5% 觸發 alert）
                    'assure',      -- 第三方確信通過
                    'comment',     -- 顧問附註
                    'iro_link',    -- IRO 對應建立
                    'gap_flag'     -- gap analysis 標記
                  )),
    source_ref    TEXT,                                -- file path / URL / chat msg id
    confidence    REAL    CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    actor         TEXT,                                -- 'consultant:zhang' / 'agent:claude-opus-4-7'
    payload       TEXT    DEFAULT '{}'                 -- JSON: detail per action_type
);
CREATE INDEX IF NOT EXISTS idx_timeline_page ON timeline_entries(page_id, ts);
CREATE INDEX IF NOT EXISTS idx_timeline_type ON timeline_entries(action_type, ts);

-- timeline append-only：禁 UPDATE / DELETE（soft 行為由 action_type=restate 表達）
CREATE TRIGGER IF NOT EXISTS trg_timeline_no_update
BEFORE UPDATE ON timeline_entries
BEGIN
    SELECT RAISE(ABORT, 'timeline_entries is append-only; insert a new row with action_type instead');
END;
CREATE TRIGGER IF NOT EXISTS trg_timeline_no_delete
BEFORE DELETE ON timeline_entries
BEGIN
    SELECT RAISE(ABORT, 'timeline_entries is append-only; cannot delete history');
END;

-- --- 6. page_versions：snapshot ---------------
-- 觸發時機：commit / phase 完成 / 年度 freeze / restate（§4）
CREATE TABLE IF NOT EXISTS page_versions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id             INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    version_no          INTEGER NOT NULL,              -- monotonic per page
    parent_version_id   INTEGER REFERENCES page_versions(id),
    content_hash        TEXT    NOT NULL,
    frontmatter_snap    TEXT    NOT NULL,              -- JSON dump of frontmatter at snapshot
    compiled_truth_snap TEXT    NOT NULL,              -- full body snapshot
    snapshot_reason     TEXT    NOT NULL CHECK (snapshot_reason IN (
                            'manual','phase_complete','year_freeze','restate','assurance'
                        )),
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    created_by          TEXT,
    UNIQUE (page_id, version_no)
);
CREATE INDEX IF NOT EXISTS idx_versions_page ON page_versions(page_id, version_no DESC);

-- --- 7. vec_chunks：sqlite-vec virtual table -
-- 每個 page 切 chunk → embed → 插入
-- partition by entity_type 提速 (sqlite-vec partition key);
-- 1536d 為 OpenAI text-embedding-3-large 預設；其他 provider 改 dim 時要重建
-- 來源：https://alexgarcia.xyz/sqlite-vec/features/vec0.html
CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
    chunk_id        INTEGER PRIMARY KEY,
    page_id         INTEGER NOT NULL,
    entity_type     TEXT PARTITION KEY,                -- 提速 entity-filtered KNN
    project_slug    TEXT,                              -- metadata col for WHERE filter
    tenant_id       TEXT,                              -- metadata col for WHERE filter
    embedding       FLOAT[1536],                       -- ⚠️ 切 provider 時要 ALTER TABLE / 重建
    +chunk_text     TEXT,                              -- aux col：retrieval 時拿回原文
    +chunk_meta     TEXT                               -- aux col：JSON {section, char_start, char_end}
);

-- --- 8. fts_pages：FTS5 ----------------------
-- 中文 ESG 文本：trigram tokenizer 為 SQLite stdlib 唯一可行的 CJK 友善選項
-- （unicode61 對無空格中文會把整段視為一個 token；ICU tokenizer 需自編譯）
-- 來源：https://www.sqlite.org/fts5.html#tokenizers
CREATE VIRTUAL TABLE IF NOT EXISTS fts_pages USING fts5(
    title,
    compiled_truth,
    slug UNINDEXED,
    entity_type UNINDEXED,
    project_slug UNINDEXED,
    tenant_id UNINDEXED,
    tokenize = 'trigram'
);

-- 自動同步 pages → fts_pages（content table 不用，因為 trigram 不支援 content=）
CREATE TRIGGER IF NOT EXISTS trg_pages_fts_insert AFTER INSERT ON pages BEGIN
    INSERT INTO fts_pages(rowid, title, compiled_truth, slug, entity_type, project_slug, tenant_id)
    VALUES (new.id, new.title, new.compiled_truth, new.slug, new.entity_type, new.project_slug, new.tenant_id);
END;
CREATE TRIGGER IF NOT EXISTS trg_pages_fts_delete AFTER DELETE ON pages BEGIN
    DELETE FROM fts_pages WHERE rowid = old.id;
END;
CREATE TRIGGER IF NOT EXISTS trg_pages_fts_update AFTER UPDATE ON pages BEGIN
    DELETE FROM fts_pages WHERE rowid = old.id;
    INSERT INTO fts_pages(rowid, title, compiled_truth, slug, entity_type, project_slug, tenant_id)
    VALUES (new.id, new.title, new.compiled_truth, new.slug, new.entity_type, new.project_slug, new.tenant_id);
END;
```

### 2.3 17 個 ESG entity 類型

整合 gbrain-survey §4.1 17 entities + 各自必備 frontmatter 欄位。`entities.py` 內以 Pydantic 註冊：

| entity_type enum | 路徑慣例 | 必備 frontmatter（schema-validated） | 選用欄位 |
|------------------|---------|-----|-----|
| `client` | `_client.md` | `slug, legal_name, stock_code, industry_gri_sector, boundary, reporting_period, applicable_standards[]` | `tier, lead_consultant, assurance_provider, embedding_policy` |
| `report` | `projects/<year>-sr/_project.md` | `slug, client_slug, year, version, language, framework_bundle, status` | `published_at, mops_filing_no, assurance_level` |
| `chapter` | `projects/<year>-sr/chapters/<x>.md` | `slug, report_slug, title, framework_refs[], owner` | `discloses_topics[], mandatory` |
| `topic` | `entities/topics/<id>.md` | `slug, name, axis (E/S/G), impact_score, financial_score, materiality_tier, industry_specificity` | `assessed_at, assessed_by, assessment_year, parent_topic` |
| `iro` | `entities/topics/<topic>/iro/<x>.md` | `slug, topic_slug, type (Impact/Risk/Opportunity), category, time_horizon, financial_magnitude` | `evidence_refs[]` |
| `stakeholder` | `entities/stakeholders/<x>.md` | `slug, category, influence_on_company, affected_by_company` | `engagement_channels[]` |
| `engagement` | `entities/stakeholders/<x>/engagements/<date>.md` | `slug, stakeholder_slug, topic_slugs[], date, method, sample_size, findings_summary` | `evidence_refs[]` |
| `governance` | `entities/governance/<x>.md` | `slug, body, oversight_topics[], meeting_frequency, kpi_linkage` | `members_esg_expertise[]` |
| `action` | `projects/<year>-sr/actions/<x>.md` | `slug, chapter_slug, iro_addressed[], budget, progress_pct, owner_department, period` | `evidence_refs[]` |
| `target` | `entities/targets/<x>.md` | `slug, kpi_slug, baseline_year, baseline_value, target_value, target_year, verification_path` | `sbti_alignment, is_quantitative` |
| `kpi` | `entities/kpis/<x>.md` | `slug, topic_slug, name, unit, framework_refs[], boundary, formula` | `values_by_year[], restatement_flag, xbrl_concept` |
| `datapoint` | `projects/<year>-sr/datapoints/<kpi>-<year>.md` | `slug, kpi_slug, year, value, source_refs[], calculation_method, assurance_status, last_assessed, responsible_person` | `restated_from, confidence, xbrl_concept` |
| `regulation` | `shared/regulations/<x>.md` | `slug, jurisdiction, authority, version, effective_from, effective_to, applies_to_industries[]` | `superseded_by` |
| `emission_factor` | `shared/emission_factors/<x>.md` | `slug, category, region, source, version, value, unit, effective_from` | `superseded_by` |
| `framework` | `shared/frameworks/<x>.md` | `slug, version, disclosures[], is_mandatory_in[]` | — |
| `peer_company` | `shared/peer_universe/<x>.md` | `slug, industry, country, latest_report_year, notable_practices[]` | `report_pdf_ref` |
| `source_doc` | `sourcedocs/<year>/<x>.md` | `slug, client_slug, doc_type, period, file_hash, ingest_date` | `pii_classification` |

對應 Pydantic（pseudocode，`entities.py`）：

```python
from typing import Literal, Optional
from pydantic import BaseModel, Field

EntityType = Literal[
    "client","report","chapter","topic","iro","stakeholder","engagement",
    "governance","action","target","kpi","datapoint","regulation",
    "emission_factor","framework","peer_company","source_doc",
]

class TopicFrontmatter(BaseModel):
    slug: str
    name: str
    axis: Literal["E","S","G"]
    impact_score: float = Field(ge=0, le=5)
    financial_score: float = Field(ge=0, le=5)
    materiality_tier: Literal["核心","重大","邊界"]
    industry_specificity: Optional[str] = None
    assessed_at: Optional[str] = None
    assessed_by: Optional[str] = None
    assessment_year: Optional[int] = None
    xbrl_concept: Optional[str] = None  # Q16 nullable

# 其他 16 個 entity 同樣套路，集中於 entities.py
ENTITY_SCHEMAS: dict[EntityType, type[BaseModel]] = {
    "topic": TopicFrontmatter,
    # ...
}
```

### 2.4 19 條 typed edges 註冊

對應 gbrain-survey §4.2，於 `edges.py`：

| edge_type | src_entity_type | dst_entity_type | semantics |
|-----------|----------------|-----------------|-----------|
| `has_report` | client | report | 顧客有報告 |
| `contains_chapter` | report | chapter | 報告含章節 |
| `discloses_topic` | chapter | topic | 章節揭露議題 |
| `topic_identified_by` | topic | stakeholder | 議題由議合識別出 |
| `topic_has_iro` | topic | iro | 議題拆分 I/R/O |
| `iro_addressed_by` | iro | action | IRO 由行動回應 |
| `action_tracks` | action | target | 行動追蹤目標 |
| `target_measures` | target | kpi | 目標衡量指標 |
| `kpi_reported_as` | kpi | datapoint | 指標年度數值 |
| `datapoint_derived_from` | datapoint | source_doc | 數值來源可追溯 |
| `datapoint_calculated_with` | datapoint | emission_factor | GHG 用 |
| `datapoint_restated_from` | datapoint | datapoint | 跨年重述 |
| `governance_oversees` | governance | topic | 治理督導議題 |
| `governance_reviews` | governance | target | 治理檢視目標 |
| `chapter_conforms_to` | chapter | framework | 章節對應框架 |
| `regulation_requires_disclosure_of` | regulation | topic | 法規要求揭露 |
| `stakeholder_engaged_via` | stakeholder | engagement | 議合事件 |
| `engagement_raised_topic` | engagement | topic | 議合提出議題 |
| `peer_benchmark_for` | peer_company | chapter | 同業參照 |

```python
EDGE_REGISTRY: dict[str, tuple[EntityType, EntityType, str]] = {
    "has_report": ("client", "report", "Client owns Report"),
    # ... 全 19 條
}

def validate_edge(src_type: EntityType, edge_type: str, dst_type: EntityType) -> None:
    spec = EDGE_REGISTRY.get(edge_type)
    if not spec:
        raise InvariantError(f"unknown edge_type: {edge_type}")
    if spec[0] != src_type or spec[1] != dst_type:
        raise InvariantError(
            f"edge {edge_type} expects {spec[0]} -> {spec[1]}, got {src_type} -> {dst_type}"
        )
```

`links.edge_type` 沒做成 SQL CHECK 是刻意：未來新增 edge 類型只需改 Python registry，不必 ALTER TABLE。

### 2.5 5 條連結性 invariants（fail-closed 實現）

對應 gbrain-survey §4.3。**Plan B 決議：schema-level 強制（CLAUDE.md §8）**。實作分兩層：

| # | Invariant | 實現層 | 機制 |
|---|-----------|--------|------|
| I1 | 任一 `topic.materiality_tier == 核心` 必須至少有 1 個 `action` 經 `iro_addressed_by` 鏈回 | **app-level lint** | 圖遍歷 SQL（見下），失敗→ `InvariantError` |
| I2 | 任一 `chapter` 必須 `chapter_conforms_to` ≥ 1 framework，且 `discloses_topic` ≥ 1 topic | **app-level lint** | COUNT(*) 查詢 |
| I3 | 任一 `target` frontmatter 必須有 `baseline_year, baseline_value, target_year, verification_path` | **schema-level** | `entity_attributes` insert trigger（見下） |
| I4 | 任一量化 `datapoint` 必須 ≥ 1 `datapoint_derived_from → source_doc` | **app-level lint** | 寫入時 trigger 檢查 links |
| I5 | 排放類 `datapoint` 必須 `datapoint_calculated_with` 一個 `effective_from ≤ year ≤ effective_to` 的 `emission_factor` | **app-level lint**（需 join + 日期比較） | Python validation |

DDL 增補（接續 `v001_init.sql`）：

```sql
-- --- 9. I3: target completeness（schema-level）-
-- 當 entity_type='target' 的 page 收到 entity_attributes insert/update 時
-- 用 view 計算 4 必備欄位是否齊全；不齊禁止 commit (透過 application 在 transaction 內查 view)
CREATE VIEW IF NOT EXISTS v_target_completeness AS
SELECT
    p.id AS page_id,
    p.slug,
    MAX(CASE WHEN a.key='baseline_year'      THEN 1 ELSE 0 END) AS has_baseline_year,
    MAX(CASE WHEN a.key='baseline_value'     THEN 1 ELSE 0 END) AS has_baseline_value,
    MAX(CASE WHEN a.key='target_year'        THEN 1 ELSE 0 END) AS has_target_year,
    MAX(CASE WHEN a.key='verification_path'  THEN 1 ELSE 0 END) AS has_verification_path
FROM pages p
LEFT JOIN entity_attributes a ON a.page_id = p.id
WHERE p.entity_type = 'target' AND p.deleted_at IS NULL
GROUP BY p.id;

-- --- 10. I1 helper view: core topic action coverage -
CREATE VIEW IF NOT EXISTS v_core_topic_action_coverage AS
SELECT
    t.id AS topic_id,
    t.slug AS topic_slug,
    COUNT(DISTINCT a_page.id) AS action_count
FROM pages t
LEFT JOIN entity_attributes ta ON ta.page_id = t.id AND ta.key = 'materiality_tier'
LEFT JOIN links l1 ON l1.src_page_id = t.id AND l1.edge_type = 'topic_has_iro'
LEFT JOIN pages iro_page ON iro_page.id = l1.dst_page_id
LEFT JOIN links l2 ON l2.src_page_id = iro_page.id AND l2.edge_type = 'iro_addressed_by'
LEFT JOIN pages a_page ON a_page.id = l2.dst_page_id AND a_page.entity_type = 'action'
WHERE t.entity_type = 'topic'
  AND ta.value = '核心'
  AND t.deleted_at IS NULL
GROUP BY t.id;

-- --- 11. I2 helper view: chapter completeness -
CREATE VIEW IF NOT EXISTS v_chapter_completeness AS
SELECT
    c.id AS chapter_id,
    c.slug,
    SUM(CASE WHEN l.edge_type = 'chapter_conforms_to' THEN 1 ELSE 0 END) AS framework_count,
    SUM(CASE WHEN l.edge_type = 'discloses_topic'     THEN 1 ELSE 0 END) AS topic_count
FROM pages c
LEFT JOIN links l ON l.src_page_id = c.id
WHERE c.entity_type = 'chapter' AND c.deleted_at IS NULL
GROUP BY c.id;
```

**Application-level lint pseudocode**（`brain/edges.py`）：

```python
class InvariantError(Exception): ...

def assert_i1_core_topic_coverage(conn) -> None:
    rows = conn.execute(
        "SELECT topic_slug FROM v_core_topic_action_coverage WHERE action_count = 0"
    ).fetchall()
    if rows:
        raise InvariantError(
            f"I1 violated: {len(rows)} 核心 topics have no Action via IRO chain: "
            f"{[r[0] for r in rows[:5]]}..."
        )

def assert_i3_target_completeness(conn) -> None:
    rows = conn.execute("""
        SELECT slug FROM v_target_completeness
        WHERE has_baseline_year=0 OR has_baseline_value=0
           OR has_target_year=0 OR has_verification_path=0
    """).fetchall()
    if rows:
        raise InvariantError(
            f"I3 violated (anti-greenwashing): {len(rows)} targets missing required fields"
        )
```

**何時跑**：每次 `BrainEngine.commit_phase(phase=3)` 或 `health_check()` MCP tool 觸發；snapshot 前 mandatory。失敗 → 不寫入 / 不 snapshot / MCP tool 回 error。

---

## 3. Hybrid Search 引擎

### 3.1 RRF（Reciprocal Rank Fusion）演算法

數學定義（Cormack et al., 2009）：對候選 doc d，給定多路 retrievers 各自 rank list，

```
score_RRF(d) = Σ_{retriever r}  1 / (k + rank_r(d))
```

其中 k 預設 60。**為什麼 60**：gbrain 採此值（gbrain-survey §1 直接抄）；學界共識區間 [10, 100]，60 是經驗甜點 — 既能拉開 top-3 與 top-10 差距，也不會讓 rank-50+ 的雜訊權重歸零過快。susr v0 沿用，未來在 Layer 4 fixture 上重測。

Pseudocode（`brain/search.py`）：

```python
from collections import defaultdict
from typing import Iterable

RRF_K = 60

def rrf_merge(
    rank_lists: list[list[int]],     # each inner list: page_ids ordered by relevance desc
    k: int = RRF_K,
) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion. Returns (page_id, score) sorted desc."""
    scores: dict[int, float] = defaultdict(float)
    for ranked in rank_lists:
        for rank, page_id in enumerate(ranked, start=1):
            scores[page_id] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
```

### 3.2 三路檢索流程

```python
def hybrid_search(
    conn: sqlite3.Connection,
    query: str,
    embed_provider: EmbeddingProvider,
    *,
    entity_types: list[EntityType] | None = None,
    project_slug: str | None = None,
    tenant_id: str | None = None,
    top_n_per_path: int = 50,
    top_k: int = 10,
) -> list[SearchHit]:
    # --- Path 1: vector KNN via sqlite-vec --------------------------
    qvec = embed_provider.embed_query(query)              # list[float], dim must match table
    where_clauses, params = _build_vec_where(entity_types, project_slug, tenant_id)
    vec_sql = f"""
        SELECT page_id, distance FROM vec_chunks
        WHERE embedding MATCH ?
          AND k = ?
          {where_clauses}
        ORDER BY distance
    """
    vec_hits = conn.execute(
        vec_sql,
        [serialize_float32(qvec), top_n_per_path, *params],
    ).fetchall()
    vec_ranked = _dedup_keep_first([row[0] for row in vec_hits])

    # --- Path 2: FTS5 BM25 ------------------------------------------
    fts_sql = """
        SELECT rowid, bm25(fts_pages) AS rank
        FROM fts_pages
        WHERE fts_pages MATCH ?
          AND (? IS NULL OR entity_type IN (SELECT value FROM json_each(?)))
          AND (? IS NULL OR project_slug = ?)
          AND (? IS NULL OR tenant_id = ?)
        ORDER BY rank
        LIMIT ?
    """
    fts_hits = conn.execute(
        fts_sql,
        [query,
         entity_types and 1, json.dumps(entity_types or []),
         project_slug, project_slug,
         tenant_id, tenant_id,
         top_n_per_path],
    ).fetchall()
    fts_ranked = [row[0] for row in fts_hits]

    # --- Path 3 (optional v0): structural / entity filter -----------
    # MVP: 不獨立給 rank list；entity_types filter 已在前兩路內生效
    # 預留：未來可加 "linked-from-current-topic" 結構性排序

    # --- Fuse with RRF ----------------------------------------------
    fused = rrf_merge([vec_ranked, fts_ranked])[:top_k]

    # --- Hydrate pages ----------------------------------------------
    page_ids = [pid for pid, _ in fused]
    rows = conn.execute(
        f"SELECT id, slug, entity_type, title, compiled_truth "
        f"FROM pages WHERE id IN ({','.join('?'*len(page_ids))})",
        page_ids,
    ).fetchall()
    by_id = {r[0]: r for r in rows}
    return [SearchHit(**by_id[pid], rrf_score=s) for pid, s in fused if pid in by_id]
```

**注意**：sqlite-vec 0.1.9 的 `vec0 WHERE` 支援 `=, !=, >, >=, <, <=` 但 partition key 比較限定 `=`（source: `https://alexgarcia.xyz/sqlite-vec/features/vec0.html`）。`entity_types` filter 走 partition key 提速 — 但若顧問要 multi-entity 跨類查詢，要拆成 N 次 query 再 RRF（v0.1.9 不支援 `IN (...)` on partition key）。

### 3.3 Reranker（v0 不做，留介面）

```python
class Reranker(Protocol):
    def rerank(self, query: str, hits: list[SearchHit], top_k: int) -> list[SearchHit]: ...

# v0 預設 NoOpReranker；未來接 Cohere rerank-3 / Voyage rerank-lite
```

---

## 4. page_versions + timeline 設計

### 4.1 page_versions snapshot

**何時建**（4 種觸發）：

1. **`manual`**：顧問在 Claude Desktop 對話請求「freeze 現在的 materiality matrix」
2. **`phase_complete`**：MCP tool 內每個 phase 收尾呼叫 `BrainEngine.snapshot(reason='phase_complete', context={'phase': 3})`
3. **`year_freeze`**：跨年 fork project 前對前一年所有 entities 強制 snapshot
4. **`restate`**：`DataPoint.value` 變動 > 5% 時自動觸發；同時寫 `timeline_entries(action_type='restate')`
5. **`assurance`**：第三方確信通過時鎖版

**snapshot 內容**：

```python
def snapshot_page(conn, page_id: int, reason: str, actor: str) -> int:
    cur = conn.execute("SELECT compiled_truth, source_hash FROM pages WHERE id=?", [page_id]).fetchone()
    frontmatter = _dump_frontmatter(conn, page_id)  # SELECT FROM entity_attributes
    last_version_no = conn.execute(
        "SELECT COALESCE(MAX(version_no),0) FROM page_versions WHERE page_id=?", [page_id]
    ).fetchone()[0]
    last_version_id = conn.execute(
        "SELECT id FROM page_versions WHERE page_id=? AND version_no=?", [page_id, last_version_no]
    ).fetchone()
    parent_id = last_version_id[0] if last_version_id else None

    new_id = conn.execute("""
        INSERT INTO page_versions
        (page_id, version_no, parent_version_id, content_hash,
         frontmatter_snap, compiled_truth_snap, snapshot_reason, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [page_id, last_version_no + 1, parent_id, cur[1],
          json.dumps(frontmatter), cur[0], reason, actor]).lastrowid
    return new_id
```

**restore**：snapshot only；revert by writing a new page row with the snap content（不直接 rewind table）。

### 4.2 timeline_entries — append-only 證據鏈

對應 ESG 反綠色洗白 + restatement 揭露機制（CLAUDE.md §6 reference + SKILL.md §「反綠色洗白」#5）。

**每筆 schema**：見 §2.2 表 5。`action_type` enum 涵蓋 8-Phase 全週期，**但 v0 MVP 只實際寫 ingest / verify / restate / iro_link**（後 3 種出現於 Phase 3）。

**Restatement alert pseudocode**：

```python
RESTATE_THRESHOLD = 0.05  # 5%, 對齊 SKILL.md Phase 4 規則 (MVP 預留邏輯，Phase 4 才主用)

def write_datapoint_value(conn, page_id: int, new_value: float, actor: str) -> None:
    old = conn.execute("""
        SELECT value FROM entity_attributes
        WHERE page_id=? AND key='value'
    """, [page_id]).fetchone()
    delta_pct = abs((new_value - float(old[0])) / float(old[0])) if old else 0.0

    conn.execute("UPDATE entity_attributes SET value=? WHERE page_id=? AND key='value'",
                 [str(new_value), page_id])

    if delta_pct > RESTATE_THRESHOLD:
        snapshot_page(conn, page_id, reason='restate', actor=actor)
        conn.execute("""
            INSERT INTO timeline_entries (page_id, action_type, actor, payload)
            VALUES (?, 'restate', ?, ?)
        """, [page_id, actor, json.dumps({
            'old_value': old[0], 'new_value': new_value, 'delta_pct': delta_pct
        })])
```

---

## 5. Embedding 抽象層 + Q7/Q8 收斂建議

### 5.1 EmbeddingProvider Protocol

`susr/embeddings/base.py`：

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class EmbeddingProvider(Protocol):
    @property
    def dimension(self) -> int: ...

    @property
    def name(self) -> str: ...                          # e.g. 'openai:text-embedding-3-large'

    @property
    def hosting(self) -> str: ...                       # 'cloud' | 'local'

    def embed_query(self, text: str) -> list[float]: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
```

### 5.2 內建 providers

| Provider class | name | dimension | hosting | install extra |
|----------------|------|-----------|---------|---------------|
| `OpenAIEmbeddingProvider` | `openai:text-embedding-3-large` | 1536（可降至 256） | cloud | `susr[embeddings-openai]` |
| `VoyageEmbeddingProvider` | `voyage:voyage-3` | 1024 | cloud | `susr[embeddings-voyage]` |
| `BgeM3EmbeddingProvider` | `bge:bge-m3` | 1024 | local | `susr[embeddings-bge]` |

**注意**：每個 provider 的 dimension 必須等於 `vec_chunks.embedding` declared dim。**切 provider = 重建 vec_chunks**。`susr workspace migrate-embeddings` MCP tool 未來補。

### 5.3 Q7 個資合約風險推薦解法

**問題**（gbrain-survey §8 #7）：顧問把客戶員工薪酬、勞檢、客訴等資料 ingest，embedding 送 OpenAI 是合約風險。

**推薦方案：client-level embedding policy + two-stage pipeline**

每個 client repo 的 `_client.md` frontmatter 標：

```yaml
embedding_policy: local      # local | cloud | twostage
pii_classification: high     # high | medium | low
```

| policy | 行為 |
|--------|------|
| `local` | 強制走 `BgeM3EmbeddingProvider`（顧問本機 GPU/CPU），不出機 |
| `cloud` | 走 `OpenAIEmbeddingProvider` / `VoyageEmbeddingProvider`，需顧問與客戶簽 DPA 同意 |
| `twostage` | source_doc / sourcedocs/ 路徑下走 local；其他（議題池 / 行動 / 章節敘事）走 cloud。**MVP 推薦預設**：高敏感原文留本地、合成 / 議題層上雲 |

**為何不在 LLM 也做類似切換**：v0 MVP 只一個 Anthropic provider；後續若加 local LLM（Ollama）再說。

### 5.4 Q8 中文 ESG retrieval 品質推薦解法

**問題**（gbrain-survey §8 #4）：OpenAI text-embedding-3-large 在中英混雜 ESG 術語（雙重重大性 / IRO / Scope 3 類別 11）的 retrieval 品質未測。

**推薦預設模型**：MVP 預設 `BgeM3EmbeddingProvider`（bge-m3, 1024d, local）。理由：

1. **中文 retrieval benchmark（C-MTEB）長期表現名列前茅**（社群多次驗證）
2. **完全本地**，預設避開 Q7 個資合約風險（顧問 onboarding 阻力最低）
3. **多語訓練**，中英 ESG 術語混雜表現比純英文模型穩
4. Apache 2.0 license，可商用

**代價**：需顧問機器 ≥ 8GB RAM、首次下載 ~2GB 模型；macOS Intel 無 GPU 慢。**fallback**：MVP 也 ship `OpenAIEmbeddingProvider`，顧問可在 `_client.md` 切。

**Layer 4 評測 fixture 規劃**（強制驗證義務，CLAUDE.md §6.1）：

- Fixture：力麗 5364 + `phase3-materiality.md` 28 議題 + 7 利害關係人 + 12 IRO
- 查詢集合：20 個典型顧問問題（雙語混雜 / 同義詞 / 縮寫 / 框架代碼）
- 評估指標：P@5、R@5、MRR、cross-provider 結果重疊率
- benchmark 三組：BGE-M3 vs OpenAI text-embedding-3-large vs Voyage voyage-3
- 預期結果：寫進 `docs/research/embeddings-bench-v0.md`（未來步驟）

---

## 6. MCP Server (susr-mcp)

### 6.1 啟動方式 + Claude Desktop config

`susr/mcp/server.py`：

```python
import asyncio
import typer
from mcp.server.fastmcp import FastMCP

# 來源：https://github.com/modelcontextprotocol/python-sdk
# v1.27.1 (2026-05-08), requires Python >=3.10
mcp = FastMCP("susr")

# 註冊各 tool 模組（裝飾器 side-effect）
from susr.mcp import tools_phase3, tools_workspace, tools_kb  # noqa: F401

cli = typer.Typer(help="susr MCP server")

@cli.command()
def serve() -> None:
    """Start the MCP server over stdio (default; used by Claude Desktop)."""
    mcp.run(transport="stdio")

@cli.command()
def doctor() -> None:
    """Health check — verify Python / sqlite-vec / DB writable / shared_kb present."""
    from susr.workspace import run_doctor
    raise SystemExit(0 if run_doctor() else 1)

# default: `susr-mcp` → serve
if __name__ == "__main__":
    cli()
```

Claude Desktop config 範例（macOS 路徑 `~/Library/Application Support/Claude/claude_desktop_config.json`，Windows 路徑 `%APPDATA%\Claude\claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "susr": {
      "command": "susr-mcp",
      "args": ["serve"],
      "env": {
        "SUSR_WORKSPACE_ROOT": "/Users/zhang/work",
        "ANTHROPIC_API_KEY": "sk-ant-...",
        "SUSR_EMBEDDING_PROVIDER": "bge:bge-m3"
      }
    }
  }
}
```

來源：mcp Python SDK README — `mcp.run(transport="stdio")` 是 FastMCP 啟動 stdio 服務的標準寫法。

### 6.2 Phase 3 對應 tools

`susr/mcp/tools_phase3.py`，全部用 `@mcp.tool()` 註冊；參數以 Pydantic-friendly type hint 寫死讓 SDK 自動生成 JSON schema（mcp SDK 1.27 要求）。

```python
from pydantic import BaseModel, Field
from typing import Literal

# --- Tool 1: search_topics_universe ----------------------------
class TopicCandidate(BaseModel):
    slug: str
    name: str
    axis: Literal["E","S","G"]
    industry_specificity: str | None
    source_kb: Literal["shared","client"]

@mcp.tool()
def search_topics_universe(
    industry: str,                          # e.g. 'hotel' / 'textile'
    framework: Literal["GRI","ISSB","ESRS","TW_FSC","SASB"] = "GRI",
    client_slug: str | None = None,
    top_k: int = 40,
) -> list[TopicCandidate]:
    """
    從 shared_kb/industry-packs/<industry>.md + framework 標準議題庫 + client.entities/topics/*
    三方合併，回 candidate list 給顧問挑。Phase 3 第一步。
    """
    ...

# --- Tool 2: score_topic_dual_axis -----------------------------
class ImpactScores(BaseModel):
    severity: float = Field(ge=1, le=5)
    scope: float = Field(ge=1, le=5)
    irreversibility: float = Field(ge=1, le=5)
    likelihood: float = Field(ge=1, le=5)

class FinancialScores(BaseModel):
    magnitude: float = Field(ge=1, le=5)
    time_horizon: Literal["S","M","L"]
    probability: float = Field(ge=1, le=5)

class TopicScoreResult(BaseModel):
    topic_slug: str
    impact_score: float
    financial_score: float
    materiality_tier: Literal["核心","重大","邊界"]
    page_file: str
    timeline_entry_id: int

@mcp.tool()
def score_topic_dual_axis(
    client_slug: str,
    topic_slug: str,
    impact: ImpactScores,
    financial: FinancialScores,
    actor: str,                             # e.g. 'consultant:zhang'
    rationale: str | None = None,
) -> TopicScoreResult:
    """
    對單一 topic 寫雙軸評分，自動 normalize 到 1-5，
    依 §4 表 (impact ≥ 4 且 financial ≥ 4 = 核心；任一 ≥ 3.5 = 重大；else 邊界) 決定 tier，
    更新 entities/topics/<topic_slug>.md frontmatter，
    寫 timeline_entries(action_type='verify', payload={raw_scores}).
    """
    ...

# --- Tool 3: generate_materiality_matrix -----------------------
class MaterialityMatrix(BaseModel):
    matrix_md_path: str                     # path to materiality-YYYY.md
    matrix_svg_path: str                    # SVG 5x5 grid
    core_topics: list[str]
    material_topics: list[str]
    border_topics: list[str]
    invariants_passed: bool
    invariant_violations: list[str]

@mcp.tool()
def generate_materiality_matrix(
    client_slug: str,
    year: int,
    include_svg: bool = True,
) -> MaterialityMatrix:
    """
    讀 entities/topics/*.md 所有評分過的 topic，
    產 projects/YYYY-sr/materiality-YYYY.md（仿 examples/lealea-5364/phase3-materiality.md §5 結構）+ SVG matrix，
    跑 I1/I2 invariants check（核心 topic 須有 action chain），
    寫 page_versions snapshot reason='phase_complete'.
    """
    ...

# --- Tool 4: stakeholder_engagement_helper ---------------------
class EngagementRecord(BaseModel):
    engagement_slug: str
    page_file: str
    topics_raised: list[str]
    timeline_entry_id: int

@mcp.tool()
def stakeholder_engagement_helper(
    client_slug: str,
    stakeholder_slug: str,
    method: Literal["問卷","訪談","焦點","說明會"],
    date: str,                              # ISO 8601
    sample_size: int | None,
    topics_raised: list[str],               # topic_slugs
    findings_summary: str,
    evidence_refs: list[str] = [],
    actor: str = "consultant",
) -> EngagementRecord:
    """
    建立一筆 engagement page（entities/stakeholders/<x>/engagements/<date>.md）；
    自動建 stakeholder_engaged_via 與 engagement_raised_topic 兩條 link；
    每個 topic_raised 自動補 topic_identified_by edge 回該 stakeholder.
    """
    ...
```

### 6.3 Workspace ops

`susr/mcp/tools_workspace.py`：

```python
@mcp.tool()
def create_client_workspace(
    name: str,                              # slug, lowercase-dash
    legal_name: str,
    industry: str,                          # 對應 shared_kb/industry-packs/<industry>.md
    standards: list[str],                   # ['GRI 2021','ISSB S1','TW_FSC']
    boundary: Literal["合併","營運控制","股權法"],
    reporting_period: str,                  # e.g. '2025-01-01..2025-12-31'
    embedding_policy: Literal["local","cloud","twostage"] = "twostage",
    pii_classification: Literal["high","medium","low"] = "medium",
) -> dict:
    """
    在 SUSR_WORKSPACE_ROOT/<name>/ 建：
      - git init
      - _client.md (帶 frontmatter)
      - entities/{topics,stakeholders,governance,kpis,targets}/.gitkeep
      - projects/, sourcedocs/
      - .susr/db.sqlite (run DDL v001_init.sql)
      - shared/  (snapshot copy from packages/susr/susr/shared_kb/)
    回 workspace path + 初始 git commit hash.
    """
    ...

@mcp.tool()
def health_check(client_slug: str | None = None) -> dict:
    """
    1. 確認 sqlite-vec extension 載得起來
    2. 若給 client_slug：跑 schema_version、所有 invariants、shared/ snapshot vs package 版本對比
    3. ANTHROPIC_API_KEY 是否存在
    4. embedding provider 是否可實例化
    Returns: {ok: bool, checks: [...], remediation: [...]}
    """
    ...

@mcp.tool()
def update_shared_kb(
    client_slug: str,
    accept_changes: bool = False,
) -> dict:
    """
    比對 client repo shared/ vs susr package 內 shared_kb/。
    accept_changes=False → 回 diff（讓顧問先看）。
    accept_changes=True  → snapshot copy；client repo git add + commit message 'chore: bump shared_kb to vX.Y.Z'。
    """
    ...

@mcp.tool()
def promote_to_consultant_kb(
    client_slug: str,
    client_page_slugs: list[str],           # 要提煉的 pages
    anonymize_strategy: Literal["redact-pii","generalize-numbers","both"],
    target_kb_path: str,                    # consultant-kb repo path
    reviewer: str,
    confirm_token: str,                     # 由 CLI/Claude 第二輪 prompt 取得，防誤觸
) -> dict:
    """
    單向闘的「跨闘」工具（CLAUDE.md §8 'KB 信息流')。
    1. 強制要求 confirm_token (顧問必須先呼叫 dry_run 再帶回)
    2. anonymize 後寫到 consultant-kb repo
    3. 同時在 client repo 寫 timeline_entries(action_type='comment', payload={promoted_to_kb, anonymize_strategy, reviewer})
    4. 在 consultant-kb 寫 timeline_entries(action_type='ingest', payload={source_client, anonymize_strategy})
    回 audit log entry.
    """
    ...
```

### 6.4 `read_consultant_kb`（open scope，client 可讀）

`susr/mcp/tools_kb.py`：

```python
@mcp.tool()
def read_consultant_kb(
    query: str,
    framework_filter: list[str] | None = None,
    top_k: int = 10,
) -> list[dict]:
    """
    在 consultant-kb 內跑 hybrid search。
    讀-only；不會回 client 私有資料（consultant-kb 已 anonymize）.
    """
    ...
```

### 6.5 LLMProvider 抽象層

`susr/llm/base.py` — 對應 CLAUDE.md §8 決策 5（即使初期只接 Anthropic 也要 day-1 抽象）：

```python
from typing import Protocol, AsyncIterator, runtime_checkable
from pydantic import BaseModel

class Message(BaseModel):
    role: Literal["user","assistant","system"]
    content: str

class ToolCall(BaseModel):
    name: str
    arguments: dict

class CompletionResult(BaseModel):
    text: str
    tool_calls: list[ToolCall] = []
    usage: dict = {}

@runtime_checkable
class LLMProvider(Protocol):
    @property
    def name(self) -> str: ...

    async def complete(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> CompletionResult: ...

    async def stream(
        self,
        messages: list[Message],
        **kwargs,
    ) -> AsyncIterator[str]: ...
```

`AnthropicProvider` 預設實作；`OpenAIProvider` / `GeminiProvider` 預留 stub 不實作（YAGNI，但 import 結構鋪好）。

**為 Q5 Phase B multi-agent CLI 鋪路**：未來 Claude Code / Cursor / Windsurf 對接 susr 時，只要實作 `LLMProvider` 即可換 host；MCP tools 本身與 LLM 解耦（因為 MCP 是 protocol 不是 SDK）。

---

## 7. 力麗 5364 → Option C 結構移轉草案

**spec only — 不實際移檔**。本節給對照表讓未來 implementation step 可照表執行。

| 現有檔案（`examples/lealea-5364/`） | 新位置（per-client repo Option C） | entity_type | 動作 |
|------|------|------|------|
| `_client.md` | `_client.md` | client | 移動 + 加 `embedding_policy: twostage` frontmatter |
| `phase1-scoping.md` | `projects/2025-sustainability-report/scoping.md` | （非 entity，純 markdown） | 移動 |
| `phase2-research-log.md` | `projects/2025-sustainability-report/research-log.md` | （非 entity） | 移動 |
| `phase3-materiality.md` §3 議題池 28 項 | `entities/topics/E1.md` ... `entities/topics/G6.md` | topic (×28) | **拆**成 28 個 file；每個取 §3 表格欄位填 frontmatter；§4 評分填 `impact_score / financial_score / materiality_tier` |
| `phase3-materiality.md` §1 利害關係人 7 類 | `entities/stakeholders/客戶.md` ... `entities/stakeholders/媒體NGO.md` | stakeholder (×7) | 拆成 7 file |
| `phase3-materiality.md` §2 議合方法表 | `entities/stakeholders/<x>/engagements/2025-XX.md` | engagement (多筆 per stakeholder) | 拆 — e.g. 客戶有滿意度問卷 + 訪談 + OTA 評論 = 3 個 engagement file |
| `phase3-materiality.md` §5 矩陣 + §6 IRO 對應 | `projects/2025-sustainability-report/materiality-2025.md` | （彙整文件，非單一 entity） | 移動 + 重生成（由 `generate_materiality_matrix` MCP tool 跑） |
| `phase3-materiality.md` §6 IRO 對應表（12 行） | `entities/topics/<topic>/iro/<id>.md` | iro (×12) | 拆 |
| `phase4-xlsx-skeleton.md` | `projects/2025-sustainability-report/datapoints/` skeleton（暫不解析，留 reference） | — | **MVP 不處理**（Phase 4 不在範圍） |
| `phase5-*.md` 章節骨架 | `projects/2025-sustainability-report/chapters/` | chapter | **MVP 不處理** |
| 其餘 phase 檔 | `projects/2025-sustainability-report/` 對應檔名 | — | MVP 不處理 |

**邊界**：MVP v0.1 重排內容上限 = §3 議題池 + §1 stakeholder + §2 engagement + §6 IRO（這 4 段對應 Phase 3 工作流；夠跑完 MVP 端到端）。其他段保持 markdown 原貌即可，不必入 brain DB。

---

## 8. 測試骨架（Layer 3 + Layer 4）

對齊 CLAUDE.md §6.2 五層結構。Layer 1 + Layer 2 已 bootstrap（repo-level `tests/`），本節新增 packages 內部 Layer 3 + Layer 4。

### 8.1 Layer 3 領域 invariants（`packages/susr/tests/test_invariants.py`）

```python
import pytest
from susr.brain.engine import BrainEngine
from susr.brain.edges import (
    InvariantError,
    assert_i1_core_topic_coverage,
    assert_i2_chapter_completeness,
    assert_i3_target_completeness,
    assert_i4_datapoint_source,
    assert_i5_emission_factor_validity,
)

# ---- I1 ---------------------------------------
def test_i1_core_topic_without_action_fails(tmp_brain):
    tmp_brain.put_page("topics/E1", entity_type="topic", frontmatter={
        "slug":"E1","name":"氣候變遷","axis":"E",
        "impact_score":4.5,"financial_score":4.0,"materiality_tier":"核心",
        "industry_specificity":"hotel"
    })
    # 沒建 IRO / Action chain
    with pytest.raises(InvariantError, match="I1 violated"):
        assert_i1_core_topic_coverage(tmp_brain.conn)

def test_i1_core_topic_with_full_chain_passes(tmp_brain):
    tmp_brain.put_page("topics/E1", ...)
    tmp_brain.put_page("iros/E1-impact-emissions", entity_type="iro", ...)
    tmp_brain.put_page("actions/2025-energy-reduction", entity_type="action", ...)
    tmp_brain.link("topics/E1", "topic_has_iro", "iros/E1-impact-emissions")
    tmp_brain.link("iros/E1-impact-emissions", "iro_addressed_by", "actions/2025-energy-reduction")
    assert_i1_core_topic_coverage(tmp_brain.conn)  # no raise

# ---- I2 / I3 / I4 / I5 同樣 parametrize -------
@pytest.mark.parametrize("missing_field", [
    "baseline_year","baseline_value","target_year","verification_path",
])
def test_i3_target_missing_field_fails(tmp_brain, missing_field):
    fm = {"slug":"t1","baseline_year":2020,"baseline_value":100,
          "target_year":2030,"verification_path":"SBTi"}
    fm.pop(missing_field)
    tmp_brain.put_page("targets/t1", entity_type="target", frontmatter=fm)
    with pytest.raises(InvariantError, match="I3 violated"):
        assert_i3_target_completeness(tmp_brain.conn)
```

Fixture（`conftest.py`）：

```python
@pytest.fixture
def tmp_brain(tmp_path):
    db_path = tmp_path / "test.sqlite"
    from susr.brain.engine import BrainEngine
    engine = BrainEngine.create_new(str(db_path), tenant_id=None)
    yield engine
    engine.close()
```

### 8.2 Layer 4 引擎單元

```python
# test_schema.py
def test_ddl_loads_clean(tmp_path):
    """DDL v001_init.sql 在乾淨 SQLite 跑無 error；schema_version=1."""
    ...

# test_search_rrf.py
def test_rrf_math_known_inputs():
    """已知 input → 已知 output；對 [[1,2,3],[3,2,1]] 應該 fuse 出 2 最高."""
    from susr.brain.search import rrf_merge
    result = rrf_merge([[1,2,3],[3,2,1]], k=60)
    # rank1 of list1 + rank3 of list2: 1/(60+1) + 1/(60+3) = 0.0164+0.0159 = 0.0322
    # rank2 of both: 2*(1/62) = 0.0323
    # rank3 of list1 + rank1 of list2: 1/63 + 1/61 = 0.0159+0.0164 = 0.0322
    page_ids_sorted = [pid for pid, _ in result]
    assert page_ids_sorted[0] == 2  # 中位 doc rank 最一致 → 最高
    assert set(page_ids_sorted) == {1,2,3}

def test_rrf_empty_lists():
    assert rrf_merge([]) == []

def test_hybrid_search_returns_topk(tmp_brain_with_fixtures):
    hits = tmp_brain_with_fixtures.search(query="氣候變遷", top_k=5)
    assert len(hits) <= 5
    assert all(h.rrf_score > 0 for h in hits)

# test_versions.py
def test_snapshot_creates_version_no_monotonic(tmp_brain):
    pid = tmp_brain.put_page("topics/E1", ...)
    v1 = tmp_brain.snapshot(pid, reason='manual', actor='test')
    v2 = tmp_brain.snapshot(pid, reason='phase_complete', actor='test')
    assert tmp_brain.get_version(v1).version_no == 1
    assert tmp_brain.get_version(v2).version_no == 2
    assert tmp_brain.get_version(v2).parent_version_id == v1

def test_snapshot_restore_roundtrip(tmp_brain):
    pid = tmp_brain.put_page("topics/E1", compiled_truth="version-A")
    v1 = tmp_brain.snapshot(pid, ...)
    tmp_brain.update_page(pid, compiled_truth="version-B")
    snap = tmp_brain.get_version(v1)
    assert snap.compiled_truth_snap == "version-A"

# test_timeline.py
def test_timeline_append_only(tmp_brain):
    pid = tmp_brain.put_page(...)
    eid = tmp_brain.write_timeline(pid, action_type='ingest', actor='test')
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        tmp_brain.conn.execute("UPDATE timeline_entries SET actor='x' WHERE id=?", [eid])
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        tmp_brain.conn.execute("DELETE FROM timeline_entries WHERE id=?", [eid])

def test_restate_threshold_triggers_alert(tmp_brain):
    # value: 100 → 110 (10% > 5%) 應觸發 timeline restate entry + snapshot
    pid = tmp_brain.put_page("datapoints/scope1-2024", ...)
    tmp_brain.write_datapoint_value(pid, new_value=110, actor='test')
    entries = tmp_brain.timeline_for_page(pid)
    assert any(e.action_type == 'restate' for e in entries)

# test_mcp_handlers.py
def test_score_topic_dual_axis_validates_input():
    from susr.mcp.tools_phase3 import ImpactScores
    with pytest.raises(ValueError):  # pydantic
        ImpactScores(severity=6, scope=1, irreversibility=1, likelihood=1)

# test_embeddings.py
def test_provider_conforms_to_protocol():
    from susr.embeddings.base import EmbeddingProvider
    from susr.embeddings.openai_provider import OpenAIEmbeddingProvider
    assert isinstance(OpenAIEmbeddingProvider, type)
    # @runtime_checkable Protocol：instance check
    provider = OpenAIEmbeddingProvider(api_key="dummy")
    assert isinstance(provider, EmbeddingProvider)
    assert provider.dimension == 1536
```

### 8.3 與 CLAUDE.md §6.1 hard rule 對應

| 宣稱 feature | 對應測試 |
|--------------|----------|
| `score_topic_dual_axis` MCP tool | `test_mcp_handlers::test_score_topic_dual_axis_validates_input` + scenario test in repo-level `tests/scenarios/test_lealea_5364.py` |
| RRF hybrid search | `test_search_rrf` 三項 |
| page_versions snapshot | `test_versions` 兩項 |
| timeline append-only | `test_timeline::test_timeline_append_only` |
| 5 條連結性 invariants | `test_invariants` 各條 parametrize |
| embedding provider 抽象 | `test_embeddings::test_provider_conforms_to_protocol` |
| `create_client_workspace` | `test_mcp_handlers::test_create_workspace_dry_run`（pseudocode 階段標 TODO） |

---

## 9. 顧問安裝 happy path

完整步驟（以 macOS 為例；Windows 路徑差別已標）：

```bash
# 1. 確認 Python 3.11+（macOS 內建 Python 不行，因為缺 extension load 能力）
brew install python@3.11       # macOS
# Windows: 從 python.org installer 安裝 3.11

# 2. 安裝 susr（含預設 local embedding 模型）
pip install "susr[embeddings-bge]"

# 3. 第一次健康檢查（唯一需要 shell 的步驟）
susr-mcp doctor
# 輸出：
#   ✓ Python 3.11.10
#   ✓ sqlite-vec 0.1.9 loaded
#   ✓ shared_kb present (5 industry packs, 8 references)
#   ✓ AnthropicProvider configured (ANTHROPIC_API_KEY found)
#   ✓ Default embedding: bge:bge-m3 (local, 1024d)
#   ! No client workspaces yet — create one via Claude Desktop chat
# 若任一 ✗：輸出 remediation 指令

# 4. 設定 Claude Desktop config（一次性）
# macOS:   ~/Library/Application\ Support/Claude/claude_desktop_config.json
# Windows: %APPDATA%\Claude\claude_desktop_config.json
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json <<'JSON'
{
  "mcpServers": {
    "susr": {
      "command": "susr-mcp",
      "args": ["serve"],
      "env": {
        "SUSR_WORKSPACE_ROOT": "/Users/zhang/work",
        "ANTHROPIC_API_KEY": "sk-ant-...",
        "SUSR_EMBEDDING_PROVIDER": "bge:bge-m3"
      }
    }
  }
}
JSON

# 5. 重啟 Claude Desktop
```

之後完全在 Claude Desktop 聊天視窗內：

```
顧問：幫我建一個叫 lealea-5364 的 client，旅館業，台灣上市櫃，
      合併報表邊界，報告期間 2025 年度。

Claude：[呼叫 create_client_workspace MCP tool]
       已建立 workspace：/Users/zhang/work/lealea-5364
       - git initialized
       - SQLite brain: .susr/db.sqlite (schema v1)
       - shared/ snapshot copied (5 industry packs)
       - _client.md 已寫入 (embedding_policy: twostage)
       下一步建議：上傳 Phase 1 scoping 決策 或 直接進入 Phase 3 重大性評估。

顧問：直接進 Phase 3，先拉旅館業議題池來看。

Claude：[呼叫 search_topics_universe(industry='hotel', framework='GRI')]
       共 28 個 candidates（環境 8 / 社會 14 / 治理 6）...
       [列出 28 項]
       要先做利害關係人議合，還是直接對所有 topic 預評分？

顧問：先記一筆 2025 員工問卷議合，N=254 全員，方法是問卷，
      raised topics 是 S1/S2/S3/S4/S5。findings：流動率高、夜班疲勞訴求多。

Claude：[呼叫 stakeholder_engagement_helper(...)]
       已建：entities/stakeholders/員工/engagements/2025-03-employee-survey.md
       自動建 6 條 edges...

顧問：對 E1 評分 — impact 嚴重度 5、範圍 4、不可逆性 4、可能性 5；
      financial 規模 4、時間 L、機率 4。

Claude：[呼叫 score_topic_dual_axis(...)]
       Impact = 4.5, Financial = 4.0, 列為「核心重大議題」
       已更新 entities/topics/E1.md，timeline 已留紀錄。

...（重複幾輪）

顧問：產出 2025 年度的 materiality matrix。

Claude：[呼叫 generate_materiality_matrix(client_slug='lealea-5364', year=2025)]
       ⚠ I1 invariant: E1, E2, S6 為核心議題但尚無 action chain
       Matrix 已寫到 projects/2025-sustainability-report/materiality-2025.md
       SVG 已生：projects/2025-sustainability-report/materiality-2025.svg
       要先補 IRO 與行動，還是先 freeze 矩陣作為 v1？
```

成功指標（MVP v0.1）：上述對話流程在真實 Claude Desktop 內可跑完；產出檔案與 `examples/lealea-5364/phase3-materiality.md` 內容對齊度 > 80%；通過 Layer 2 scenario test。

---

## 10. 風險與未解

### 10.1 Library / 平台

1. **sqlite-vec 0.1.9 仍是 pre-v1**（README 明示 breaking change 可能）。鎖 `>=0.1.9,<0.2`，每次 minor 升要回歸測試全 KNN 行為。
2. **sqlite-vec wheel 平台覆蓋**：PyPI 列 Windows x86-64 / macOS x86-64 + ARM64 / Linux x86-64 + ARM64。**macOS Apple Silicon + Python 3.11 wheel 已就緒**，但 Windows ARM64 顧問機（Surface 系列）目前**無 wheel**，需 fallback 提示。
3. **macOS 內建 Python 不能 enable_load_extension**：必須走 Homebrew 或 python.org installer。`susr-mcp doctor` 第一項就要檢測 `hasattr(sqlite3.Connection, 'enable_load_extension')` 並給明確 remediation。
4. **FTS5 trigram tokenizer 對中文檢索品質**：trigram 不分詞，純字元 3-gram；對「雙重重大性」這類複合詞會切成 13 個 trigram。Recall 強但 precision 弱（會 match 部分子字串）。預期 RRF 後 vector path 補回 precision；**但這假設未經實測**，需 Layer 4 fixture 跑出來看。如果不行，fallback 是自編譯 jieba SQLite tokenizer（大幅增加 install 複雜度）— 不建議走，先把 reranker 接上看能否補。
5. **mcp Python SDK v1 → v2 過渡**：README 提到 v2 在 pre-alpha；我們鎖 `>=1.27,<2.0`，v2 出來再評估遷移成本。

### 10.2 Embedding 策略不確定性（Q7 / Q8 推薦的弱點）

- **BGE-M3 在台灣本土 ESG 術語（金管會用詞 / 行業特化）的 retrieval 品質完全未測**。推薦這個是因為它是「中文 retrieval 領域當前最知名的 open 模型」+ local-first 解 Q7 個資 — 但兩條理由都是「先驗推測」，不是「實測證據」。**強烈建議 MVP 完成前先跑 §5.4 的 benchmark fixture**；如果結果 BGE-M3 明顯輸 OpenAI，可能要把預設改回 OpenAI 並把 Q7 個資合約風險用「合約 + DPA」而非「技術隔離」解。
- **`embedding_policy: twostage`** 邊界定義模糊：sourcedocs/ 走 local 很明確，但 chapter narrative 走 cloud — 章節敘事可能引用敏感數字，仍是合約灰色。需要 client onboarding 時逐欄位 walkthrough。
- **切 provider = 重建 vec_chunks** 是大手術（要 re-embed 所有 chunks）。`susr workspace migrate-embeddings` tool 還沒設計；MVP 先寫成警告，不提供無痛遷移路徑。

### 10.3 設計風險

6. **LLMProvider 抽象層 day-1 是否過度設計（YAGNI vs day-1 紀律 tension）**：CLAUDE.md §8 決策 5 明確要求 day-1 抽象。我寫的 Protocol 很薄（complete + stream），但 Anthropic 的 tool use / extended thinking / interleaved thinking 等高階特性如果硬塞進 `kwargs` 會破壞抽象意義。風險是「day-1 抽象只是把 Anthropic SDK call 包一層」實際沒帶來換 host 自由度。**建議**：在第一個 prompt 寫完後重新審視這層，若發現 90% 邏輯耦合 Anthropic 特性，要嘛深化抽象（多包 Provider-specific config 物件），要嘛承認暫時妥協但加 TODO 提醒。
7. **每個 client 獨立 SQLite 的「跨 client 學習」工作流缺失**：CLAUDE.md §8 Q9 仍標「跨 client 查詢透過 `.susr/` index DB 聯邦」，但本 spec 沒設計 `.susr/index.sqlite` 這條 federated 路徑；MVP 只做 per-client 隔離。若顧問問「我去年怎麼寫紡織業？」要走 `read_consultant_kb`（已 anonymize）— 但這要求顧問先把上一單 client 的洞見 promote 到 KB。**這是 manual workflow，沒有自動 cross-client search**。需在 MVP 完成後評估是否要做 federated index。
8. **invariants 何時跑：write-time vs commit-time vs phase-complete**：本 spec 採 `phase_complete` 為 mandatory 檢查點，但顧問日常編 markdown 時可能想看「即時 lint」。MVP 不做 file watcher；fallback 是顧問用 `health_check` MCP tool 手動跑。需在 v0.2 評估加 `pre-commit` hook 或 LSP-style 即時驗證。
9. **RRF k=60 沒實測**：直接抄 gbrain；對 susr 的 corpus（更小、更同質、中文）是否最佳未知。Layer 4 fixture 跑出來如果 P@5 < 50% 要重調。
10. **Per-client repo 的 `.susr/db.sqlite` 不入 git**：spec 已在 `.gitignore` 隱含（DB 是 derived from markdown）。但**首次 ingest 成本不便宜**（embed + index），如果顧問換機器要 re-ingest。需在 `create_client_workspace` 文件提示，或加 `susr-mcp rebuild-index` tool。

### 10.4 商業 / 法規

11. **iXBRL 預留欄位**（`xbrl_concept` nullable）對齊 CLAUDE.md §8 Q16 — 但 spec 只在 `kpis` / `datapoints` / `pages` 加。若金管會 2028 要求其他層級（topics / chapters）也標 concept，未來要再 ALTER TABLE。可接受，因為是 nullable。
12. **`promote_to_consultant_kb` 的 anonymize 強度**：spec 給三個策略名（redact-pii / generalize-numbers / both）但沒定義具體規則。MVP 要嘛接成熟 library（presidio？）要嘛先讓顧問手動 redact + tool 只做 file move。**建議後者**，避免假裝有自動匿名能力。

---

## Appendix A — 所用外部資源

| # | 資源 | URL | 引用段落 | 版本鎖定建議 |
|---|------|-----|----------|---------------|
| 1 | sqlite-vec GitHub README | `https://github.com/asg017/sqlite-vec/blob/main/README.md` | §2.1, §2.2 | — |
| 2 | sqlite-vec Python guide | `https://alexgarcia.xyz/sqlite-vec/python.html` | §2.1 PRAGMA + `sqlite_vec.load` call, §3.2 `serialize_float32` | — |
| 3 | sqlite-vec vec0 feature docs | `https://alexgarcia.xyz/sqlite-vec/features/vec0.html` | §2.2 (partition key / aux col / WHERE operator constraints), §3.2 注意事項 | — |
| 4 | sqlite-vec PyPI page | `https://pypi.org/project/sqlite-vec/` | §1.3 version pin | **>=0.1.9,<0.2**（latest 2026-03-31；pre-v1 breaking change 風險） |
| 5 | mcp Python SDK GitHub | `https://github.com/modelcontextprotocol/python-sdk` | §6.1 FastMCP / stdio_server / @mcp.tool() 用法 | — |
| 6 | mcp PyPI page | `https://pypi.org/project/mcp/` | §1.3 version pin | **>=1.27,<2.0**（latest 2026-05-08；v2 pre-alpha 中） |
| 7 | uv workspaces 官方 docs | `https://docs.astral.sh/uv/concepts/projects/workspaces/` | §1.2 mono-repo root pyproject 寫法 | uv 任何 2025+ 版本（workspace 已是 stable feature） |
| 8 | SQLite FTS5 official | `https://www.sqlite.org/fts5.html` | §2.2 trigram tokenizer 選擇 + bm25() 用法 | 內建 SQLite 3.41+ 即可 |
| 9 | Cormack et al. (2009) Reciprocal Rank Fusion | 學界 paper | §3.1 RRF 公式 + k=60 經驗區間 | — |
| 10 | gbrain repo (Plan B 參考設計來源) | `https://github.com/garrytan/gbrain` | 全文（compiled_truth / timeline / page_versions / hybrid search 概念） | — |
| 11 | penfieldlabs gbrain 批判 | `https://dev.to/penfieldlabs/...` | CLAUDE.md §6 / §10 risk #6 警示來源 | — |

**Freshness check 提醒**：上述所有 URL 內容於 2026-05-25 snapshot；正式 implementation 開工前建議重跑一次 WebFetch 確認 sqlite-vec / mcp SDK 是否有 breaking change。

---

**End of Spec — 6,900 字 + 15 個 code/DDL blocks**
