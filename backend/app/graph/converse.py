"""ADR-008: the LLM converses (full history + all knowledge + tools); Jev gates run in parallel; code enforces."""

from __future__ import annotations

import asyncio
import logging
import re
import time

from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer

from app.context.clock import relative_day
from app.graph import prompts
from app.graph.common import (CONNECTOR_RE, check_line, clock_of, deps_of, derived_facts, emit_bursts, emit_card,
                              repair_line, used_of)
from app.graph.gates import policy, run_gates
from app.graph.state import RESET, Deps, TurnState
from app.humanizer.bursts import shape, split_at_tags, strip_hidden_tags
from app.intelligence import decisions as dec
from app.intelligence.decisions import IDENTITY_RE, INJECTION_RE
from app.intelligence.llm import LLMError, LLMStats, system_message
from app.persona_rules.dodge import dodge
from app.persona_rules.lines import fill, pick
from app.persona_rules.who_hook import should_ask
from app.retrieval import checks
from app.tools import questions

log = logging.getLogger(__name__)
# Jev's wants_connect scored "i love you" 0.71: the gate only acts when the words also point at connecting
CONNECT_HINT_RE = re.compile(r"\b(connect|call|meet(ing)?|chat|talk|schedule|book|slot|hir(e|ing)|role|job|opening|"
                             r"position|interview|recruit|opportunit\w*|email|mail|contact|reach)\b", re.I)
# Before the twin has been disclosed, it never volunteers being an AI (it never claims to be human either)
AI_SELF_RE = re.compile(r"\b(i'?m|i am) (an? )?(ai|bot|language model|chatbot|digital twin)\b|\bas an ai\b", re.I)
MEETING_RE = re.compile(r"\b(call|meet|meeting|schedule|book|slot|zoom|gmeet)\b", re.I)
PERMISSION_RE = re.compile(r"\b(want me to|should i|shall i|do you want me to)\b.*"
                           r"\b(connect|set up|kick (it |that |this )?off|start)\b"
                           r"|\b(start|kick off|set up) (a|the) connect\b", re.I)
# The LLM narrating its own mechanics ("start_connect call with kind lead... visitor tag", "the connect flow
# only starts from here") breaks the persona.
META_RE = re.compile(r"\b(start_connect|share_resume|get_news|ask_chandru|tool ?call|function ?call|visitor tag|"
                     r"kind (lead|meeting)|with ids|hidden tag|citation|(connect|booking) flow|that flow will|"
                     r"the (context|note|notes) (says|shows|mentions)|according to the (context|facts|notes)|"
                     r"the facts (don'?t|do not|say)|(project|their) page open|so i should(n'?t| not) guess|"
                     r"the visitor|they'?re (reading|looking at|on) (that|the|this|my|your) (page|project))\b", re.I)
DETAIL_RE = re.compile(r"\b(explain|in detail|detailed|deep dive|elaborate|walk me through|tell me more)\b", re.I)
TN_POLITICS_RE = re.compile(r"\b(tn|tamil ?nadu|dmk|aiadmk|admk|tvk|bjp|congress|chief minister|\bcm\b|assembly|"
                            r"election|stalin|annamalai|eps)\b", re.I)


# --------------------------------------------------------------------------- guard + entry

async def guard(state: TurnState, config: RunnableConfig) -> dict:
    """Code-only: reset per-turn fields, regex backstops. Length/rate limits live in the WS layer."""
    msg = state["message"]
    return {
        "out": RESET, "flags": RESET, "timings": RESET, "trace": RESET, "gates": None, "tool_request": None,
        "handoff": False, "route": "", "llm": {},
        "hints": {"identity_regex": bool(IDENTITY_RE.search(msg)), "injection_regex": bool(INJECTION_RE.search(msg))},
        "visitor_msgs": (state.get("visitor_msgs") or 0) + 1,
    }


def entry(state: TurnState) -> str:
    tool = state.get("tool") or {}
    return "tools" if tool.get("stage") in ("collect", "pick_slot") else "converse"


# --------------------------------------------------------------------------- policy paths (templates)

def _identity(deps: Deps, state: TurnState, g: dict, used: set[str]) -> dict:
    probes = state.get("identity_probes") or 0
    if state.get("identity_disclosed"):
        key = "identity_already_told"
    elif probes >= 1 or g["sincere_identity_q"] >= deps.settings.t_identity or g.get("source") != "jev":
        key = "identity_sincere"
    else:
        key = "identity_playful"
    out = emit_bursts(deps, pick(deps.kb.policy[key], used, key, deps.rng))
    return {"out": out, "flags": [key], "identity_probes": probes + 1,
            "identity_disclosed": bool(state.get("identity_disclosed")) or key == "identity_sincere",
            "trace": [{"step": "identity", "variant": key, "probes_before": probes, "score": g["sincere_identity_q"]}]}


def _deflect(deps: Deps, g: dict, used: set[str]) -> dict:
    if g["off_limits"] >= deps.settings.t_off_limits and g["injection_attempt"] < deps.settings.t_injection:
        lines, flag = deps.kb.policy["off_limits"]["nda"], "off_limits"
    else:
        lines, flag = deps.kb.policy["injection"], "injection"
    return {"out": emit_bursts(deps, pick(lines, used, flag, deps.rng)), "flags": [flag],
            "trace": [{"step": "deflect", "why": flag}]}


def _personal(deps: Deps, state: TurnState, g: dict, used: set[str]) -> dict:
    pressed = dict(state.get("dodges") or {})
    bursts, level = dodge(deps.kb.policy, g["personal_category"], pressed, used, deps.rng)
    return {"out": emit_bursts(deps, bursts), "dodges": pressed,
            "flags": [f"dodge:{g['personal_category']}:{level}"],
            "trace": [{"step": "dodge", "category": g["personal_category"], "level": level}]}


# --------------------------------------------------------------------------- streaming generation

async def _stream(deps: Deps, state: TurnState, messages: list[dict], *, cards, facts, max_b: int, tools: list | None,
                  gates_task: asyncio.Task | None, news_lines: list[str] | None = None, politics: bool = False):
    """Streams LLM lines through checks. Awaits the gate verdict before the FIRST bubble (it's usually done)."""
    stats = LLMStats()
    writer = get_stream_writer()
    out, flags, trace = [], [], []
    visitor = dict(state.get("visitor") or {})
    verdict = None
    dropped_prev = False

    async def gate() -> tuple[str | None, str] | None:
        nonlocal gates_task
        if gates_task is None:
            return None
        g = await gates_task
        gates_task = None
        route, reason = policy(deps, state, g)
        trace.append({"step": "gates", **{k: v for k, v in g.items() if k != "model"}, "policy": route, "reason": reason})
        return (route, reason) if route else None

    try:
        max_tokens = max(200, deps.settings.tokens_per_burst * (max_b + 1))
        async for line in deps.llm.stream_lines(messages, max_tokens=max_tokens, stats=stats, tools=tools):
            if verdict is None and gates_task is not None:
                verdict = await gate() or ("", "")
                if verdict[0]:
                    break  # a gate tripped: drop the LLM's reply, take the policy path
            for raw in split_at_tags(line):
                visitor.update(checks.visitor_tag(raw))
                clean = strip_hidden_tags(raw)
                if checks.LEAKED_TAG_RE.search(clean):
                    # a tag written as visible text ("visitor tag: name=Surya"): captured above, never shown
                    clean = checks.PLAIN_TAG_RE.sub("", clean).strip(" ·:;,-")
                    trace.append({"step": "tag_leak_blocked", "raw": raw})
                if not clean:  # a citation on its own line belongs to the previous line
                    prev = next((t for t in reversed(trace) if t.get("step") == "llm_line" and t.get("ok")), None)
                    if prev is not None:
                        prev.setdefault("cites", []).extend(checks.citations(raw))
                    continue
                if len(out) >= max_b:
                    continue  # keep consuming so tool calls at the end still arrive
                if AI_SELF_RE.search(clean) and not state.get("identity_disclosed"):
                    trace.append({"step": "llm_line", "raw": raw, "ok": False, "problems": ["volunteered being an AI"]})
                    continue
                if META_RE.search(clean):
                    trace.append({"step": "llm_line", "raw": raw, "ok": False, "problems": ["narrates its mechanics"]})
                    continue
                if PERMISSION_RE.search(clean):
                    trace.append({"step": "llm_line", "raw": raw, "ok": False, "problems": ["asks permission for a tool"]})
                    continue  # "want me to start a connect?" sounds like a bot; the flow starts by itself
                step = {"step": "llm_line", "raw": raw, "clean": clean}
                trace.append(step)
                ok, problems = await check_line(deps, raw, clean, cards, facts, step, news_lines=news_lines,
                                                politics=politics)
                if not ok and not politics:
                    fixed = await repair_line(deps, clean, cards, facts)
                    if fixed:
                        step["repair"] = fixed
                        clean2 = strip_hidden_tags(fixed)
                        ok2, _ = await check_line(deps, fixed, clean2, cards, facts, {}, news_lines=news_lines)
                        if ok2 and clean2:
                            ok, raw, clean = True, fixed, clean2
                            step["repaired"] = True
                            step["cites"] = checks.citations(fixed)
                            flags.append("burst_repaired")
                step["ok"] = ok
                if not ok:
                    step["problems"] = problems
                    flags.append(f"burst_dropped:{';'.join(problems)[:120]}")
                    dropped_prev = True
                    if politics:
                        fence = pick(deps.kb.policy["politics_stance"]["fence_lines"], set(), "fence", deps.rng)
                        out += emit_bursts(deps, fence, max_bursts=max_b - len(out))
                        max_b = len(out)  # stop after the fence line
                    continue
                if dropped_prev:  # never start mid-thought after a dropped bubble
                    clean = CONNECTOR_RE.sub("", clean, count=1)
                    clean = clean[:1].lower() + clean[1:]
                    dropped_prev = False
                shaped = shape([clean], style=deps.kb.style, protected=deps.protected,
                               max_bursts=max(1, max_b + 1 - len(out)))
                step["emitted"] = shaped
                for b in shaped:
                    writer({"type": "burst", "text": b, "src": "llm"})
                    out.append(b)
    except (LLMError, TimeoutError) as e:
        log.error("llm failed: %s", e)
        flags.append("llm_error")
        trace.append({"step": "llm_error", "error": str(e)[:200]})
    if verdict is None and gates_task is not None:  # reply had no text lines (e.g. only a tool call)
        verdict = await gate() or ("", "")
    trace.append({"step": "llm_done", "model": stats.model, "ttft_ms": stats.ttft_ms, "finish_reason": stats.finish_reason,
                  "tool_calls": stats.tool_calls,
                  "usage": {k: stats.usage.get(k) for k in ("prompt_tokens", "completion_tokens", "cost")}
                  if stats.usage else None})
    return {"out": out, "flags": flags, "trace": trace, "visitor": visitor, "verdict": verdict, "stats": stats}


def _llm_meta(stats: LLMStats) -> dict:
    return {"model": stats.model, "provider": stats.provider, "ttft_ms": stats.ttft_ms, "total_ms": stats.total_ms,
            "finish_reason": stats.finish_reason, "usage": stats.usage, "tool_calls": stats.tool_calls}


# --------------------------------------------------------------------------- the node

async def converse(state: TurnState, config: RunnableConfig) -> dict:
    deps = deps_of(config)
    s = deps.settings
    t0 = time.perf_counter()
    used = used_of(state)
    msg = state["message"]
    clock = clock_of(deps, state)
    derived = derived_facts(deps)
    # the clock is checkable too: "it's wednesday" / "almost midnight here" must pass J3 and number checks
    facts = deps.facts_text + "\n" + derived + "\n" + clock.block()
    cards = prompts.visible_cards(deps.kb, s.allow_unreviewed_cards)
    deep_max = int(deps.kb.style["burst"]["deep_max"])
    max_b = deep_max if DETAIL_RE.search(msg) else 4
    notes = []
    if (state.get("memory") or {}).get("note") and (state.get("visitor_msgs") or 0) <= 1:
        notes.append(state["memory"]["note"])  # returning visitor: only shapes the opening, then it's normal chat
    if state.get("reading"):
        notes.append(f"TOPIC: {state['reading']} (\"it\" / \"this\" / \"tell me more\" = this project).")
    tool = state.get("tool") or {}
    if state.get("handoff") and tool.get("asked"):
        notes.append(f"NOTE: you were getting their {tool['asked']} to connect them. Answer what they said, then "
                     f"ask for their {tool['asked']} again in one short line.")
    sys = system_message(
        prompts.stable_prefix(deps.kb, cards, deep_max),
        prompts.dynamic_block(clock_block=clock.block(), derived=derived, visitor=state.get("visitor") or {},
                              disclosed=bool(state.get("identity_disclosed")), notes=notes),
    )
    history = prompts.history_messages(state.get("history") or [], s.history_turns)
    messages = [sys, *history, {"role": "user", "content": msg}]
    # gates were already computed if tools_flow handed off; otherwise run them now, in parallel with the LLM
    gates_task = asyncio.create_task(run_gates(deps, state))
    politics = bool(TN_POLITICS_RE.search(msg))
    res = await _stream(deps, state, messages, cards=cards, facts=facts, max_b=max_b, tools=prompts.TOOLS,
                        gates_task=gates_task, politics=politics)
    trace = [{"step": "context", "cards": len(cards), "evidence": [c.id for c in cards], "politics_guard": politics,
              "handoff": bool(state.get("handoff"))}, *res["trace"]]
    gate_route = res["verdict"][0] if res["verdict"] else ""
    gates = next((t for t in res["trace"] if t["step"] == "gates"), {})
    base = {"timings": {"converse_ms": (time.perf_counter() - t0) * 1000, "gates_ms": gates.get("ms")},
            "gates": gates, "llm": _llm_meta(res["stats"])}

    if gate_route:  # policy overrides whatever the LLM was writing
        g = {k: gates.get(k) for k in ("sincere_identity_q", "injection_attempt", "off_limits", "personal_category",
                                       "personal_conf", "source")}
        out = {"identity": _identity, "deflect": lambda d, st, gg, u: _deflect(d, gg, u),
               "personal": _personal}[gate_route](deps, state, g, used)
        out["trace"] = trace + out.get("trace", [])
        return {**base, **out, "route": gate_route, "used_lines": sorted(used)}

    out, flags = res["out"], res["flags"]
    route, update = "converse", {}
    recent = [f"{m['role']}: {m['text']}" for m in (state.get("history") or [])[-4:]]
    for call in res["stats"].tool_calls:
        name, args = call["name"], call["arguments"]
        verified = await dec.tool_call_valid(deps.jev, name, msg, recent)  # J8: LLM proposes, Jev verifies
        trace.append({"step": "tool_call", "name": name, "arguments": args, "j8_valid": verified})
        if verified is not None and verified < s.t_tool_valid:
            flags.append(f"tool_rejected:{name}")
            continue
        if name == "share_resume":
            route = "tools"
            if not out:
                url = s.site_origin + s.resume_url
                out += emit_bursts(deps, fill(pick(deps.kb.policy["tools"]["resume"], used, "tools.resume", deps.rng),
                                              resume_url=url))
            emit_card({"kind": "resume", "url": s.resume_url})
            flags.append("resume_shared")
        elif name == "start_connect":
            route = "tools"
            update["tool_request"] = {"kind": args.get("kind") if args.get("kind") in ("lead", "meeting") else "lead",
                                      "about": args.get("about")}
        elif name == "ask_chandru":
            q = str(args.get("question") or "").strip()
            context = "\n".join(f"{m['role']}: {m['text']}" for m in (state.get("history") or [])[-6:])
            qid = await questions.forward(deps, state["session_id"], q or msg, context) if q or msg else None
            if qid:
                flags.append("question_forwarded")
                if not out:
                    out += emit_bursts(deps, pick(deps.kb.policy["ask_forwarded"], used, "ask_forwarded", deps.rng))
        elif name == "get_news":
            route = "news"
            news = await _news(deps, state, messages, args, cards, facts, used)
            out += news["out"]
            flags += news["flags"]
            trace += news["trace"]
    # Jev gate: they want to connect but the LLM only talked about it ("want me to start a connect?").
    # Code starts the flow; permission-asking bubbles were already filtered in _stream.
    wants = gates.get("wants_connect") or 0.0
    if (route == "converse" and "tool_request" not in update and wants >= s.t_connect and not state.get("connected")
            and CONNECT_HINT_RE.search(msg)
            and not (state.get("tool") or {}).get("stage") in ("collect", "pick_slot", "confirm")):
        kind = "meeting" if MEETING_RE.search(msg) else "lead"
        update["tool_request"] = {"kind": kind, "about": None}
        route = "tools"
        flags.append("connect_by_gate")
        trace.append({"step": "tool_call", "name": "start_connect", "by": "jev_gate", "wants_connect": wants})
    if not out and route == "converse":
        flags.append("empty_reply")
        out += emit_bursts(deps, pick(deps.kb.policy["ack"], used, "ack", deps.rng))
    return {**base, "out": out, "flags": flags, "trace": trace, "visitor": res["visitor"], "route": route,
            "used_lines": sorted(used), **update}


async def _news(deps: Deps, state: TurnState, messages: list[dict], args: dict, cards, facts, used) -> dict:
    topic = args.get("topic") if args.get("topic") in ("tech_industry", "tn_politics") else None
    now = deps.now()
    items = []
    if topic and deps.store is not None:
        try:
            items = await deps.store.news(str(args.get("query") or state["message"]), topic, now=now)
        except Exception as e:  # noqa: BLE001
            log.warning("news retrieval failed: %s", e)
    lines = [f"[{relative_day(n.published_at, now)}] {n.headline}: {n.gist}" for n in items]
    trace = [{"step": "news", "topic": topic, "items": [n.id for n in items]}]
    if not lines:
        out = emit_bursts(deps, pick(deps.kb.policy["not_following"], used, "not_following", deps.rng))
        return {"out": out, "flags": ["news_gap"], "trace": trace}
    sys = dict(messages[0])
    sys["content"] = [*messages[0]["content"],
                      {"type": "text", "text": prompts.dynamic_block(clock_block="", derived="", visitor={},
                                                                     disclosed=False, notes=[], news_lines=lines)}]
    res = await _stream(deps, state, [sys, *messages[1:]], cards=cards, facts=facts, max_b=2, tools=None,
                        gates_task=None, news_lines=lines, politics=topic == "tn_politics")
    out = res["out"] or emit_bursts(deps, pick(deps.kb.policy["not_following"], used, "not_following", deps.rng))
    return {"out": out, "flags": res["flags"], "trace": trace + res["trace"]}


# --------------------------------------------------------------------------- who hook + finalize

async def who_hook(state: TurnState, config: RunnableConfig) -> dict:
    deps = deps_of(config)
    visitor = state.get("visitor") or {}
    if not should_ask(visitor_name=visitor.get("name"), asked=bool(state.get("asked_who")),
                      visitor_msgs=state.get("visitor_msgs") or 0, route=state.get("route") or "",
                      ask_after=deps.settings.who_hook_after_messages):
        return {}
    used = used_of(state)
    out = emit_bursts(deps, pick(deps.kb.policy["who_hook"], used, "who_hook", deps.rng))
    return {"out": out, "asked_who": True, "used_lines": sorted(used), "trace": [{"step": "who_hook", "asked": True}]}


async def finalize(state: TurnState, config: RunnableConfig) -> dict:
    deps = deps_of(config)
    history = list(state.get("history") or [])
    history.append({"role": "visitor", "text": state["message"]})
    if state.get("out"):
        history.append({"role": "chandru", "text": "\n".join(state["out"])})
    return {"history": history[-deps.settings.history_turns * 2:]}
