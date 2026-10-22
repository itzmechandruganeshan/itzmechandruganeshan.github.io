"""Runs one turn: graph (producer) → queue → humanized, paced WS events (consumer)."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from langgraph.types import Command

from app.context.clock import build_clock
from app.graph.state import Deps
from app.humanizer.fillers import FillerBudget
from app.humanizer.pacing import remaining_wait
from app.humanizer.reply import ReplyHumanizer

log = logging.getLogger(__name__)
Send = Callable[[dict], Awaitable[None]]
_DONE = object()


class TurnRunner:
    def __init__(self, graph, deps: Deps, sleep: Callable[[float], Awaitable[None]] = asyncio.sleep):
        self.graph = graph
        self.deps = deps
        self.sleep = sleep
        # fillers used in each session's last 2 replies (single machine, so in-memory is fine)
        self.recent_fillers: dict[str, deque] = defaultdict(lambda: deque(maxlen=2))

    async def append_history(self, session_id: str, bubbles: list[str]) -> None:
        """Bubbles sent outside a turn (e.g. a delivered answer) join the conversation history."""
        config = {"configurable": {"thread_id": session_id, "deps": self.deps}}
        snap = await self.graph.aget_state(config)
        if snap.values:
            hist = list(snap.values.get("history") or []) + [{"role": "chandru", "text": "\n".join(bubbles)}]
            await self.graph.aupdate_state(config, {"history": hist}, as_node="finalize")

    async def run(self, session_id: str, text: str, send: Send, *, action: dict | None = None,
                  visitor_tz: str | None = None, memory: dict | None = None) -> dict:
        """session_id is the conversation id (one per visit). `memory` = returning-visitor profile + note."""
        t_recv = time.perf_counter()
        turn_id = f"t-{uuid.uuid4().hex[:10]}"
        config = {"configurable": {"thread_id": session_id, "deps": self.deps}}
        snapshot = await self.graph.aget_state(config)
        pending = any(task.interrupts for task in (snapshot.tasks or ()))
        if pending:
            inp = Command(resume={"text": text, "turn_id": turn_id, "action": action})
        else:
            inp = {"session_id": session_id, "message": text, "turn_id": turn_id, "action": action}
            if not snapshot.values:  # first turn of this session
                known = {k: v for k, v in ((memory or {}).get("profile") or {}).items()
                         if k in ("name", "company", "role") and v}
                preface = (memory or {}).get("preface") or []
                inp |= {"history": [{"role": "chandru", "text": "\n".join(preface)}] if preface else [],
                        "visitor": {**known, **({"tz": visitor_tz} if visitor_tz else {})},
                        "memory": {"note": (memory or {}).get("note", "")},
                        "asked_who": bool(known.get("name")),
                        "visitor_msgs": 0, "identity_probes": 0, "identity_disclosed": False,
                        "connected": bool(((memory or {}).get("profile") or {}).get("lead_saved")), "dodges": {},
                        "used_lines": [], "tool": None}
            elif visitor_tz and not (snapshot.values.get("visitor") or {}).get("tz"):
                inp["visitor"] = {**(snapshot.values.get("visitor") or {}), "tz": visitor_tz}

        clock = build_clock(self.deps.kb, now=self.deps.now(), tz=self.deps.settings.timezone, rng=self.deps.rng)
        fillers = FillerBudget(self.recent_fillers[session_id])
        # The visitor's own name/company are never typo targets ("bye kaaviya" in prod), even lowercase.
        visitor = {**(snapshot.values.get("visitor") or {}),
                   **((inp.get("visitor") if isinstance(inp, dict) else None) or {})}
        protected = self.deps.protected | {w.lower() for k in ("name", "company")
                                           for w in str(visitor.get(k) or "").split()}
        human = ReplyHumanizer(self.deps.kb.style, protected, self.deps.rng, clock.pacing_multiplier, fillers)
        queue: asyncio.Queue = asyncio.Queue()
        await send({"type": "typing", "on": True})

        async def produce():
            try:
                async for ev in self.graph.astream(inp, config, stream_mode="custom"):
                    await queue.put(ev)
            except Exception:  # noqa: BLE001 - never leave the socket hanging
                log.exception("graph failed")
                await queue.put({"type": "burst", "text": "ugh my phone's acting up 😅", "src": "template",
                                 "error": True})
            finally:
                await queue.put(_DONE)

        producer = asyncio.create_task(produce())
        first_sent_ms = None
        seq = 0
        bursts: list[str] = []
        while True:
            ev = await queue.get()
            if ev is _DONE:
                break
            if ev.get("type") == "card":
                await send({**ev, "turn_id": turn_id})
                continue
            for out_text, delay in human.process(ev["text"], ev.get("src", "llm")):
                if seq == 0:
                    delay = remaining_wait(delay, time.perf_counter() - t_recv)
                await send({"type": "typing", "on": True})
                await self.sleep(delay)
                await send({"type": "burst", "turn_id": turn_id, "seq": seq, "text": out_text})
                if first_sent_ms is None:
                    first_sent_ms = (time.perf_counter() - t_recv) * 1000
                bursts.append(out_text)
                seq += 1
        await producer
        fillers.close()
        await send({"type": "typing", "on": False})
        await send({"type": "turn_complete", "turn_id": turn_id})

        final = (await self.graph.aget_state(config)).values
        record = {
            "turn_id": turn_id, "route": final.get("route"), "gates": final.get("gates"),
            "flags": final.get("flags"), "timings": {**(final.get("timings") or {}),
                                                     "first_burst_sent_ms": first_sent_ms,
                                                     "total_ms": (time.perf_counter() - t_recv) * 1000},
            "llm": final.get("llm"), "bursts": len(bursts), "resumed": pending,
            "message": text, "replies": bursts,
            "trace": (final.get("trace") or []) + human.trace,
        }
        if self.deps.db is not None:
            await self.deps.db.add_message(session_id, turn_id, "visitor", text, None)
            await self.deps.db.add_message(session_id, turn_id, "chandru", "\n".join(bursts), final.get("route"))
            await self.deps.db.log_turn(turn_id, session_id, record)
        # stdout/Fly logs get no visitor text; full trace lives in turn_logs (30-day retention)
        log.info("turn %s", {k: v for k, v in record.items() if k not in ("message", "replies", "trace")})
        return record
