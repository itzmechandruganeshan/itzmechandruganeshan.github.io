import aiosqlite
import logging

logger = logging.getLogger(__name__)

DB_FILE = "portfolio.db"
db_connection: aiosqlite.Connection | None = None

async def init_db():
    """
    Initializes the SQLite database with WAL mode and keeps a global connection open.
    Creates session and message tables for chat persistence.
    """
    global db_connection
    try:
        db_connection = await aiosqlite.connect(DB_FILE, timeout=15.0)
        await db_connection.execute("PRAGMA journal_mode=WAL;")
        await db_connection.execute("PRAGMA synchronous=NORMAL;")
        await db_connection.execute("PRAGMA foreign_keys=ON;")

        await db_connection.execute("""
            CREATE TABLE IF NOT EXISTS session (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                user_hash_id TEXT,
                last_active_at DATETIME,
                conversation_summary TEXT,
                created_at DATETIME NOT NULL
            )
        """)
        await db_connection.execute("""
            CREATE TABLE IF NOT EXISTS message (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                FOREIGN KEY(session_id) REFERENCES session(id)
            )
        """)
        await db_connection.commit()
        logger.info("Database initialized (WAL mode, session + message tables).")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

async def close_db():
    """Closes the global database connection."""
    global db_connection
    if db_connection:
        await db_connection.close()
        logger.info("Database connection closed.")
