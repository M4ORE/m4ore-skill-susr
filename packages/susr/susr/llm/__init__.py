"""susr.llm — Pluggable LLM providers.

Day-1 abstraction per CLAUDE.md §8 decision 8: even though Anthropic is
the only target for MVP, we keep the surface behind a Protocol so
Phase B (multi-agent CLI support) does not require a refactor.

Spec §6.5 explains the trade-off and the risk that the Protocol is
too thin to abstract Anthropic-specific features (tool use, extended
thinking).  R2 implementations should keep provider-specific config
in dedicated dataclasses, not as kwargs soup.

Default provider: Anthropic (susr.llm.anthropic).
"""

from __future__ import annotations

from susr.llm.provider import LLMProvider

__all__ = ["LLMProvider"]
