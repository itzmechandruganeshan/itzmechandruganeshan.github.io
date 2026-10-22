"""Jev call sites that remain after ADR-008: J3 grounding, J4 confirmation, slot pick, J6 news, J7 partisan.
The per-turn gates live in app/graph/gates.py. Intent routing was removed: the LLM handles the conversation.

Question wording matters: the question id is never sent to the model, so each
criterion description has to carry the whole meaning.
"""

from __future__ import annotations

import logging
import re

from app.intelligence.jev import JevClient, JevError, q_choice, q_noul, q_score

log = logging.getLogger(__name__)

PERSONAL = {
    "relationship": "Dating, girlfriend, marriage, relationship status",
    "family": "Parents, siblings, family members",
    "religion_caste": "Religion, caste, community, beliefs",
    "political_allegiance": "Which party or leader he supports or votes for",
    "salary": "Salary, CTC, compensation, expected pay",
    "health": "Health, body, weight, medical",
    "address": "Home address, exact area or street where he lives",
    "age": "His age or birth year",
    "controversial": "Hot-button controversial social topics",
    "other_personal": "Some other genuinely private matter a stranger shouldn't ask",
    "none": "Not a private question. Hobbies, fun, gym, weekends, cooking, food, routine, work and city are all fine to talk about",
}
NEWS_TOPICS = {
    "tech_industry": "Tech industry news: AI and LLM releases, big tech companies, startups, layoffs, hiring trends",
    "tn_politics": "Tamil Nadu politics: state government, parties, elections, policies, political leaders",
    "other": "Some other news: sports, entertainment, world politics, other states",
    "none": "Not about news or recent events",
}
IDENTITY_RE = re.compile(
    r"\b(are|r) (you|u) (a |an )?(bot|ai|robot|real|human|chatgpt|gpt|llm)\b"
    r"|\b(am i|i'm|im) (talking|chatting|texting) (to|with) (a |an )?(bot|ai|real|human)\b"
    r"|\bis this (a |an )?(bot|ai|automated|real)\b|\b(the )?real chandru\b|\b(actually|really) (you|him)\b|\byou'?re (a |an )?(bot|ai|robot)\b",
    re.I,
)
INJECTION_RE = re.compile(
    r"ignore (all |your |the )?(previous |prior )?(instructions|prompt|rules)|system prompt|"
    r"you are now|developer mode|jailbreak|print your (prompt|instructions)|act as",
    re.I,
)


# ---------------------------------------------------------------- J3, J4, slot pick, J6, J7

async def burst_grounded(jev: JevClient, burst: str, evidence: list[str]) -> float | None:
    try:
        res = await jev.decide(
            {"reply": burst, "evidence": evidence},
            {"ok": q_noul("Is every factual claim in `reply` supported by `evidence`? Casual filler with no facts counts as supported.")},
        )
        return res.noul("ok")
    except JevError as e:
        log.warning("jev J3 failed: %s", e)
        return None


CONFIRM = {
    "confirm": "Agrees or confirms, e.g. yes, sure, sounds good, go ahead, works",
    "reject": "Declines or cancels, e.g. no, not now, never mind",
    "change": "Wants to change a detail, e.g. a different time or a corrected email",
    "unrelated": "Talks about something else entirely and ignores the question",
    "unclear": "Cannot tell",
}


async def confirmation(jev: JevClient, asked: str, reply: str) -> str:
    try:
        res = await jev.decide(
            {"bot_asked": asked, "visitor_reply": reply},
            {"c": q_choice("How does `visitor_reply` respond to the confirmation question in `bot_asked`?", CONFIRM)},
        )
        return res.choice("c").choice
    except JevError as e:
        log.warning("jev J4 failed, using rules: %s", e)
        r = reply.lower().strip()
        if re.match(r"^(y|ya|yes|yep|yeah|sure|ok|okay|go ahead|confirm|done|sounds good|works|perfect)\b", r):
            return "confirm"
        if re.match(r"^(no|nope|nah|cancel|never ?mind|not now)\b", r):
            return "reject"
        return "unclear"


async def pick_slot(jev: JevClient, reply: str, slots: dict[str, str]) -> tuple[str, float]:
    criteria = dict(slots)
    criteria["none"] = "None of these times, or no time mentioned"
    try:
        res = await jev.decide(
            {"offered": slots, "visitor_reply": reply},
            {"slot": q_choice("Which offered meeting time does `visitor_reply` pick?", criteria)},
        )
        a = res.choice("slot")
        return a.choice, a.confidence
    except JevError:
        return "none", 0.0


async def news_relevance(jev: JevClient, title: str, summary: str) -> tuple[str, float, float]:
    res = await jev.decide(
        {"title": title, "summary": summary[:800]},
        {
            "topic": q_choice("What is this news item about?", {
                "tech_industry": NEWS_TOPICS["tech_industry"],
                "tn_politics": NEWS_TOPICS["tn_politics"],
                "neither": "Anything else, including opinion columns and ads",
            }),
            "newsworthy": q_score("How significant is this news for someone following the topic?", [
                "Trivial or promotional", "Minor update", "Notable news", "Major news people will talk about",
            ]),
        },
    )
    t = res.choice("topic")
    return t.choice, t.confidence, res.score("newsworthy").score


async def partisan(jev: JevClient, burst: str) -> float | None:
    try:
        res = await jev.decide(
            {"reply": burst},
            {"p": q_noul("Does `reply` endorse, praise, attack or mock a political party, leader, caste, religion or community, or say who to vote for?")},
        )
        return res.noul("p")
    except JevError as e:
        log.warning("jev J7 failed: %s", e)
        return None


# ---------------------------------------------------------------- J8: verify an LLM tool call, J9: slot answered
TOOL_CHECKS = {
    "share_resume": "Is the visitor asking for Chandru's resume or CV?",
    "start_connect": "Does the visitor want to connect with Chandru, talk about a job/role/hiring, share their "
                     "details, or book a call?",
    "get_news": "Is the visitor asking about recent news or current events?",
    "ask_chandru": "Has the visitor agreed to (or asked for) Chandru checking something and getting back to them?",
}


async def tool_call_valid(jev: JevClient, tool: str, message: str, recent: list[str]) -> float | None:
    """The LLM proposes a tool; Jev verifies the visitor actually asked for it (LLMs over-call tools)."""
    q = TOOL_CHECKS.get(tool)
    if not q:
        return None
    try:
        res = await jev.decide({"message": message, "recent_turns": recent},
                               {"ok": q_noul(q + " Judge `message` in the context of `recent_turns`.")})
        return res.noul("ok")
    except JevError as e:
        log.warning("jev J8 failed: %s", e)
        return None


async def answers_question(jev: JevClient, asked: str, reply: str) -> float | None:
    """J9: during lead/meeting collection, is the visitor's reply an answer to what we asked?"""
    try:
        res = await jev.decide({"we_asked_for": asked, "visitor_reply": reply},
                               {"ok": q_noul("Does `visitor_reply` answer `we_asked_for` (or decline to share it), "
                                             "rather than talk about something else?")})
        return res.noul("ok")
    except JevError as e:
        log.warning("jev J9 failed: %s", e)
        return None
