"""susr.embeddings.bge_m3 — BGE-M3 local provider (DEFAULT)。

BGE-M3 (BAAI/bge-m3, Apache 2.0) 是 MVP 預設 embedding，依據:
    - CLAUDE.md §8 decision 10 與 Q11 (本地預設、避開 Q7 個資合約風險)
    - spec §5.4 (C-MTEB 中文 retrieval 表現 + 多語混雜穩定)

Install:  pip install "susr[embeddings-bge]"  (拉 sentence-transformers + torch)
Dimension: 1024  (對齊 vec_chunks DDL §7 預設)
Hosting:   local

Lazy init:
    模型權重 (~570MB) 在 __init__ **不**載入,首次呼叫 embed_* 才透過
    ``_ensure_loaded()`` 觸發 SentenceTransformer 初始化。原因:

    1. ``susr-mcp doctor`` 健檢需能匯入物件但不下載權重
    2. 顧問機沒裝 sentence-transformers 時,只要不呼叫 embed 就不報錯
    3. 單元測試可建立 provider 物件做型別檢查 (Protocol conformance)
       而不必下載 2GB 模型

    第一次 ``embed_*`` 會卡住下載 — 顧問安裝後跑一次 doctor warm-load
    比較不會中斷對話 (見 spec §10 / docs/research/step1-r1-notes.md)。

BGE-M3 prompt 行為:
    BGE-M3 不像 e5 系列那樣強制 ``query:`` / ``passage:`` prefix —
    query 與 document 皆可直接餵 raw text。``normalize_embeddings=True``
    讓 cosine 相似度退化為內積,符合 sqlite-vec 預設距離度量。
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

# 預設 HF 模型 id;air-gapped 部署可在 __init__ 傳 local 路徑覆寫。
_DEFAULT_MODEL_PATH = "BAAI/bge-m3"


class BgeM3Provider:
    """Local sentence-transformers wrapper for BAAI/bge-m3."""

    name = "bge-m3"
    dimension = 1024
    hosting = "local"

    def __init__(
        self,
        model_path: str | None = None,
        *,
        device: str = "auto",
    ) -> None:
        """建立 provider,**不**載入模型權重。

        Args:
            model_path: 覆寫預設 HF identifier(``BAAI/bge-m3``);
                顧問若 air-gapped 可傳 local snapshot 路徑。
            device: ``"auto"`` 由 sentence-transformers 自決
                (cuda > mps > cpu);可硬指定 ``"cpu"`` / ``"mps"`` / ``"cuda"``。
        """
        self._model_path = model_path or _DEFAULT_MODEL_PATH
        self._device = device
        self._model = None  # type: ignore[var-annotated]

    def _ensure_loaded(self) -> None:
        """Lazy load — 首次呼叫 embed_* 時觸發,後續為 no-op。

        Trap 避免:
            - None-check 必要,因 ``SentenceTransformer.__init__`` 失敗
              (例:無網路 / HF rate-limit) 不能讓 ``self._model`` 被
              半完成物件污染;失敗就讓 exception bubble,下次再試。
        """
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "BgeM3Provider 需要 sentence-transformers — "
                "請執行 `pip install \"susr[embeddings-bge]\"`"
            ) from exc

        kwargs: dict = {}
        if self._device != "auto":
            kwargs["device"] = self._device
        self._model = SentenceTransformer(self._model_path, **kwargs)

    def embed_query(self, text: str) -> np.ndarray:
        """編碼單一 query,回傳 ``(dimension,)`` ndarray (已 L2-normalized)。

        BGE-M3 query 不需特殊 prefix(對比 e5 系列要 ``query:``)。
        """
        self._ensure_loaded()
        assert self._model is not None
        vecs = self._model.encode(
            [text],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vecs[0]

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        """批次編碼 documents,回傳 ``(N, dimension)`` ndarray。"""
        self._ensure_loaded()
        assert self._model is not None
        return self._model.encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )


# Backward-compat alias — R1 scaffold 內部使用的長名,避免下游 grep 漏掉
BgeM3EmbeddingProvider = BgeM3Provider
