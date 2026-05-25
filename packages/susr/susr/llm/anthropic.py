"""susr.llm.anthropic — Anthropic LLMProvider implementation (default).

Wraps the official `anthropic` SDK.  Default model is the latest Claude
production tier (configurable per `_client.md` or env var).

API key resolution order (R2 will implement):
    1. constructor arg
    2. ANTHROPIC_API_KEY env var
    3. raise with remediation message pointing at Claude Desktop config

R1: signature scaffold.  R2: implement complete + stream with tool use.
"""

from __future__ import annotations

from typing import AsyncIterator, Optional

from susr.llm.provider import CompletionResult, Message


class AnthropicProvider:
    """anthropic.AsyncAnthropic-backed LLMProvider."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: str = "claude-opus-4-7",
        base_url: Optional[str] = None,
    ) -> None:
        """Construct provider with API key + default model.

        Args:
            api_key: overrides ANTHROPIC_API_KEY env
            model: anthropic model id (defaults to current Opus tier)
            base_url: for proxies / private deployments
        """
        raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §6.5")

    @property
    def name(self) -> str:
        raise NotImplementedError("Step 1 R2 — return f'anthropic:{self._model}'")

    async def complete(
        self,
        messages: list[Message],
        *,
        system: Optional[str] = None,
        tools: Optional[list[dict]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> CompletionResult:
        raise NotImplementedError("Step 1 R2 — adapt anthropic.AsyncAnthropic.messages.create()")

    async def stream(
        self,
        messages: list[Message],
        *,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        raise NotImplementedError("Step 1 R2 — adapt anthropic.AsyncAnthropic.messages.stream()")
