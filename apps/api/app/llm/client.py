"""LLM client for the hosted gateway (multiple models behind one base URL).

Default transport is the OpenAI Chat Completions API (`/v1/chat/completions`),
which every provider on the gateway (Claude, Llama, Kimi) speaks and which
supports tool-calling uniformly. Set ``LLM_API_STYLE=anthropic`` to target
``/v1/messages`` instead (no tool-calling on that path).

The client never raises to the caller for expected failures — the research
pipeline falls back to a deterministic extractive answer when the LLM is
unavailable, so the app always responds.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx

from app.config import settings
from app.logging import get_logger

log = get_logger("llm")


class LLMError(RuntimeError):
    """Raised when a hosted model call fails."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict
    raw: dict = field(default_factory=dict)


@dataclass
class ChatResult:
    content: str
    tool_calls: list[ToolCall]
    raw_message: dict = field(default_factory=dict)


class LLMClient:
    def available(self) -> bool:
        return settings.llm_configured

    def _headers(self) -> dict[str, str]:
        key = settings.llm_api_key
        if settings.llm_api_style == "anthropic":
            return {
                "content-type": "application/json",
                "x-api-key": key,
                "anthropic-version": settings.llm_anthropic_version,
                "authorization": f"Bearer {key}",
            }
        return {"content-type": "application/json", "authorization": f"Bearer {key}"}

    def _endpoint(self) -> str:
        base = settings.llm_base_url.rstrip("/")
        if settings.llm_api_style == "anthropic":
            return f"{base}/v1/messages"
        return f"{base}/v1/chat/completions"

    # ---- Non-streaming chat (supports tools) -------------------------------- #
    async def chat(
        self,
        messages: list[dict],
        model: str,
        system: str | None = None,
        tools: list[dict] | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> ChatResult:
        if not self.available():
            raise LLMError("LLM is not configured")
        payload = self._build_payload(messages, model, system, tools, temperature, max_tokens, False)
        try:
            async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
                resp = await client.post(self._endpoint(), headers=self._headers(), json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"LLM HTTP {exc.response.status_code}: {exc.response.text[:200]}") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc
        return _parse_chat(data)

    # ---- Streaming text (no tools) ------------------------------------------ #
    async def stream(
        self,
        messages: list[dict],
        model: str,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        if not self.available():
            raise LLMError("LLM is not configured")
        payload = self._build_payload(messages, model, system, None, temperature, max_tokens, True)
        try:
            async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
                async with client.stream(
                    "POST", self._endpoint(), headers=self._headers(), json=payload
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        chunk = line[5:].strip()
                        if not chunk or chunk == "[DONE]":
                            continue
                        try:
                            event = json.loads(chunk)
                        except json.JSONDecodeError:
                            continue
                        text = _stream_delta(event)
                        if text:
                            yield text
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM stream failed: {exc}") from exc

    def _build_payload(
        self,
        messages: list[dict],
        model: str,
        system: str | None,
        tools: list[dict] | None,
        temperature: float,
        max_tokens: int | None,
        stream: bool,
    ) -> dict:
        if settings.llm_api_style == "anthropic":
            body: dict = {
                "model": model,
                "max_tokens": max_tokens or settings.llm_max_tokens,
                "temperature": temperature,
                "messages": messages,
                "stream": stream,
            }
            if system:
                body["system"] = system
            return body
        # OpenAI chat completions
        full_messages = ([{"role": "system", "content": system}] if system else []) + messages
        body = {
            "model": model,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or settings.llm_max_tokens,
            "stream": stream,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        return body


def _parse_chat(data: dict) -> ChatResult:
    # OpenAI shape
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {}) or {}
        content = message.get("content") or ""
        tool_calls: list[ToolCall] = []
        for tc in message.get("tool_calls") or []:
            fn = tc.get("function", {})
            args = fn.get("arguments", "{}")
            try:
                parsed = json.loads(args) if isinstance(args, str) else (args or {})
            except json.JSONDecodeError:
                parsed = {}
            tool_calls.append(
                ToolCall(id=tc.get("id", ""), name=fn.get("name", ""), arguments=parsed, raw=tc)
            )
        return ChatResult(content=content, tool_calls=tool_calls, raw_message=message)
    # Anthropic shape
    blocks = data.get("content", [])
    if isinstance(blocks, list):
        text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text")
        return ChatResult(content=text.strip(), tool_calls=[], raw_message={})
    return ChatResult(content="", tool_calls=[], raw_message={})


def _stream_delta(event: dict) -> str:
    # OpenAI streaming
    choices = event.get("choices")
    if isinstance(choices, list) and choices:
        return choices[0].get("delta", {}).get("content", "") or ""
    # Anthropic streaming
    if event.get("type") == "content_block_delta":
        return event.get("delta", {}).get("text", "") or ""
    return ""


llm = LLMClient()
