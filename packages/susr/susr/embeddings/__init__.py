"""susr.embeddings — Pluggable text embedding providers.

Day-1 abstraction (CLAUDE.md §8 decision 10): the brain calls only the
Protocol in `base.provider`; concrete providers ship behind optional
dependency extras so a `pip install susr` minimal does not pull in torch.

Default: BGE-M3 (local, 1024d) — CLAUDE.md §8 decision 10. Switching
provider requires rebuilding vec_chunks (different embedding dimension);
see spec §5.2.

Available providers (R2 will implement; R1 are stubs):
    bge_m3   — BGE-M3, local sentence-transformers, 1024d (DEFAULT)
    qwen3    — Qwen3 embedding model, local, 1024d (backup)
    openai   — OpenAI text-embedding-3-large, cloud, 1536d (cloud fallback)
"""

from __future__ import annotations

from susr.embeddings.provider import EmbeddingProvider

__all__ = ["EmbeddingProvider"]
