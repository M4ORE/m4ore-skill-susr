"""Layer 4 — EmbeddingProvider Protocol conformance（spec §5.1）。

不真的載入 BGE-M3 / Qwen3 / OpenAI（會拖慢且需網路 + 模型 weights）。
測試對象：
    - Protocol 的 runtime_checkable 行為（@runtime_checkable 對 attr 檢查）
    - mock_embedding_provider fixture 通過 isinstance 檢查
    - mock provider 行為符合 spec（embed_query / embed_documents 形狀正確）
    - 確定性：同 input → 同 output（測 hash-based mock 行為）
"""

from __future__ import annotations

import numpy as np

from susr.embeddings.provider import EmbeddingProvider


def test_mock_provider_satisfies_protocol(mock_embedding_provider) -> None:
    """mock_embedding_provider 應 isinstance(EmbeddingProvider) — Protocol 對齊。"""
    assert isinstance(mock_embedding_provider, EmbeddingProvider)


def test_mock_provider_has_required_attributes(mock_embedding_provider) -> None:
    """Protocol 要求 name / dimension / hosting 三個 attr。"""
    assert isinstance(mock_embedding_provider.name, str)
    assert isinstance(mock_embedding_provider.dimension, int)
    assert mock_embedding_provider.dimension > 0
    assert mock_embedding_provider.hosting in ("local", "cloud")


def test_mock_provider_embed_query_shape(mock_embedding_provider) -> None:
    """embed_query 回 shape == (dimension,) 的 ndarray。"""
    vec = mock_embedding_provider.embed_query("永續報告書")
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (mock_embedding_provider.dimension,)
    assert vec.dtype == np.float32


def test_mock_provider_embed_documents_shape(mock_embedding_provider) -> None:
    """embed_documents 回 shape == (N, dimension) 的 ndarray。"""
    texts = ["a", "b", "c"]
    matrix = mock_embedding_provider.embed_documents(texts)
    assert isinstance(matrix, np.ndarray)
    assert matrix.shape == (3, mock_embedding_provider.dimension)


def test_mock_provider_is_deterministic(mock_embedding_provider) -> None:
    """同 input → 同 output（mock 是 hash-based）。"""
    v1 = mock_embedding_provider.embed_query("氣候變遷")
    v2 = mock_embedding_provider.embed_query("氣候變遷")
    np.testing.assert_array_equal(v1, v2)


def test_mock_provider_different_inputs_give_different_vectors(
    mock_embedding_provider,
) -> None:
    """不同 input → 至少有部分位元不同。"""
    v1 = mock_embedding_provider.embed_query("氣候變遷")
    v2 = mock_embedding_provider.embed_query("水資源")
    assert not np.array_equal(v1, v2)


def test_mock_provider_embed_documents_empty_list(mock_embedding_provider) -> None:
    """空 list → 回 shape == (0, dimension) 或 (0,)（兩者都可接受）。"""
    out = mock_embedding_provider.embed_documents([])
    assert isinstance(out, np.ndarray)
    assert out.shape[0] == 0


# ---------------------------------------------------------------------------
# 已實作 provider 的 import smoke（不實際 instantiate）
# ---------------------------------------------------------------------------


def test_bge_m3_provider_class_importable() -> None:
    """BgeM3EmbeddingProvider 應可 import；屬性 name / hosting / dimension 對齊 spec。

    name 接受 ``bge-m3`` 或 ``bge:bge-m3`` 兩種寫法（spec §5.2 用後者，
    R1 stub 用前者；R2 收斂時擇一）。
    """
    from susr.embeddings.bge_m3 import BgeM3EmbeddingProvider

    assert BgeM3EmbeddingProvider.name in ("bge:bge-m3", "bge-m3")
    assert BgeM3EmbeddingProvider.hosting == "local"
    # dimension 可能是 class attr 或 property，兩種都接受；值必須 1024（DDL 對齊）
    assert getattr(BgeM3EmbeddingProvider, "dimension", None) == 1024


def test_openai_provider_class_importable() -> None:
    """OpenAIEmbeddingProvider 應可 import（不 instantiate，避免 API key 要求）。"""
    from susr.embeddings import openai as openai_mod

    # 至少要有 provider class
    assert hasattr(openai_mod, "OpenAIEmbeddingProvider") or hasattr(
        openai_mod, "OpenAiEmbeddingProvider"
    )


def test_qwen3_provider_class_importable() -> None:
    """Qwen3EmbeddingProvider 應可 import（spec §5.2 三個 provider 之一）。"""
    from susr.embeddings import qwen3 as qwen3_mod

    # 至少要有 module，不強制 class 名（R2 可定）
    assert qwen3_mod is not None
