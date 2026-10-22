"""SQLite (WAL) for sessions, messages, leads, bookings, outbox, turn logs."""

from __future__ import annotations

import json
import time
from pathlib import Path

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY, created_at REAL, last_seen REAL, persona TEXT, tz TEXT,
  visitor_name_enc BLOB, visitor_company_enc BLOB, turns INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, turn_id TEXT, role TEXT,
  text TEXT, route TEXT, created_at REAL
);
CREATE INDEX IF NOT EXISTS messages_session ON messages(session_id, id);
CREATE TABLE IF NOT EXISTS client_msgs (session_id TEXT, client_msg_id TEXT, PRIMARY KEY (session_id, client_msg_id));
CREATE TABLE IF NOT EXISTS leads (
  id TEXT PRIMARY KEY, session_id TEXT, name_enc BLOB, company_enc BLOB, role_enc BLOB,
  email_enc BLOB, about_enc BLOB, created_at REAL
);
CREATE TABLE IF NOT EXISTS bookings (
  id TEXT PRIMARY KEY, session_id TEXT, idempotency_key TEXT UNIQUE, event_id TEXT,
  start TEXT, end TEXT, attendee_email_enc BLOB, meet_url TEXT, status TEXT, created_at REAL
);
CREATE TABLE IF NOT EXISTS outbox (
  event_id TEXT PRIMARY KEY, kind TEXT, payload_enc BLOB, attempts INTEGER DEFAULT 0,
  next_attempt_at REAL, sent_at REAL, last_error TEXT, created_at REAL
);
CREATE TABLE IF NOT EXISTS turn_logs (turn_id TEXT PRIMARY KEY, session_id TEXT, created_at REAL, json TEXT);
CREATE TABLE IF NOT EXISTS visitors (
  id TEXT PRIMARY KEY, created_at REAL, last_seen REAL, visits INTEGER DEFAULT 0, tz TEXT,
  profile_enc BLOB, current_conv TEXT
);
CREATE TABLE IF NOT EXISTS conversations (
  id TEXT PRIMARY KEY, visitor_id TEXT, started_at REAL, last_msg_at REAL, msg_count INTEGER DEFAULT 0,
  summarized INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS conversations_visitor ON conversations(visitor_id);
CREATE TABLE IF NOT EXISTS questions (
  id TEXT PRIMARY KEY, visitor_id TEXT, conversation_id TEXT, question_enc BLOB, context_enc BLOB,
  thread_id TEXT, answer_enc BLOB, status TEXT, created_at REAL, answered_at REAL, delivered_at REAL
);
CREATE INDEX IF NOT EXISTS questions_visitor ON questions(visitor_id, status);
CREATE TABLE IF NOT EXISTS news_runs (
  run_id TEXT PRIMARY KEY, started_at REAL, fetched INTEGER, kept INTEGER, upserted INTEGER,
  status TEXT, error TEXT
);
"""


class DB:
    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn

    @classmethod
    async def open(cls, path: Path) -> "DB":
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(path)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA busy_timeout=5000")
        await conn.executescript(SCHEMA)
        await conn.commit()
        return cls(conn)

    async def close(self) -> None:
        await self.conn.close()

    async def execute(self, sql: str, params: tuple = ()) -> None:
        await self.conn.execute(sql, params)
        await self.conn.commit()

    async def fetchall(self, sql: str, params: tuple = ()) -> list[aiosqlite.Row]:
        async with self.conn.execute(sql, params) as cur:
            return list(await cur.fetchall())

    async def fetchone(self, sql: str, params: tuple = ()) -> aiosqlite.Row | None:
        async with self.conn.execute(sql, params) as cur:
            return await cur.fetchone()

    # --- sessions / messages
    async def touch_session(self, sid: str, tz: str | None) -> None:
        now = time.time()
        await self.execute(
            "INSERT INTO sessions(id, created_at, last_seen, tz) VALUES (?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen, tz=COALESCE(excluded.tz, sessions.tz)",
            (sid, now, now, tz),
        )

    async def seen_client_msg(self, sid: str, client_msg_id: str) -> bool:
        cur = await self.conn.execute(
            "INSERT OR IGNORE INTO client_msgs(session_id, client_msg_id) VALUES (?,?)", (sid, client_msg_id))
        await self.conn.commit()
        return cur.rowcount == 0

    async def add_message(self, sid: str, turn_id: str, role: str, text: str, route: str | None) -> None:
        await self.execute(
            "INSERT INTO messages(session_id, turn_id, role, text, route, created_at) VALUES (?,?,?,?,?,?)",
            (sid, turn_id, role, text, route, time.time()),
        )

    async def log_turn(self, turn_id: str, sid: str, data: dict) -> None:
        await self.execute(
            "INSERT OR REPLACE INTO turn_logs(turn_id, session_id, created_at, json) VALUES (?,?,?,?)",
            (turn_id, sid, time.time(), json.dumps(data, default=str)),
        )

    async def purge(self, retention_days: int) -> None:
        cutoff = time.time() - retention_days * 86400
        for table, col in (("messages", "created_at"), ("turn_logs", "created_at"), ("sessions", "last_seen")):
            await self.conn.execute(f"DELETE FROM {table} WHERE {col} < ?", (cutoff,))
        await self.conn.execute("DELETE FROM outbox WHERE sent_at IS NOT NULL AND sent_at < ?", (time.time() - 90 * 86400,))
        await self.conn.commit()
