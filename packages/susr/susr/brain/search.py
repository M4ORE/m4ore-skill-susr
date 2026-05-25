"""susr.brain.search — Hybrid vector + FTS5 retrieval with RRF fusion.

Three-path retrieval (spec §3.2):
    Path 1  sqlite-vec KNN over vec_chunks (semantic)
    Path 2  FTS5 BM25 over fts_pages (lexical, trigram tokenizer for CJK)
    Path 3  reserved structural / entity filter (MVP just filters in 1+2)

The two rank lists are fused via Reciprocal Rank Fusion (Cormack 2009)
with k=60 (gbrain default; spec §3.1 cites the empirical sweet-spot range
[10,100]).  Top-k results are hydrated from `pages` and returned.

R1: dataclasses + signatures + RRF stub.
R2: implement.  Layer 4 tests in tests/test_search_rrf.py will pin RRF math.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, Sequence

# Default RRF k.  See spec §3.1 for the empirical-range discussion.
RRF_K: int = 60


@dataclass
class SearchResult:
    """One hit from hybrid_search.

    Attributes:
        page_id: row id in pages table
        slug: stable slug of the hit page (e.g. 'topics/E1')
        entity_type: one of EntityType
        title: human-readable title
        score: RRF fused score (higher = better)
        snippet: optional excerpt around the match (R2 will fill from chunk_text)
    """

    page_id: int
    slug: str
    entity_type: str
    title: str
    score: float
    snippet: Optional[str] = None
    matched_paths: list[str] = field(default_factory=list)  # which legs (vec/fts) hit


def rrf_merge(
    rank_lists: Sequence[Sequence[int]],
    k: int = RRF_K,
) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion of multiple page_id rank lists.

    Each inner list is a relevance-descending sequence of page_ids.
    Returns (page_id, score) sorted by score desc.

    Math: score(d) = sum over retrievers r of  1 / (k + rank_r(d))
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §3.1")


def hybrid_search(
    conn: sqlite3.Connection,
    query: str,
    *,
    embed_provider: Optional[object] = None,   # EmbeddingProvider; loose to avoid import cycle
    entity_types: Optional[Sequence[str]] = None,
    project_slug: Optional[str] = None,
    tenant_id: Optional[str] = None,
    top_n_per_path: int = 50,
    top_k: int = 10,
    rrf_k: int = RRF_K,
) -> list[SearchResult]:
    """Vector + FTS5 hybrid search fused by RRF.

    Filters (entity_types / project_slug / tenant_id) apply to BOTH legs;
    sqlite-vec 0.1.9 partition-key only supports `=`, so multi-entity filter
    must be issued per type then merged (spec §3.2 note).

    R2 must:
        1. Encode query via embed_provider.embed_query(query)
        2. Vector leg: SELECT page_id FROM vec_chunks WHERE embedding MATCH ?
        3. FTS leg:    SELECT rowid FROM fts_pages WHERE fts_pages MATCH ?
        4. Dedup chunk→page on the vector side
        5. RRF merge → top_k
        6. Hydrate pages
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §3.2")
