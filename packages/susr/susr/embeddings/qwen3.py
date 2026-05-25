"""susr.embeddings.qwen3 — Qwen3 embedding local provider (backup).

Listed as a backup per CLAUDE.md §8 decision 10.  Considered when BGE-M3
underperforms on a specific client corpus (e.g. heavy Simplified Chinese
or domain-specific jargon).

Install:  pip install "susr[embeddings-bge]"   (also covers Qwen3 via sentence-transformers)
Dimension: 1024  (matches DDL default; if Qwen3 variant produces different dim, R2 must rebuild vec_chunks)
Hosting:   local

R1: signature scaffold.  R2: implement + benchmark vs BGE-M3 on the
spec §5.4 Layer 4 fixture.
"""

from __future__ import annotations

from typing import Sequence


class Qwen3EmbeddingProvider:
    """Local sentence-transformers wrapper for Qwen3 embedding models."""

    name = "qwen3:qwen3-embedding"
    hosting = "local"
    _dimension = 1024

    def __init__(self, *, model_path: str | None = None, device: str = "auto") -> None:
        raise NotImplementedError("Step 1 R2 — pick the Qwen3 embedding variant + dim during R2")

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError("Step 1 R2")

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        raise NotImplementedError("Step 1 R2")
