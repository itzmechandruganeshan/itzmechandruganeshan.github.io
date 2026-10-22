"""WebSocket endpoint and protocol (architecture §7)."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from zoneinfo import ZoneInfo

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import time

from app.chat import TurnRunner
from app.tools import questions
from app.memory import FORGET_RE, VisitorMemory, memory_note
from app.persona_rules.lines import fill, pick
from app.ratelimit import Limiter, ip_key

log = logging.getLogger(__name__)
router = APIRouter()
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def valid_tz(tz: object) -> str | None:
    """The browser's IANA zone, or None if this server can't load it (a bad zone crashed slot labels in prod)."""
    if not isinstance(tz, str) or not tz or len(tz) >= 64:
        return None
    try:
        ZoneInfo(tz)
    except (ValueError, KeyError):  # ZoneInfoNotFoundError is a KeyError
        log.warning("unknown visitor tz %r; using the default", tz)
        return None
    return tz


def reading_project(kb, ctx: object):
    """The project the visitor is reading, resolved against our own data: browser text never reaches the prompt."""
    label = ctx.get("project") if isinstance(ctx, dict) else None
    if not isinstance(label, str) or not 0 < len(label) <= 80:
        return None
    label = label.lower().strip()
    for p in kb.projects:
        if p.visibility == "public" and (p.name.split(" - ")[0].lower() == label or any(
                re.search(rf"\b{re.escape(a)}\b", label) for a in p.aliases)):
            return p
    return None
limiter = Limiter()


@router.websocket("/ws/chat")
async def chat(ws: WebSocket):
    app = ws.app
    rt = app.state.runtime
    s = rt.deps.settings
    origin = ws.headers.get("origin")
    if s.is_prod and origin not in s.allowed_origins:
        await ws.close(code=1008)
        return
    await ws.accept()
    runner: TurnRunner = app.state.runner
    send_lock = asyncio.Lock()

    async def send(ev: dict):
        async with send_lock:
            await ws.send_text(json.dumps(ev, ensure_ascii=False))

    try:
        hello = json.loads(await asyncio.wait_for(ws.receive_text(), timeout=15))
    except (asyncio.TimeoutError, json.JSONDecodeError, WebSocketDisconnect):
        await ws.close(code=1008)
        return
    # visitor_id: long-lived, random, per browser. (session_id accepted from older frontends.)
    vid = str(hello.get("visitor_id") or hello.get("session_id") or "").lower()
    if hello.get("type") != "hello" or not UUID_RE.match(vid):
        await ws.close(code=1008)
        return
    tz = valid_tz(hello.get("tz"))
    memory: VisitorMemory = app.state.memory
    sid = vid  # rate limits and dedupe are per visitor
    preface: list[str] = []
    try:  # "ask the real me": an answer is waiting, so Chandru texts first
        preface = await questions.deliver(rt.deps, vid)
        if preface:
            visit0 = await memory.open(vid, tz)
            await send({"type": "typing", "on": True})
            for i, b in enumerate(preface):
                await asyncio.sleep(min(2.5, 0.6 + len(b) / 18))
                await send({"type": "burst", "turn_id": "answer", "seq": i, "text": b})
            await send({"type": "typing", "on": False})
            await rt.deps.db.add_message(visit0.conversation_id, "answer", "chandru", "\n".join(preface), "answer")
            if not visit0.new_conversation:
                await runner.append_history(visit0.conversation_id, preface)
                preface = []
    except Exception:  # noqa: BLE001 - never block the chat on this
        log.exception("answer delivery failed")
    ipk = ip_key(ws.client.host if ws.client else None)
    nudged = False
    sent_any = False
    turns = 0
    # shortcut: openers are remembered per connection, so a page reload can greet again; fine at portfolio traffic
    greeted: set[str] = set()

    while True:
        try:
            raw = await asyncio.wait_for(ws.receive_text(), timeout=s.idle_nudge_s)
        except asyncio.TimeoutError:
            if sent_any and not nudged:
                nudged = True
                for b in pick(rt.deps.kb.policy["idle_nudge"], set(), "nudge", rt.deps.rng):
                    await send({"type": "burst", "turn_id": "nudge", "seq": 0, "text": b})
            continue
        except WebSocketDisconnect:
            return
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue
        kind = msg.get("type")
        if kind == "forget" or (kind == "message" and FORGET_RE.search(str(msg.get("text", "")))):
            await memory.forget(vid)
            for b in pick(rt.deps.kb.policy["forget_done"], set(), "forget", rt.deps.rng):
                await send({"type": "burst", "turn_id": "forget", "seq": 0, "text": b})
            await send({"type": "forgotten"})
            continue
        if kind == "opened":  # chat opened while reading a project: Chandru texts first about it
            p = reading_project(rt.deps.kb, msg.get("context"))
            lines = rt.deps.kb.policy.get("context_opener")
            if not p or not lines or p.id in greeted or not limiter.hit(f"s:{sid}", s.rate_per_min_session, 60):
                continue
            greeted.add(p.id)
            bubbles = fill(pick(lines, set(), "ctx", rt.deps.rng), project=p.aliases[0] if p.aliases else p.name)
            try:
                visit = await memory.open(vid, tz)
                await send({"type": "typing", "on": True})
                for i, b in enumerate(bubbles):
                    await asyncio.sleep(min(2.5, 0.6 + len(b) / 18))
                    await send({"type": "burst", "turn_id": "opener", "seq": i, "text": b})
                await send({"type": "typing", "on": False})
                await rt.deps.db.add_message(visit.conversation_id, "opener", "chandru", "\n".join(bubbles), "opener")
                if visit.new_conversation:
                    preface += bubbles  # joins the history on their first message, like a delivered answer
                else:
                    await runner.append_history(visit.conversation_id, bubbles)
            except WebSocketDisconnect:
                return
            except Exception:  # noqa: BLE001 - an opener must never break the chat
                log.exception("context opener failed")
            continue
        if kind not in ("message", "action"):
            continue
        text = str(msg.get("text", "")).strip()[: s.max_message_chars]
        action = None
        if kind == "action":
            action = {"action": str(msg.get("action")), "slot_id": msg.get("slot_id")}
            text = text or {"pick_slot": "this one works", "confirm": "yes"}.get(action["action"], "ok")
        if not text:
            continue
        cmid = msg.get("client_msg_id")
        if isinstance(cmid, str) and await rt.deps.db.seen_client_msg(sid, cmid[:64]):
            continue  # duplicate after reconnect
        if not (limiter.hit(f"s:{sid}", s.rate_per_min_session, 60) and limiter.hit(
                f"sd:{sid}", s.rate_per_day_session, 86400) and limiter.hit(ipk, s.rate_per_min_ip, 60)):
            await send({"type": "error", "code": "rate_limited",
                        "text": pick(rt.deps.kb.policy["rate_limited"], set(), "rl", rt.deps.rng)[0]})
            continue
        turns += 1
        if turns > s.max_turns_per_session:
            await send({"type": "burst", "turn_id": "limit", "seq": 0,
                        "text": "gotta run now haha, drop me a mail if u wanna continue 🙌"})
            await ws.close(code=1000)
            return
        sent_any = True
        try:
            visit = await memory.open(vid, tz)  # same conversation, or a new one after a long silence
            mem = None
            if visit.new_conversation or preface:
                mem = {"profile": visit.profile, "preface": preface,
                       "note": memory_note(visit.profile, visit.visits, visit.last_seen, time.time())}
                preface = []
            await memory.touch(visit)  # activity recorded on arrival, before the (slow) reply
            reading = reading_project(rt.deps.kb, msg.get("context"))
            await runner.run(visit.conversation_id, text, send, action=action, visitor_tz=tz, memory=mem,
                             reading=reading.name if reading else None)
        except WebSocketDisconnect:
            return
        except Exception:  # noqa: BLE001
            log.exception("turn failed")
            await send({"type": "error", "code": "internal", "text": "ugh my phone's acting up 😅"})
