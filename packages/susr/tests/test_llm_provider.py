"""Layer 4 — LLMProvider Protocol conformance（spec §6.5 + R1 modifications）。

不真的 call Anthropic API（要 key + 網路 + 花錢）。測試對象：
    - LLMMessage / LLMToolCall / LLMResponse dataclass 行為
    - LLMProvider Protocol runtime_checkable 行為
    - 自製 mock 通過 isinstance(LLMProvider)
    - AnthropicProvider class 可 import + 簽名對齊（不 instantiate 觸發 SDK）
    - 兼容 alias: Message / CompletionResult

注意：R1 把原 spec §6.5 的 async API 改成 sync（對齊 MCP stdio handler）。
"""

from __future__ import annotations

from typing import Any, Iterator, Optional

import pytest

from susr.llm.provider import (
    CompletionResult,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    LLMToolCall,
    Message,
)


# ---------------------------------------------------------------------------
# Dataclass models — basic field checks
# ---------------------------------------------------------------------------


def test_llm_message_basic_roles() -> None:
    """LLMMessage 接受三種 role。"""
    for r in ("user", "assistant", "system"):
        m = LLMMessage(role=r, content="hi")  # type: ignore[arg-type]
        assert m.role == r
        assert m.content == "hi"


def test_message_alias_points_to_llm_message() -> None:
    """backward-compat alias Message == LLMMessage。"""
    assert Message is LLMMessage


def test_completion_result_alias_points_to_llm_response() -> None:
    """backward-compat alias CompletionResult == LLMResponse。"""
    assert CompletionResult is LLMResponse


def test_llm_tool_call_basic() -> None:
    """LLMToolCall 基本欄位 + 可選 id。"""
    tc = LLMToolCall(name="search_topics", arguments={"industry": "hotel"})
    assert tc.name == "search_topics"
    assert tc.arguments == {"industry": "hotel"}
    assert tc.id is None
    tc2 = LLMToolCall(name="x", arguments={}, id="toolu_123")
    assert tc2.id == "toolu_123"


def test_llm_response_minimal() -> None:
    """LLMResponse 只給 content → 其餘欄位為 None。"""
    r = LLMResponse(content="hello")
    assert r.content == "hello"
    assert r.tool_calls is None
    assert r.usage is None
    assert r.stop_reason is None
    assert r.model is None


def test_llm_response_full() -> None:
    """LLMResponse 帶完整 metadata。"""
    r = LLMResponse(
        content="hi",
        tool_calls=[{"id": "t1", "name": "search", "arguments": {}}],
        usage={"input_tokens": 100, "output_tokens": 50},
        stop_reason="end_turn",
        model="claude-opus-4-7",
    )
    assert r.tool_calls is not None and len(r.tool_calls) == 1
    assert r.usage["input_tokens"] == 100  # type: ignore[index]
    assert r.stop_reason == "end_turn"


# ---------------------------------------------------------------------------
# Protocol conformance — define a sync mock that satisfies the Protocol
# ---------------------------------------------------------------------------


class _MockLLM:
    """假 LLMProvider 用於 Protocol 對齊測試 — 不真的 call API。"""

    name = "mock:fake-model"

    def complete(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict]] = None,
        system: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        return LLMResponse(content="mock response", model="mock")

    def stream(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict]] = None,
        system: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> Iterator[str]:
        yield "mock chunk"

    @property
    def extras(self) -> Any:
        return None


def test_mock_llm_satisfies_protocol() -> None:
    """_MockLLM 應 isinstance(LLMProvider) — runtime Protocol 檢查。"""
    assert isinstance(_MockLLM(), LLMProvider)


def test_mock_complete_returns_llm_response() -> None:
    """_MockLLM.complete 行為 — sync 回 LLMResponse。"""
    out = _MockLLM().complete([LLMMessage(role="user", content="hi")])
    assert isinstance(out, LLMResponse)
    assert out.content == "mock response"


def test_mock_stream_is_iterator() -> None:
    """_MockLLM.stream 回 iterator of str。"""
    chunks = list(_MockLLM().stream([LLMMessage(role="user", content="hi")]))
    assert chunks == ["mock chunk"]


# ---------------------------------------------------------------------------
# AnthropicProvider — import + class-shape smoke only
# ---------------------------------------------------------------------------


def test_anthropic_provider_importable() -> None:
    """AnthropicProvider 應可 import（不 instantiate 觸發 anthropic SDK）。"""
    from susr.llm.anthropic import AnthropicProvider

    assert AnthropicProvider is not None
    # Protocol-required attrs
    for attr in ("complete", "stream", "name", "extras"):
        assert hasattr(AnthropicProvider, attr), f"AnthropicProvider missing {attr}"


def test_anthropic_provider_construct_without_key() -> None:
    """AnthropicProvider __init__ 不該觸發 API key 檢查（lazy init 設計）。"""
    from susr.llm.anthropic import AnthropicProvider

    # 不該 raise — 即使沒 ANTHROPIC_API_KEY env
    provider = AnthropicProvider(api_key=None)
    assert provider is not None
    # name 是 class attr，不要求 SDK
    assert provider.name == "anthropic"


def test_anthropic_provider_extras_lazy(monkeypatch) -> None:
    """provider.extras 應 lazily 建立 AnthropicExtras（不需 client）。"""
    from susr.llm.anthropic import AnthropicExtras, AnthropicProvider

    provider = AnthropicProvider(api_key=None)
    extras = provider.extras
    assert isinstance(extras, AnthropicExtras)
    # 第二次取 → 同物件（cache）
    assert provider.extras is extras


def test_anthropic_extras_extended_thinking_config_shape() -> None:
    """extras.extended_thinking 回固定 shape dict（不需 client）。"""
    from susr.llm.anthropic import AnthropicProvider

    provider = AnthropicProvider(api_key=None)
    cfg = provider.extras.extended_thinking(budget_tokens=2048)
    assert cfg == {"type": "enabled", "budget_tokens": 2048}


def test_anthropic_extras_prompt_caching_marks_messages() -> None:
    """extras.enable_prompt_caching 把 str content 包成 list[dict]。"""
    from susr.llm.anthropic import AnthropicProvider

    provider = AnthropicProvider(api_key=None)
    msgs = [{"role": "user", "content": "hello"}]
    out = provider.extras.enable_prompt_caching(msgs)
    assert isinstance(out[0]["content"], list)
    block = out[0]["content"][0]
    assert block["type"] == "text"
    assert block["text"] == "hello"
    assert block["cache_control"] == {"type": "ephemeral"}


def test_anthropic_complete_without_key_raises() -> None:
    """無 key 環境下 complete() 應 raise RuntimeError（_ensure_client 守門）。"""
    import os

    from susr.llm.anthropic import AnthropicProvider

    # 確保沒 key
    old = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        provider = AnthropicProvider(api_key=None)
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            provider.complete([LLMMessage(role="user", content="hi")])
    finally:
        if old is not None:
            os.environ["ANTHROPIC_API_KEY"] = old
