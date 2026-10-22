"""C1-C4: resume, lead capture, meeting booking. Side effects only after a confirmed interrupt."""

from __future__ import annotations

import hashlib
import logging
import re
import time
from datetime import datetime

from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from app.graph.common import deps_of
from app.graph.common import emit_bursts as _emit_bursts
from app.graph.common import emit_card as _emit_card
from app.graph.common import used_of as _used
from app.graph.state import RESET, Deps, TurnState
from app.intelligence import decisions as dec
from app.intelligence.decisions import IDENTITY_RE, INJECTION_RE
from app.intelligence.llm import LLMError
from app.persona_rules.lines import fill, pick
from app.tools import calendar as cal
from app.tools import leads, notify

log = logging.getLogger(__name__)
SKIP_RE = re.compile(r"^\s*(skip|no|nah|rather not|not now|pass|-)\s*$", re.I)
# "nah leave it" mid-flow cancels the whole connect; a bare "skip"/"no" only skips an optional field
CANCEL_RE = re.compile(r"\b(leave it|never ?mind|forget it|cancel( it)?|drop it|not interested|no thanks)\b", re.I)
EMAILISH_RE = re.compile(r"@|\bat\b.*\b(gmail|yahoo|outlook|hotmail|mail)\b|\.(com|in|io|org)\b", re.I)


def _lines(deps: Deps, used: set[str], key: str, **values) -> list[str]:
    t = deps.kb.policy["tools"]
    options = t["ask"][key.split(".", 1)[1]] if key.startswith("ask.") else t[key]
    return fill(pick(options, used, f"tools.{key}", deps.rng), **{k: str(v) for k, v in values.items()})


async def _extract(deps: Deps, message: str, asked: str | None) -> dict:
    """Pull name/company/role/email/about from a free-text reply. Email by regex, the rest by a cheap LLM."""
    out: dict = {}
    email = leads.find_email(message)
    if email:
        out["email"] = email
    text = leads.EMAIL_RE.sub("", message).strip()
    if asked == "about" and text and not SKIP_RE.match(text):
        out["about"] = text[:200]
    if SKIP_RE.match(message) and asked in ("company", "about"):
        out[asked] = ""
        return out
    if not text or asked in ("email", "about"):
        return out
    try:
        j = await deps.llm.complete_json([
            {"role": "system", "content": (
                "Extract the visitor's own details from their chat message. Return JSON with keys "
                "name, company, role, about (what they want to connect about, a few words; null when not stated). "
                "Never invent values.")},
            {"role": "user", "content": f"Question they were answering: {asked or 'none'}\nMessage: {text}"},
        ], max_tokens=80, timeout=4.0)
        for k in ("name", "company", "role", "about"):
            v = j.get(k)
            if isinstance(v, str) and v.strip() and len(v) <= (200 if k == "about" else 80):
                out[k] = v.strip()
    except LLMError as e:
        log.warning("extraction failed, using heuristic: %s", e)
        if asked in ("name", "company") and len(text.split()) <= 4:
            out[asked] = re.sub(r"^(i'?m|i am|this is|my name is|it'?s|from|at)\s+", "", text, flags=re.I).strip(" .!")
    return out


def _tool_from_visitor(kind: str, visitor: dict) -> dict:
    slots = {k: visitor[k] for k in ("name", "company", "role", "email") if visitor.get(k)}
    return {"kind": kind, "stage": "collect", "slots": slots, "asked": None}


async def tools(state: TurnState, config: RunnableConfig) -> dict:
    """Lead/meeting flow. Started by the LLM's start_connect call; continued deterministically while collecting.
    If the visitor says something that doesn't answer what was asked, hand the turn to the LLM (handoff)."""
    deps = deps_of(config)
    if state.get("handoff") and not state.get("tool_request"):
        # second visit in the same turn with no new request: converse already answered and re-asked
        return {"trace": [{"step": "tool", "skipped": "already handed off this turn"}]}
    used = _used(state)
    tool = dict(state.get("tool") or {}) or None
    visitor = dict(state.get("visitor") or {})
    msg = state["message"]
    out: list[str] = list(state.get("out") or [])  # the LLM may already have said "sure, happy to connect"
    llm_spoke = bool(out)
    out_new: list[str] = []
    request = state.get("tool_request")

    switching = bool(request and tool and tool.get("stage") in ("collect", "pick_slot")
                     and tool.get("kind") != request["kind"])
    if request and (tool is None or tool.get("stage") == "parked" or switching):
        kind = request["kind"]
        parked = tool if tool and tool.get("stage") in ("parked", "collect", "pick_slot") else None
        tool = parked if parked and parked["kind"] == kind else _tool_from_visitor(kind, visitor)
        if parked and parked["kind"] != kind:  # e.g. a lead flow was open, now they want a call
            tool["slots"] = {**parked.get("slots", {}), **tool["slots"]}
        # details may have been shared before the flow started ("priya@zoho.com" two messages ago)
        recent = [m["text"] for m in (state.get("history") or [])[-6:] if m["role"] == "visitor"]
        tool["slots"].update(await _extract(deps, "\n".join([*recent, msg]), None))
        if request.get("about") and kind == "lead":
            tool["slots"].setdefault("about", request["about"][:200])
        if kind == "lead":
            if not llm_spoke:
                key = "open_to_roles" if re.search(r"\b(role|hiring|opening|position|opportunit|job)", msg, re.I) else None
                out_new += _emit_bursts(deps, pick(deps.kb.policy["open_to_roles"], used, "open_to_roles", deps.rng)
                                        if key else _lines(deps, used, "lead_start"))
        else:
            if not llm_spoke:
                out_new += _emit_bursts(deps, _lines(deps, used, "meeting_start"))
            res = await _offer_slots(deps, state, tool, visitor, used, out_new)
            return {**res, "route": "tools", "trace": [{"step": "tool", "start": kind}]}

    elif tool["stage"] == "pick_slot":
        chosen = None
        action = state.get("action") or {}
        if action.get("action") == "pick_slot":
            chosen = next((s for s in tool["offered"] if s["id"] == action.get("slot_id")), None)
        if chosen is None:
            labels = {s["id"]: s["label"] for s in tool["offered"]}
            sid, conf = await dec.pick_slot(deps.jev, msg, labels)
            chosen = next((s for s in tool["offered"] if s["id"] == sid and conf >= 0.5), None)
        if chosen is None and not re.search(r"\b(none|other|another|different|neither|later|next week)\b", msg, re.I) \
                and len(msg.split()) > 3:
            # not a slot pick at all (e.g. a question): let the LLM answer, keep the slots open
            return {"handoff": True, "trace": [{"step": "tool", "stage": "pick_slot", "handoff": True}]}
        if chosen is None:
            tool["repicks"] = tool.get("repicks", 0) + 1
            if tool["repicks"] >= 2:  # stop looping: take an email instead
                tool = _tool_from_visitor("lead", visitor) | {"slots": {**tool["slots"], "about": "wants a call"}}
                out_new += _emit_bursts(deps, _lines(deps, used, "meeting_none_free"))
            else:
                out_new += _emit_bursts(deps, _lines(deps, used, "meeting_repick"))
                _emit_card({"kind": "slots", "slots": tool["offered"]})
                return {"out": out_new, "tool": tool, "used_lines": sorted(used), "route": "tools"}
        else:
            tool["chosen"] = chosen
            tool["stage"] = "collect"
            tool["slots"].update(await _extract(deps, msg, None))

    else:  # collect
        asked = tool.get("asked")
        if CANCEL_RE.search(msg):
            out_new += _emit_bursts(deps, _lines(deps, used, "reject"))
            return {"out": out_new, "tool": None, "used_lines": sorted(used), "route": "tools",
                    "flags": ["connect_cancelled"], "trace": [{"step": "tool", "cancelled": True, "asked": asked}]}
        before = dict(tool["slots"])
        tool["slots"].update(await _extract(deps, msg, asked))
        answered = tool["slots"] != before or (asked in ("company", "about") and SKIP_RE.match(msg))
        if asked:
            j9 = await dec.answers_question(deps.jev, f"their {asked}", msg)  # J9: is this an answer at all?
            if j9 is not None and j9 < deps.settings.t_answered:
                answered = False
                # drop only the asked field ("btw what's your stack?" isn't an 'about'); keep e.g. an email
                if asked in before:
                    tool["slots"][asked] = before[asked]
                else:
                    tool["slots"].pop(asked, None)
                answered = any(tool["slots"].get(k) != before.get(k) for k in tool["slots"])
        if asked == "email" and "email" not in tool["slots"] and EMAILISH_RE.search(msg):
            out_new += _emit_bursts(deps, _lines(deps, used, "bad_email"))
            return {"out": out_new, "tool": tool, "used_lines": sorted(used), "route": "tools"}
        if not answered:
            # e.g. "btw what's your stack?" while we asked for their email: the LLM answers and re-asks.
            # A flow ignored twice in a row is parked, so the bot stops asking the same thing.
            tool["handoffs"] = tool.get("handoffs", 0) + 1
            if tool["handoffs"] >= 2:
                tool["stage"] = "parked"
            return {"handoff": True, "tool": tool,
                    "trace": [{"step": "tool", "stage": "collect", "asked": asked, "handoff": True,
                               "parked": tool["stage"] == "parked"}]}
        tool["handoffs"] = 0

    # ask for the next missing field, or read back for confirmation
    need = ["name", "email"] if tool["kind"] == "meeting" else leads.missing(tool["slots"])
    need = [k for k in need if not tool["slots"].get(k) and (k in leads.REQUIRED or k not in tool["slots"])]
    if need:
        field = need[0]
        if field in ("company", "about"):
            tool["slots"].setdefault(field, None)
        tool["asked"] = field
        tool["stage"] = "collect"
        out_new += _emit_bursts(deps, _lines(deps, used, f"ask.{field}"))
        visitor.update({k: v for k, v in tool["slots"].items() if k in ("name", "company", "role", "email") and v})
        return {"out": out_new, "tool": tool, "visitor": visitor, "used_lines": sorted(used), "route": "tools"}

    tool["stage"] = "confirm"
    s = tool["slots"]
    if tool["kind"] == "lead":
        who = s.get("name") + (f" from {s['company']}" if s.get("company") else "")
        readback = _lines(deps, used, "lead_readback", who=who, about=s.get("about") or "connecting",
                          email=s.get("email"))
    else:
        tz = visitor.get("tz") or deps.settings.timezone
        readback = _lines(deps, used, "meeting_readback", when=tool["chosen"]["label"], tz=tz, email=s.get("email"))
    tool["confirm_text"] = " ".join(readback)
    out_new += _emit_bursts(deps, readback)
    visitor.update({k: v for k, v in s.items() if k in ("name", "company", "role", "email") and v})
    return {"out": out_new, "tool": tool, "visitor": visitor, "used_lines": sorted(used), "route": "tools"}


async def _offer_slots(deps: Deps, state: TurnState, tool: dict, visitor: dict, used: set[str], out: list[str]) -> dict:
    if not (deps.actions and deps.actions.configured()):
        out += _emit_bursts(deps, pick(deps.kb.policy["calendar_down"], used, "calendar_down", deps.rng))
        lead = _tool_from_visitor("lead", visitor)
        lead["slots"]["about"] = "wants a call"
        lead["asked"] = "email"
        return {"out": out, "tool": lead, "used_lines": sorted(used), "flags": ["calendar_unconfigured"], "route": "tools"}
    try:
        slots = await cal.free_slots(deps.settings, deps.now(), deps.actions)
    except Exception as e:  # noqa: BLE001
        log.error("freebusy failed: %s", e)
        slots = None
    if not slots:
        key = "calendar_down" if slots is None else None
        lines = pick(deps.kb.policy["calendar_down"], used, "calendar_down", deps.rng) if key else _lines(
            deps, used, "meeting_none_free")
        out += _emit_bursts(deps, lines)
        lead = _tool_from_visitor("lead", visitor)
        lead["slots"]["about"] = "wants a call"
        lead["asked"] = "email"
        return {"out": out, "tool": lead, "used_lines": sorted(used)}
    tz = visitor.get("tz") or deps.settings.timezone
    tool["offered"] = [{"id": s.id, "start": s.start.isoformat(), "end": s.end.isoformat(), "label": s.label(tz)}
                       for s in slots]
    tool["stage"] = "pick_slot"
    out += _emit_bursts(deps, _lines(deps, used, "meeting_offer"))
    _emit_card({"kind": "slots", "tz": tz, "slots": tool["offered"]})
    return {"out": out, "tool": tool, "used_lines": sorted(used)}


# --------------------------------------------------------------------------- confirmation (C4)

async def await_confirm(state: TurnState, config: RunnableConfig) -> dict:
    """Pauses the graph. Resumed by the WS layer with the visitor's next message."""
    reply = interrupt({"type": "confirm", "asked": (state.get("tool") or {}).get("confirm_text")})
    return {
        "message": reply["text"], "turn_id": reply["turn_id"], "action": reply.get("action"),
        "out": RESET, "flags": RESET, "timings": RESET, "trace": RESET, "gates": None, "tool_request": None,
        "handoff": False, "route": "confirm", "llm": {},
        "hints": {"identity_regex": bool(IDENTITY_RE.search(reply["text"])),
                  "injection_regex": bool(INJECTION_RE.search(reply["text"]))}, "visitor_msgs": (state.get("visitor_msgs") or 0) + 1,
    }


async def confirm_handle(state: TurnState, config: RunnableConfig) -> dict:
    deps = deps_of(config)
    tool = dict(state["tool"])
    action = state.get("action") or {}
    if action.get("action") == "confirm":
        verdict = "confirm"
    else:
        verdict = await dec.confirmation(deps.jev, tool.get("confirm_text", ""), state["message"])
    tool["verdict"] = verdict
    if verdict == "change":
        tool["stage"] = "pick_slot" if tool["kind"] == "meeting" and leads.find_email(state["message"]) is None else "collect"
        tool["asked"] = None
    elif verdict == "unrelated":
        tool["stage"] = "parked"
    return {"tool": tool, "flags": [f"confirm:{verdict}"]}


def after_confirm(state: TurnState) -> str | list[str]:
    v = (state.get("tool") or {}).get("verdict")
    if v == "confirm":
        return "execute"
    if v in ("change", "unclear"):
        return "tools_again" if v == "change" else "reask"
    if v == "unrelated":
        return "converse"
    return "cancel"


async def reask(state: TurnState, config: RunnableConfig) -> dict:
    deps = deps_of(config)
    used = _used(state)
    out = _emit_bursts(deps, _lines(deps, used, "unclear_confirm"))
    return {"out": out, "used_lines": sorted(used)}


async def cancel(state: TurnState, config: RunnableConfig) -> dict:
    deps = deps_of(config)
    used = _used(state)
    out = _emit_bursts(deps, _lines(deps, used, "reject"))
    return {"out": out, "tool": None, "used_lines": sorted(used)}


async def _summary(deps: Deps, history: list[dict], about: str | None) -> str:
    convo = "\n".join(f"{m['role']}: {m['text']}" for m in history[-10:])
    try:
        j = await deps.llm.complete_json([
            {"role": "system", "content": "Summarise this portfolio-site chat for Chandru in at most 3 short lines. "
                                          "Return JSON {\"summary\": str}. Do not quote the visitor verbatim."},
            {"role": "user", "content": convo},
        ], max_tokens=120, timeout=6.0)
        return str(j.get("summary", ""))[:500]
    except LLMError:
        return about or ""


async def execute(state: TurnState, config: RunnableConfig) -> dict:
    deps = deps_of(config)
    used = _used(state)
    tool = dict(state["tool"])
    s = tool["slots"]
    sid = state["session_id"]
    summary = await _summary(deps, state.get("history") or [], s.get("about"))
    if tool["kind"] == "lead":
        lead_id = await leads.save_lead(deps.db, deps.box, sid, s)
        await notify.enqueue(deps.db, deps.box, f"lead.created:{lead_id}", "lead.created", {
            "name": s.get("name"), "company": s.get("company"), "role": s.get("role"), "email": s.get("email"),
            "about": s.get("about"), "summary": summary, "session_id": sid,
        })
        out = _emit_bursts(deps, _lines(deps, used, "lead_done", email=s.get("email")))
        return {"out": out, "tool": None, "used_lines": sorted(used), "flags": ["lead_saved"], "connected": True}

    chosen = tool["chosen"]
    key = hashlib.sha256(f"{sid}|{chosen['start']}|{s.get('email')}".encode()).hexdigest()[:32]
    existing = await deps.db.fetchone("SELECT meet_url FROM bookings WHERE idempotency_key=?", (key,))
    if existing is None:
        slot = cal.Slot(id=chosen["id"], start=datetime.fromisoformat(chosen["start"]),
                        end=datetime.fromisoformat(chosen["end"]))
        try:
            ev = await cal.book(deps.settings, slot, attendee_email=s["email"], attendee_name=s.get("name"),
                                idempotency_key=key, about=summary or s.get("about"), cx=deps.actions)
        except Exception as e:  # noqa: BLE001
            log.error("booking failed: %s", e)
            await notify.enqueue(deps.db, deps.box, f"booking.failed:{key}", "booking.failed", {
                "name": s.get("name"), "email": s.get("email"), "when": chosen["label"], "error": str(e)[:200],
                "session_id": sid,
            })
            out = _emit_bursts(deps, pick(deps.kb.policy["calendar_down"], used, "calendar_down", deps.rng))
            return {"out": out, "tool": None, "used_lines": sorted(used), "flags": ["booking_failed"]}
        await deps.db.execute(
            "INSERT INTO bookings(id, session_id, idempotency_key, event_id, start, end, attendee_email_enc, "
            "meet_url, status, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (f"bk-{key[:12]}", sid, key, ev["event_id"], chosen["start"], chosen["end"],
             deps.box.seal(s["email"]), ev.get("meet_url"), "booked", time.time()),
        )
        meet = ev.get("meet_url")
        await notify.enqueue(deps.db, deps.box, f"booking.created:{key}", "booking.created", {
            "name": s.get("name"), "company": s.get("company"), "email": s.get("email"),
            "when": chosen["label"], "meet_url": meet, "summary": summary,
            "session_id": sid,
        })
    else:
        meet = existing["meet_url"]
    out = _emit_bursts(deps, _lines(deps, used, "meeting_done"))
    _emit_card({"kind": "booking", "start": chosen["start"], "label": chosen["label"], "meet_url": meet})
    return {"out": out, "tool": None, "used_lines": sorted(used), "flags": ["booked"], "connected": True}
