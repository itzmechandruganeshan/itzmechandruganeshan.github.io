"""Helpers shared by the conversation and tool nodes."""

from __future__ import annotations

import logging
import re
from datetime import datetime

from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer

from app.context.clock import build_clock
from app.data import Card
from app.graph.state import Deps, TurnState
from app.humanizer.bursts import shape
from app.intelligence import decisions as dec
from app.intelligence.llm import LLMError
from app.persona_rules.politics_guard import keyword_flag
from app.retrieval import checks

log = logging.getLogger(__name__)
CONNECTOR_RE = re.compile(r"^\s*(then|and|also|so|but|plus|or)\b[\s,]*", re.I)


def deps_of(config: RunnableConfig) -> Deps:
    return config["configurable"]["deps"]


def emit_bursts(deps: Deps, bursts: list[str], *, max_bursts: int = 6) -> list[str]:
    shaped = shape(bursts, style=deps.kb.style, protected=deps.protected, max_bursts=max_bursts)
    writer = get_stream_writer()
    for b in shaped:
        writer({"type": "burst", "text": b, "src": "template"})
    return shaped


def emit_card(card: dict) -> None:
    get_stream_writer()({"type": "card", **card})


def clock_of(deps: Deps, state: TurnState):
    return build_clock(deps.kb, now=deps.now(), visitor_tz=(state.get("visitor") or {}).get("tz"),
                       tz=deps.settings.timezone, rng=deps.rng)


def used_of(state: TurnState) -> set[str]:
    return set(state.get("used_lines") or [])


def derived_facts(deps: Deps) -> str:
    """Facts that need date math are computed in code, so the LLM never does arithmetic and checks can verify."""
    since = str(deps.kb.facts.get("current", {}).get("since", ""))
    if not since:
        return ""
    y, m = (int(x) for x in since.split("-")[:2])
    now = deps.now()
    months = (now.year - y) * 12 + (now.month - m)

    def span(ym: str) -> str:
        yy, mm = (int(x) for x in str(ym).split("-")[:2])
        total = (now.year - yy) * 12 + (now.month - mm)
        return f"{total} months (~{total / 12:.1f} years)"

    exp = deps.kb.facts.get("experience", [])
    first_any = min((str(e["from"]) for e in exp), default=since)
    first_full = min((str(e["from"]) for e in exp if "intern" not in e["role"].lower()), default=since)
    return (f"DERIVED: at {deps.kb.facts['current']['company']} for {months} months "
            f"(since {datetime(y, m, 1):%B %Y}); full-time experience {span(first_full)}; "
            f"including internships {span(first_any)}; today is {now:%A %d %B %Y}")


def needs_grounding(clean: str, raw: str, entities: set[str]) -> bool:
    """J3 only for lines that state checkable facts (cites, numbers, Chandru's tech/companies)."""
    low = clean.lower()
    return bool(checks.citations(raw)) or bool(checks.NUMBER.search(clean)) or any(
        re.search(rf"(?<![\w]){re.escape(e)}(?![\w])", low) for e in entities)


_WORD = re.compile(r"[a-z0-9]{3,}")


def relevant_cards(deps: Deps, text: str, cards: list[Card], k: int = 8) -> list[Card]:
    """Evidence for a line that cites nothing: cards of any project it names, else closest by word overlap."""
    low = text.lower()
    named = {p.id for p in deps.kb.projects if any(re.search(rf"(?<![\w]){re.escape(a)}(?![\w])", low)
                                                   for a in (*p.aliases, p.id))}
    if named:
        return [c for c in cards if c.project_id in named]
    words = set(_WORD.findall(low))
    scored = sorted(cards, key=lambda c: -len(words & set(_WORD.findall(c.text.lower()))))
    return scored[:k]


async def check_line(deps: Deps, raw: str, clean: str, cards: list[Card], facts: str, step: dict, *,
                     news_lines: list[str] | None = None, politics: bool = False) -> tuple[bool, list[str]]:
    """Code checks (numbers/entities/citations/negative cards), J7 for TN politics, J3 for factual lines.
    A line that cites nothing is checked against the cards it is plausibly about, not the whole knowledge base."""
    cites = checks.citations(raw)
    by_id = {c.id: c for c in cards}
    support = [by_id[c] for c in cites if c in by_id] or relevant_cards(deps, clean, cards)
    if news_lines is not None:
        res = checks.check_burst(raw, clean, [], " ".join(news_lines) + " " + facts, set())
    else:
        res = checks.check_burst(raw, clean, cards if cites else support, facts, deps.entities)
    ok, problems = res.ok, res.problems
    step["cites"] = checks.citations(raw)
    step["code_checks"] = problems or "pass"
    if ok and politics:
        if keyword_flag(clean, deps.kb.banned_politics_terms):
            ok, problems = False, ["politics keyword"]
        else:
            p = await dec.partisan(deps.jev, clean)
            step["j7_partisan"] = p
            if p is not None and p >= deps.settings.t_partisan:
                ok, problems = False, [f"partisan {p:.2f}"]
    if ok and news_lines is None and needs_grounding(clean, raw, deps.entities):
        # registry entries (name, company, tech) back the cards: "parses .rex files in python" is supported
        pids = {c.project_id for c in support}
        registry = [f"{p.name} at {p.company}; tech: {', '.join(p.tech)}" for p in deps.kb.projects if p.id in pids]
        g = await dec.burst_grounded(deps.jev, clean, [c.text for c in support] + registry + [facts])
        step["j3_grounded"] = g
        if g is not None and g < deps.settings.t_grounded:
            ok, problems = False, [f"j3 {g:.2f}"]
    return ok, problems


async def repair_line(deps: Deps, line: str, cards: list[Card], facts: str) -> str | None:
    """One rewrite attempt for a bubble that failed a check: keep the voice, drop anything unsupported."""
    ev = "\n".join(f"⟦c:{c.id}⟧ {c.text}" for c in cards)
    try:
        j = await deps.llm.complete_json([
            {"role": "system", "content": (
                "You fix one casual text message so every fact in it is supported by CARDS or FACTS. "
                "Remove or soften any number, tool, company or claim that isn't there; never add new ones. "
                "Keep it short, lowercase-ish, same tone. End with the ids used, like ⟦c:mw-07⟧ or ⟦c:facts⟧. "
                "Return JSON {\"line\": str}. If nothing true is left to say, return {\"line\": \"\"}.")},
            {"role": "user", "content": f"CARDS:\n{ev}\n\nFACTS:\n{facts[:3000]}\n\nMESSAGE: {line}"},
        ], model=deps.settings.llm_models[0], max_tokens=120, timeout=4.0)
        return str(j.get("line") or "").strip() or None
    except LLMError as e:
        log.warning("repair failed: %s", e)
        return None
