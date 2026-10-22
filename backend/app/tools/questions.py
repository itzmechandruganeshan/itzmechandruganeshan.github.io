"""'Ask the real me' (human in the loop, ADR-010).

1. The LLM offers "lemme check and get back to u?"; when the visitor agrees it calls `ask_chandru`, verified by
   Jev J8. `forward()` stores the question and queues an email to Chandru (Gmail via Composio MCP).
2. `collect()` (scheduler) reads replies in those Gmail threads; Jev J9 checks the reply answers the question.
3. `deliver()` runs when that visitor next opens the chat: the bot texts first, in Chandru's voice, using only
   his answer. The answer also becomes a draft card for review (`admin.py learned`).
"""

from __future__ import annotations

import logging
import re
import time
import uuid

from app.graph.state import Deps
from app.humanizer.bursts import shape
from app.intelligence import decisions as dec
from app.intelligence.llm import LLMError
from app.tools import notify

log = logging.getLogger(__name__)
MAX_OPEN_QUESTIONS = 3
QUOTED_RE = re.compile(r"\n\s*On .{5,200}wrote:.*\Z|\n\s*-{2,}\s*Original Message.*\Z", re.S | re.I)


def strip_quoted(text: str) -> str:
    text = QUOTED_RE.sub("", text or "")
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith(">")]
    return "\n".join(lines).strip()


async def forward(deps: Deps, conversation_id: str, question: str, context: str) -> str | None:
    row = await deps.db.fetchone("SELECT visitor_id FROM conversations WHERE id=?", (conversation_id,))
    visitor_id = row["visitor_id"] if row else None
    if not visitor_id:
        return None
    row = await deps.db.fetchone("SELECT COUNT(*) AS n FROM questions WHERE visitor_id=? AND status='asked'",
                                 (visitor_id,))
    if row and row["n"] >= MAX_OPEN_QUESTIONS:
        return None  # each question emails Chandru: cap what one visitor can send
    qid = f"q-{uuid.uuid4().hex[:12]}"
    await deps.db.execute(
        "INSERT INTO questions(id, visitor_id, conversation_id, question_enc, context_enc, status, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (qid, visitor_id, conversation_id, deps.box.seal(question[:500]), deps.box.seal(context[:1500]), "asked",
         time.time()))
    await notify.enqueue(deps.db, deps.box, f"question.asked:{qid}", "question.asked", {
        "question": question[:200], "context": context[:1000], "question_id": qid, "session_id": conversation_id})
    return qid


def _messages(data) -> list[dict]:
    """Normalise a Gmail thread result into [{"text": ...}, ...] in thread order."""
    msgs = None
    if isinstance(data, dict):
        for k in ("messages", "thread_messages", "items"):
            if isinstance(data.get(k), list):
                msgs = data[k]
                break
    elif isinstance(data, list):
        msgs = data
    out = []
    for m in msgs or []:
        if isinstance(m, dict):
            text = m.get("messageText") or m.get("message_text") or m.get("text") or m.get("body") or \
                m.get("snippet") or ""
            out.append({"text": str(text)})
    return out


async def collect(deps: Deps) -> int:
    """Scheduler job: pull Chandru's replies from the Gmail threads of open questions."""
    cx = deps.actions
    if not (cx and cx.configured()):
        return 0
    rows = await deps.db.fetchall("SELECT * FROM questions WHERE status='asked' AND thread_id IS NOT NULL")
    answered = 0
    for r in rows:
        try:
            from app.integrations.composio_mcp import pick_args
            args = pick_args(cx.schema("fetch_thread"), {"thread": ["thread_id", "threadId", "id"]},
                             {"thread": r["thread_id"]})
            data = await cx.call("fetch_thread", args)
        except Exception as e:  # noqa: BLE001
            log.warning("thread fetch failed for %s: %s", r["id"], e)
            continue
        msgs = _messages(data)
        if len(msgs) < 2:
            continue  # only our own email so far
        reply = strip_quoted(msgs[-1]["text"])
        question = deps.box.open(r["question_enc"])
        ok = await dec.answers_question(deps.jev, question, reply)  # J9: is this actually an answer?
        if not reply or (ok is not None and ok < deps.settings.t_answered):
            continue
        await deps.db.execute("UPDATE questions SET answer_enc=?, answered_at=?, status='answered' WHERE id=?",
                              (deps.box.seal(reply[:2000]), time.time(), r["id"]))
        answered += 1
    return answered


async def deliver(deps: Deps, visitor_id: str) -> list[str]:
    """When the visitor opens the chat: answered questions → bubbles in Chandru's voice (his facts only)."""
    rows = await deps.db.fetchall(
        "SELECT * FROM questions WHERE visitor_id=? AND status='answered' ORDER BY answered_at", (visitor_id,))
    bubbles: list[str] = []
    for r in rows:
        q, a = deps.box.open(r["question_enc"]), deps.box.open(r["answer_enc"])
        try:
            j = await deps.llm.complete_json([
                {"role": "system", "content": (
                    "You are Chandru texting a visitor who asked you something earlier that you said you'd check. "
                    "Tell them the answer now, like WhatsApp: 1-3 short casual lines, lowercase-ish, start with "
                    "something like 'oh btw, about ur question on <topic>'. Use ONLY facts from ANSWER; never add any. "
                    "Return JSON {\"bubbles\": [str]}.")},
                {"role": "user", "content": f"QUESTION: {q}\nANSWER (your own words): {a}"},
            ], model=deps.settings.llm_models[0], max_tokens=200, timeout=8.0)
            lines = [str(b) for b in j.get("bubbles") or [] if str(b).strip()]
        except LLMError as e:
            log.warning("delivery phrasing failed, sending the answer as is: %s", e)
            lines = [f"oh btw, about ur question: {a}"]
        bubbles += shape(lines, style=deps.kb.style, protected=deps.protected, max_bursts=4)
        await deps.db.execute("UPDATE questions SET status='delivered', delivered_at=? WHERE id=?",
                              (time.time(), r["id"]))
    return bubbles
