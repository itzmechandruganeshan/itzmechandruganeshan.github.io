"""C2a: emails to Chandru through an outbox (exactly one per event, retried with backoff), sent with Gmail via
Composio MCP (ADR-010). "Ask the real me" questions go out the same way; their Gmail thread id is kept so the
reply can be collected."""

from __future__ import annotations

import json
import logging
import time

from app.config import Settings
from app.storage.crypto import Box
from app.storage.db import DB

log = logging.getLogger(__name__)
MAX_ATTEMPTS = 5

SUBJECTS = {
    "lead.created": "New connect request: {name} ({company})",
    "booking.created": "Call booked: {name} on {when}",
    "booking.failed": "Booking failed for {name}",
    "news_ingest.failing": "Virtual Me: news ingest failing",
    "digest": "Virtual Me daily digest",
    "question.asked": "A visitor asked: {question}",
}


async def enqueue(db: DB, box: Box, event_id: str, kind: str, payload: dict) -> None:
    await db.execute(
        "INSERT OR IGNORE INTO outbox(event_id, kind, payload_enc, attempts, next_attempt_at, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (event_id, kind, box.seal(json.dumps(payload)), 0, time.time(), time.time()),
    )


def render(kind: str, p: dict) -> tuple[str, str]:
    subject = SUBJECTS.get(kind, kind).format_map({k: (v or "-") for k, v in p.items()} | _Missing())
    lines = [f"{k}: {v}" for k, v in p.items() if k not in ("summary",) and v]
    if p.get("summary"):
        lines += ["", "Chat summary:", p["summary"]]
    if kind == "question.asked":
        lines += ["", "Reply to this email with your answer. It goes back to them, in your voice, "
                      "the next time they open the chat."]
    else:
        lines += ["", f"Transcript: uv run python scripts/admin.py transcript {p.get('session_id', '')}"]
    return subject, "\n".join(lines)


class _Missing(dict):
    def __missing__(self, key):
        return "-"


async def _send(cx, to: str, subject: str, body: str) -> dict:
    from app.integrations.composio_mcp import pick_args
    args = pick_args(cx.schema("send_email"), {
        "to": ["recipient_email", "to", "recipient"],
        "subject": ["subject"],
        "body": ["body", "message", "text"],
        "html": ["is_html"],
    }, {"to": to, "subject": subject, "body": body, "html": False})
    res = await cx.call("send_email", args)
    return res if isinstance(res, dict) else {}


async def deliver_due(db: DB, box: Box, s: Settings, cx) -> int:
    rows = await db.fetchall(
        "SELECT * FROM outbox WHERE sent_at IS NULL AND attempts < ? AND next_attempt_at <= ? LIMIT 20",
        (MAX_ATTEMPTS, time.time()),
    )
    sent = 0
    for r in rows:
        payload = json.loads(box.open(r["payload_enc"]))
        subject, body = render(r["kind"], payload)
        try:
            res = await _send(cx, s.alert_email, subject, body)
            await db.execute("UPDATE outbox SET sent_at=? WHERE event_id=?", (time.time(), r["event_id"]))
            thread = res.get("threadId") or res.get("thread_id") or (res.get("response_data") or {}).get("threadId")
            if r["kind"] == "question.asked" and thread:
                await db.execute("UPDATE questions SET thread_id=? WHERE id=?", (str(thread), payload["question_id"]))
            sent += 1
        except Exception as e:  # noqa: BLE001 - any failure is retried
            attempts = r["attempts"] + 1
            await db.execute(
                "UPDATE outbox SET attempts=?, next_attempt_at=?, last_error=? WHERE event_id=?",
                (attempts, time.time() + 30 * 2 ** attempts, str(e)[:300], r["event_id"]),
            )
            log.warning("email %s failed (attempt %d): %s", r["event_id"], attempts, e)
    return sent
