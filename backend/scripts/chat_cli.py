"""Chat with the bot in the terminal, through the real graph (needs OPENROUTER_API_KEY in backend/.env).

    uv run python scripts/chat_cli.py [--fast]   # --fast skips the human typing delays
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402

from app.chat import TurnRunner  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.graph.build import build_graph  # noqa: E402
from app.runtime import build_runtime  # noqa: E402


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--tz", default=None)
    args = ap.parse_args()
    rt = await build_runtime(get_settings())

    async def no_sleep(_):
        return None

    runner = TurnRunner(build_graph(InMemorySaver()), rt.deps, sleep=no_sleep if args.fast else asyncio.sleep)
    sid = str(uuid.uuid4())

    async def send(ev):
        if ev["type"] == "burst":
            print(f"  chandru: {ev['text']}")
        elif ev["type"] == "card":
            print(f"  [card {ev['kind']}] {ev}")

    print(f"store={rt.store_backend}. ctrl-c to quit.")
    try:
        while True:
            text = await asyncio.to_thread(input, "you: ")
            rec = await runner.run(sid, text, send, visitor_tz=args.tz)
            t = rec["timings"]
            print(f"  ({rec['route']} · jev {t.get('jev_ms', 0):.0f}ms · first {t.get('first_burst_sent_ms') or 0:.0f}ms"
                  f" · flags {rec['flags']})")
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        await rt.close()


if __name__ == "__main__":
    asyncio.run(main())
