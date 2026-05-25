"""susr.brain.search — Hybrid vector + FTS5 retrieval with RRF fusion.

Spec §3: two-leg retrieval — sqlite-vec KNN + FTS5 BM25 — fused via
Reciprocal Rank Fusion (Cormack 2009) with k=60.  Filters apply to both
legs.  Multi-entity vector filter is split into N queries (sqlite-vec
0.1.9 partition key only supports `=`).
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
        snippet: optional excerpt around the match (R2 fills compiled_truth head)
        matched_paths: which legs hit ('vec' / 'fts')
    """

    page_id: int
    slug: str
    entity_type: str
    title: str
    score: float
    snippet: Optional[str] = None
    matched_paths: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# RRF fusion
# ---------------------------------------------------------------------------


def rrf_merge(
    rank_lists: Sequence[Sequence[int]],
    k: int = RRF_K,
) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion of multiple page_id rank lists.

    Each inner list is a relevance-descending sequence of page_ids.
    Returns (page_id, score) sorted by score desc.

    Math: score(d) = sum over retrievers r of  1 / (k + rank_r(d))
    where rank is 1-based per the original Cormack 2009 paper.
    Within a single rank_list, only the first occurrence of a page_id
    counts (dedup), so callers can pass raw chunk→page rankings safely.
    """
    scores: dict[int, float] = defaultdict(float)
    for ranked in rank_lists:
        seen: set[int] = set()
        rank = 1
        for page_id in ranked:
            if page_id in seen:
                continue
            seen.add(page_id)
            scores[page_id] += 1.0 / (k + rank)
            rank += 1
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


# ---------------------------------------------------------------------------
# Vector leg
# ---------------------------------------------------------------------------


def _serialize_vector(vec: Sequence[float]) -> bytes:
    """Encode floats as little-endian f32 (sqlite-vec wire format)."""
    try:
        import sqlite_vec  # type: ignore

        if hasattr(sqlite_vec, "serialize_float32"):
            return sqlite_vec.serialize_float32(list(vec))
    except Exception:  # pragma: no cover
        pass
    import struct

    return struct.pack(f"{len(vec)}f", *vec)


def _vector_search(
    conn: sqlite3.Connection,
    query_vec: Sequence[float],
    *,
    top_n: int,
    entity_types: Optional[Sequence[str]],
    project_slug: Optional[str],
    tenant_id: Optional[str],
) -> list[int]:
    """KNN over vec_chunks → page_ids by ascending distance.  Multi-entity
    filter issues one query per type and stitches results."""
    serialized = _serialize_vector(query_vec)
    types = list(entity_types) if entity_types else [None]

    candidates: list[tuple[float, int]] = []
    for t in types:
        sql_parts = [
            "SELECT page_id, distance FROM vec_chunks",
            "WHERE embedding MATCH ? AND k = ?",
        ]
        params: list[object] = [serialized, top_n]
        if t is not None:
            sql_parts.append("AND entity_type = ?")
            params.append(t)
        if project_slug is not None:
            sql_parts.append("AND project_slug = ?")
            params.append(project_slug)
        if tenant_id is not None:
            sql_parts.append("AND tenant_id = ?")
            params.append(tenant_id)
        sql_parts.append("ORDER BY distance")
        rows = conn.execute(" ".join(sql_parts), params).fetchall()
        candidates.extend((float(d), int(pid)) for pid, d in rows)

    candidates.sort(key=lambda kv: kv[0])
    seen: set[int] = set()
    out: list[int] = []
    for _, pid in candidates:
        if pid in seen:
            continue
        seen.add(pid)
        out.append(pid)
        if len(out) >= top_n:
            break
    return out


# ---------------------------------------------------------------------------
# FTS leg
# ---------------------------------------------------------------------------


def _fts_search(
    conn: sqlite3.Connection,
    query: str,
    *,
    top_n: int,
    entity_types: Optional[Sequence[str]],
    project_slug: Optional[str],
    tenant_id: Optional[str],
) -> list[int]:
    """BM25 over fts_pages → page_ids by ascending rank (FTS5: lower is better)."""
    sql_parts = [
        "SELECT rowid, bm25(fts_pages) AS rank FROM fts_pages",
        "WHERE fts_pages MATCH ?",
    ]
    params: list[object] = [query]
    if entity_types:
        placeholders = ",".join("?" * len(entity_types))
        sql_parts.append(f"AND entity_type IN ({placeholders})")
        params.extend(entity_types)
    if project_slug is not None:
        sql_parts.append("AND project_slug = ?")
        params.append(project_slug)
    if tenant_id is not None:
        sql_parts.append("AND tenant_id = ?")
        params.append(tenant_id)
    sql_parts.append("ORDER BY rank LIMIT ?")
    params.append(top_n)
    try:
        rows = conn.execute(" ".join(sql_parts), params).fetchall()
    except sqlite3.OperationalError:
        # Malformed FTS query (e.g. unbalanced quotes) → degrade to empty.
        return []
    return [int(r[0]) for r in rows]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def hybrid_search(
    conn: sqlite3.Connection,
    query: str,
    *,
    embed_provider: Optional[object] = None,  # EmbeddingProvider; loose to avoid import cycle
    entity_types: Optional[Sequence[str]] = None,
    project_slug: Optional[str] = None,
    tenant_id: Optional[str] = None,
    top_n_per_path: int = 50,
    top_k: int = 10,
    rrf_k: int = RRF_K,
) -> list[SearchResult]:
    """Vector + FTS5 hybrid search fused by RRF.

    Filters (entity_types / project_slug / tenant_id) apply to BOTH legs.
    Vector leg is skipped when embed_provider is None (FTS-only fallback,
    e.g. when the consultant hasn't installed an embedding extra).
    """
    rank_lists: list[list[int]] = []
    matched_by_page: dict[int, set[str]] = defaultdict(set)

    # Vector leg
    if embed_provider is not None:
        try:
            query_vec = embed_provider.embed_query(query)  # type: ignore[attr-defined]
        except Exception:
            query_vec = None
        if query_vec is not None:
            try:
                vec_ranked = _vector_search(
                    conn,
                    query_vec,
                    top_n=top_n_per_path,
                    entity_types=entity_types,
                    project_slug=project_slug,
                    tenant_id=tenant_id,
                )
            except sqlite3.OperationalError:
                # vec_chunks empty or extension missing — treat as no hits.
                vec_ranked = []
            if vec_ranked:
                rank_lists.append(vec_ranked)
                for pid in vec_ranked:
                    matched_by_page[pid].add("vec")

    # FTS leg
    fts_ranked = _fts_search(
        conn,
        query,
        top_n=top_n_per_path,
        entity_types=entity_types,
        project_slug=project_slug,
        tenant_id=tenant_id,
    )
    if fts_ranked:
        rank_lists.append(fts_ranked)
        for pid in fts_ranked:
            matched_by_page[pid].add("fts")

    if not rank_lists:
        return []

    fused = rrf_merge(rank_lists, k=rrf_k)[:top_k]
    if not fused:
        return []

    page_ids = [pid for pid, _ in fused]
    placeholders = ",".join("?" * len(page_ids))
    rows = conn.execute(
        f"SELECT id, slug, entity_type, title, compiled_truth "
        f"FROM pages WHERE id IN ({placeholders}) AND deleted_at IS NULL",
        page_ids,
    ).fetchall()
    by_id = {int(r[0]): r for r in rows}

    results: list[SearchResult] = []
    for pid, score in fused:
        row = by_id.get(pid)
        if row is None:
            continue
        _id, slug, entity_type, title, compiled = row
        snippet = (compiled or "")[:200] if compiled else None
        results.append(
            SearchResult(
                page_id=int(_id),
                slug=str(slug),
                entity_type=str(entity_type),
                title=str(title),
                score=float(score),
                snippet=snippet,
                matched_paths=sorted(matched_by_page.get(pid, set())),
            )
        )
    return results
