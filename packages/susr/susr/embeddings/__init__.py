"""susr.embeddings — Pluggable text embedding providers.

Day-1 abstraction (CLAUDE.md §8 decision 10): the brain calls only the
Protocol in `provider`; concrete providers ship behind optional
dependency extras so a `pip install susr` minimal does not pull in torch.

Default: BGE-M3 (local, 1024d) — CLAUDE.md §8 decision 10. Switching
provider requires rebuilding vec_chunks (different embedding dimension);
see spec §5.2.

Available providers:
    bge_m3   — BgeM3Provider, local sentence-transformers, 1024d (DEFAULT)
    qwen3    — Qwen3Provider, local, 1024d nominal (auto-detect) (backup)
    openai   — OpenAIProvider, cloud, 3072d (cloud fallback)
"""

from __future__ import annotations

from susr.embeddings.provider import EmbeddingProvider

__all__ = ["EmbeddingProvider"]
