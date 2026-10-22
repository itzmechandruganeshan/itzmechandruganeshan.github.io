"""Composio over MCP: Google Calendar + Gmail for booking calls and sending emails (ADR-010).

One Composio session for Chandru's own account (`COMPOSIO_USER_ID`), connected once via an auth link
(`scripts/composio_connect.py`). We open the session's hosted MCP endpoint with the official `mcp` client and
call tools *deterministically* from code (after Jev J4 confirmation); no LLM agent picks these tools.

Two ways in, picked by the key:
  - `ck_…` consumer key → **Composio Connect** (https://connect.composio.dev/mcp, `x-consumer-api-key`). It exposes
    meta tools only: COMPOSIO_GET_TOOL_SCHEMAS (real input schemas), COMPOSIO_MULTI_EXECUTE_TOOL (run a tool),
    COMPOSIO_MANAGE_CONNECTIONS (connect / list Google accounts). Verified against the live server 2026-10-22.
  - `ak_…` project key → developer platform session (`composio.create(..., mcp=True)`), same calls.

Composio's docs disagree on exact tool slugs and argument names, so nothing is hard-coded:
  - tools are resolved by name pattern from `list_tools()` (direct app tools, e.g. GOOGLECALENDAR_CREATE_EVENT);
  - if the endpoint only exposes Composio's meta tools, or MCP is unavailable, calls go through the SDK's
    `session.execute(slug, arguments=...)` instead;
  - arguments are mapped onto each tool's own input schema (see app/tools/calendar.py, notify.py).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
from typing import Any

from app.config import Settings

log = logging.getLogger(__name__)
TOOLKITS = ["googlecalendar", "gmail"]
CONNECT_URL = "https://connect.composio.dev/mcp"
# Canonical slugs, confirmed with COMPOSIO_GET_TOOL_SCHEMAS on 2026-10-22
SLUGS = {"free_slots": "GOOGLECALENDAR_FIND_FREE_SLOTS", "create_event": "GOOGLECALENDAR_CREATE_EVENT",
         "send_email": "GMAIL_SEND_EMAIL", "fetch_thread": "GMAIL_FETCH_MESSAGE_BY_THREAD_ID"}

# kind -> (must match, preferred order of substrings). Resolved against the real tool list at startup.
PATTERNS: dict[str, list[str]] = {
    "free_slots": ["GOOGLECALENDAR_FIND_FREE_SLOTS", "FREE_SLOTS", "FREE_BUSY", "FREEBUSY"],
    "create_event": ["GOOGLECALENDAR_CREATE_EVENT", "CREATE_EVENT"],
    "send_email": ["GMAIL_SEND_EMAIL", "SEND_EMAIL"],
    "fetch_thread": ["GMAIL_FETCH_MESSAGE_BY_THREAD_ID", "THREAD_ID", "FETCH_THREAD", "GET_THREAD"],
}


class ComposioError(RuntimeError):
    pass


def _parse_result(res: Any) -> Any:
    """MCP CallToolResult or SDK response -> plain data."""
    if hasattr(res, "structured_content") and res.structured_content:
        data = res.structured_content
    elif hasattr(res, "content"):
        texts = [getattr(c, "text", "") for c in res.content or []]
        raw = "".join(texts).strip()
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {"text": raw}
        if getattr(res, "is_error", False):
            raise ComposioError(raw[:300] or "tool error")
    else:  # SDK SessionExecuteResponse
        if getattr(res, "error", None):
            raise ComposioError(str(res.error)[:300])
        data = getattr(res, "data", res)
    if isinstance(data, dict) and data.get("successful") is False:
        raise ComposioError(str(data.get("error") or data)[:300])
    return data.get("data", data) if isinstance(data, dict) and "data" in data else data


class ComposioMCP:
    def __init__(self, settings: Settings):
        self.s = settings
        self.session = None            # Composio SDK session
        self.mcp = None                # mcp.ClientSession
        self._stack: contextlib.AsyncExitStack | None = None
        self.tools: dict[str, dict] = {}   # name -> input schema
        self.resolved: dict[str, str] = {}
        self.connected: dict[str, bool] = {}
        self.meta = False              # endpoint exposes only Composio meta tools (Connect)
        self._lock = asyncio.Lock()

    @property
    def consumer(self) -> bool:
        return self.s.composio_api_key.startswith("ck_")

    # ------------------------------------------------------------------ lifecycle
    def configured(self) -> bool:
        """An API key is set AND both Google toolkits are connected to Chandru's account."""
        return bool(self.s.composio_api_key) and all(self.connected.get(t) for t in TOOLKITS)

    async def start(self) -> None:
        if not self.s.composio_api_key:
            log.info("composio: no API key, calendar/email disabled (bot falls back to lead capture)")
            return
        try:
            if self.consumer:
                await self._open_mcp(CONNECT_URL, {"x-consumer-api-key": self.s.composio_api_key})
                self.connected = await self._meta_connections()
            else:
                self.session = await asyncio.to_thread(self._create_session)
                self.connected = await asyncio.to_thread(self._connection_states)
                cfg = self.session.mcp
                headers = {k: v for k, v in (cfg.headers or {}).items() if v}
                headers.setdefault("x-api-key", self.s.composio_api_key)
                await self._open_mcp(cfg.url, headers)
            log.info("composio: connected=%s tools=%d resolved=%s", self.connected, len(self.tools), self.resolved)
        except Exception as e:  # noqa: BLE001 - never block startup on an external service
            log.error("composio unavailable: %s", e)

    def _create_session(self):
        from composio import Composio
        client = Composio(api_key=self.s.composio_api_key)
        return client.create(user_id=self.s.composio_user_id, toolkits=TOOLKITS, mcp=True)

    def _connection_states(self) -> dict[str, bool]:
        details = self.session.toolkits(toolkits=TOOLKITS)
        return {item.slug.lower(): bool(item.connection and item.connection.is_active) for item in details.items}

    async def _open_mcp(self, url: str, headers: dict) -> None:
        from mcp import ClientSession
        from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client
        self._endpoint = (url, headers)
        stack = contextlib.AsyncExitStack()
        http = await stack.enter_async_context(create_mcp_http_client(headers=headers))
        read, write = await stack.enter_async_context(streamable_http_client(url, http_client=http))
        mcp = await stack.enter_async_context(ClientSession(read, write, read_timeout_seconds=30))
        await mcp.initialize()
        listed = await mcp.list_tools()
        self.tools = {t.name: (t.input_schema or {}) for t in listed.tools}
        self._stack, self.mcp = stack, mcp
        self.meta = "COMPOSIO_MULTI_EXECUTE_TOOL" in self.tools and not any(
            n.startswith(("GOOGLECALENDAR_", "GMAIL_")) for n in self.tools)
        if self.meta:
            await self._meta_schemas()
        else:
            self._resolve()

    async def _raw(self, name: str, args: dict, timeout: float = 30.0) -> Any:
        async with self._lock:
            res = await asyncio.wait_for(self.mcp.call_tool(name, args), timeout)
        return _parse_result(res)

    async def _meta_schemas(self) -> None:
        """Connect only lists meta tools: fetch the real input schemas of the four tools we use."""
        data = await self._raw("COMPOSIO_GET_TOOL_SCHEMAS", {"tool_slugs": list(SLUGS.values())})
        schemas = (data or {}).get("tool_schemas", {}) if isinstance(data, dict) else {}
        for kind, slug in SLUGS.items():
            if slug in schemas:
                self.tools[slug] = schemas[slug].get("input_schema") or {}
                self.resolved[kind] = slug

    async def _meta_connections(self) -> dict[str, bool]:
        data = await self._raw("COMPOSIO_MANAGE_CONNECTIONS",
                               {"toolkits": [{"name": t, "action": "list"} for t in TOOLKITS]})
        results = (data or {}).get("results", {}) if isinstance(data, dict) else {}
        out = {}
        for tk in TOOLKITS:
            r = results.get(tk) or {}
            accounts = r.get("accounts") or []
            out[tk] = str(r.get("status", "")).lower() == "active" or any(
                str(a.get("status", "")).lower() == "active" for a in accounts if isinstance(a, dict))
        return out

    def _resolve(self) -> None:
        names = list(self.tools)
        for kind, pats in PATTERNS.items():
            for p in pats:
                hit = next((n for n in names if p in n.upper()), None)
                if hit:
                    self.resolved[kind] = hit
                    break

    async def refresh(self) -> dict[str, bool]:
        """Re-read connection state (e.g. after Chandru finishes the Google consent), no restart needed."""
        try:
            if self.consumer and self.mcp is not None:
                self.connected = await self._meta_connections()
            elif self.session is not None:
                self.connected = await asyncio.to_thread(self._connection_states)
        except Exception as e:  # noqa: BLE001
            log.warning("composio refresh failed: %s", e)
        return self.connected

    async def close(self) -> None:
        if self._stack is not None:
            with contextlib.suppress(Exception):
                await self._stack.aclose()

    # ------------------------------------------------------------------ calls
    def schema(self, kind: str) -> dict:
        name = self.resolved.get(kind)
        return (self.tools.get(name) or {}).get("properties", {}) if name else {}

    async def call(self, kind: str, args: dict, *, timeout: float = 20.0) -> Any:
        """Direct MCP tool when the endpoint lists it; SDK `session.execute` otherwise. One reconnect on failure."""
        if self.mcp is None and self.session is None:
            raise ComposioError("composio not started")
        name = self.resolved.get(kind)
        if self.meta:
            return await self._meta_execute(SLUGS[kind], args, timeout)
        if name and self.mcp is not None:
            for attempt in (1, 2):
                try:
                    async with self._lock:
                        res = await asyncio.wait_for(self.mcp.call_tool(name, args), timeout)
                    return _parse_result(res)
                except ComposioError:
                    raise
                except Exception as e:  # noqa: BLE001 - dropped stream: reconnect once
                    log.warning("composio mcp call %s failed (%s), attempt %d", name, e, attempt)
                    if attempt == 1:
                        await self.close()
                        await self._open_mcp(*self._endpoint)
            raise ComposioError(f"mcp call {name} failed")
        slug = name or PATTERNS[kind][0]  # meta-tools-only endpoint: execute the canonical slug via the SDK
        res = await asyncio.wait_for(asyncio.to_thread(self.session.execute, slug, arguments=args), timeout)
        return _parse_result(res)

    async def _meta_execute(self, slug: str, args: dict, timeout: float) -> Any:
        payload = {"tools": [{"tool_slug": slug, "arguments": args}], "sync_response_to_workbench": False,
                   "thought": f"Virtual Me: {slug.lower()}"}
        for attempt in (1, 2):
            try:
                data = await self._raw("COMPOSIO_MULTI_EXECUTE_TOOL", payload, timeout)
                break
            except ComposioError:
                raise
            except Exception as e:  # noqa: BLE001 - dropped stream: reconnect once
                log.warning("composio connect call %s failed (%s), attempt %d", slug, e, attempt)
                if attempt == 2:
                    raise ComposioError(f"{slug} failed") from e
                await self.close()
                await self._open_mcp(*self._endpoint)
        results = (data or {}).get("results") if isinstance(data, dict) else None
        item = (results or [data])[0] if isinstance(results or [data], list) else data
        if isinstance(item, dict):
            if item.get("error"):
                raise ComposioError(str(item["error"])[:300])
            resp = item.get("response", item)
            if isinstance(resp, dict):
                if resp.get("successful") is False or resp.get("error"):
                    raise ComposioError(str(resp.get("error") or resp)[:300])
                return resp.get("data", resp)
            return resp
        return item

    async def auth_links(self) -> dict[str, str]:
        """For scripts/composio_connect.py: one auth link per toolkit not yet connected."""
        todo = [tk for tk in TOOLKITS if not self.connected.get(tk)]
        if not todo:
            return {}
        if not self.consumer:
            return {tk: self.session.authorize(tk).redirect_url for tk in todo}
        data = await self._raw("COMPOSIO_MANAGE_CONNECTIONS", {"toolkits": [{"name": t, "action": "add"} for t in todo]})
        results = (data or {}).get("results", {}) if isinstance(data, dict) else {}
        links = {}
        for tk in todo:
            r = results.get(tk) or {}
            url = r.get("redirect_url") or r.get("redirectUrl") or r.get("auth_url") or next(
                (a.get("redirect_url") for a in r.get("accounts") or [] if isinstance(a, dict) and a.get("redirect_url")),
                None)
            links[tk] = url or json.dumps(r)[:300]
        return links


def pick_args(schema: dict, wanted: dict[str, list[str]], values: dict[str, Any]) -> dict:
    """Map our values onto a tool's real parameter names: wanted = {our_key: [candidate param names]}."""
    out = {}
    for key, candidates in wanted.items():
        if values.get(key) is None:
            continue
        name = next((c for c in candidates if c in schema), None) if schema else candidates[0]
        if name:
            out[name] = values[key]
    return out


def find_intervals(data: Any, key_pattern: str) -> list[tuple[str, str]]:
    """Walk a JSON result and collect {start, end} intervals under keys matching `key_pattern` (busy/free)."""
    rx = re.compile(key_pattern, re.I)
    found: list[tuple[str, str]] = []

    def walk(node, under=False):
        if isinstance(node, dict):
            if under and "start" in node and "end" in node:
                found.append((str(node["start"]), str(node["end"])))
            for k, v in node.items():
                walk(v, under or bool(rx.search(str(k))))
        elif isinstance(node, list):
            for v in node:
                walk(v, under)
    walk(data)
    return found
