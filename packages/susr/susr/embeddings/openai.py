"""susr.embeddings.openai — OpenAI 雲端 embedding provider。

依 CLAUDE.md §8 decision 10 列為雲端選項;僅在 ``_client.md`` 標示
``embedding_policy: cloud`` 或 ``twostage`` (對非敏感 page) 才使用。

PII WARNING (spec §5.3 / Q7):
    不可將 ``sourcedocs/`` 原始客戶資料送這條路徑,除非客戶已簽 DPA。
    此規則由 brain orchestrator 強制 (檢查 page 路徑 / classification),
    本檔不做 policy enforcement —— 本檔只負責「送 API + 拿 vector」。

Install:   pip install "susr[embeddings-openai]"
Dimension: 3072 (text-embedding-3-large 預設;可透過 ``dimensions`` 參數降為
           256 / 512 / 1024 — 降維可省 sqlite-vec 儲存,但要重建 vec_chunks)
Hosting:   cloud

Lazy init:
    OpenAI client 在 ``__init__`` **不**連線、**不**驗證 key;首次呼叫
    embed_* 才透過 ``_ensure_client()`` 建立。原因:

    1. doctor 健檢需能匯入物件做 Protocol conformance 檢查
    2. 即使 ``OPENAI_API_KEY`` 未設,只要顧問用 BgeM3Provider 就不該爆
    3. 單元測試可建 ``OpenAIProvider(api_key="dummy")`` 跑 sanity check
       (Protocol / dimension / name) 不接網路
"""

from __future__ import annotations

import os
from typing import Sequence

import numpy as np


class OpenAIProvider:
    """OpenAI text-embedding-3-* 包裝。"""

    name = "openai-text-embedding-3-large"
    dimension = 3072
    hosting = "cloud"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str = "text-embedding-3-large",
        dimensions: int | None = None,
    ) -> None:
        """建立 provider,**不**連線。

        Args:
            api_key: 覆寫 ``OPENAI_API_KEY`` env;傳 ``None`` 則延後
                到 ``_ensure_client()`` 從環境讀。
            model: 模型 id (預設 ``text-embedding-3-large``,可改 small)。
            dimensions: 截斷維度;``None`` 用模型 default (3072 for large)。
                若設 1024 等,記得同步 brain 端 ``self.dimension`` 與
                vec_chunks DDL,否則 dim mismatch。
        """
        self._api_key = api_key
        self._model = model
        self._client = None  # type: ignore[var-annotated]

        # dimensions 不為 None 時,覆寫 instance attr 讓 brain 端拿到正確值
        if dimensions is not None:
            self.dimension = dimensions
            self._dimensions_arg = dimensions
        else:
            self._dimensions_arg = None

    def _ensure_client(self) -> None:
        """Lazy 建立 OpenAI client 並驗證 API key 存在。

        Trap 避免:
            - None-check 必要,失敗時不污染 ``self._client``。
            - API key 檢查必須延後到此處,而非 ``__init__`` —— 確保
              import 階段絕對不會因 env 缺失就爆。
        """
        if self._client is not None:
            return
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "OpenAIProvider 需要 openai SDK — "
                "請執行 `pip install \"susr[embeddings-openai]\"`"
            ) from exc

        key = self._api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError(
                "OPENAI_API_KEY 未設定 — "
                "請在 Claude Desktop config env 補上,或改用 BgeM3Provider"
            )
        self._client = OpenAI(api_key=key)

    def _build_kwargs(self, inputs: list[str]) -> dict:
        kwargs: dict = {"model": self._model, "input": inputs}
        if self._dimensions_arg is not None:
            kwargs["dimensions"] = self._dimensions_arg
        return kwargs

    def embed_query(self, text: str) -> np.ndarray:
        """編碼單一 query。回傳 ``(dimension,)`` ndarray (float32)。

        OpenAI embeddings API 對 query / document 不區分 prompt prefix。
        """
        self._ensure_client()
        assert self._client is not None
        resp = self._client.embeddings.create(**self._build_kwargs([text]))
        return np.asarray(resp.data[0].embedding, dtype=np.float32)

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        """批次編碼。OpenAI API 單次最多 2048 inputs;超過要 caller 自切批。"""
        self._ensure_client()
        assert self._client is not None
        resp = self._client.embeddings.create(**self._build_kwargs(list(texts)))
        vectors = [item.embedding for item in resp.data]
        return np.asarray(vectors, dtype=np.float32)


# Backward-compat alias
OpenAIEmbeddingProvider = OpenAIProvider
