"""Long-term visitor memory (same browser only).

visitor_id (browser localStorage, long-lived) → many conversations (one per visit; a new one after
`conversation_gap_min` of silence). Each finished conversation is summarised into a small encrypted profile
(name/company/role they shared, topics, lead saved). The next visit starts a FRESH conversation with that
profile in context: a person remembers who you are, not the transcript.

Never: link visitors by a claimed name, IP or fingerprint; store answers to personal questions; keep anything
past `retention_days` of inactivity. "Forget me" wipes it all, including LangGraph checkpoints.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field

from app.graph.state import Deps
from app.intelligence.llm import LLMError

log = logging.getLogger(__name__)
SENSITIVE_RE = re.compile(r"\b(salary|ctc|pay|package|single|married|girlfriend|boyfriend|relationship|religion|"
                          r"caste|address|age|how old|party|vote|politic\w*|health|family|parents)\b", re.I)
FORGET_RE = re.compile(r"^\s*(please\s+)?(forget|delete|erase)\s+(me|about me|everything|my (data|chats?))\b", re.I)
MAX_TOPICS = 8


@dataclass
class Visit:
    visitor_id: str
    conversation_id: str
    visits: int
    profile: dict = field(default_factory=dict)
    last_seen: float | None = None   # previous visit's last activity
    new_conversation: bool = True

    @property
    def returning(self) -> bool:
        return self.visits > 1 and bool(self.profile or self.last_seen)


class VisitorMemory:
    def __init__(self, deps: Deps, graph, checkpointer):
        self.deps = deps
        self.db = deps.db
        self.box = deps.box
        self.graph = graph
        self.checkpointer = checkpointer

    # ------------------------------------------------------------------ visits
    async def _load(self, visitor_id: str):
        return await self.db.fetchone("SELECT * FROM visitors WHERE id=?", (visitor_id,))

    def _profile(self, row) -> dict:
        if row is None or row["profile_enc"] is None:
            return {}
        try:
            return json.loads(self.box.open(row["profile_enc"]))
        except Exception:  # noqa: BLE001 - key rotated / corrupt: start clean rather than crash
            return {}

    async def open(self, visitor_id: str, tz: str | None = None) -> Visit:
        """Called on hello and before every message: reuse the conversation unless it went quiet."""
        now = time.time()
        row = await self._load(visitor_id)
        if row is None:
            conv = self._new_id()
            await self.db.execute(
                "INSERT INTO visitors(id, created_at, last_seen, visits, tz, current_conv) VALUES (?,?,?,?,?,?)",
                (visitor_id, now, now, 1, tz, conv))
            await self._start_conversation(conv, visitor_id, now)
            return Visit(visitor_id, conv, visits=1)
        profile = self._profile(row)
        conv = row["current_conv"]
        c = await self.db.fetchone("SELECT * FROM conversations WHERE id=?", (conv,)) if conv else None
        gap_s = self.deps.settings.conversation_gap_min * 60
        if c is not None and now - (c["last_msg_at"] or c["started_at"]) <= gap_s:
            return Visit(visitor_id, conv, visits=row["visits"], profile=profile, last_seen=row["last_seen"],
                         new_conversation=False)
        # gone quiet: summarise the old conversation into the profile, start a new one
        if c is not None and not c["summarized"]:
            profile = await self.summarize(conv, visitor_id) or profile
        new = self._new_id()
        await self.db.execute("UPDATE visitors SET visits=visits+1, current_conv=?, tz=COALESCE(?, tz) WHERE id=?",
                              (new, tz, visitor_id))
        await self._start_conversation(new, visitor_id, now)
        return Visit(visitor_id, new, visits=row["visits"] + 1, profile=profile, last_seen=row["last_seen"])

    async def touch(self, visit: Visit) -> None:
        now = time.time()
        await self.db.execute("UPDATE visitors SET last_seen=? WHERE id=?", (now, visit.visitor_id))
        await self.db.execute("UPDATE conversations SET last_msg_at=?, msg_count=msg_count+1 WHERE id=?",
                              (now, visit.conversation_id))

    async def _start_conversation(self, conv: str, visitor_id: str, now: float) -> None:
        await self.db.execute(
            "INSERT INTO conversations(id, visitor_id, started_at, last_msg_at) VALUES (?,?,?,?)",
            (conv, visitor_id, now, None))

    @staticmethod
    def _new_id() -> str:
        return str(uuid.uuid4())

    # ------------------------------------------------------------------ summarise
    async def summarize(self, conversation_id: str, visitor_id: str) -> dict | None:
        """Fold one finished conversation into the visitor profile. Idempotent per conversation."""
        rows = await self.db.fetchall("SELECT role, text FROM messages WHERE session_id=? ORDER BY id",
                                      (conversation_id,))
        await self.db.execute("UPDATE conversations SET summarized=1 WHERE id=?", (conversation_id,))
        if not rows:
            return None
        row = await self._load(visitor_id)
        profile = self._profile(row)
        state = {}
        try:
            snap = await self.graph.aget_state({"configurable": {"thread_id": conversation_id, "deps": self.deps}})
            state = snap.values or {}
        except Exception as e:  # noqa: BLE001
            log.warning("no checkpoint for %s: %s", conversation_id, e)
        for k in ("name", "company", "role"):
            v = (state.get("visitor") or {}).get(k)
            if v:
                profile[k] = v
        if state.get("connected"):
            profile["lead_saved"] = True
        transcript = "\n".join(f"{r['role']}: {r['text']}" for r in rows[-30:])
        try:
            j = await self.deps.llm.complete_json([
                {"role": "system", "content": (
                    "From this portfolio-site chat, note what Chandru should remember about the visitor next time. "
                    "Return JSON {\"topics\": [up to 4 short phrases about what they were interested in, e.g. "
                    "\"mewatch language routing\"], \"note\": \"one short line, e.g. recruiter hiring for an AI role\"}. "
                    "Never include personal or sensitive subjects (salary, relationships, religion, caste, politics, "
                    "health, age, address) and never quote the visitor.")},
                {"role": "user", "content": transcript},
            ], max_tokens=150, timeout=8.0)
            topics = [str(t)[:60] for t in (j.get("topics") or []) if t and not SENSITIVE_RE.search(str(t))]
            note = str(j.get("note") or "")[:120]
            profile["topics"] = (topics + [t for t in profile.get("topics", []) if t not in topics])[:MAX_TOPICS]
            if note and not SENSITIVE_RE.search(note):
                profile["note"] = note
        except LLMError as e:
            log.warning("memory summary failed: %s", e)
        await self.db.execute("UPDATE visitors SET profile_enc=? WHERE id=?",
                              (self.box.seal(json.dumps(profile)), visitor_id))
        return profile

    async def summarize_idle(self) -> int:
        """Scheduler job: summarise conversations that went quiet (so the profile is ready before they return)."""
        cutoff = time.time() - self.deps.settings.conversation_gap_min * 60
        rows = await self.db.fetchall(
            "SELECT id, visitor_id FROM conversations WHERE summarized=0 AND last_msg_at IS NOT NULL AND last_msg_at < ?",
            (cutoff,))
        for r in rows:
            await self.summarize(r["id"], r["visitor_id"])
        return len(rows)

    # ------------------------------------------------------------------ forget + retention
    async def forget(self, visitor_id: str) -> int:
        """Right to erasure: visitor, profile, conversations, transcripts, logs, leads, bookings, checkpoints."""
        convs = [r["id"] for r in await self.db.fetchall("SELECT id FROM conversations WHERE visitor_id=?",
                                                         (visitor_id,))]
        for conv in convs:
            for table in ("messages", "turn_logs", "client_msgs", "leads", "bookings", "sessions"):
                col = "id" if table == "sessions" else "session_id"
                await self.db.conn.execute(f"DELETE FROM {table} WHERE {col}=?", (conv,))
            try:
                await self.checkpointer.adelete_thread(conv)
            except Exception as e:  # noqa: BLE001
                log.warning("checkpoint delete failed for %s: %s", conv, e)
        await self.db.conn.execute("DELETE FROM questions WHERE visitor_id=?", (visitor_id,))
        await self.db.conn.execute("DELETE FROM conversations WHERE visitor_id=?", (visitor_id,))
        await self.db.conn.execute("DELETE FROM visitors WHERE id=?", (visitor_id,))
        await self.db.conn.commit()
        return len(convs)

    async def purge(self) -> int:
        """Forget visitors inactive for `retention_days`; also drop checkpoints of legacy sessions."""
        cutoff = time.time() - self.deps.settings.retention_days * 86400
        stale = [r["id"] for r in await self.db.fetchall("SELECT id FROM visitors WHERE last_seen < ?", (cutoff,))]
        for v in stale:
            await self.forget(v)
        for r in await self.db.fetchall("SELECT id FROM sessions WHERE last_seen < ?", (cutoff,)):
            try:
                await self.checkpointer.adelete_thread(r["id"])
            except Exception:  # noqa: BLE001
                pass
        await self.db.purge(self.deps.settings.retention_days)
        return len(stale)


def memory_note(visit_profile: dict, visits: int, last_seen: float | None, now: float) -> str:
    """Prompt note for a returning visitor: light familiarity, no transcript."""
    if visits <= 1:
        return ""
    days = (now - last_seen) / 86400 if last_seen else None
    when = ("earlier today" if days is not None and days < 1 else
            "yesterday" if days is not None and days < 2 else
            f"{int(days)} days ago" if days is not None else "before")
    bits = []
    who = " ".join(x for x in (visit_profile.get("name"),
                               f"from {visit_profile['company']}" if visit_profile.get("company") else None) if x)
    if who:
        bits.append(f"they are {who}")
    if visit_profile.get("note"):
        bits.append(visit_profile["note"])
    if visit_profile.get("topics"):
        bits.append("last time they asked about " + ", ".join(visit_profile["topics"][:4]))
    if visit_profile.get("lead_saved"):
        bits.append("you already noted their contact details")
    known = "; ".join(bits) if bits else "nothing specific"
    return (f"MEMORY: this visitor has chatted with you before (visit {visits}, last seen {when}). What you remember: "
            f"{known}. Greet them lightly like a person who remembers them, at most once. Don't quote old messages "
            f"or resume the old thread unless they bring it up.")
