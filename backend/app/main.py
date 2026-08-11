import contextlib
import logging
import warnings
from typing import AsyncGenerator

from fastapi import FastAPI, Request

from app.database import init_db, close_db
from app.websocket import router as websocket_router, manager
from app.graph import graph

# Suppress harmless Pydantic serialization warnings caused by LangChain's AIMessage.parsed field
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

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
    await close_db()


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

@app.post("/api/evaluate")
async def evaluate_query(request: Request):
    data = await request.json()
    initial_state = {
        "session_id": "eval_session",
        "user_message": data["query"],
        "history_list": [],
        "intent": None,
        "retrieved_context": "",
        "messages": []
    }
    state = await graph.ainvoke(initial_state)
    return {
        "actual_answer": state["messages"][-1].content,
        "retrieved_context": state.get("retrieved_context", "")
    }
