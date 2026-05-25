"""Embedding provider wrappers for Layer 4 benchmark harness.

本模組提供統一的 ``EmbeddingProvider`` Protocol 與三個候選 provider 的 wrapper:

* :class:`BgeM3Provider` — BAAI/bge-m3,本地 sentence-transformers,1024d
* :class:`Qwen3Provider` — Qwen/Qwen3-Embedding-0.6B,本地 sentence-transformers,1024d
* :class:`OpenAIProvider` — OpenAI text-embedding-3-large,雲端 API,3072d

設計理由(對齊 ``docs/research/step1-spec.md §5.2`` `EmbeddingProvider Protocol`):

* 本 harness 只是 **spike** — Provider 介面與 ``packages/susr/susr/embeddings/base.py``
  日後正式版**形態相似但不共用**(harness 跑時 susr package 可能還沒 import-able)。
* Provider 物件 lazy init(模型在 ``__init__`` 才載入,避免 import 時就拉 ~2GB 模型)。
* 沒做 batching tuning / connection pool — 留給 susr package 正式版做。

⚠️ 跑前提醒:

* BgeM3 / Qwen3 需 ``pip install sentence-transformers torch``(可能下載大型模型權重)
* OpenAI 需 ``export OPENAI_API_KEY=...`` 與 ``pip install openai``
* macOS Apple Silicon 會自動走 MPS backend(sentence-transformers 3.x 預設行為)
"""

from __future__ import annotations

import os
import time
from typing import List, Protocol, runtime_checkable

import numpy as np


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class EmbeddingProvider(Protocol):
    """共用 embedding provider 介面。

    Attributes:
        name: 識別字串(出現在 results JSON / summary table)。
        dimension: 嵌入向量維度。corpus / query 必須一致。
        hosting: ``"local"`` | ``"cloud"`` — 給 by-hosting 拆解用。
    """

    name: str
    dimension: int
    hosting: str

    def embed(self, texts: List[str]) -> np.ndarray:  # noqa: D401
        """將 texts 嵌入成 ``(len(texts), dimension)`` 的 ``np.ndarray``。"""
        ...


# ---------------------------------------------------------------------------
# BGE-M3 (local, sentence-transformers)
# ---------------------------------------------------------------------------


class BgeM3Provider:
    """BAAI/bge-m3 — 預設候選之一。

    選擇理由(``step1-spec.md §5.4``):

    1. C-MTEB 中文 retrieval benchmark 長期表現名列前茅
    2. 完全本地,預設避開 Q7 個資合約風險
    3. 多語訓練,中英 ESG 術語混雜表現比純英文模型穩
    4. Apache-2.0 license,可商用
    5. 1024 dim 對 sqlite-vec 友善(比 OpenAI 3072 省 3x 儲存空間)

    代價:
    * 首次下載 ~570MB 模型權重(HF cache)
    * macOS Intel 無 GPU 慢
    """

    name = "bge-m3"
    dimension = 1024
    hosting = "local"

    def __init__(self) -> None:
        # 延遲 import,避免本 module 在沒裝 sentence-transformers 的環境 import 失敗
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "BgeM3Provider 需要 sentence-transformers — "
                "請執行 `pip install sentence-transformers torch`"
            ) from exc

        # BAAI/bge-m3 在 HF Hub 已是 sentence-transformers 相容格式
        self._model = SentenceTransformer("BAAI/bge-m3")

    def embed(self, texts: List[str]) -> np.ndarray:
        # convert_to_numpy=True 直接拿 np.ndarray;normalize 為 False(由 caller 做)
        return self._model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=False,
        )


# ---------------------------------------------------------------------------
# Qwen3-Embedding-0.6B (local, sentence-transformers)
# ---------------------------------------------------------------------------


class Qwen3Provider:
    """Qwen/Qwen3-Embedding-0.6B — 2025 新一代候選。

    選擇理由:

    1. 阿里 2025 發布的新一代 embedding model(訓練資料含大量中文 ESG / 金融文本)
    2. 與 Claude / OpenAI 生態解耦,給 susr 一個「完全離 Anthropic 的選項」
    3. 跑得動的最小尺寸(0.6B params),適合顧問本機
    4. 支援 instruction-aware embedding(可給 task description 提升 retrieval)

    ⚠️ Dimension 待確認:
    Qwen3-Embedding-0.6B 官方文件標 1024;若實際 load 後 ``model.get_sentence_embedding_dimension()``
    不同,跑 harness 時要在 results JSON 校正(本 harness 第一次 init 後可 print 確認)。

    代價:
    * 首次下載 ~1.2GB
    * 比 BGE-M3 大 ~2x,CPU only 慢約 1.5x
    """

    name = "qwen3-embedding-0.6b"
    dimension = 1024  # ⚠️ 待 user 本機跑時實際 print model.get_sentence_embedding_dimension() 確認
    hosting = "local"

    def __init__(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Qwen3Provider 需要 sentence-transformers — "
                "請執行 `pip install sentence-transformers torch`"
            ) from exc

        self._model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")

        # 校正實際 dim(覆寫 class attr,避免 dim mismatch)
        actual_dim = self._model.get_sentence_embedding_dimension()
        if actual_dim and actual_dim != self.__class__.dimension:
            # 不 raise — 而是覆寫 instance attr,讓 caller 拿到正確值
            self.dimension = actual_dim

    def embed(self, texts: List[str]) -> np.ndarray:
        return self._model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=False,
        )


# ---------------------------------------------------------------------------
# OpenAI text-embedding-3-large (cloud, API)
# ---------------------------------------------------------------------------


class OpenAIProvider:
    """OpenAI text-embedding-3-large — 雲端 baseline。

    選擇理由:

    1. 業界 baseline,離 / 留 都需要有它的數字才有 reference
    2. 3072 dim 是 retrieval 上限典型;支援 ``dimensions`` 參數降至 256/1024
       (本 harness v0 用 default 3072,future work:測 1024 truncated)
    3. 多語表現雖不如 BGE-M3 中文專精,但泛化最好

    代價(對 susr 的 Q7 拷問):
    * 需要 OPENAI_API_KEY env var
    * 顧問需與每位客戶簽 DPA 同意 embedding 送 OpenAI
    * Rate limit / API outage 影響顧問即時體感

    成本:本 fixture (~40 corpus + ~22 queries,共 ~30k tokens) < 1 美分。
    """

    name = "openai-text-embedding-3-large"
    dimension = 3072
    hosting = "cloud"

    def __init__(self) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OpenAIProvider 需要 OPENAI_API_KEY 環境變數;"
                "本地測請改用 BgeM3Provider 或 Qwen3Provider"
            )

        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "OpenAIProvider 需要 openai SDK — 請執行 `pip install openai`"
            ) from exc

        self._client = OpenAI(api_key=api_key)
        self._model_id = "text-embedding-3-large"

    def embed(self, texts: List[str]) -> np.ndarray:
        # OpenAI API 單次最多 2048 inputs;本 fixture 不會超過,直接打
        resp = self._client.embeddings.create(model=self._model_id, input=texts)
        vectors = [item.embedding for item in resp.data]
        return np.array(vectors, dtype=np.float32)


# ---------------------------------------------------------------------------
# Registry / Lookup
# ---------------------------------------------------------------------------


PROVIDER_REGISTRY: dict[str, type] = {
    "bge-m3": BgeM3Provider,
    "qwen3": Qwen3Provider,
    "qwen3-embedding-0.6b": Qwen3Provider,
    "openai": OpenAIProvider,
    "openai-text-embedding-3-large": OpenAIProvider,
}


def load_provider(name: str) -> EmbeddingProvider:
    """根據 CLI 短名或全名載入 provider instance(lazy import 大型依賴)。"""

    key = name.lower().strip()
    if key not in PROVIDER_REGISTRY:
        raise ValueError(
            f"未知 provider: {name!r};可用: {sorted(set(PROVIDER_REGISTRY.keys()))}"
        )
    cls = PROVIDER_REGISTRY[key]

    t0 = time.perf_counter()
    instance = cls()
    elapsed = time.perf_counter() - t0
    print(f"[providers] loaded {instance.name} (dim={instance.dimension}, {elapsed:.1f}s)")
    return instance
