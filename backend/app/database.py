import aiosqlite
import logging

logger = logging.getLogger(__name__)

DB_FILE = "portfolio.db"


async def init_db():
    """
    Initializes the SQLite database with WAL mode.
    Creates session and message tables for chat persistence.
    """
    try:
        async with aiosqlite.connect(DB_FILE, timeout=15.0) as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("PRAGMA synchronous=NORMAL;")
            await db.execute("PRAGMA foreign_keys=ON;")

            await db.execute("""
                CREATE TABLE IF NOT EXISTS session (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL UNIQUE,
                    user_hash_id TEXT,
                    last_active_at DATETIME,
                    conversation_summary TEXT,
                    created_at DATETIME NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS message (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES session(id)
                )
            """)
            await db.commit()
            logger.info("Database initialized (WAL mode, session + message tables).")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
