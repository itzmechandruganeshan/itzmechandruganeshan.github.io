import contextlib
import logging
from typing import AsyncGenerator

from fastapi import FastAPI

from app.database import init_db
from app.websocket import router as websocket_router, manager

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifecycle manager — initializes the database on startup, cleans up on shutdown."""
    logger.info("Starting Portfolio Bot...")
    await init_db()
    yield
    logger.info("Shutting down Portfolio Bot...")
    for session_id, ws in list(manager.active_connections.items()):
        await ws.close(code=1001, reason="Server shutting down")


app = FastAPI(
    title="Portfolio Bot Backend",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(websocket_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "active_websockets": len(manager.active_connections)}
