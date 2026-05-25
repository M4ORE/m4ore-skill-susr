"""susr.embeddings.provider — EmbeddingProvider Protocol.

Per CLAUDE.md §8 decision 8 ("LLMProvider day-1 抽象") and decision 10
("Embedding 預設 BGE-M3, Qwen3+OpenAI 列備援"), the brain treats
embeddings as a swappable Protocol.

Spec §5.1 defines the surface; this file is the canonical signature
that bge_m3 / qwen3 / openai must satisfy.

NB: switching providers between writes is unsafe — vec_chunks.embedding
is fixed-dimension.  Spec §5.2 explains the rebuild cost.
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Pluggable text → vector encoder.

    Implementations MUST:
        - have a stable `dimension` matching the vec_chunks schema
        - support both single-query and batch embedding paths
        - be safe to call from sync context (use background thread for IO if needed)
    """

    @property
    def dimension(self) -> int:
        """Vector size produced; MUST equal vec_chunks.embedding declared dim."""
        ...

    @property
    def name(self) -> str:
        """Stable identifier, e.g. 'bge:bge-m3', 'openai:text-embedding-3-large'."""
        ...

    @property
    def hosting(self) -> str:
        """Either 'local' (no network) or 'cloud' (external API call)."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Encode a single query string. Returns a vector of length `dimension`."""
        ...

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Batch-encode document chunks. Returns one vector per input text."""
        ...
