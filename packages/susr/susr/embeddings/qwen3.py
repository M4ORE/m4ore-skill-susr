"""susr.embeddings.qwen3 — Qwen3-Embedding local provider (備援)。

依 CLAUDE.md §8 decision 10 與 Q11 列為備援:當 BGE-M3 對特定 corpus
(例如重簡中 / 行業特化術語) 表現不佳時切換。

Install:   pip install "susr[embeddings-bge]"  (sentence-transformers 共用)
Dimension: 1024  (Qwen3-Embedding-0.6B 官方標示;首次載入會 runtime 校正)
Hosting:   local

⚠️ Dimension auto-detect:
    Qwen3 系列有多個尺寸 (0.6B / 4B / 8B),官方文件主要標 1024d 但
    可能依 variant 變動。本 provider 在 ``_ensure_loaded()`` 後呼叫
    ``model.get_sentence_embedding_dimension()`` 取實際值,並覆寫
    instance attribute (不動 class attribute,避免污染其他 instance)。
    與 R1 notes §1.5 「Anthropic model id runtime 取」同樣 pattern。

Qwen3 prompt 規範 (官方 model card):
    Qwen3-Embedding 是 instruction-aware 模型,query 端要加 task
    description:

        Instruct: <task description>
        Query: <query>

    Document 端不加 prefix,直接餵 raw text。
    本實作預設 task description 為 retrieval 場景:
        ``"Given a web search query, retrieve relevant passages
        that answer the query"``
    顧問場景未來可改為 ESG 領域特化 (例:「給定永續報告查詢,檢索
    相關章節 / 議題 / 證據」),benchmark 時可比較不同 instruction
    對 retrieval 品質的影響。
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

# 預設模型;同樣允許 air-gapped 部署傳 local 路徑覆寫。
_DEFAULT_MODEL_PATH = "Qwen/Qwen3-Embedding-0.6B"

# Qwen3 官方建議的 generic retrieval task description (英文版)。
# 中文 corpus 可改為 ESG 領域特化版本以提升 retrieval 表現。
_DEFAULT_QUERY_INSTRUCTION = (
    "Given a web search query, retrieve relevant passages that answer the query"
)


def _format_qwen3_query(query: str, instruction: str) -> str:
    """組 Qwen3 query prompt — ``Instruct: ...\\nQuery: ...`` 兩行格式。

    Document 端不套此函式,直接傳 raw text 即可。
    """
    return f"Instruct: {instruction}\nQuery: {query}"


class Qwen3Provider:
    """Local sentence-transformers wrapper for Qwen/Qwen3-Embedding-*."""

    name = "qwen3-embedding-0.6b"
    dimension = 1024  # 預設,runtime 校正 (見 _ensure_loaded)
    hosting = "local"

    def __init__(
        self,
        model_path: str | None = None,
        *,
        device: str = "auto",
        query_instruction: str = _DEFAULT_QUERY_INSTRUCTION,
    ) -> None:
        """建立 provider,**不**載入模型權重。

        Args:
            model_path: 覆寫 HF identifier。可換成 4B/8B variant 或
                local snapshot;若 dim 不同,自動 detect 並覆寫
                ``self.dimension``。
            device: ``"auto"`` / ``"cpu"`` / ``"mps"`` / ``"cuda"``。
            query_instruction: query prompt 的 task description。
                預設為 Qwen3 model card 通用 retrieval 描述;ESG 場景
                可改為領域特化版本以提升表現。
        """
        self._model_path = model_path or _DEFAULT_MODEL_PATH
        self._device = device
        self._query_instruction = query_instruction
        self._model = None  # type: ignore[var-annotated]

    def _ensure_loaded(self) -> None:
        """Lazy load + dimension auto-detect。

        Trap 避免:
            - None-check 必要 (同 BgeM3Provider) — 載入失敗不污染 state。
            - dim 覆寫只動 instance attr,不動 class attr。多個 instance
              不會互相干擾;且 class attr 1024 仍是 spec 預設文件值。
        """
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Qwen3Provider 需要 sentence-transformers — "
                "請執行 `pip install \"susr[embeddings-bge]\"`"
            ) from exc

        kwargs: dict = {}
        if self._device != "auto":
            kwargs["device"] = self._device
        self._model = SentenceTransformer(self._model_path, **kwargs)

        # Runtime dim 校正 — 不 raise,直接覆寫 instance attr。
        actual_dim = self._model.get_sentence_embedding_dimension()
        if actual_dim and actual_dim != type(self).dimension:
            self.dimension = actual_dim  # instance 覆寫,不動 class

    def embed_query(self, text: str) -> np.ndarray:
        """編碼 query — 套用 ``Instruct: ...\\nQuery: ...`` prompt。"""
        self._ensure_loaded()
        assert self._model is not None
        formatted = _format_qwen3_query(text, self._query_instruction)
        vecs = self._model.encode(
            [formatted],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vecs[0]

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        """批次編碼 documents — **不**加 prefix,raw text 直送。"""
        self._ensure_loaded()
        assert self._model is not None
        return self._model.encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )


# Backward-compat alias
Qwen3EmbeddingProvider = Qwen3Provider
