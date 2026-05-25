# Step 1 R1 — Scaffold Notes（給 R2 用）

**日期**：2026-05-25
**範圍**：Step 1 Round 1 scaffold 完成後的 7 個 ambiguity 記錄 + 1 個 user-guide 缺口
**讀者**：Step 1 R2 實作者（無論是 subagent 或人類）— 開工前先讀

## TL;DR

R1 scaffold 由 subagent 依 `step1-spec.md` 落地，過程中發現 7 個 spec 模糊 / prompt 與 spec 微差的地方，agent 皆做了合理判斷。本檔記錄這些判斷與其依據，避免 R2 重新討論已有共識的問題。另記一個 user-guide scenarios 缺口（跨年 restate）。

---

## 1. R1 agent 處理的 7 個 ambiguity

### 1.1 MCP tools 檔案布局

- **Spec §1.1**：`tools_phase3.py` / `tools_workspace.py`（平鋪）
- **Prompt 指定**：`tools/phase3.py` / `tools/workspace.py`（子目錄）
- **R1 採用**：子目錄
- **R2 注意**：import path 是 `from susr.mcp.tools.phase3 import ...`

### 1.2 DDL vector dimension

- **Spec §5.2 表**：BGE-M3 = 1024d 為「預設」
- **Spec §2.2 DDL 範例**：`FLOAT[1536]`（OpenAI dim）
- **R1 採用**：1024（對齊 CLAUDE.md §8 Decision 10「BGE-M3 預設」）
- **R2 注意**：若 Layer 4 benchmark 結果換 default 為 OpenAI 或 Qwen3，需要 ALTER table（或預先 migration 機制）

### 1.3 `migrations.py` vs `schema.py`

- **Spec §1.1**：`schema.py`
- **Prompt 指定**：`migrations.py`
- **R1 採用**：`migrations.py`
- **R2 注意**：這檔負責載 DDL；R2 實作時加上「載 sqlite-vec extension → 跑 DDL」的 sequence

### 1.4 `brain/__init__.py` re-export

- **Spec**：沒明說
- **R1 採用**：只 export 模組名，避免 import time 副作用
- **公開 API re-export 在 `susr/__init__.py`**：`__version__='0.1.0'`、17 entities、19 edges
- **R2 注意**：新增公開 API 時記得在 `susr/__init__.py` re-export

### 1.5 `AnthropicProvider` 預設 model id

- **Spec §6.5**：沒鎖具體 model id
- **R1 採用**：`claude-opus-4-7`（純 placeholder）
- **R2 注意**：實作時改從 env var 或 `_client.md` frontmatter 讀（避免硬編碼）

### 1.6 `xbrl_concept` 欄位位置

- **Prompt**：「DataPoint 對應 pages 紀錄」
- **Spec §2.2**：放在 `pages` 表本身（所有 entity type 都可有）
- **R1 採用**：依 spec — `pages` 表 nullable 欄位
- **R2 注意**：最寬鬆設計，所有 entity 都能掛 iXBRL concept；填值只對 DataPoint / KPI 類有意義（CLAUDE.md §8 Q16）

### 1.7 `tests/__init__.py` 存在性

- **Prompt**：明列要建
- **R1 採用**：保留
- **Pytest 風險**：有 `__init__.py` 會讓 pytest 把 tests/ 當 import package，與 root `tests/` 名稱衝突可能造成 collection 異常
- **R2 注意**：跑 `pytest packages/susr/tests/` 若 collision 就拿掉這個 `__init__.py`

---

## 2. user-guide 缺口：跨年 restate 場景

R1 user-guide agent 完成 3 個 scenarios 後標出**缺一個典型場景**：

> 「客戶今年要把去年的範疇 3 重述」場景

這是 `restate` action_type + `> 5% threshold` 揭露機制最能展現價值的地方。對應到：
- `timeline_entries` table 的 `action_type = 'restate'`
- `page_versions` 跨年比對
- 反綠色洗白 §1 強制揭露未達標 / 目標調整理由
- ESG 顧問實務中極常見（年度資料校正、邊界擴大、計算方法升級）

**建議**：寫成 `docs/user-guide/scenarios/客戶今年要重述去年範疇3.md`（待後續補）。

---

## 3. R2 開工前 checklist

- [ ] 讀本檔（§1 七個判斷依據 + §2 缺口）
- [ ] 讀 `docs/research/step1-spec.md`（特別 §3 RRF / §4 page_versions / §5 embedding / §6 MCP tools）
- [ ] 確認 `packages/susr/` 結構與 spec 對齊
- [ ] 跑 `pytest tests/` 確認既有測試 19/19 仍 pass（baseline）
- [ ] `pip install sqlite-vec` 然後驗 DDL：
  ```bash
  python -c "import sqlite3, sqlite_vec; conn=sqlite3.connect(':memory:'); conn.enable_load_extension(True); sqlite_vec.load(conn); conn.executescript(open('packages/susr/susr/brain/ddl/v001_init.sql', encoding='utf-8').read()); print('OK')"
  ```
- [ ] 認領 R2 切片（schema 載入 / brain engine CRUD / RRF / MCP server / Layer 3+4 tests）
- [ ] 維持 §4.6 Content Hygiene（單檔 < 300 行 Python，超過拆模組）
- [ ] 維持 §6.1 testing hard rule（feature ↔ test 一對一）

---

## 4. R1 不在範圍但 R2 / 後續要做

- shared_kb/data/ 目前空 — Step 3（references → shared_kb 遷移）會填
- MCP tools 邏輯全為 `NotImplementedError` stub — R2 填
- LLMProvider extras（caching / extended thinking）— spec 標折衷，R2 試水溫
- Layer 3 invariant lint 對應 DDL 的 view（`v_core_topic_action_coverage` / `v_chapter_completeness` / `v_target_completeness`）— R2 把 view 包成 Python invariant runner
