"""susr.llm.anthropic — Anthropic LLMProvider 實作 (預設)。

包 anthropic SDK 的 ``messages.create`` / ``messages.stream``。
預設 model 為 ``claude-opus-4-7`` (per R1 notes §1.5);實務上由
``_client.md`` frontmatter 或 ``ANTHROPIC_MODEL`` env 覆寫。

API key 解析順序:
    1. constructor ``api_key`` 參數
    2. ``ANTHROPIC_API_KEY`` env var
    3. raise RuntimeError + remediation 指向 Claude Desktop config

Lazy init:
    SDK client 在 ``__init__`` **不**連線、**不**驗證 key;首次呼叫
    complete/stream 才透過 ``_ensure_client()`` 建立。原因同 embedding
    providers — doctor 健檢、單元測試、無 key 環境都要能 import 物件。

Anthropic extras (Q17 折衷):
    高階特性透過 ``provider.extras`` 暴露:
        - ``enable_prompt_caching(messages, cache_control=...)`` 把
          指定 message 標 ephemeral cache (Anthropic prompt caching)
        - ``extended_thinking(budget_tokens=...)`` 取得 extended thinking
          (Opus 4+) 的 config 物件,供 caller 帶進下一次 complete()
        - ``count_tokens(messages, system=...)`` 提供 vendor-only API

    呼叫端碰 extras 就明確承認綁定 Anthropic,不假裝 portable。
"""

from __future__ import annotations

import os
from typing import Any, Iterator, Optional

from susr.llm.provider import LLMMessage, LLMResponse


# 預設 model id — 來自 R1 notes §1.5;可由 env 或 caller 覆寫。
_DEFAULT_MODEL = "claude-opus-4-7"


def _split_system(
    messages: list[LLMMessage],
    system: Optional[str],
) -> tuple[Optional[str], list[dict]]:
    """把 messages 拆成 (system_text, non_system_messages)。

    Anthropic SDK 的 ``messages.create`` 把 system 當頂層參數 (不在
    messages list 裡),所以要把 role=='system' 的 message 抽出來。
    若 caller 同時傳 ``system`` 與 system message,合併 (caller 的
    優先放前面,讓後續 message override)。
    """
    sys_parts: list[str] = []
    if system:
        sys_parts.append(system)
    out: list[dict] = []
    for m in messages:
        if m.role == "system":
            sys_parts.append(m.content)
        else:
            out.append({"role": m.role, "content": m.content})
    system_text = "\n\n".join(sys_parts) if sys_parts else None
    return system_text, out


class AnthropicProvider:
    """anthropic SDK 包裝;sync API (對齊 MCP server stdio handler)。"""

    name = "anthropic"

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        model: str = _DEFAULT_MODEL,
        base_url: Optional[str] = None,
    ) -> None:
        """建立 provider,**不**連線。

        Args:
            api_key: 覆寫 ``ANTHROPIC_API_KEY`` env。
            model: Anthropic model id (預設 ``claude-opus-4-7``)。
            base_url: 給 proxy / private deployment 用。
        """
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._client = None  # type: ignore[var-annotated]
        self._extras: Optional[AnthropicExtras] = None

    def _ensure_client(self) -> None:
        """Lazy 建 SDK client + 驗證 key。

        Trap 避免:
            - None-check 必要 — 載入失敗 (例:無 key、SDK 版本不符)
              不可污染 ``self._client``,讓下次呼叫能重試或顯示完整錯誤。
        """
        if self._client is not None:
            return
        try:
            from anthropic import Anthropic  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "AnthropicProvider 需要 anthropic SDK — "
                "預設已在 susr 主依賴,請確認 `pip install susr` 成功"
            ) from exc

        key = self._api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY 未設定 — "
                "請在 Claude Desktop config 的 mcpServers.susr.env 補上"
            )

        kwargs: dict = {"api_key": key}
        if self._base_url:
            kwargs["base_url"] = self._base_url
        self._client = Anthropic(**kwargs)

    def complete(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict]] = None,
        system: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Single-shot completion → ``LLMResponse``。

        Tool use:
            若 model 回 ``stop_reason == 'tool_use'``,將 tool_use blocks
            轉成 ``LLMResponse.tool_calls`` (list of dict),caller 自行
            處理 round-trip。文字 block 集合成 ``content``。
        """
        self._ensure_client()
        assert self._client is not None

        system_text, msg_dicts = _split_system(messages, system)
        kwargs: dict = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": msg_dicts,
        }
        if system_text:
            kwargs["system"] = system_text
        if tools:
            kwargs["tools"] = tools

        resp = self._client.messages.create(**kwargs)

        # 解析 content blocks — text 與 tool_use 各歸各。
        text_parts: list[str] = []
        tool_calls: list[dict] = []
        for block in resp.content:
            btype = getattr(block, "type", None)
            if btype == "text":
                text_parts.append(getattr(block, "text", ""))
            elif btype == "tool_use":
                tool_calls.append({
                    "id": getattr(block, "id", None),
                    "name": getattr(block, "name", None),
                    "arguments": getattr(block, "input", {}),
                })

        usage = None
        if getattr(resp, "usage", None) is not None:
            u = resp.usage
            usage = {
                "input_tokens": getattr(u, "input_tokens", None),
                "output_tokens": getattr(u, "output_tokens", None),
                # caching 統計;若無 extras 可能為 None
                "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", None),
                "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", None),
            }

        return LLMResponse(
            content="".join(text_parts),
            tool_calls=tool_calls or None,
            usage=usage,
            stop_reason=getattr(resp, "stop_reason", None),
            model=getattr(resp, "model", self._model),
        )

    def stream(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict]] = None,
        system: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> Iterator[str]:
        """串流 text chunks。yield 純文字 delta;tool_use 與 metadata 略過。

        若 caller 需 raw event stream (含 tool_use blocks),走 extras
        或直接拿 client 自行呼叫;此處只做 UI rendering 用的 text-only
        簡化路徑。
        """
        self._ensure_client()
        assert self._client is not None

        system_text, msg_dicts = _split_system(messages, system)
        kwargs: dict = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": msg_dicts,
        }
        if system_text:
            kwargs["system"] = system_text
        if tools:
            kwargs["tools"] = tools

        with self._client.messages.stream(**kwargs) as stream:
            for chunk in stream.text_stream:
                yield chunk

    @property
    def extras(self) -> "AnthropicExtras":
        """暴露 Anthropic-specific 高階特性 (見 module docstring)。"""
        if self._extras is None:
            self._extras = AnthropicExtras(self)
        return self._extras


class AnthropicExtras:
    """Anthropic vendor-specific 特性 — 不在 cross-vendor 抽象內。

    呼叫此物件的 code 就**明確承認**綁定 Anthropic;未來換 OpenAI/Gemini
    時需重寫該段邏輯,不會有 silent breakage (因為 OpenAIProvider /
    GeminiProvider 的 extras 是各自獨立的 class)。
    """

    def __init__(self, provider: AnthropicProvider) -> None:
        self._p = provider

    def enable_prompt_caching(
        self,
        messages: list[dict],
        cache_control: Optional[dict] = None,
    ) -> list[dict]:
        """把指定 messages 標 cache_control,啟用 Anthropic prompt caching。

        Args:
            messages: 已轉為 Anthropic SDK dict 格式的 messages
                (e.g. complete() 內部 ``msg_dicts``)。
            cache_control: 預設 ``{"type": "ephemeral"}``;caller 可
                自訂 ttl 等。

        Returns:
            修改後的 messages (in-place + return,方便 chaining)。

        典型用法:給長 system / KB context 標 ephemeral,後續對話省 token。
        最多標 4 個 cache breakpoints (Anthropic 限制)。
        """
        cc = cache_control or {"type": "ephemeral"}
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, str):
                msg["content"] = [{"type": "text", "text": content, "cache_control": cc}]
            elif isinstance(content, list):
                # 已是 block list — 在最後一個 block 掛 cache_control
                if content:
                    content[-1]["cache_control"] = cc
        return messages

    def extended_thinking(self, *, budget_tokens: int) -> dict:
        """回 extended thinking config dict,caller 帶進下次 complete 的 raw kwargs。

        Opus 4+ 支援 extended thinking — 模型在回答前先「想」一段,可顯著
        提升複雜推理品質。本方法僅產 config 物件;實際使用要透過 raw
        SDK (因 ``complete()`` 介面已固定);未來可考慮把 ``thinking``
        參數加進 ``complete()`` signature,但目前留在 extras 避免抽象
        滲漏。

        Args:
            budget_tokens: 思考預算 (建議 >= 1024;越多越深入)。

        Returns:
            ``{"type": "enabled", "budget_tokens": N}`` 直接送 SDK。
        """
        return {"type": "enabled", "budget_tokens": budget_tokens}

    def count_tokens(
        self,
        messages: list[LLMMessage],
        system: Optional[str] = None,
    ) -> int:
        """呼叫 Anthropic ``messages.count_tokens`` (vendor-only 端點)。

        用於 prompt budget 規劃 (e.g. 確認 context 不超 200K)。
        若 SDK 版本太舊無此方法,raise AttributeError (caller 自處理)。
        """
        self._p._ensure_client()
        assert self._p._client is not None
        system_text, msg_dicts = _split_system(messages, system)
        kwargs: dict = {"model": self._p._model, "messages": msg_dicts}
        if system_text:
            kwargs["system"] = system_text
        resp = self._p._client.messages.count_tokens(**kwargs)
        return getattr(resp, "input_tokens", 0)
