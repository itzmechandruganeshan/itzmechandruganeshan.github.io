import hashlib
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

import aiosqlite

from app.database import DB_FILE

logger = logging.getLogger(__name__)


class SessionService:
    """Handles user session retrieval, creation, and message persistence."""

    @staticmethod
    def get_user_hash_id(client_ip: str, user_agent: str) -> str:
        """Returns a stable, anonymous hash for a given IP and User-Agent."""
        return hashlib.sha256(f"{client_ip}-{user_agent}".encode()).hexdigest()

    @staticmethod
    async def get_or_create_session(user_hash_id: str) -> Tuple[str, list[dict]]:
        """
        Looks up an existing active session (within 24 hours), or creates a new one.
        Returns a tuple: (session_id, history_messages, conversation_summary)
        """
        session_id: Optional[str] = None
        history: list[dict] = []
        conversation_summary: Optional[str] = None

        try:
            async with aiosqlite.connect(DB_FILE, timeout=15.0) as db:
                cursor = await db.execute(
                    """
                    SELECT session_id, last_active_at, id, conversation_summary FROM session
                    WHERE user_hash_id = ?
                    ORDER BY last_active_at DESC LIMIT 1
                    """,
                    (user_hash_id,),
                )
                row = await cursor.fetchone()

                if row:
                    db_session_id_str, last_active_str, internal_id, conv_summary = row
                    if last_active_str:
                        try:
                            clean_str = last_active_str.replace("Z", "+00:00")
                            last_active = datetime.fromisoformat(clean_str)
                            if last_active.tzinfo is None:
                                last_active = last_active.replace(tzinfo=timezone.utc)

                            if datetime.now(timezone.utc) - last_active < timedelta(hours=24):
                                session_id = db_session_id_str
                                logger.info(f"Resuming session {session_id[:8]}...")

                                hist_cur = await db.execute(
                                    """
                                    SELECT role, content FROM message
                                    WHERE session_id = ?
                                    ORDER BY created_at ASC
                                    """,
                                    (internal_id,),
                                )
                                for r_role, r_content in await hist_cur.fetchall():
                                    if r_content is not None:
                                        history.append({"role": r_role, "content": r_content})

                                await db.execute(
                                    "UPDATE session SET last_active_at = ? WHERE session_id = ?",
                                    (datetime.now(timezone.utc).isoformat(), session_id),
                                )
                                await db.commit()
                                
                                if conv_summary:
                                    conversation_summary = conv_summary
                                    
                        except Exception as e:
                            logger.error(f"Time parsing error {e}, generating new session")

                if not session_id:
                    session_id = str(uuid.uuid4())
                    logger.info(f"New session {session_id[:8]}...")
                    now_str = datetime.now(timezone.utc).isoformat()
                    await db.execute(
                        "INSERT INTO session (session_id, user_hash_id, last_active_at, created_at) VALUES (?, ?, ?, ?)",
                        (session_id, user_hash_id, now_str, now_str),
                    )
                    await db.commit()

        except Exception as e:
            logger.error(f"SQLite error determining session: {e}")
            if not session_id:
                session_id = str(uuid.uuid4())

        return session_id, history, conversation_summary

    @staticmethod
    async def save_message(session_id_str: str, role: str, content: str):
        """Saves a single message to the associated session."""
        try:
            async with aiosqlite.connect(DB_FILE, timeout=15.0) as db:
                cursor = await db.execute(
                    "SELECT id FROM session WHERE session_id = ?", (session_id_str,)
                )
                row = await cursor.fetchone()
                if not row:
                    logger.error(f"Cannot save message, session {session_id_str} not found.")
                    return

                await db.execute(
                    "INSERT INTO message (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                    (row[0], role, content, datetime.now(timezone.utc).isoformat()),
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to save message to DB: {e}")
