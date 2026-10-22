"""One-time: connect Chandru's Google Calendar + Gmail to Composio, then show what the MCP endpoint exposes.

    1. Create a Composio account and API key; put COMPOSIO_API_KEY in backend/.env (Fly: fly secrets set).
    2. uv run python scripts/composio_connect.py          # prints an auth link per unconnected toolkit
    3. Open each link, approve with your Google account, re-run to confirm "connected" and see resolved tools.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.integrations.composio_mcp import PATTERNS, ComposioMCP  # noqa: E402


async def main() -> int:
    s = get_settings()
    if not s.composio_api_key:
        print("COMPOSIO_API_KEY is not set (backend/.env).")
        return 1
    cx = ComposioMCP(s)
    await cx.start()
    if cx.mcp is None and cx.session is None:
        print("Could not reach Composio; check the key.")
        return 1
    mode = "Composio Connect (consumer key)" if cx.consumer else f"platform project, user {s.composio_user_id}"
    print(f"mode: {mode}\nconnected: {cx.connected}")
    links = await cx.auth_links()
    for tk, url in links.items():
        print(f"\nConnect {tk}: {url}")
    if not links:
        print(f"\nMCP tools listed: {len(cx.tools)}")
        for kind in PATTERNS:
            name = cx.resolved.get(kind)
            params = sorted(cx.schema(kind)) if name else []
            print(f"  {kind:13} -> {name or 'NOT FOUND'} {json.dumps(params)[:160]}")
    await cx.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
