"""Layer 4 embedding benchmark runner.

跑法:
    python -m tests.benchmarks.embedding.run_benchmark
    python -m tests.benchmarks.embedding.run_benchmark --providers bge-m3,openai
    python -m tests.benchmarks.embedding.run_benchmark --queries-limit 5

流程:
    1. 載入 fixtures (queries.yaml + corpus.yaml)
    2. 對每個 provider:
       a. embed corpus → 矩陣 (N_corpus, dim)
       b. embed each query → vector (dim,)
       c. cosine similarity ranking
       d. 計算 Recall@1/@5/@10, MRR
       e. 計時(總 corpus embed + per-query)
    3. 輸出 results/<provider>.json 與 results/summary.md

設計原則:
    * 不做 reranker / dimension reduction(YAGNI,留給正式版)
    * cosine similarity 用 sklearn-free 純 numpy
    * 失敗 fail-fast(corpus / query 對不上、provider load 失敗 → 直接 raise)
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Sequence

import numpy as np
import yaml

from tests.benchmarks.embedding.providers import EmbeddingProvider, load_provider

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
FIXTURES_DIR = HERE / "fixtures"
RESULTS_DIR = HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class CorpusItem:
    id: str
    text: str
    topic_slug: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Query:
    query: str
    expected_topics: List[str]
    category: str
    notes: str | None = None


@dataclass
class QueryResult:
    """單一 query 對單一 provider 的執行結果。"""

    query: str
    category: str
    expected_topics: List[str]
    top10_ids: List[str]           # corpus item id, top-10
    top10_topic_slugs: List[str]   # 對應的 topic_slug
    top10_scores: List[float]
    first_hit_rank: int | None     # 第一次命中的 1-based rank(沒命中 = None)
    recall_at_1: int
    recall_at_5: int
    recall_at_10: int
    reciprocal_rank: float          # 1/first_hit_rank 或 0
    embed_latency_ms: float         # 該 query 的 embed wall-clock


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_corpus() -> List[CorpusItem]:
    with (FIXTURES_DIR / "corpus.yaml").open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    items = [CorpusItem(**row) for row in raw["corpus"]]
    if not items:
        raise RuntimeError("corpus.yaml 為空")
    return items


def load_queries() -> List[Query]:
    with (FIXTURES_DIR / "queries.yaml").open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return [Query(**row) for row in raw["queries"]]


# ---------------------------------------------------------------------------
# Math
# ---------------------------------------------------------------------------


def cosine_similarity_matrix(query_vec: np.ndarray, corpus_mat: np.ndarray) -> np.ndarray:
    """單一 query vector 與 corpus matrix 的 cosine similarity 向量。

    Args:
        query_vec: shape (dim,)
        corpus_mat: shape (N, dim)

    Returns:
        shape (N,) cosine sim ∈ [-1, 1]
    """
    q_norm = np.linalg.norm(query_vec)
    c_norms = np.linalg.norm(corpus_mat, axis=1)
    if q_norm == 0 or np.any(c_norms == 0):
        # 防 zero vector (極端情況);讓那些 norm 0 的位置 score = 0
        c_norms = np.where(c_norms == 0, 1e-9, c_norms)
        q_norm = max(q_norm, 1e-9)
    return (corpus_mat @ query_vec) / (c_norms * q_norm)


# ---------------------------------------------------------------------------
# Per-query evaluation
# ---------------------------------------------------------------------------


def evaluate_query(
    query: Query,
    query_vec: np.ndarray,
    corpus: Sequence[CorpusItem],
    corpus_mat: np.ndarray,
    embed_latency_ms: float,
) -> QueryResult:
    sims = cosine_similarity_matrix(query_vec, corpus_mat)
    # argsort desc → top-10
    order = np.argsort(-sims)[:10]
    top10_items = [corpus[i] for i in order]
    top10_ids = [item.id for item in top10_items]
    top10_topic_slugs = [item.topic_slug for item in top10_items]
    top10_scores = [float(sims[i]) for i in order]

    expected = set(query.expected_topics)

    first_hit_rank: int | None = None
    for rank_zero, slug in enumerate(top10_topic_slugs):
        if slug in expected:
            first_hit_rank = rank_zero + 1
            break

    def hit_in_top_k(k: int) -> int:
        return int(any(slug in expected for slug in top10_topic_slugs[:k]))

    return QueryResult(
        query=query.query,
        category=query.category,
        expected_topics=list(query.expected_topics),
        top10_ids=top10_ids,
        top10_topic_slugs=top10_topic_slugs,
        top10_scores=top10_scores,
        first_hit_rank=first_hit_rank,
        recall_at_1=hit_in_top_k(1),
        recall_at_5=hit_in_top_k(5),
        recall_at_10=hit_in_top_k(10),
        reciprocal_rank=(1.0 / first_hit_rank) if first_hit_rank else 0.0,
        embed_latency_ms=embed_latency_ms,
    )


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def aggregate(results: List[QueryResult]) -> Dict[str, Any]:
    """整體 + by-category metrics."""

    def avg(values: List[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    overall = {
        "n_queries": len(results),
        "recall@1": avg([r.recall_at_1 for r in results]),
        "recall@5": avg([r.recall_at_5 for r in results]),
        "recall@10": avg([r.recall_at_10 for r in results]),
        "mrr": avg([r.reciprocal_rank for r in results]),
        "avg_embed_latency_ms": avg([r.embed_latency_ms for r in results]),
    }

    by_category: Dict[str, Dict[str, float]] = {}
    grouped: Dict[str, List[QueryResult]] = defaultdict(list)
    for r in results:
        grouped[r.category].append(r)

    for cat, items in grouped.items():
        by_category[cat] = {
            "n": len(items),
            "recall@1": avg([r.recall_at_1 for r in items]),
            "recall@5": avg([r.recall_at_5 for r in items]),
            "recall@10": avg([r.recall_at_10 for r in items]),
            "mrr": avg([r.reciprocal_rank for r in items]),
        }

    return {"overall": overall, "by_category": by_category}


# ---------------------------------------------------------------------------
# Provider run
# ---------------------------------------------------------------------------


def run_provider(
    provider: EmbeddingProvider,
    corpus: List[CorpusItem],
    queries: List[Query],
) -> Dict[str, Any]:
    print(f"\n=== running provider: {provider.name} (dim={provider.dimension}) ===")

    # 1) embed full corpus once
    t0 = time.perf_counter()
    corpus_mat = provider.embed([c.text for c in corpus])
    corpus_embed_secs = time.perf_counter() - t0
    print(f"[{provider.name}] corpus embedded ({len(corpus)} items) in {corpus_embed_secs:.2f}s")

    if corpus_mat.shape != (len(corpus), provider.dimension):
        # 不嚴格 fail — 但 warn(Qwen3 dim 可能與 class attr 不同,已在 init 校正)
        print(
            f"[{provider.name}] WARN: corpus_mat shape {corpus_mat.shape} vs "
            f"expected ({len(corpus)}, {provider.dimension})"
        )

    # 2) per-query embed + evaluate
    per_query_results: List[QueryResult] = []
    for q in queries:
        tq = time.perf_counter()
        qvec = provider.embed([q.query])[0]
        latency_ms = (time.perf_counter() - tq) * 1000
        res = evaluate_query(q, qvec, corpus, corpus_mat, latency_ms)
        per_query_results.append(res)

    metrics = aggregate(per_query_results)

    return {
        "provider": provider.name,
        "dimension": int(provider.dimension),
        "hosting": provider.hosting,
        "corpus_size": len(corpus),
        "n_queries": len(queries),
        "corpus_embed_secs": corpus_embed_secs,
        "metrics": metrics,
        "per_query": [
            {
                "query": r.query,
                "category": r.category,
                "expected_topics": r.expected_topics,
                "top10_ids": r.top10_ids,
                "top10_topic_slugs": r.top10_topic_slugs,
                "top10_scores": [round(s, 4) for s in r.top10_scores],
                "first_hit_rank": r.first_hit_rank,
                "recall@1": r.recall_at_1,
                "recall@5": r.recall_at_5,
                "recall@10": r.recall_at_10,
                "reciprocal_rank": round(r.reciprocal_rank, 4),
                "embed_latency_ms": round(r.embed_latency_ms, 2),
            }
            for r in per_query_results
        ],
    }


# ---------------------------------------------------------------------------
# Summary writer
# ---------------------------------------------------------------------------


def write_summary(all_results: List[Dict[str, Any]]) -> None:
    lines = [
        "# Embedding Benchmark Summary",
        "",
        "本檔由 `tests/benchmarks/embedding/run_benchmark.py` 自動產出。",
        f"Providers compared: {', '.join(r['provider'] for r in all_results)}",
        "",
        "## Overall metrics",
        "",
        "| Provider | Dim | Hosting | Recall@1 | Recall@5 | Recall@10 | MRR | Avg latency (ms/query) |",
        "|----------|-----|---------|---------:|---------:|----------:|----:|----------------------:|",
    ]
    for r in all_results:
        m = r["metrics"]["overall"]
        lines.append(
            f"| {r['provider']} | {r['dimension']} | {r['hosting']} | "
            f"{m['recall@1']:.2f} | {m['recall@5']:.2f} | {m['recall@10']:.2f} | "
            f"{m['mrr']:.3f} | {m['avg_embed_latency_ms']:.1f} |"
        )

    lines.extend(["", "## By-category breakdown (Recall@5)", ""])
    categories = sorted(
        {cat for r in all_results for cat in r["metrics"]["by_category"]}
    )
    header = "| Provider | " + " | ".join(categories) + " |"
    sep = "|----------|" + "|".join("-----:" for _ in categories) + "|"
    lines.append(header)
    lines.append(sep)
    for r in all_results:
        cells = []
        for cat in categories:
            cat_metrics = r["metrics"]["by_category"].get(cat)
            cells.append(f"{cat_metrics['recall@5']:.2f}" if cat_metrics else "—")
        lines.append(f"| {r['provider']} | " + " | ".join(cells) + " |")

    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "把這份 summary 的決策一行帶入 `docs/research/embeddings-bench-v0.md`,",
            "並更新 `packages/susr/susr/embeddings/__init__.py` 的 ``DEFAULT_PROVIDER``。",
            "",
        ]
    )

    out = RESULTS_DIR / "summary.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[summary] written to {out}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="susr Layer 4 embedding benchmark harness",
    )
    p.add_argument(
        "--providers",
        default="bge-m3,qwen3,openai",
        help="逗號分隔 provider 短名;default = bge-m3,qwen3,openai",
    )
    p.add_argument(
        "--queries-limit",
        type=int,
        default=None,
        help="只跑前 N queries(debug 用)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    provider_names = [s.strip() for s in args.providers.split(",") if s.strip()]

    corpus = load_corpus()
    queries = load_queries()
    if args.queries_limit:
        queries = queries[: args.queries_limit]
    print(f"loaded {len(corpus)} corpus items, {len(queries)} queries")

    all_results: List[Dict[str, Any]] = []
    for name in provider_names:
        try:
            provider = load_provider(name)
        except Exception as exc:  # noqa: BLE001
            # 不讓單一 provider 失敗中斷整個 run(例如 OPENAI_API_KEY 沒設)
            print(f"[{name}] SKIPPED: {exc}")
            continue

        result = run_provider(provider, corpus, queries)
        all_results.append(result)

        out = RESULTS_DIR / f"{provider.name}.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{provider.name}] result written to {out}")

    if all_results:
        write_summary(all_results)
    else:
        print("no provider produced results — check installation / API key")


if __name__ == "__main__":
    main()
