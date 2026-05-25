"""susr.embeddings.provider — EmbeddingProvider Protocol.

依 CLAUDE.md §8 decision 10 與 spec §5.1，brain 只對 Protocol 編程；
具體 BGE-M3 / Qwen3 / OpenAI 各自實作，install 時透過 extras 拉依賴。

設計要點：
    - 區分 ``embed_query`` 與 ``embed_documents`` 是必要的：
      BGE-M3 不需特殊 prefix，但 Qwen3 有 instruction-aware prompt，
      query/document 端要送入不同 prompt 才能拿到正確的對齊向量。
    - 回傳一律使用 ``numpy.ndarray`` (float32) 對齊 sqlite-vec
      ``serialize_float32`` 與 R1 benchmark harness wrapper。
    - ``hosting`` 屬性用於 by-hosting 拆解（local / cloud），對 Q7
      個資合約風險篩選 provider。
    - 切 provider 等於重建 vec_chunks (dim 可能不同)，見 spec §5.2。
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

import numpy as np


@runtime_checkable
class EmbeddingProvider(Protocol):
    """可插拔的文字 → 向量編碼器。

    Implementations MUST:
        - 提供穩定的 ``name`` / ``dimension`` / ``hosting`` 屬性
          (class attribute 或 instance attribute 皆可)
        - 支援 single-query 與 batch document 兩條路徑
        - 在 sync 環境下安全呼叫
    """

    name: str
    dimension: int
    hosting: str  # "local" | "cloud"

    def embed_query(self, text: str) -> np.ndarray:
        """編碼單一查詢字串。回傳形狀 ``(dimension,)`` 的 ndarray。"""
        ...

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        """批次編碼文件 chunk。回傳形狀 ``(len(texts), dimension)`` 的 ndarray。"""
        ...
