"""Composio MCP actions + "ask the real me", with a fake MCP client (no network, no credits)."""

import json

import pytest

from app.tools import notify, questions


class FakeCX:
    """Mimics ComposioMCP: resolved tools with real-looking schemas, records every call."""

    def __init__(self):
        self.calls = []
        self.resolved = {"free_slots": "GOOGLECALENDAR_FIND_FREE_SLOTS", "create_event": "GOOGLECALENDAR_CREATE_EVENT",
                         "send_email": "GMAIL_SEND_EMAIL", "fetch_thread": "GMAIL_FETCH_MESSAGE_BY_THREAD_ID"}
        self.schemas = {
            "free_slots": {"time_min": {}, "time_max": {}, "items": {}, "timezone": {}},
            "create_event": {"summary": {}, "description": {}, "start_datetime": {}, "end_datetime": {},
                             "event_duration_minutes": {}, "attendees": {}, "create_meeting_room": {}, "timezone": {},
                             "calendar_id": {}, "send_updates": {}},
            "send_email": {"recipient_email": {}, "subject": {}, "body": {}, "is_html": {}},
            "fetch_thread": {"thread_id": {}},
        }
        self.thread_reply = None

    def configured(self):
        return True

    def schema(self, kind):
        return self.schemas[kind]

    async def call(self, kind, args, timeout=20.0):
        self.calls.append((kind, args))
        if kind == "free_slots":
            return {"calendars": {"primary": {"busy": [{"start": "2026-10-22T10:00:00+05:30",
                                                         "end": "2026-10-22T12:00:00+05:30"}]}}}
        if kind == "create_event":
            return {"response_data": {"id": "ev123", "hangoutLink": "https://meet.google.com/abc-defg-hij"}}
        if kind == "send_email":
            return {"threadId": "th-1"}
        if kind == "fetch_thread":
            msgs = [{"messageText": "A visitor asked: ..."}]
            if self.thread_reply:
                msgs.append({"messageText": self.thread_reply + "\n\nOn Tue, 21 Oct 2026 Chandru wrote:\n> A visitor"})
            return {"messages": msgs}
        raise AssertionError(kind)


@pytest.fixture
def cx(env):
    env.deps.actions = FakeCX()
    return env.deps.actions


async def test_meeting_booked_via_composio_with_meet_link(env, cx):
    env.llm.replies.append({"lines": ["ya let's do a call"], "tools": [{"name": "start_connect", "arguments": {"kind": "meeting"}}]})
    b1, cards, r1 = await env.say("can we set up a call?")
    slots = next(c for c in cards if c["kind"] == "slots")["slots"]
    assert r1["route"] == "tools" and len(slots) == 3
    assert all(not s["start"].startswith("2026-10-22T10:") and not s["start"].startswith("2026-10-22T11:")
               for s in slots)  # busy window respected
    env.llm.json_replies.append({"name": None})
    await env.say(slots[0]["label"], action={"action": "pick_slot", "slot_id": slots[0]["id"]})
    env.llm.json_replies.append({"name": "Priya"})
    await env.say("i'm priya")
    b4, _, _ = await env.say("priya@zoho.com")
    assert "book" in " ".join(b4).lower()
    env.jev.turns["yes"] = {"c": "confirm"}
    env.llm.json_replies.append({"summary": "Priya wants a call."})
    b5, cards5, r5 = await env.say("yes")
    assert "booked" in r5["flags"] and cards5[-1]["meet_url"].startswith("https://meet.google.com/")
    kind, args = next(c for c in cx.calls if c[0] == "create_event")
    assert args["attendees"] == ["priya@zoho.com"] and args["create_meeting_room"] is True
    # real GOOGLECALENDAR_CREATE_EVENT schema: local times + timezone; duration field (0-59 only) not used
    assert "event_duration_minutes" not in args and args["timezone"] == "Asia/Kolkata"
    assert len(args["start_datetime"]) == 19 and args["end_datetime"] > args["start_datetime"]
    assert args["send_updates"] == "all"
    rows = await env.db.fetchall("SELECT * FROM bookings")
    assert len(rows) == 1 and rows[0]["event_id"] == "ev123"


async def test_alert_email_via_gmail_mcp(env, cx):
    await notify.enqueue(env.db, env.deps.box, "lead.created:x", "lead.created",
                         {"name": "Priya", "company": "Zoho", "email": "p@z.com", "session_id": "s"})
    assert await notify.deliver_due(env.db, env.deps.box, env.deps.settings, cx) == 1
    kind, args = cx.calls[-1]
    assert kind == "send_email" and args["recipient_email"] == env.deps.settings.alert_email
    assert "Priya" in args["subject"]
    assert await notify.deliver_due(env.db, env.deps.box, env.deps.settings, cx) == 0  # exactly once


async def test_ask_the_real_me_round_trip(env, cx):
    vid = "11111111-1111-4111-8111-111111111111"
    await env.db.execute("INSERT INTO conversations(id, visitor_id, started_at) VALUES (?,?,?)", (env.sid, vid, 0))
    env.llm.replies.append({"lines": ["cool, lemme check"], "tools": [{"name": "ask_chandru",
                                                                      "arguments": {"question": "did you use kubernetes at searce?"}}]})
    _, _, rec = await env.say("yes pls check")
    assert "question_forwarded" in rec["flags"]
    # email goes out, its Gmail thread is remembered
    await notify.deliver_due(env.db, env.deps.box, env.deps.settings, cx)
    q = await env.db.fetchone("SELECT * FROM questions WHERE visitor_id=?", (vid,))
    assert q["thread_id"] == "th-1" and q["status"] == "asked"
    assert "kubernetes" in cx.calls[-1][1]["subject"].lower()
    # Chandru replies; J9 (fake: ok) accepts it; quoted text is stripped
    cx.thread_reply = "nope, mewatch runs on cloud run, no k8s there"
    assert await questions.collect(env.deps) == 1
    # next visit: delivered in his voice, only once
    env.llm.json_replies.append({"bubbles": ["oh btw, about ur kubernetes question", "nope, mewatch runs on cloud run"]})
    bubbles = await questions.deliver(env.deps, vid)
    assert bubbles and "cloud run" in " ".join(bubbles)
    assert await questions.deliver(env.deps, vid) == []


def test_strip_quoted_reply():
    assert questions.strip_quoted("yes we did\n\nOn Mon, X wrote:\n> old") == "yes we did"
    assert questions.strip_quoted("> quoted only\nreal line") == "real line"
