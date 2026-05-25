"""susr.llm.provider — LLMProvider Protocol。

依 CLAUDE.md §8 decision 5/8 與 Q17:day-1 抽象 + vendor extras 折衷。
所有需呼叫 LLM 的 susr code 透過此 Protocol;**不**直接 import
anthropic SDK 進 domain logic。

Q17 折衷重點:
    - 共通介面薄 (complete + stream),只承諾 cross-vendor 一定有的
      message → text 與 tool-use 行為
    - vendor-specific 高階特性 (prompt caching / extended thinking /
      interleaved thinking) 透過 ``provider.extras`` 暴露,呼叫端如果
      用了 extras 就**明確承認**綁定該 vendor,不假裝是 portable

R2 不做 async (spec §6.5 原本標 async,但 MCP server 在 stdio 端
本身是 sync handler,brain orchestrator 也以 sync 為主;先 sync,
未來需要 streaming UI 再加 async wrapper)。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, Literal, Optional, Protocol, runtime_checkable


@dataclass
class LLMMessage:
    """Chat message envelope used across providers."""

    role: Literal["user", "assistant", "system"]
    content: str


@dataclass
class LLMToolCall:
    """Provider-agnostic tool invocation request from the model."""

    name: str
    arguments: dict
    # 部分 vendor (e.g. Anthropic) 會帶 tool_use_id 給 result 配對
    id: Optional[str] = None


@dataclass
class LLMResponse:
    """Result envelope for a non-streaming completion call."""

    content: str
    tool_calls: Optional[list[dict]] = None
    usage: Optional[dict] = None
    # 給呼叫端 inspect 用 (e.g. "end_turn" vs "tool_use" vs "max_tokens")
    stop_reason: Optional[str] = None
    # 回傳的 raw model id,讓 logging / billing 對得回去
    model: Optional[str] = None


# Backward-compat aliases — R1 既有 pydantic 版本的 imports 不會壞
Message = LLMMessage
CompletionResult = LLMResponse


@runtime_checkable
class LLMProvider(Protocol):
    """Sync chat-completion provider (with optional streaming)。

    Implementations MUST:
        - 提供穩定的 ``name`` 屬性
        - ``complete`` / ``stream`` 兩條路徑
        - ``extras`` property 暴露 vendor-specific 子物件 (可為 None
          if no extras supported)
    """

    name: str

    def complete(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict]] = None,
        system: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Single-shot completion。回傳 text + 可選 tool_calls。"""
        ...

    def stream(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict]] = None,
        system: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> Iterator[str]:
        """串流回傳 text chunks 給 UI 渲染。"""
        ...

    @property
    def extras(self) -> Any:
        """Vendor-specific 高階特性 (caching / extended thinking / etc.)。

        呼叫端碰 extras 就明確承認綁定該 vendor;cross-vendor swap
        時要重寫此處邏輯。
        """
        ...
