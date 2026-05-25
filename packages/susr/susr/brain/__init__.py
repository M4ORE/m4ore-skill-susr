"""susr.brain — Core engine package.

Responsibilities:
    - Own the SQLite + sqlite-vec + FTS5 connection lifecycle
    - Provide CRUD over pages / entity_attributes / links / timeline
    - Enforce the 17 ESG entity schemas and 19 typed edges
    - Run the 5 connectivity invariants (fail-closed)
    - Hybrid retrieval (RRF fusion of vector KNN + FTS5 BM25)
    - Snapshot via page_versions; append-only timeline_entries

Sub-modules (all R2 placeholders today):
    engine       — BrainEngine façade
    migrations   — DDL loader + version bookkeeping
    entities     — 17 entity types + Pydantic frontmatter schemas
    edges        — 19 typed edges registry + validate_edge
    invariants   — I1..I5 connectivity checks
    search       — RRF hybrid search
    pages        — page CRUD
    timeline     — append-only timeline_entries writer/reader
    versions     — page_versions snapshot/restore
    ingest       — 真實 markdown → brain 的容忍層（R3 P0a）

Sub-package:
    ddl/v001_init.sql — complete, runnable schema (no R2 changes expected)

See docs/research/step1-spec.md §2..§4 for the full design.
"""

from __future__ import annotations

from susr.brain.ingest import (
    ingest_directory,
    ingest_markdown_file,
    normalize_frontmatter,
)

__all__ = [
    "engine",
    "migrations",
    "entities",
    "edges",
    "invariants",
    "search",
    "pages",
    "timeline",
    "versions",
    "ingest",
    # ingest tolerance layer (R3 P0a) — re-exported for top-level convenience
    "normalize_frontmatter",
    "ingest_markdown_file",
    "ingest_directory",
]
