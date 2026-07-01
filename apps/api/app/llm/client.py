"""One hosted model, one base URL, Anthropic Messages API shape.

The operator configures ``LLM_BASE_URL`` + ``LLM_API_KEY`` once; end users never
provide keys. When no key is configured the client reports itself unavailable
and the research pipeline uses its deterministic extractive fallback instead of
crashing.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.config import settings
from app.logging import get_logger

log = get_logger("llm")


class LLMError(RuntimeError):
    """Raised when the hosted model call fails."""


class LLMClient:
    def __init__(self) -> None:
        self.model = settings.llm_model

    def available(self) -> bool:
        return settings.llm_configured

    def _headers(self) -> dict[str, str]:
        return {
            "content-type": "application/json",
            "x-api-key": settings.llm_api_key,
            "anthropic-version": settings.llm_anthropic_version,
            # Bearer included for proxies that expect it; harmless for real Anthropic.
            "authorization": f"Bearer {settings.llm_api_key}",
        }

    def _endpoint(self) -> str:
        base = settings.llm_base_url.rstrip("/")
        return f"{base}/v1/messages"

    def _body(
        self,
        messages: list[dict[str, str]],
        system: str | None,
        max_tokens: int | None,
        temperature: float,
        stream: bool,
    ) -> dict:
        body: dict = {
            "model": settings.llm_model,
            "max_tokens": max_tokens or settings.llm_max_tokens,
            "temperature": temperature,
            "messages": messages,
            "stream": stream,
        }
        if system:
            body["system"] = system
        return body

    async def chat(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.3,
    ) -> str:
        """Return the full completion text (non-streaming)."""
        if not self.available():
            raise LLMError("LLM is not configured")
        body = self._body(messages, system, max_tokens, temperature, stream=False)
        try:
            async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
                resp = await client.post(self._endpoint(), headers=self._headers(), json=body)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"LLM HTTP {exc.response.status_code}: {exc.response.text[:200]}") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc
        return _extract_text(data)

    async def stream(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.3,
    ) -> AsyncIterator[str]:
        """Yield text deltas as they arrive (SSE)."""
        if not self.available():
            raise LLMError("LLM is not configured")
        body = self._body(messages, system, max_tokens, temperature, stream=True)
        try:
            async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
                async with client.stream(
                    "POST", self._endpoint(), headers=self._headers(), json=body
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        payload = line[len("data:") :].strip()
                        if not payload or payload == "[DONE]":
                            continue
                        try:
                            event = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        if event.get("type") == "content_block_delta":
                            text = event.get("delta", {}).get("text", "")
                            if text:
                                yield text
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM stream failed: {exc}") from exc


def _extract_text(data: dict) -> str:
    """Pull text out of an Anthropic-style response body."""
    content = data.get("content", [])
    if isinstance(content, list):
        parts = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        text = "".join(parts).strip()
        if text:
            return text
    # Some OpenAI-compatible proxies return choices[].message.content.
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        return str(choices[0].get("message", {}).get("content", "")).strip()
    return ""


llm = LLMClient()
