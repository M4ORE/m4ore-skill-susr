-- =====================================================================
-- susr brain v001 — initial schema
-- =====================================================================
--
-- Target  : SQLite >= 3.41 (sqlite-vec virtual-table requirement)
-- Loads   : sqlite-vec extension MUST be loaded before this script runs
--           (the vec0 virtual table on §7 will otherwise fail).
-- Source  : docs/research/step1-spec.md §2.2 — Plan B Phase 3 MVP
-- Decisions: CLAUDE.md §8
--   - SQLite + sqlite-vec + FTS5 (no Postgres)
--   - Per-client repo .susr/db.sqlite (single file)
--   - tenant_id NULLABLE  → future team edition
--   - xbrl_concept NULLABLE → future iXBRL/ESEF (Q16)
--   - 5 connectivity invariants partly schema, partly app-level (§2.5)
--
-- Layout of this script (search for the divider banners):
--   1.  Migration bookkeeping
--   2.  pages                 (markdown source of truth row)
--   3.  entity_attributes     (frontmatter flattened)
--   4.  links                 (typed edges, 19 registered in edges.py)
--   5.  timeline_entries      (append-only evidence chain)
--   6.  page_versions         (snapshot for restate / freeze / assure)
--   7.  vec_chunks            (sqlite-vec virtual table; hybrid search vec leg)
--   8.  fts_pages             (FTS5 virtual table; hybrid search lexical leg)
--   9.  v_target_completeness (I3 helper view — schema-level invariant)
--  10.  v_core_topic_action_coverage (I1 helper view)
--  11.  v_chapter_completeness (I2 helper view)
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. Migration bookkeeping
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now')),
    description TEXT
);

INSERT OR IGNORE INTO schema_version (version, description)
VALUES (1, 'initial schema: pages + entity_attributes + links + timeline + versions + vec + fts');


-- ---------------------------------------------------------------------
-- 2. pages — every markdown file maps to one row.
-- ---------------------------------------------------------------------
-- compiled_truth = markdown body ABOVE the '---' separator (gbrain pattern):
--                  the "conclusion / current best truth"
-- timeline lives below the separator but is split out to timeline_entries
-- on ingest (table 5) so it can be queried append-only.
--
-- slug is unique per tenant (UNIQUE (slug, tenant_id)) — tenant_id NULL today
-- means "single consultant local workspace"; future team edition flips it on.
CREATE TABLE IF NOT EXISTS pages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT    NOT NULL,
    entity_type     TEXT    NOT NULL,
    title           TEXT    NOT NULL,
    compiled_truth  TEXT    NOT NULL DEFAULT '',
    file_path       TEXT    NOT NULL,
    source_hash     TEXT    NOT NULL,
    tenant_id       TEXT,                              -- nullable; future team edition (CLAUDE.md §8 Q4 退路)
    project_slug    TEXT,                              -- nullable; for projects/* pages
    xbrl_concept    TEXT,                              -- nullable; iXBRL/ESEF future (CLAUDE.md §8 Q16)
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    deleted_at      TEXT,                              -- soft delete
    UNIQUE (slug, tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_pages_entity_type ON pages(entity_type);
CREATE INDEX IF NOT EXISTS idx_pages_project     ON pages(project_slug);
CREATE INDEX IF NOT EXISTS idx_pages_tenant      ON pages(tenant_id);
CREATE INDEX IF NOT EXISTS idx_pages_deleted     ON pages(deleted_at);


-- ---------------------------------------------------------------------
-- 3. entity_attributes — frontmatter dict flattened to (page,key,value).
-- ---------------------------------------------------------------------
-- value_type lets us round-trip back to typed Python without per-key schema.
-- Pydantic schemas in entities.py enforce per-entity required keys.
CREATE TABLE IF NOT EXISTS entity_attributes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id     INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    key         TEXT    NOT NULL,
    value       TEXT,                                  -- JSON-encoded for arrays/dicts; bare text for primitives
    value_type  TEXT    NOT NULL CHECK (value_type IN (
                    'text','int','float','bool','date','json_array','json_object'
                )),
    UNIQUE (page_id, key)
);

CREATE INDEX IF NOT EXISTS idx_attr_page     ON entity_attributes(page_id);
CREATE INDEX IF NOT EXISTS idx_attr_key      ON entity_attributes(key);
CREATE INDEX IF NOT EXISTS idx_attr_key_val  ON entity_attributes(key, value);


-- ---------------------------------------------------------------------
-- 4. links — typed edges between pages.
-- ---------------------------------------------------------------------
-- edge_type is NOT a SQL CHECK: registering new edges should not require
-- ALTER TABLE.  Validation lives in susr.brain.edges.EDGE_REGISTRY
-- (which also enforces src→dst entity_type compatibility).
CREATE TABLE IF NOT EXISTS links (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    src_page_id   INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    dst_page_id   INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    edge_type     TEXT    NOT NULL,
    properties    TEXT    DEFAULT '{}',                -- JSON: e.g. {confidence:0.8, year:2025}
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (src_page_id, dst_page_id, edge_type)
);

CREATE INDEX IF NOT EXISTS idx_links_src  ON links(src_page_id, edge_type);
CREATE INDEX IF NOT EXISTS idx_links_dst  ON links(dst_page_id, edge_type);
CREATE INDEX IF NOT EXISTS idx_links_type ON links(edge_type);


-- ---------------------------------------------------------------------
-- 5. timeline_entries — APPEND-ONLY evidence chain (anti-greenwashing).
-- ---------------------------------------------------------------------
-- action_type enum covers the full 8-Phase workflow but MVP v0.1 writes
-- only: ingest / verify / restate / iro_link.  See spec §4.2.
CREATE TABLE IF NOT EXISTS timeline_entries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id       INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    ts            TEXT    NOT NULL DEFAULT (datetime('now')),
    action_type   TEXT    NOT NULL CHECK (action_type IN (
                    'ingest',      -- first write / re-ingest
                    'verify',      -- consultant double-check
                    'restate',     -- value restatement (>5% triggers alert)
                    'assure',      -- third-party assurance passed
                    'comment',     -- consultant annotation
                    'iro_link',    -- IRO mapping established
                    'gap_flag'     -- gap-analysis flag
                  )),
    source_ref    TEXT,                                -- file path / URL / chat msg id
    confidence    REAL    CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    actor         TEXT,                                -- 'consultant:zhang' / 'agent:claude-opus-4-7'
    payload       TEXT    DEFAULT '{}'                 -- JSON: detail per action_type
);

CREATE INDEX IF NOT EXISTS idx_timeline_page ON timeline_entries(page_id, ts);
CREATE INDEX IF NOT EXISTS idx_timeline_type ON timeline_entries(action_type, ts);

-- Append-only enforcement: UPDATE/DELETE both ABORT.
-- Use action_type='restate' instead of mutating earlier rows.
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


-- ---------------------------------------------------------------------
-- 6. page_versions — snapshots taken at commit / phase / freeze / restate.
-- ---------------------------------------------------------------------
-- version_no is monotonic per page; parent_version_id forms the snapshot
-- chain so restore can walk back the history.
CREATE TABLE IF NOT EXISTS page_versions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id             INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    version_no          INTEGER NOT NULL,
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


-- ---------------------------------------------------------------------
-- 7. vec_chunks — sqlite-vec virtual table (hybrid search vector leg).
-- ---------------------------------------------------------------------
-- Each page is chunked + embedded; partition key (entity_type) speeds up
-- entity-filtered KNN.  '+' prefix marks AUX columns: stored but not
-- indexed, retrievable on hit.
--
-- Embedding dim is 1024 (BGE-M3 default, see CLAUDE.md §10 decision 10:
-- "Embedding 預設 BGE-M3").  Switching providers (e.g. OpenAI 1536d)
-- requires DROP+rebuild of this virtual table; see spec §5.2.
--
-- Source: https://alexgarcia.xyz/sqlite-vec/features/vec0.html
CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
    chunk_id        INTEGER PRIMARY KEY,
    page_id         INTEGER NOT NULL,
    entity_type     TEXT PARTITION KEY,
    project_slug    TEXT,
    tenant_id       TEXT,
    embedding       FLOAT[1024],
    +chunk_text     TEXT,
    +chunk_meta     TEXT                               -- JSON {section, char_start, char_end}
);


-- ---------------------------------------------------------------------
-- 8. fts_pages — FTS5 virtual table (hybrid search BM25 leg).
-- ---------------------------------------------------------------------
-- trigram tokenizer is the only CJK-friendly tokenizer in stock SQLite
-- (unicode61 treats spaceless Chinese as a single token; ICU needs custom
-- build).  Trade-off: high recall, lower precision; the vector leg in
-- §7 plus RRF fusion is expected to recover precision.  Spec §10.1 #4.
--
-- Source: https://www.sqlite.org/fts5.html#tokenizers
CREATE VIRTUAL TABLE IF NOT EXISTS fts_pages USING fts5(
    title,
    compiled_truth,
    slug UNINDEXED,
    entity_type UNINDEXED,
    project_slug UNINDEXED,
    tenant_id UNINDEXED,
    tokenize = 'trigram'
);

-- Sync triggers: keep fts_pages in lock-step with pages.
-- (content= shortcut is incompatible with trigram tokenizer, so we mirror.)
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


-- ---------------------------------------------------------------------
-- 9. v_target_completeness — I3 helper view.
-- ---------------------------------------------------------------------
-- Invariant I3: every target must declare baseline_year, baseline_value,
-- target_year, verification_path (anti-greenwashing).  This view exposes
-- per-target completeness flags; app-level code asserts no zeros remain.
CREATE VIEW IF NOT EXISTS v_target_completeness AS
SELECT
    p.id   AS page_id,
    p.slug AS slug,
    MAX(CASE WHEN a.key='baseline_year'     THEN 1 ELSE 0 END) AS has_baseline_year,
    MAX(CASE WHEN a.key='baseline_value'    THEN 1 ELSE 0 END) AS has_baseline_value,
    MAX(CASE WHEN a.key='target_year'       THEN 1 ELSE 0 END) AS has_target_year,
    MAX(CASE WHEN a.key='verification_path' THEN 1 ELSE 0 END) AS has_verification_path
FROM pages p
LEFT JOIN entity_attributes a ON a.page_id = p.id
WHERE p.entity_type = 'target' AND p.deleted_at IS NULL
GROUP BY p.id;


-- ---------------------------------------------------------------------
-- 10. v_core_topic_action_coverage — I1 helper view.
-- ---------------------------------------------------------------------
-- Invariant I1: every topic with materiality_tier='核心' must reach at
-- least one Action via topic_has_iro → iro_addressed_by chain.
CREATE VIEW IF NOT EXISTS v_core_topic_action_coverage AS
SELECT
    t.id   AS topic_id,
    t.slug AS topic_slug,
    COUNT(DISTINCT a_page.id) AS action_count
FROM pages t
LEFT JOIN entity_attributes ta ON ta.page_id = t.id AND ta.key = 'materiality_tier'
LEFT JOIN links l1            ON l1.src_page_id = t.id AND l1.edge_type = 'topic_has_iro'
LEFT JOIN pages iro_page      ON iro_page.id = l1.dst_page_id
LEFT JOIN links l2            ON l2.src_page_id = iro_page.id AND l2.edge_type = 'iro_addressed_by'
LEFT JOIN pages a_page        ON a_page.id = l2.dst_page_id AND a_page.entity_type = 'action'
WHERE t.entity_type = 'topic'
  AND ta.value = '核心'
  AND t.deleted_at IS NULL
GROUP BY t.id;


-- ---------------------------------------------------------------------
-- 11. v_chapter_completeness — I2 helper view.
-- ---------------------------------------------------------------------
-- Invariant I2: every chapter must have >=1 chapter_conforms_to (framework)
-- AND >=1 discloses_topic (topic) edge.
CREATE VIEW IF NOT EXISTS v_chapter_completeness AS
SELECT
    c.id   AS chapter_id,
    c.slug AS slug,
    SUM(CASE WHEN l.edge_type = 'chapter_conforms_to' THEN 1 ELSE 0 END) AS framework_count,
    SUM(CASE WHEN l.edge_type = 'discloses_topic'     THEN 1 ELSE 0 END) AS topic_count
FROM pages c
LEFT JOIN links l ON l.src_page_id = c.id
WHERE c.entity_type = 'chapter' AND c.deleted_at IS NULL
GROUP BY c.id;


-- =====================================================================
-- End of v001_init.sql
-- =====================================================================
