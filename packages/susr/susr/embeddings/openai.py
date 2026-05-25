"""susr.embeddings.openai — OpenAI cloud embedding provider (fallback).

Listed as cloud fallback per CLAUDE.md §8 decision 10.  Only used when
the per-client `_client.md` has `embedding_policy: cloud` (or `twostage`
for non-sensitive pages); see spec §5.3 for the policy semantics.

PII WARNING: spec §5.3 (Q7) — never embed `sourcedocs/` content here
unless the client has explicitly signed a DPA.  Enforcement lives in
the brain orchestrator, not in this file.

Install:  pip install "susr[embeddings-openai]"
Dimension: 1536  (text-embedding-3-large default; can be reduced to 256/512/1024)
Hosting:   cloud

R1: signature scaffold.  R2: implement.
"""

from __future__ import annotations

from typing import Sequence


class OpenAIEmbeddingProvider:
    """OpenAI text-embedding-3-* wrapper."""

    name = "openai:text-embedding-3-large"
    hosting = "cloud"
    _dimension = 1536

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "text-embedding-3-large",
        dimensions: int | None = None,
    ) -> None:
        """Construct with API key from env or explicit arg.

        Args:
            api_key: OPENAI_API_KEY override
            model: e.g. 'text-embedding-3-large', 'text-embedding-3-small'
            dimensions: optional reduction (3-large supports 256/512/1024/1536)
        """
        raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §5.2")

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError("Step 1 R2")

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        raise NotImplementedError("Step 1 R2")
