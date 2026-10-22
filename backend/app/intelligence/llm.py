"""The only place that talks to OpenRouter chat completions.

`stream_lines` yields one burst per completed line as tokens arrive, so the first
burst can be sent before generation finishes.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx

from app.config import Settings

log = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


@dataclass
class LLMStats:
    model: str = ""
    provider: str = ""
    ttft_ms: float | None = None
    finish_reason: str | None = None
    tool_calls: list[dict] = field(default_factory=list)  # [{"name": str, "arguments": dict}] after the stream
    total_ms: float = 0.0
    usage: dict = field(default_factory=dict)


def system_message(stable: str, dynamic: str) -> dict:
    """Stable prefix gets a cache breakpoint (honoured by Anthropic/Gemini; others cache automatically)."""
    return {
        "role": "system",
        "content": [
            {"type": "text", "text": stable, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": dynamic},
        ],
    }


class LLMClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self.s = settings
        self.http = client

    def _headers(self) -> dict:
        if not self.s.openrouter_api_key:
            raise LLMError("no OpenRouter key configured")
        return {
            "Authorization": f"Bearer {self.s.openrouter_api_key}",
            "HTTP-Referer": self.s.site_origin,
            "X-Title": "Virtual Me",
        }

    async def stream_lines(
        self,
        messages: list[dict],
        *,
        max_tokens: int,
        stats: LLMStats,
        models: list[str] | None = None,
        temperature: float | None = None,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        models = models or self.s.llm_models
        body = {
            "model": models[0],
            "models": models,
            "messages": messages,
            "stream": True,
            "max_tokens": max_tokens,
            "temperature": self.s.llm_temperature if temperature is None else temperature,
            "provider": {"sort": "latency"},
            # Reasoning models otherwise spend max_tokens on hidden thinking and emit nothing (seen with
            # claude-haiku-5.5 on the full prompt). Texting needs no chain of thought.
            "reasoning": {"enabled": False},
            "usage": {"include": True},
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        calls: dict[int, dict] = {}  # tool-call deltas arrive in fragments, keyed by index
        t0 = time.perf_counter()
        buf = ""
        async with asyncio.timeout(self.s.llm_total_timeout_s):
            async with self.http.stream(
                "POST", f"{self.s.openrouter_base}/v1/chat/completions",
                json=body, headers=self._headers(), timeout=self.s.llm_total_timeout_s,
            ) as resp:
                if resp.status_code != 200:
                    raise LLMError(f"http {resp.status_code}: {(await resp.aread())[:200]!r}")
                lines = resp.aiter_lines()
                while True:
                    try:
                        if stats.ttft_ms is None:
                            line = await asyncio.wait_for(anext(lines), self.s.llm_first_token_timeout_s)
                        else:
                            line = await anext(lines)
                    except StopAsyncIteration:
                        break
                    except TimeoutError as e:
                        raise LLMError("first token timeout") from e
                    if not line.startswith("data:"):
                        continue  # SSE comments like ": OPENROUTER PROCESSING"
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    if "error" in chunk:
                        raise LLMError(str(chunk["error"])[:200])
                    stats.model = chunk.get("model", stats.model)
                    stats.provider = chunk.get("provider", stats.provider)
                    if chunk.get("usage"):
                        stats.usage = chunk["usage"]
                    for choice in chunk.get("choices") or []:
                        if choice.get("finish_reason"):
                            stats.finish_reason = choice["finish_reason"]
                        for tc in (choice.get("delta") or {}).get("tool_calls") or []:
                            slot = calls.setdefault(tc.get("index", 0), {"name": "", "arguments": ""})
                            fn = tc.get("function") or {}
                            slot["name"] += fn.get("name") or ""
                            slot["arguments"] += fn.get("arguments") or ""
                        delta = (choice.get("delta") or {}).get("content") or ""
                        if not delta:
                            continue
                        if stats.ttft_ms is None:
                            stats.ttft_ms = (time.perf_counter() - t0) * 1000
                        buf += delta
                        while "\n" in buf:
                            out, buf = buf.split("\n", 1)
                            if out.strip():
                                yield out.strip()
        if buf.strip() and stats.finish_reason != "length":
            yield buf.strip()  # a line cut off by max_tokens is dropped, never sent half-finished
        for _, c in sorted(calls.items()):
            try:
                args = json.loads(c["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            if c["name"]:
                stats.tool_calls.append({"name": c["name"], "arguments": args if isinstance(args, dict) else {}})
        stats.total_ms = (time.perf_counter() - t0) * 1000

    async def complete_json(self, messages: list[dict], *, model: str | None = None,
                            max_tokens: int = 400, timeout: float = 10.0) -> dict:
        body = {
            "model": model or self.s.llm_cheap_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0,
            "reasoning": {"enabled": False},
            "response_format": {"type": "json_object"},
        }
        try:
            resp = await self.http.post(f"{self.s.openrouter_base}/v1/chat/completions",
                                        json=body, headers=self._headers(), timeout=timeout)
        except httpx.HTTPError as e:
            raise LLMError(f"transport: {e!r}") from e
        if resp.status_code != 200:
            raise LLMError(f"http {resp.status_code}: {resp.text[:200]}")
        content = resp.json()["choices"][0]["message"]["content"] or ""
        start, end = content.find("{"), content.rfind("}")
        if start < 0 or end < start:
            raise LLMError("no JSON object in response")
        return json.loads(content[start:end + 1])
