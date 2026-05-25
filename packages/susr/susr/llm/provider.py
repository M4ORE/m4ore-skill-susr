"""susr.llm.provider — LLMProvider Protocol.

Per CLAUDE.md §8 decision 5+8: day-1 abstraction. All susr code that
needs to call an LLM (synthesis, summarization, gap-analysis prose)
goes through this Protocol — never directly against the Anthropic SDK.

Spec §6.5 documents the risk that this layer ends up being a thin
pass-through to Anthropic with kwargs leaking provider-specific
features. R2 should keep Anthropic-specific config (tool use,
extended thinking) in a typed sub-config object, not bare kwargs.
"""

from __future__ import annotations

from typing import AsyncIterator, Literal, Optional, Protocol, runtime_checkable

from pydantic import BaseModel


class Message(BaseModel):
    """Chat message envelope used across providers."""

    role: Literal["user", "assistant", "system"]
    content: str


class ToolCall(BaseModel):
    """Provider-agnostic tool invocation request from the model."""

    name: str
    arguments: dict


class CompletionResult(BaseModel):
    """Result envelope for a non-streaming completion call."""

    text: str
    tool_calls: list[ToolCall] = []
    usage: dict = {}


@runtime_checkable
class LLMProvider(Protocol):
    """Async chat-completion provider."""

    @property
    def name(self) -> str:
        """Stable identifier, e.g. 'anthropic:claude-opus-4-7'."""
        ...

    async def complete(
        self,
        messages: list[Message],
        *,
        system: Optional[str] = None,
        tools: Optional[list[dict]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> CompletionResult:
        """Single-shot completion returning text (+ optional tool_calls)."""
        ...

    async def stream(
        self,
        messages: list[Message],
        *,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        """Stream completion text chunks for UI rendering."""
        ...
