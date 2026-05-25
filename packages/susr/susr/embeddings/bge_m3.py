"""susr.embeddings.bge_m3 — BGE-M3 local provider (DEFAULT).

BGE-M3 (BAAI/bge-m3, Apache 2.0) is the default per CLAUDE.md §8
decision 10.  It runs entirely on the consultant's machine via
sentence-transformers, which sidesteps the Q7 PII contract risk for
high-sensitivity client data (spec §5.3).

Install:  pip install "susr[embeddings-bge]"   (pulls torch + sentence-transformers)
Dimension: 1024  (matches vec_chunks default declared in DDL §7)
Hosting:   local

Note: first invocation downloads ~2GB of model weights; the doctor
command should warm-load the model so consultants don't hit it mid-chat.

R1: signature scaffold.  R2: implement.
"""

from __future__ import annotations

from typing import Sequence


class BgeM3EmbeddingProvider:
    """Local sentence-transformers wrapper for BAAI/bge-m3."""

    name = "bge:bge-m3"
    hosting = "local"
    _dimension = 1024

    def __init__(self, *, model_path: str | None = None, device: str = "auto") -> None:
        """Construct without downloading weights yet (lazy load on first embed).

        Args:
            model_path: override default HF identifier (e.g. for air-gapped install)
            device: 'auto' picks cuda > mps > cpu
        """
        raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §5.2")

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError("Step 1 R2")

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        raise NotImplementedError("Step 1 R2")
